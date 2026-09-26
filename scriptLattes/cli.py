#!/usr/bin/env python
# encoding: utf-8
#
#  scriptLattes
#
#  Este programa é um software livre; você pode redistribui-lo e/ou 
#  modifica-lo dentro dos termos da Licença Pública Geral GNU como 
#  publicada pela Fundação do Software Livre (FSF); na versão 2 da 
#  Licença, ou (na sua opinião) qualquer versão.
#
#  Este programa é distribuído na esperança que possa ser util, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implicita de ADEQUAÇÂO a qualquer
#  MERCADO ou APLICAÇÃO EM PARTICULAR. Veja a
#  Licença Pública Geral GNU para maiores detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU
#  junto com este programa, se não, escreva para a Fundação do Software
#  Livre(FSF) Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
import argparse
import datetime
import os
import pathlib
import sys
import webbrowser

from scriptLattes.baixaLattes import CurriculoInvalidoError, adicionar_cv_local
from scriptLattes.diagnostico import executar_diagnostico
from scriptLattes.erros import imprimir_erro
from scriptLattes.grupo import *
from scriptLattes.util import *

EXEMPLO = os.path.join('exemplo', 'demo.config')


def executar_scriptLattes(arquivoConfiguracao):
    print("[SCRIPTLATTES INICIADO]\n")
    # os.chdir( os.path.abspath(os.path.join(arquivoConfiguracao, os.pardir)))
    tempo_inicial = datetime.datetime.now()
    novoGrupo = Grupo(arquivoConfiguracao)
    novoGrupo.imprimirListaDeTermos()
    novoGrupo.imprimirListaDeRotulos()

    diretorioDeSaida = novoGrupo.obterParametro('global-diretorio_de_saida')
    if not criarDiretorio(diretorioDeSaida):
        raise PermissionError(f'não foi possível criar a pasta de saída: {diretorioDeSaida}')

    novoGrupo.carregarDadosCVLattes() #obrigatorio
    novoGrupo.compilarListasDeItems() # obrigatorio
    novoGrupo.gerarGrafosDeColaboracoes() # obrigatorio
    novoGrupo.gerarPaginasWeb() # obrigatorio
    novoGrupo.gerarArquivosTemporarios() # obrigatorio
    novoGrupo.gerarArquivosJSONIndividuais() # gerar JSON individual por pesquisador

    # copiar css
    copiarArquivos(diretorioDeSaida)

    # finalizando o processo
    print ('\n[PARA REFERENCIAR/CITAR ESTE SOFTWARE USE] \n\
    Jesus P. Mena-Chalco & Roberto M. Cesar-Jr.\n\
    scriptLattes: An open-source knowledge extraction system from the Lattes Platform.\n\
    Journal of the Brazilian Computer Society, vol.15, n.4, páginas 31-39, 2009.\n\
    http://dx.doi.org/10.1007/BF03194511\n')

    tempo_final = datetime.datetime.now()
    tempo_decorrido = formatar_tempo_decorrido(tempo_final - tempo_inicial)
    print(f"scriptLattes executado em: {tempo_decorrido}.\n")
    return novoGrupo

def formatar_tempo_decorrido(tempo_decorrido):
    segundos = int(tempo_decorrido.total_seconds())

    if segundos < 60:
        return f"{segundos} segundos"
    elif segundos < 3600:
        minutos, segundos = divmod(segundos, 60)
        return f"{minutos} minutos e {segundos} segundos"
    else:
        horas, segundos = divmod(segundos, 3600)
        minutos, segundos = divmod(segundos, 60)
        return f"{horas} horas, {minutos} minutos e {segundos} segundos"


class _EspelhoDeSaida:
    """Duplica a saída do programa (tela + arquivo de log) sem interferir na tela."""

    def __init__(self, original, arquivo):
        self.original = original
        self.arquivo = arquivo

    def write(self, texto):
        try:
            self.original.write(texto)
        except UnicodeEncodeError:
            # console do Windows sem suporte ao caractere: não deixe a execução quebrar por isso
            codificacao = getattr(self.original, 'encoding', None) or 'utf-8'
            self.original.write(texto.encode(codificacao, 'replace').decode(codificacao))
        if '\r' not in texto:   # progresso redesenha a mesma linha: não polui o log
            try:
                self.arquivo.write(texto)
                self.arquivo.flush()
            except (OSError, ValueError):
                pass
        return len(texto)

    def flush(self):
        try:
            self.original.flush()
        except (OSError, ValueError):
            pass
        try:
            self.arquivo.flush()
        except (OSError, ValueError):
            pass

    def __getattr__(self, nome):
        # isatty, encoding, fileno, ... são repassados para a saída original
        return getattr(self.original, nome)


