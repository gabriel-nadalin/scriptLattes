#!/usr/bin/env python
# encoding: utf-8
"""Janela gráfica do scriptLattes (Tkinter, sem dependência extra).

Quatro campos e um botão: nome do grupo, currículos, período e pasta de saída. A execução
roda em uma thread para a janela não travar, e tudo o que o scriptLattes escreve aparece
na caixa de log — o mesmo conteúdo do `scriptlattes-log.txt`.
"""

import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from scriptLattes.assistente import (PADRAO_ATE, PADRAO_DESDE, Resultado, criar_projeto,
                                     interpretar_entrada, nome_de_arquivo)
from scriptLattes.erros import classificar
from scriptLattes.util import nome_do_programa

TITULO = 'scriptLattes - relatórios de produção científica'
AJUDA_CURRICULOS = ('Cole um currículo por linha: o link ou o número do Lattes '
                    '(http://lattes.cnpq.br/1234567890123456).\n'
                    'Opcionalmente, depois do número, o nome da pessoa separado por vírgula.')


class FilaDeSaida:
    """Substitui o sys.stdout durante a execução e envia o texto para a janela."""

    def __init__(self, fila):
        self.fila = fila

    def write(self, texto):
        if texto and '\r' not in texto:
            self.fila.put(texto)
        return len(texto or '')

    def flush(self):
        pass

    def isatty(self):
        return False

    def fileno(self):
        raise OSError('sem descritor de arquivo')


