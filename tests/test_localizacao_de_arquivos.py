"""Testes de localização de arquivos e diretórios.

O programa tem de funcionar rodando de qualquer pasta: os arquivos que o acompanham
(css, js, tabelas de aliases, exemplos) ficam no projeto, e não na pasta de execução.
"""

import os
import shutil
import tempfile
import unittest

from scriptLattes.grupo import Grupo
from scriptLattes.util import ABSBASE, buscarArquivo, buscarDiretorio, diretorio_do_projeto

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDiretorioDoProjeto(unittest.TestCase):
    def test_aponta_para_a_raiz_do_projeto(self):
        self.assertEqual(RAIZ, diretorio_do_projeto())
        self.assertTrue(os.path.isfile(os.path.join(ABSBASE, 'css', 'scriptLattes.css'))
                        or os.path.isdir(os.path.join(ABSBASE, 'css')))

    def test_nao_depende_da_pasta_de_execucao(self):
        pasta = tempfile.mkdtemp()
        anterior = os.getcwd()
        try:
            os.chdir(pasta)
            self.assertEqual(RAIZ, diretorio_do_projeto())
        finally:
            os.chdir(anterior)
            shutil.rmtree(pasta, ignore_errors=True)


class TestBuscarArquivo(unittest.TestCase):
    def test_encontra_arquivo_ao_lado_do_config(self):
        with tempfile.TemporaryDirectory() as pasta:
            lista = os.path.join(pasta, 'grupo.list')
            open(lista, 'w', encoding='utf-8').close()
            config = os.path.join(pasta, 'grupo.config')
            open(config, 'w', encoding='utf-8').close()

            encontrado = buscarArquivo('./grupo.list', config)
            self.assertEqual(os.path.abspath(lista), encontrado)

    def test_encontra_arquivo_que_acompanha_o_programa(self):
        encontrado = buscarArquivo('exemplo/demo-lattes/demo.list')
        self.assertTrue(os.path.isfile(encontrado))

    def test_caminho_vazio_nao_quebra(self):
        self.assertEqual('', buscarArquivo(''))
        self.assertEqual('', buscarArquivo(None))

    def test_arquivo_inexistente_devolve_caminho_para_a_mensagem_de_erro(self):
        caminho = buscarArquivo('lista-que-nao-existe.list')
        self.assertTrue(caminho.endswith('lista-que-nao-existe.list'))


class TestBuscarDiretorio(unittest.TestCase):
    def test_encontra_o_cache_do_projeto_mesmo_de_outra_pasta(self):
        pasta = tempfile.mkdtemp()
        anterior = os.getcwd()
        try:
            os.chdir(pasta)
            encontrado = buscarDiretorio('./cache/', os.path.join(RAIZ, 'exemplo', 'demo.config'))
        finally:
            os.chdir(anterior)
            shutil.rmtree(pasta, ignore_errors=True)
        self.assertEqual(os.path.join(RAIZ, 'cache'), encontrado)

    def test_diretorio_inexistente_e_criado_na_pasta_de_execucao(self):
        with tempfile.TemporaryDirectory() as pasta:
            anterior = os.getcwd()
            try:
                os.chdir(pasta)
                encontrado = buscarDiretorio('./cache-de-teste/')
            finally:
                os.chdir(anterior)
            self.assertEqual(os.path.join(pasta, 'cache-de-teste'), encontrado)

    def test_caminho_absoluto_e_preservado(self):
        with tempfile.TemporaryDirectory() as pasta:
            self.assertEqual(os.path.normpath(pasta), buscarDiretorio(pasta))


class TestParametrosBooleanos(unittest.TestCase):
    """'sim'/'nao' e '1'/'0' precisam significar a mesma coisa.

    `obterParametro` devolve 1/0; um .config que gravasse o número fazia o programa
    interpretar '0' (string não vazia) como ligado.
    """

    def _config(self, pasta, valor):
        lista = os.path.join(pasta, 'g.list')
        with open(lista, 'w', encoding='utf-8') as arquivo:
            arquivo.write('1111111111111111 , Ana\n')
        config = os.path.join(pasta, 'g.config')
        with open(config, 'w', encoding='utf-8') as arquivo:
            arquivo.write(f'global-arquivo_de_entrada = {lista}\n'
                          f'global-diretorio_de_armazenamento_de_cvs = {pasta}/cache\n'
                          f'global-identificar_producoes_por_termos = {valor}\n')
        return config

    def test_nao_e_zero_significam_desligado(self):
        for valor in ('nao', 'não', '0', 'false'):
            with self.subTest(valor=valor):
                with tempfile.TemporaryDirectory() as pasta:
                    grupo = Grupo(self._config(pasta, valor))
                self.assertEqual(0, grupo.obterParametro('global-identificar_producoes_por_termos'))

    def test_sim_e_um_significam_ligado(self):
        for valor in ('sim', '1', 'true'):
            with self.subTest(valor=valor):
                with tempfile.TemporaryDirectory() as pasta:
                    grupo = Grupo(self._config(pasta, valor))
                self.assertEqual(1, grupo.obterParametro('global-identificar_producoes_por_termos'))

    def test_filtro_ligado_sem_lista_de_termos_apenas_avisa(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as pasta:
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                grupo = Grupo(self._config(pasta, 'sim'))
            self.assertIn('filtro por termos está ligado', saida.getvalue())
            self.assertEqual({}, grupo.dicionarioDeTermos)


if __name__ == '__main__':
    unittest.main()
