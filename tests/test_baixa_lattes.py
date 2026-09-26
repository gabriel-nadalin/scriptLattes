"""Testes do módulo de download/importação de currículos (scriptLattes/baixaLattes.py).

Cobrem o que dá para testar sem navegador: validação de currículo, extração do
identificador, importação manual e escolha do ChromeDriver.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scriptLattes import baixaLattes
from scriptLattes.baixaLattes import (CurriculoInvalidoError, adicionar_cv_local,
                                      baixaCVLattes, fechar_driver, identificador_do_cv,
                                      nome_do_driver_no_sistema, obter_driver,
                                      parece_um_cv_lattes, resolver_chromedriver)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CV_SINTETICO = os.path.join(RAIZ, 'exemplo', 'demo-lattes', 'cache', '1111111111111111')


def ler(caminho):
    with open(caminho, encoding='utf-8') as arquivo:
        return arquivo.read()


class TestValidacaoDeCurriculo(unittest.TestCase):
    def test_aceita_curriculo_sintetico_do_projeto(self):
        self.assertTrue(parece_um_cv_lattes(ler(CV_SINTETICO)))

    def test_rejeita_pagina_pequena_ou_estranha(self):
        self.assertFalse(parece_um_cv_lattes('<html>página de erro</html>'))
        self.assertFalse(parece_um_cv_lattes(''))
        self.assertFalse(parece_um_cv_lattes('x' * 4000))

    def test_extrai_identificador_16_digitos(self):
        self.assertEqual('1111111111111111', identificador_do_cv(ler(CV_SINTETICO)))

    def test_extrai_identificador_de_varias_formas(self):
        casos = {
            '<span style="font-weight: bold; color: #326C99;">1234567890123456</span>': '1234567890123456',
            '<a href="http://lattes.cnpq.br/9876543210987654">cv</a>': '9876543210987654',
            '<a href="visualizacv.do?id=1234567890">cv</a>': '1234567890',
        }
        for texto, esperado in casos.items():
            self.assertEqual(esperado, identificador_do_cv(texto))

    def test_sem_identificador_devolve_vazio(self):
        self.assertEqual('', identificador_do_cv('<html>sem identificador</html>'))


class TestImportacaoManual(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.cache = os.path.join(self.pasta, 'cache')

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_importa_curriculo_e_usa_o_identificador_como_nome(self):
        origem = os.path.join(self.pasta, 'Currículo salvo do navegador.html')
        shutil.copyfile(CV_SINTETICO, origem)

        adicionados, problemas = adicionar_cv_local(origem, self.cache)

        self.assertEqual([], problemas)
        self.assertEqual(1, len(adicionados))
        self.assertTrue(os.path.isfile(os.path.join(self.cache, '1111111111111111')))

    def test_importa_pasta_inteira(self):
        adicionados, problemas = adicionar_cv_local(
            os.path.join(RAIZ, 'exemplo', 'demo-lattes', 'cache'), self.cache)
        self.assertEqual(3, len(adicionados))
        self.assertEqual([], problemas)

    def test_rejeita_arquivo_que_nao_e_curriculo(self):
        origem = os.path.join(self.pasta, 'ruim.html')
        with open(origem, 'w', encoding='utf-8') as arquivo:
            arquivo.write('<html>não é um currículo</html>')

        adicionados, problemas = adicionar_cv_local(origem, self.cache)

        self.assertEqual([], adicionados)
        self.assertEqual(1, len(problemas))
        self.assertIn('não parece um currículo', problemas[0][1])

    def test_nao_sobrescreve_sem_permissao_explicita(self):
        origem = os.path.join(self.pasta, 'cv.html')
        shutil.copyfile(CV_SINTETICO, origem)
        adicionar_cv_local(origem, self.cache)

        _, problemas = adicionar_cv_local(origem, self.cache)
        self.assertEqual(1, len(problemas))
        self.assertIn('já está no cache', problemas[0][1])

        adicionados, problemas = adicionar_cv_local(origem, self.cache, sobrescrever=True)
        self.assertEqual(1, len(adicionados))
        self.assertEqual([], problemas)

    def test_origem_inexistente(self):
        adicionados, problemas = adicionar_cv_local('/nao/existe/cv.html', self.cache)
        self.assertEqual([], adicionados)
        self.assertIn('não encontrado', problemas[0][1])


class TestChromeDriver(unittest.TestCase):
    def test_sem_caminho_usa_selenium_manager(self):
        self.assertEqual('', resolver_chromedriver(''))

    def test_caminho_explicito_inexistente_e_erro_claro(self):
        with self.assertRaises(FileNotFoundError) as contexto:
            resolver_chromedriver('./chromedriver-inexistente')
        self.assertIn('ChromeDriver', str(contexto.exception))

    def test_caminho_relativo_ao_projeto(self):
        with tempfile.TemporaryDirectory(dir=RAIZ) as pasta_relativa:
            nome = os.path.basename(pasta_relativa)
            destino = os.path.join(pasta_relativa, 'chromedriver-falso')
            open(destino, 'w').close()
            try:
                esperado = os.path.abspath(destino)
                self.assertEqual(esperado, resolver_chromedriver(os.path.join(nome, 'chromedriver-falso')))
            finally:
                os.remove(destino)

    def test_nome_do_driver_no_sistema(self):
        self.assertIn(nome_do_driver_no_sistema(), ('chromedriver', 'chromedriver.exe'))


class TestSessaoDoNavegador(unittest.TestCase):
    def test_erro_claro_quando_selenium_ausente(self):
        with patch.object(baixaLattes, 'webdriver', None):
            with self.assertRaises(RuntimeError) as contexto:
                baixaLattes.LattesRobot(driver_path='', results_dir=tempfile.mkdtemp())
        mensagem = str(contexto.exception)
        self.assertIn('Selenium', mensagem)
        self.assertIn('venv', mensagem)

    def test_erro_claro_quando_caminho_do_driver_nao_existe(self):
        with self.assertRaises(FileNotFoundError) as contexto:
            baixaLattes.LattesRobot(driver_path='./chromedriver-inexistente',
                                    results_dir=tempfile.mkdtemp())
        self.assertIn('ChromeDriver', str(contexto.exception))

    def test_sem_internet_e_sem_driver_local_explica_e_nao_abre_navegador(self):
        with patch.object(baixaLattes, 'tem_internet', return_value=False):
            with self.assertRaises(ConnectionError) as contexto:
                obter_driver(tempfile.mkdtemp(), '')
        self.assertIn('Sem conexão', str(contexto.exception))
        self.assertIn('--adicionar-cv', str(contexto.exception))

    def test_fechar_driver_e_seguro_sem_sessao(self):
        fechar_driver()   # não deve levantar exceção


class TestBaixaCVLattesComCache(unittest.TestCase):
    def test_usa_o_arquivo_já_existente_sem_abrir_navegador(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = os.path.join(pasta, '1111111111111111')
            shutil.copyfile(CV_SINTETICO, destino)

            with patch.object(baixaLattes, '__get_data') as falsa:
                caminho = baixaCVLattes('1111111111111111', pasta)

            self.assertEqual(destino, caminho)
            falsa.assert_not_called()

    def test_falha_apos_as_tentativas_traz_instrucoes(self):
        with tempfile.TemporaryDirectory() as pasta:
            with patch.object(baixaLattes, '__get_data', side_effect=lambda *a, **k: None):
                with self.assertRaises(RuntimeError) as contexto:
                    baixaCVLattes('9999999999999999', pasta, max_tentativas=2, espera=0)
        mensagem = str(contexto.exception)
        self.assertIn('Não foi possível baixar', mensagem)
        self.assertIn('--adicionar-cv', mensagem)


if __name__ == '__main__':
    unittest.main()
