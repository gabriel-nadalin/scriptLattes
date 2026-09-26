"""Testes do diagnóstico de ambiente (scriptLattes/diagnostico.py)."""
import contextlib
import io
import os
import tempfile
import unittest

from scriptLattes.diagnostico import (DEPENDENCIAS, _contar_cvs, _parametro_do_config,
                                      eh_ambiente_virtual, executar_diagnostico,
                                      versao_do_chromedriver, versao_instalada)


class TestAuxiliares(unittest.TestCase):
    def test_contar_cvs_aceita_10_e_16_digitos(self):
        with tempfile.TemporaryDirectory() as pasta:
            for nome in ('1234567890', '1234567890123456'):
                open(os.path.join(pasta, nome), 'w').close()
            open(os.path.join(pasta, 'anotacoes.txt'), 'w').close()
            open(os.path.join(pasta, '12345'), 'w').close()
            self.assertEqual(2, _contar_cvs(pasta))

    def test_contar_cvs_em_pasta_inexistente(self):
        self.assertEqual(0, _contar_cvs('/pasta/que/nao/existe'))

    def test_parametro_do_config_ignora_comentarios(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, 'x.config')
            with open(caminho, 'w', encoding='utf-8') as arquivo:
                arquivo.write('# global-diretorio_de_saida = /nao/usar\n'
                              'global-diretorio_de_saida   = ./saida/   # pasta final\n')
            self.assertEqual('./saida/', _parametro_do_config(caminho, 'global-diretorio_de_saida'))

    def test_parametro_ausente_devolve_vazio(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, 'x.config')
            open(caminho, 'w', encoding='utf-8').close()
            self.assertEqual('', _parametro_do_config(caminho, 'global-nome_do_grupo'))

    def test_versao_instalada(self):
        self.assertIsNotNone(versao_instalada('networkx'))
        self.assertIsNone(versao_instalada('pacote-que-nao-existe-xyz'))

    def test_versao_do_chromedriver_sem_binario(self):
        self.assertIsNone(versao_do_chromedriver('/caminho/que/nao/existe/chromedriver'))

    def test_ambiente_virtual_e_booleano(self):
        self.assertIsInstance(eh_ambiente_virtual(), bool)

    def test_dependencias_declaram_modulo_e_essencialidade(self):
        for distribuicao, modulo, descricao, essencial in DEPENDENCIAS:
            self.assertTrue(distribuicao and modulo and descricao)
            self.assertIsInstance(essencial, bool)


class TestExecucaoDoDiagnostico(unittest.TestCase):
    def test_diagnostico_sem_config_e_informativo(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            codigo = executar_diagnostico()
        texto = saida.getvalue()
        self.assertIn(codigo, (0, 3))          # 0 = pode rodar; 3 = falta ambiente
        self.assertIn('DIAGNÓSTICO DO AMBIENTE', texto)
        self.assertIn('Interpretador Python', texto)
        self.assertIn('currículos no cache', texto)

    def test_diagnostico_com_config_inexistente(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            codigo = executar_diagnostico('/caminho/que/nao/existe.config')
        self.assertEqual(2, codigo)
        self.assertIn('NÃO PODE RODAR AINDA', saida.getvalue())


if __name__ == '__main__':
    unittest.main()
