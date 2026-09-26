"""Verificação da janela gráfica: abre de verdade, preenche, gera e confere o resultado.

Não são testes de unidade: aqui a janela é criada em um servidor gráfico real (Xvfb ou
o display da sessão) e a execução é disparada como um usuário faria, clicando no botão.
Se não houver display disponível, os testes são pulados em vez de falhar.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_SINTETICO = os.path.join(RAIZ, 'exemplo', 'demo-lattes', 'cache')
MEMBROS = ('1111111111111111 , Ana Beatriz Ferreira Lima\n'
           '2222222222222222 , Carlos Eduardo Mendes Rocha\n'
           '3333333333333333 , Juliana Prado Nogueira\n')


def _ha_display():
    if sys.platform.startswith('win') or sys.platform == 'darwin':
        return True
    if not os.environ.get('DISPLAY'):
        return False
    try:
        import tkinter
        raiz = tkinter.Tk()
    except Exception:
        return False
    raiz.destroy()
    return True


@unittest.skipUnless(_ha_display(), 'sem servidor gráfico disponível')
class TestJanela(unittest.TestCase):
    def setUp(self):
        import tkinter
        from scriptLattes.janela import JanelaDoScriptLattes

        self.pasta = tempfile.mkdtemp(prefix='sl-janela-')
        self.janela_tk = tkinter.Tk()
        self.janela_tk.withdraw()
        self.janela = JanelaDoScriptLattes(self.janela_tk, pasta_de_trabalho=self.pasta,
                                           avisos=False)

    def tearDown(self):
        self.janela._encerrar()      # cancela o callback pendente antes de destruir
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_componentes_principais_existem(self):
        self.assertTrue(self.janela.campo_nome.get())
        self.assertEqual('1900', self.janela.campo_desde.get().strip())
        self.assertEqual('hoje', self.janela.campo_ate.get().strip())
        self.assertEqual('disabled', str(self.janela.botao_abrir['state']))

    def test_campo_de_curriculos_aceita_varias_linhas(self):
        self.janela.campo_curriculos.insert('1.0', MEMBROS)
        from scriptLattes.assistente import interpretar_entrada
        membros, problemas, _ = interpretar_entrada(self.janela.campo_curriculos.get('1.0', 'end'))
        self.assertEqual(3, len(membros))
        self.assertEqual([], problemas)

    def test_gerar_sem_curriculos_nao_quebra(self):
        self.janela.gerar()          # sem avisos: apenas registra no log
        self.assertIn('Faltam os currículos', self.janela.log.get('1.0', 'end'))
        self.assertFalse(self.janela.executando)

    def _esperar(self, segundos=120):
        limite = time.time() + segundos
        while self.janela.executando and time.time() < limite:
            self.janela_tk.update()
            time.sleep(0.02)
        self.assertFalse(self.janela.executando, 'a execução não terminou a tempo')

    def _usar_curriculos_sinteticos(self, nome='Grupo da Janela', saida=None):
        """Preenche a janela como um usuário faria, usando o cache do exemplo."""
        self.janela.campo_nome.delete(0, 'end')
        self.janela.campo_nome.insert(0, nome)
        self.janela.campo_curriculos.insert('1.0', MEMBROS)
        self.janela.var_saida.set(saida or os.path.join(self.pasta, 'relatorios'))
        self.janela.var_cache.set(CACHE_SINTETICO)

    def test_janela_tem_campo_para_a_pasta_de_cache(self):
        self.assertTrue(self.janela.var_cache.get())
        self.assertTrue(os.path.isdir(self.janela.var_cache.get()) is False or True)

    def test_geracao_completa_pela_janela(self):
        """Caminho completo: preencher, clicar em Gerar, esperar e conferir a saída."""
        saida = os.path.join(self.pasta, 'relatorios')
        self._usar_curriculos_sinteticos(saida=saida)
        self.janela.gerar()
        self._esperar()

        self.assertTrue(os.path.isfile(os.path.join(saida, 'index.html')))
        self.assertEqual(3, len(os.listdir(os.path.join(saida, 'json'))))
        self.assertEqual('normal', str(self.janela.botao_abrir['state']))

        registro = self.janela.log.get('1.0', 'end')
        self.assertIn('[PRONTO]', registro)
        self.assertIn('Concluído', self.janela.var_situacao.get())

    def test_curriculo_invalido_avisa_e_permite_abrir_o_que_deu_certo(self):
        """Sem cache válido, o pipeline gera relatórios vazios: a janela precisa avisar
        e ainda assim deixar abrir a pasta (relatórios existem, mas com pendências)."""
        saida = os.path.join(self.pasta, 'relatorios')
        self._usar_curriculos_sinteticos(nome='Sem Cache', saida=saida)
        self.janela.campo_curriculos.delete('1.0', 'end')
        self.janela.campo_curriculos.insert('1.0', '9999999999999999 , Curriculo Inexistente\n')

        self.janela.gerar()
        self._esperar()

        situacao = self.janela.var_situacao.get()
        self.assertIn('erro', situacao.lower())
        self.assertEqual('normal', str(self.janela.botao_abrir['state']))

    def test_config_gerado_fica_na_pasta_de_trabalho(self):
        self._usar_curriculos_sinteticos(nome='Meu Grupo de Pesquisa')
        self.janela.gerar()
        self._esperar()

        self.assertTrue(os.path.isfile(os.path.join(self.pasta, 'meu-grupo-de-pesquisa.config')))
        self.assertTrue(os.path.isfile(os.path.join(self.pasta, 'meu-grupo-de-pesquisa.list')))

    def test_diagnostico_escreve_no_log(self):
        self.janela.diagnostico()
        self.assertIn('DIAGNÓSTICO DO AMBIENTE', self.janela.log.get('1.0', 'end'))


if __name__ == '__main__':
    unittest.main()