class JanelaDoScriptLattes:
    def __init__(self, janela, pasta_de_trabalho=None, avisos=True):
        self.janela = janela
        self.agendamento = None
        self.pasta_de_trabalho = os.path.abspath(pasta_de_trabalho or os.getcwd())
        # avisos=False permite rodar a janela sem ninguém para clicar nas caixas de
        # diálogo (útil em testes automatizados e em execução não assistida)
        self.avisos = avisos
        self.fila = queue.Queue()
        self.executando = False
        self.resultado = None

        janela.title(TITULO)
        janela.geometry('880x720')
        janela.minsize(720, 560)

        self._montar_cabecalho()
        self._montar_formulario()
        self._montar_botoes()
        self._montar_log()

        self.agendamento = janela.after(100, self._bombear_fila)
        janela.protocol('WM_DELETE_WINDOW', self._ao_fechar)

    # ------------------------------------------------------------------ layout
    def _montar_cabecalho(self):
        moldura = ttk.Frame(self.janela, padding=(12, 12, 12, 0))
        moldura.pack(fill='x')
        ttk.Label(moldura, text='Gerar relatórios a partir de currículos Lattes',
                  font=('TkDefaultFont', 13, 'bold')).pack(anchor='w')
        ttk.Label(moldura, text='Preencha os campos e clique em "Gerar relatórios". '
                                'Os currículos já baixados ficam guardados e são reaproveitados.',
                  wraplength=820, justify='left').pack(anchor='w', pady=(4, 0))

    def _montar_formulario(self):
        moldura = ttk.Frame(self.janela, padding=(12, 8, 12, 0))
        moldura.pack(fill='both', expand=True)
        moldura.columnconfigure(1, weight=1)
        moldura.rowconfigure(1, weight=3)

        ttk.Label(moldura, text='Nome do grupo:').grid(row=0, column=0, sticky='w',
                                                       pady=(0, 4), padx=(0, 8))
        self.campo_nome = ttk.Entry(moldura)
        self.campo_nome.insert(0, 'Meu Grupo')
        self.campo_nome.grid(row=0, column=1, columnspan=2, sticky='ew', pady=(0, 8))

        ttk.Label(moldura, text='Currículos Lattes:').grid(row=1, column=0, sticky='nw',
                                                           pady=(0, 4), padx=(0, 8))
        self.campo_curriculos = tk.Text(moldura, height=8, wrap='none')
        self.campo_curriculos.grid(row=1, column=1, sticky='nsew', pady=(0, 2))
        barra = ttk.Scrollbar(moldura, orient='vertical', command=self.campo_curriculos.yview)
        barra.grid(row=1, column=2, sticky='ns', pady=(0, 2))
        self.campo_curriculos.configure(yscrollcommand=barra.set)
        ttk.Label(moldura, text=AJUDA_CURRICULOS, wraplength=620,
                  justify='left').grid(row=2, column=1, columnspan=2, sticky='w', pady=(0, 8))

        ttk.Label(moldura, text='Período (ano inicial e final):').grid(row=3, column=0,
                                                                      sticky='w', padx=(0, 8))
        linha = ttk.Frame(moldura)
        linha.grid(row=3, column=1, columnspan=2, sticky='w', pady=(0, 8))
        self.campo_desde = ttk.Entry(linha, width=8)
        self.campo_desde.insert(0, PADRAO_DESDE)
        self.campo_desde.pack(side='left')
        ttk.Label(linha, text=' até ').pack(side='left')
        self.campo_ate = ttk.Entry(linha, width=8)
        self.campo_ate.insert(0, PADRAO_ATE)
        self.campo_ate.pack(side='left')
        ttk.Label(linha, text='   (use "hoje" para o ano atual)').pack(side='left')

        self.var_saida = tk.StringVar(
            value=os.path.join(self.pasta_de_trabalho, 'saida-meu-grupo'))
        ttk.Label(moldura, text='Pasta dos relatórios:').grid(row=4, column=0, sticky='w',
                                                              padx=(0, 8), pady=(0, 4))
        ttk.Entry(moldura, textvariable=self.var_saida).grid(row=4, column=1, sticky='ew', pady=(0, 4))
        ttk.Button(moldura, text='Escolher...',
                   command=lambda: self._escolher_pasta(self.var_saida)).grid(
            row=4, column=2, sticky='ew', padx=(6, 0), pady=(0, 4))

        self.var_cache = tk.StringVar(value=os.path.join(self.pasta_de_trabalho, 'cache'))
        ttk.Label(moldura, text='Pasta de cache:').grid(row=5, column=0, sticky='w',
                                                        padx=(0, 8), pady=(0, 4))
        ttk.Entry(moldura, textvariable=self.var_cache).grid(row=5, column=1, sticky='ew', pady=(0, 4))
        ttk.Button(moldura, text='Escolher...',
                   command=lambda: self._escolher_pasta(self.var_cache)).grid(
            row=5, column=2, sticky='ew', padx=(6, 0), pady=(0, 4))
        ttk.Label(moldura, text='A pasta de cache guarda cada currículo baixado: a segunda '
                                'execução é bem mais rápida e funciona sem internet.',
                  wraplength=620, justify='left').grid(row=6, column=1, columnspan=2,
                                                       sticky='w', pady=(0, 6))

    def _montar_botoes(self):
        moldura = ttk.Frame(self.janela, padding=(12, 0, 12, 6))
        moldura.pack(fill='x')

        self.botao_gerar = ttk.Button(moldura, text='Gerar relatórios', command=self.gerar)
        self.botao_gerar.pack(side='left')
        self.botao_diagnostico = ttk.Button(moldura, text='Verificar ambiente',
                                            command=self.diagnostico)
        self.botao_diagnostico.pack(side='left', padx=(6, 0))
        ttk.Button(moldura, text='Como conseguir os currículos?',
                   command=self._ajuda_curriculos).pack(side='left', padx=(6, 0))

        self.botao_abrir = ttk.Button(moldura, text='Abrir pasta de relatórios',
                                      command=self._abrir_saida, state='disabled')
        self.botao_abrir.pack(side='right')

        self.barra = ttk.Progressbar(self.janela, mode='indeterminate')
        self.barra.pack(fill='x', padx=12)
        self.var_situacao = tk.StringVar(value='Pronto.')
        ttk.Label(self.janela, textvariable=self.var_situacao, padding=(12, 4)).pack(anchor='w')

    def _montar_log(self):
        moldura = ttk.Frame(self.janela, padding=(12, 0, 12, 12))
        moldura.pack(fill='both', expand=True)
        ttk.Label(moldura, text='Andamento e mensagens de erro:').pack(anchor='w')
        self.log = tk.Text(moldura, height=12, wrap='word', background='#101418',
                           foreground='#e6e6e6', insertbackground='#e6e6e6')
        self.log.pack(side='left', fill='both', expand=True)
        barra = ttk.Scrollbar(moldura, orient='vertical', command=self.log.yview)
        barra.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=barra.set, state='disabled')

    # -------------------------------------------------------------- utilidades
    def _escrever(self, texto):
        self.log.configure(state='normal')
        self.log.insert('end', texto)
        self.log.see('end')
        self.log.configure(state='disabled')

    def _bombear_fila(self):
        """Único consumidor da fila: escreve o texto e reconhece o fim da execução.

        Com dois consumidores (um para o texto e outro para o fim), um podia roubar o
        aviso de término do outro e a janela ficava presa em "Gerando relatórios..."."""
        try:
            while True:
                item = self.fila.get_nowait()
                if isinstance(item, tuple) and item and item[0] == '__FIM__':
                    self._terminou(item[1])
                    continue
                self._escrever(item)
        except queue.Empty:
            pass
        self.agendamento = self.janela.after(100, self._bombear_fila)

    def _escolher_pasta(self, variavel):
        escolhida = filedialog.askdirectory(title='Escolha a pasta',
                                            initialdir=self.pasta_de_trabalho)
        if escolhida:
            variavel.set(escolhida)

    def _ajuda_curriculos(self):
        self._mensagem(
            'info', 'Como conseguir o número do currículo',
            '1) Abra o currículo da pessoa no site do Lattes (http://lattes.cnpq.br).\n'
            '2) Copie o endereço da página: ele termina com o número do currículo,\n'
            '   por exemplo http://lattes.cnpq.br/1234567890123456.\n'
            '3) Cole esse endereço (ou só o número) no campo "Currículos Lattes",\n'
            '   um por linha.\n\n'
            'Sem internet ou sem Google Chrome? Salve a página do currículo no navegador\n'
            '(Ctrl+S) e importe o arquivo com:\n'
            f'   {nome_do_programa()} --adicionar-cv arquivo.html')

    def _abrir_saida(self):
        destino = self.resultado.saida if self.resultado else self.var_saida.get()
        if not destino or not os.path.isdir(destino):
            self._mensagem('info', 'Pasta não encontrada',
                           'A pasta de relatórios ainda não foi criada.')
            return
        pagina = os.path.join(destino, 'index.html')
        alvo = pagina if os.path.isfile(pagina) else destino
        webbrowser.open('file://' + os.path.abspath(alvo))

    def _ao_fechar(self):
        if self.executando and not self._mensagem(
                'pergunta', 'Execução em andamento',
                'Os relatórios ainda estão sendo gerados. Fechar mesmo assim?\n'
                '(o que já foi baixado fica guardado em cache)'):
            return
        self._encerrar()

    def _travar_formulario(self, travado):
        estado = 'disabled' if travado else 'normal'
        for widget in (self.campo_nome, self.campo_curriculos, self.campo_desde, self.campo_ate):
            widget.configure(state=estado)
        for botao in (self.botao_gerar, self.botao_diagnostico):
            botao.configure(state=estado)
        if travado:
            self.barra.start(12)
        else:
            self.barra.stop()

    def _encerrar(self):
        """Fecha a janela de forma limpa: sem callback pendente sobrando."""
        try:
            if self.agendamento:
                self.janela.after_cancel(self.agendamento)
                self.agendamento = None
        except (tk.TclError, ValueError):
            pass
        try:
            self.janela.destroy()
        except tk.TclError:
            pass

    # ----------------------------------------------------------------- ações
    def _mensagem(self, tipo, titulo, texto, padrao=True):
        """Caixa de diálogo; sem avisos ativos, apenas devolve o padrão."""
        if not self.avisos:
            self._escrever(f'[JANELA] {titulo}: {texto.splitlines()[0]}\n')
            return padrao
        if tipo == 'erro':
            messagebox.showerror(titulo, texto)
            return padrao
        if tipo == 'aviso':
            messagebox.showwarning(titulo, texto)
            return padrao
        if tipo == 'info':
            messagebox.showinfo(titulo, texto)
            return padrao
        return messagebox.askyesno(titulo, texto)

    def gerar(self):
        if self.executando:
            return

        texto = self.campo_curriculos.get('1.0', 'end')
        membros, problemas, repetidos = interpretar_entrada(texto)
        if not membros:
            self._mensagem(
                'erro', 'Faltam os currículos',
                'Nenhum número de currículo foi reconhecido.\n\n'
                'Cole um por linha, por exemplo:\n'
                'http://lattes.cnpq.br/1234567890123456\n'
                'ou apenas 1234567890123456.')
            return

        if problemas and not self._mensagem(
                'pergunta', 'Algumas linhas não foram entendidas',
                f'{len(problemas)} linha(s) não têm um número de currículo válido e serão '
                f'ignoradas. Continuar assim mesmo?'):
            return

        pasta_de_saida = self.var_saida.get().strip() or os.path.join(
            self.pasta_de_trabalho, 'saida-' + nome_de_arquivo(self.campo_nome.get()))
        try:
            resultado = criar_projeto(
                self.campo_nome.get(), texto, pasta_de_trabalho=self.pasta_de_trabalho,
                pasta_de_saida=pasta_de_saida,
                pasta_de_cache=self.var_cache.get().strip() or os.path.join(
                    self.pasta_de_trabalho, 'cache'),
                desde=self.campo_desde.get().strip() or PADRAO_DESDE,
                ate=self.campo_ate.get().strip() or PADRAO_ATE,
                sobrescrever=True)
        except (ValueError, OSError) as excecao:
            erro = classificar(excecao)
            self._mensagem('erro', erro.titulo, f'{erro.causa}\n\n' + '\n'.join(erro.solucoes))
            return

        self.resultado = resultado
        self._escrever(f'[JANELA] Configuração criada: {resultado.config}\n')
        self._escrever(f'[JANELA] Currículos em: {resultado.cache}\n')
        self._escrever(f'[JANELA] {len(membros)} currículo(s); '
                       f'relatórios em {resultado.saida}\n\n')
        self._iniciar_execucao(resultado)

    def _iniciar_execucao(self, resultado):
        self.executando = True
        self._travar_formulario(True)
        self.botao_abrir.configure(state='disabled')
        self.var_situacao.set('Gerando relatórios... isso pode levar alguns minutos.')

        def trabalhar():
            fila = self.fila
            original_saida, original_erro = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = FilaDeSaida(fila)
            try:
                from scriptLattes.cli import main as executar_pipeline
                codigo = executar_pipeline([resultado.config, '--nao-abrir'])
            except BaseException as excecao:            # a janela nunca pode morrer por isso
                codigo = 1
                erro = classificar(excecao)
                fila.put(f'\n[ERRO] {erro.titulo}: {erro.causa}\n')
                for solucao in erro.solucoes:
                    fila.put(f'   - {solucao}\n')
            finally:
                sys.stdout, sys.stderr = original_saida, original_erro
                fila.put(('__FIM__', codigo))

        threading.Thread(target=trabalhar, daemon=True).start()

    def _relatorios_existem(self):
        if not self.resultado:
            return False
        return os.path.isfile(os.path.join(self.resultado.saida, 'index.html'))

    def _terminou(self, codigo):
        self.executando = False
        self._travar_formulario(False)

        # Havendo relatórios na pasta, o botão fica disponível mesmo quando algum
        # currículo falhou: é justamente aí que a pessoa quer abrir o que deu certo.
        if self._relatorios_existem():
            self.botao_abrir.configure(state='normal')

        if codigo == 0:
            self.var_situacao.set(f'Concluído. Relatórios em: {self.resultado.saida}')
            self._escrever(f'\n[JANELA] Concluído. Relatórios em: {self.resultado.saida}\n')
            if self._mensagem('pergunta', 'Relatórios prontos',
                              'Os relatórios foram gerados.\n\n'
                              'Abrir o index.html agora?'):
                self._abrir_saida()
            return

        if codigo == 3 and self._relatorios_existem():
            self.var_situacao.set('Relatórios gerados, mas com erros em alguns currículos '
                                  '(veja as mensagens acima).')
            self._escrever(f'\n[JANELA] Relatórios gerados em {self.resultado.saida}, '
                           f'porém com pendências (código {codigo}).\n')
            self._mensagem(
                'aviso', 'Relatórios gerados com pendências',
                'Os relatórios foram gerados, mas pelo menos um currículo não pôde ser lido e '
                'ficou de fora.\n\n'
                'O motivo e a correção estão no fim do log desta janela.')
            return

        self.var_situacao.set('Terminou com erro: veja as mensagens acima.')
        self._escrever(f'\n[JANELA] A execução terminou com código {codigo}.\n')
        self._mensagem(
            'aviso', 'Não foi possível concluir',
            'Veja a explicação na caixa de mensagens abaixo.\n\n'
            'As instruções de correção estão no fim do log desta janela.')

    def diagnostico(self):
        if self.executando:
            return
        self._escrever('\n[JANELA] Verificando o ambiente...\n')
        from scriptLattes.diagnostico import executar_diagnostico
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            codigo = executar_diagnostico()
        self._escrever(buffer.getvalue())
        if codigo == 0:
            self._escrever('[JANELA] Ambiente pronto para rodar.\n')
        else:
            self._escrever(f'[JANELA] Encontrei pendências (código {codigo}). '
                           f'Veja a lista "NÃO PODE RODAR AINDA" acima.\n')