def _diretorio_de_saida_do_config(arquivoConfiguracao):
    """Lê 'global-diretorio_de_saida' sem depender de o config ser válido."""
    if not (arquivoConfiguracao and os.path.isfile(arquivoConfiguracao)):
        return ''
    try:
        for linha in lerLinhasDeTexto(arquivoConfiguracao):
            sem_comentario = linha.partition('#')[0]
            if '=' in sem_comentario:
                nome, _, valor = sem_comentario.partition('=')
                if nome.strip() == 'global-diretorio_de_saida':
                    return valor.strip()
    except (OSError, UnicodeDecodeError):
        return ''
    return ''


def abrir_log(arquivoConfiguracao):
    """Cria o log na pasta de saída (ou na pasta atual) e devolve o caminho."""
    candidatos = []
    diretorio = _diretorio_de_saida_do_config(arquivoConfiguracao)
    if diretorio:
        candidatos.append(os.path.join(os.path.abspath(diretorio), 'scriptlattes-log.txt'))
    candidatos.append(os.path.abspath('scriptlattes-log.txt'))

    for caminho in candidatos:
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            arquivo = open(caminho, 'w', encoding='utf-8')
            return caminho, arquivo
        except OSError:
            continue
    return None, None


def abrir_saida_no_navegador(diretorioDeSaida):
    """Abre o relatório final no navegador padrão (só em execução interativa)."""
    if not diretorioDeSaida:
        return
    pagina = os.path.join(os.path.abspath(diretorioDeSaida), 'index.html')
    alvo = pagina if os.path.isfile(pagina) else os.path.abspath(diretorioDeSaida)
    try:
        webbrowser.open(pathlib.Path(alvo).as_uri())
    except Exception as exc:                      # navegador ausente não é erro fatal
        print(f'[AVISO] Não foi possível abrir o navegador automaticamente: {exc}')


PASTA_DA_DEMONSTRACAO = 'resultado-demonstracao'


def _rodar_demonstracao(argumentos):
    """Sem nenhum grupo indicado, roda a demonstração offline.

    É o que acontece quando alguém dá duplo clique no programa: em vez de uma mensagem
    de ajuda, o usuário vê os relatórios de exemplo aparecerem em uma pasta, junto de um
    LEIA-ME explicando como rodar o grupo dele.
    """
    caminho_do_exemplo = os.path.join(ABSBASE, EXEMPLO)
    if not os.path.isfile(caminho_do_exemplo):
        construir_analisador().print_help()
        print(f'\nNenhum arquivo .config foi indicado, e a demonstração não foi encontrada em\n'
              f'  {caminho_do_exemplo}\n'
              f'Para rodar o seu grupo:  {nome_do_programa()} seu-grupo.config')
        return 2

    print('=' * 70)
    print(' Nenhum grupo indicado: rodando a DEMONSTRAÇÃO com currículos de exemplo')
    print('=' * 70)
    print('Os currículos de exemplo já vêm no programa: nada é baixado da internet.')
    print(f'Os relatórios serão criados em: ./{PASTA_DA_DEMONSTRACAO}\n')

    pasta_da_demonstracao = os.path.join(os.getcwd(), PASTA_DA_DEMONSTRACAO)
    configuracao = _configuracao_da_demonstracao(caminho_do_exemplo, pasta_da_demonstracao)
    argumentos_do_pipeline = [configuracao] + (['--debug'] if argumentos.debug else [])
    if argumentos.nao_abrir:
        argumentos_do_pipeline.append('--nao-abrir')

    codigo = _executar_pipeline(argumentos_do_pipeline)

    if codigo == 0:
        print('\n' + '=' * 70)
        programa = nome_do_programa()
        print(' Para rodar o SEU grupo:')
        print(f'   - no terminal:  {programa} --assistente')
        print(f'   - com janela:   {programa} --janela')
        print(f'   - conferir o ambiente:  {programa} --diagnostico')
        print('=' * 70)
    return codigo


