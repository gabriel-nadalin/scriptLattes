"""Testes da camada de mensagens de erro (scriptLattes/erros.py)."""
import unittest

from scriptLattes.erros import (CODIGO_AMBIENTE, CODIGO_ENTRADA, CODIGO_INESPERADO,
                                CODIGO_INTERROMPIDO, classificar, imprimir_erro)


class TestClassificacaoDeErros(unittest.TestCase):
    def test_arquivo_ausente_e_erro_de_entrada(self):
        erro = classificar(FileNotFoundError("[Errno 2] No such file: 'meu.config'"))
        self.assertEqual(CODIGO_ENTRADA, erro.codigo)
        self.assertTrue(erro.solucoes)

    def test_chromedriver_ausente_e_erro_de_ambiente(self):
        erro = classificar(FileNotFoundError('ChromeDriver não encontrado em: ./chromedriver'))
        self.assertEqual(CODIGO_AMBIENTE, erro.codigo)
        self.assertIn('ChromeDriver', erro.titulo)

    def test_permissao_de_escrita(self):
        erro = classificar(PermissionError('sem permissão em /saida'))
        self.assertEqual(CODIGO_ENTRADA, erro.codigo)

    def test_codificacao_errada_explica_como_salvar_em_utf8(self):
        erro = classificar(UnicodeDecodeError('utf-8', b'\xe9', 0, 1, 'invalid start byte'))
        self.assertEqual(CODIGO_ENTRADA, erro.codigo)
        self.assertTrue(any('UTF-8' in solucao for solucao in erro.solucoes))

    def test_dependencia_ausente_sugere_lancador(self):
        excecao = ModuleNotFoundError("No module named 'selenium'")
        excecao.name = 'selenium'
        erro = classificar(excecao)
        self.assertEqual(CODIGO_AMBIENTE, erro.codigo)
        self.assertIn('selenium', erro.titulo)
        self.assertTrue(any('executar' in solucao for solucao in erro.solucoes))

    def test_selenium_ausente_no_runtime(self):
        erro = classificar(RuntimeError('Selenium não está instalado, mas é necessário para baixar'))
        self.assertEqual(CODIGO_AMBIENTE, erro.codigo)

    def test_falha_do_navegador(self):
        # as exceções do selenium são reconhecidas pelo nome, sem precisar importá-lo
        classe = type('WebDriverException', (Exception,), {})
        erro = classificar(classe('chrome not reachable'))
        self.assertEqual(CODIGO_AMBIENTE, erro.codigo)
        self.assertIn('navegador', erro.titulo)

    def test_incompatibilidade_entre_chrome_e_chromedriver(self):
        classe = type('SessionNotCreatedException', (Exception,), {})
        erro = classificar(classe('session not created: This version of ChromeDriver only '
                                  'supports Chrome version 150'))
        self.assertEqual(CODIGO_AMBIENTE, erro.codigo)
        self.assertIn('versões diferentes', erro.titulo)
        self.assertTrue(any('chromedriver' in solucao.lower() for solucao in erro.solucoes))

    def test_sem_internet(self):
        classe = type('URLError', (Exception,), {})
        erro = classificar(classe('<urlopen error>'))
        self.assertEqual(CODIGO_AMBIENTE, erro.codigo)

    def test_erro_inesperado_manda_usar_debug(self):
        erro = classificar(ValueError('algo estranho'))
        self.assertEqual(CODIGO_INESPERADO, erro.codigo)
        self.assertTrue(any('--debug' in solucao for solucao in erro.solucoes))

    def test_interrupcao_do_usuario(self):
        self.assertEqual(CODIGO_INTERROMPIDO, imprimir_erro(KeyboardInterrupt()))


class TestImpressaoDeErro(unittest.TestCase):
    def test_imprime_mensagem_acionavel_e_devolve_codigo(self):
        import io
        import contextlib
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            codigo = imprimir_erro(FileNotFoundError('list não encontrada'))
        texto = saida.getvalue()
        self.assertEqual(CODIGO_ENTRADA, codigo)
        self.assertIn('[ERRO]', texto)
        self.assertIn('O que fazer:', texto)
        self.assertNotIn('Traceback', texto)

    def test_debug_mostra_traceback(self):
        import contextlib
        import io
        saida, erros = io.StringIO(), io.StringIO()
        try:
            raise ValueError('detalhe tecnico')
        except ValueError as excecao:
            with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erros):
                imprimir_erro(excecao, debug=True)
        self.assertIn('Traceback', erros.getvalue())
        self.assertIn('detalhe tecnico', erros.getvalue())


if __name__ == '__main__':
    unittest.main()