def abrir_janela(pasta_de_trabalho=None, avisos=True):
    """Abre a janela e espera o usuário fechar. Devolve o código de saída."""
    try:
        janela = tk.Tk()
    except tk.TclError as excecao:
        print('\n[ERRO] Não consegui abrir a interface gráfica neste ambiente.')
        print(f'       Detalhe: {excecao}')
        print('       Neste computador não há tela disponível para a janela abrir.')
        print('       Alternativas:')
        print(f'         1) use o assistente no terminal:  {nome_do_programa()} --assistente')
        print('         2) no Linux, instale o suporte a janelas:  sudo apt install python3-tk')
        print('            (e rode com um ambiente gráfico ativo)')
        return 3

    try:
        ttk.Style().theme_use(ttk.Style().theme_use())
    except tk.TclError:
        pass
    JanelaDoScriptLattes(janela, pasta_de_trabalho=pasta_de_trabalho, avisos=avisos)
    janela.mainloop()
    return 0


def main(argv=None):
    import argparse
    analisador = argparse.ArgumentParser(
        prog='python -m scriptLattes.janela',
        description='Abre a janela gráfica do scriptLattes.')
    analisador.add_argument('--pasta', default=os.getcwd(),
                            help='pasta onde os arquivos serão criados (padrão: pasta atual)')
    argumentos = analisador.parse_args(argv)
    return abrir_janela(argumentos.pasta, avisos=not argumentos.sem_avisos)


if __name__ == '__main__':
    sys.exit(main())