def _configuracao_da_demonstracao(caminho_do_exemplo, pasta_de_saida):
    """Cria o .config da demonstração na pasta de saída, apontando para os exemplos."""
    from scriptLattes.grupo import Grupo

    origem = Grupo(caminho_do_exemplo)
    parametros = [(nome, origem.obterParametro(nome)) for nome, _ in origem.listaDeParametros
                  if nome.startswith('global-') or nome.startswith('relatorio-') or nome.startswith('grafo-')]

    os.makedirs(pasta_de_saida, exist_ok=True)
    destino = os.path.join(pasta_de_saida, 'demonstracao.config')
    preferidos = {
        'global-nome_do_grupo': 'Demonstração (currículos de exemplo)',
        'global-arquivo_de_entrada': os.path.join(ABSBASE, 'exemplo', 'demo-lattes', 'demo.list'),
        'global-diretorio_de_saida': pasta_de_saida,
        'global-diretorio_de_armazenamento_de_cvs': os.path.join(ABSBASE, 'exemplo',
                                                                 'demo-lattes', 'cache'),
        'global-itens_desde_o_ano': '1900',
        'global-itens_ate_o_ano': 'hoje',
    }
    with open(destino, 'w', encoding='utf-8') as arquivo:
        arquivo.write('# Configuração da demonstração do scriptLattes (currículos de exemplo).\n'
                      f'# Criada automaticamente em {destino}\n\n')
        for nome, valor in parametros:
            arquivo.write(f'{nome} = {_valor_para_o_config(preferidos.get(nome, valor))}\n')
    for nome, valor in preferidos.items():
        if nome not in dict(parametros):
            with open(destino, 'a', encoding='utf-8') as arquivo:
                arquivo.write(f'{nome} = {_valor_para_o_config(valor)}\n')
    return destino


def _valor_para_o_config(valor):
    """`obterParametro` devolve 1/0 para sim/nao; ao gravar, voltamos para sim/nao."""
    if valor == 1:
        return 'sim'
    if valor == 0:
        return 'nao'
    return valor


def _executar_pipeline(argumentos):
    return main(argumentos)


def _adicionar_cv(argumentos):
    """Importa currículos salvos pelo navegador para a pasta de cache (sem baixar nada)."""
    cache = argumentos.cache or _diretorio_de_cache_do_config(argumentos.configuracao) or './cache/'
    if not os.path.exists(argumentos.adicionar_cv):
        return imprimir_erro(FileNotFoundError(
            f'arquivo ou pasta não encontrado: {argumentos.adicionar_cv}'))

    print(f'[ADICIONAR CV] Importando de: {argumentos.adicionar_cv}')
    print(f'               Para a pasta de cache: {os.path.abspath(cache)}')

    adicionados, problemas = adicionar_cv_local(argumentos.adicionar_cv, cache,
                                               sobrescrever=argumentos.sobrescrever)
    for caminho, identificador in adicionados:
        print(f'  [OK] {os.path.basename(caminho)} -> {identificador}')

    if problemas:
        for caminho, motivo in problemas:
            print(f'  [FALHA] {os.path.basename(caminho)}: {motivo}')
        return imprimir_erro(CurriculoInvalidoError(
            f'{len(problemas)} arquivo(s) não puderam ser importados'))

    print(f'\n[PRONTO] {len(adicionados)} currículo(s) disponíveis em cache. '
          f'Rode o scriptLattes normalmente para usá-los.')
    return 0


def _parametro_do_config(arquivo_configuracao, chave):
    """Lê um parâmetro de um .config sem depender de o arquivo estar válido."""
    if not (arquivo_configuracao and os.path.isfile(arquivo_configuracao)):
        return ''
    try:
        for linha in lerLinhasDeTexto(arquivo_configuracao):
            sem_comentario = linha.partition('#')[0]
            if '=' in sem_comentario:
                nome, _, valor = sem_comentario.partition('=')
                if nome.strip() == chave:
                    return valor.strip()
    except (OSError, UnicodeDecodeError):
        return ''
    return ''


def _diretorio_de_saida_do_config(arquivo_configuracao):
    return _parametro_do_config(arquivo_configuracao, 'global-diretorio_de_saida')


def _diretorio_de_cache_do_config(arquivo_configuracao):
    return _parametro_do_config(arquivo_configuracao, 'global-diretorio_de_armazenamento_de_cvs')


def abrir_log(arquivoConfiguracao):
    """Cria o log na pasta de saída (ou na pasta atual) e devolve o caminho."""
    candidatos = []
    diretorio = _diretorio_de_saida_do_config(arquivoConfiguracao)
    if diretorio:
        candidatos.append(os.path.join(os.path.abspath(diretorio), 'scriptlattes-log.txt'))
    candidatos.append(os.path.abspath('scriptlattes-log.txt'))

    for caminho in candidatos:
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            arquivo = open(caminho, 'w', encoding='utf-8')
            return caminho, arquivo
        except OSError:
            continue
    return None, None


def construir_analisador():
    analisador = argparse.ArgumentParser(
        prog='scriptLattes.py',
        description='Gera relatórios de produção científica a partir de currículos Lattes.',
        epilog=f'Exemplo que já funciona, sem configurar nada:  python scriptLattes.py {EXEMPLO}')
    analisador.add_argument('configuracao', nargs='?',
                            help='arquivo .config do grupo (ex.: meu-grupo.config)')
    analisador.add_argument('--assistente', action='store_true',
                            help='cria o .config e o .list do seu grupo respondendo a algumas '
                                 'perguntas (não precisa editar arquivos)')
    analisador.add_argument('--janela', action='store_true',
                            help='abre a interface gráfica (requer janela/Tkinter)')
    analisador.add_argument('--diagnostico', action='store_true',
                            help='verifica Python, dependências, Chrome, ChromeDriver, rede e cache, e sai')
    analisador.add_argument('--adicionar-cv', metavar='CAMINHO', dest='adicionar_cv',
                            help='importa currículos em HTML salvos pelo navegador '
                                 '(um arquivo ou uma pasta) para a pasta de cache')
    analisador.add_argument('--cache', metavar='PASTA',
                            help='pasta de cache a usar em --adicionar-cv '
                                 '(padrão: a do .config ou ./cache/)')
    analisador.add_argument('--sobrescrever', action='store_true',
                            help='em --adicionar-cv, substituir currículos já existentes no cache')
    analisador.add_argument('--debug', action='store_true',
                            help='mostra o detalhe técnico completo (traceback) quando ocorre um erro')
    analisador.add_argument('--nao-abrir', action='store_true',
                            help='não abrir o relatório no navegador ao final')
    return analisador


def main(argv=None):
    argumentos = construir_analisador().parse_args(sys.argv[1:] if argv is None else argv)

    if argumentos.assistente:
        # A entrada pode vir de um terminal ou de um script (feito de propósito: é assim
        # que times automatizam a criação do .config). Se a entrada terminar sem nenhum
        # currículo, o próprio assistente explica o que faltou.
        from scriptLattes.assistente import main as assistente
        # '--rodar' faz o assistente perguntar se é para gerar os relatórios na sequência
        return assistente(['--pasta', os.getcwd(), '--rodar'])

    if argumentos.janela:
        from scriptLattes.janela import abrir_janela
        return abrir_janela()

    if argumentos.diagnostico:
        return executar_diagnostico(argumentos.configuracao)

    if argumentos.adicionar_cv:
        return _adicionar_cv(argumentos)

    if not argumentos.configuracao:
        return _rodar_demonstracao(argumentos)

    if not os.path.isfile(argumentos.configuracao):
        return imprimir_erro(FileNotFoundError(
            f'arquivo de configuração não encontrado: {argumentos.configuracao}'),
            debug=argumentos.debug)

    caminho_do_log, arquivo_de_log = abrir_log(argumentos.configuracao)
    stdout, stderr = sys.stdout, sys.stderr
    if arquivo_de_log:
        sys.stdout = _EspelhoDeSaida(stdout, arquivo_de_log)
        sys.stderr = _EspelhoDeSaida(stderr, arquivo_de_log)

    try:
        grupo = executar_scriptLattes(argumentos.configuracao)
        diretorioDeSaida = grupo.obterParametro('global-diretorio_de_saida')
        escreverLeiaMe(diretorioDeSaida, grupo.obterParametro('global-nome_do_grupo'))
        print(f'[PRONTO] Relatórios em: {os.path.abspath(diretorioDeSaida)}')
        print(f'         Comece abrindo o arquivo index.html dessa pasta.')
        if caminho_do_log:
            print(f'         Log desta execução: {caminho_do_log}')
        if not argumentos.nao_abrir and sys.stdout.isatty():
            abrir_saida_no_navegador(diretorioDeSaida)
        if getattr(grupo, 'membrosComFalha', None):
            nomes = ', '.join(nome for nome, _, _ in grupo.membrosComFalha)
            print(f'[ATENÇÃO] {len(grupo.membrosComFalha)} currículo(s) ficaram de fora dos relatórios: {nomes}')
            return 3
        return 0
    except BaseException as excecao:              # inclui KeyboardInterrupt
        return imprimir_erro(excecao, caminho_do_log=caminho_do_log, debug=argumentos.debug)
    finally:
        sys.stdout, sys.stderr = stdout, stderr
        if arquivo_de_log:
            arquivo_de_log.close()

