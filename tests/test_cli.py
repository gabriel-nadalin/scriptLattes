"""Testes da linha de comando e da leitura de arquivos de entrada.

Cobrem o que um usuário sem experiência encontra primeiro: mensagens de erro no lugar
de tracebacks, códigos de saída estáveis e arquivos .config/.list salvos em UTF-8
(inclusive no Windows, onde a codificação local é cp1252).
"""
import os
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(RAIZ, 'scriptLattes.py')


def executar(argumentos, cwd=RAIZ):
    return subprocess.run([sys.executable, SCRIPT] + argumentos,
                          cwd=cwd, capture_output=True, text=True, timeout=300)


class TestLinhaDeComando(unittest.TestCase):
    def test_config_ausente_mostra_erro_amigavel(self):
        resultado = executar(['nao-existe.config'])
        self.assertEqual(2, resultado.returncode)
        self.assertIn('[ERRO]', resultado.stdout)
        self.assertIn('O que fazer:', resultado.stdout)
        self.assertNotIn('Traceback', resultado.stdout)
        self.assertNotIn('Traceback', resultado.stderr)

    def test_sem_argumentos_roda_a_demonstracao_offline(self):
        """Duplo clique no programa não pode terminar em mensagem de ajuda: roda o exemplo."""
        with tempfile.TemporaryDirectory() as pasta:
            resultado = executar(['--nao-abrir'], cwd=pasta)
            saida = os.path.join(pasta, 'resultado-demonstracao')

            self.assertEqual(0, resultado.returncode, resultado.stdout[-1500:])
            self.assertIn('DEMONSTRAÇÃO', resultado.stdout)
            self.assertTrue(os.path.isfile(os.path.join(saida, 'index.html')))
            self.assertTrue(os.path.isfile(os.path.join(saida, 'LEIA-ME.txt')))
            self.assertEqual(3, len(os.listdir(os.path.join(saida, 'json'))))
            # os exemplos ficam no programa, mas os relatórios saem na pasta do usuário
            self.assertTrue(os.listdir(os.path.join(saida, 'css')))

    def test_config_da_demonstracao_grava_sim_e_nao(self):
        """`obterParametro` devolve 1/0, e o .config precisa voltar com sim/nao.

        Gravar o número fazia a releitura tratar '0' como verdadeiro (string não vazia),
        ligando o filtro por termos sem lista de termos.
        """
        from scriptLattes.cli import _configuracao_da_demonstracao
        from scriptLattes.util import ABSBASE

        with tempfile.TemporaryDirectory() as pasta:
            caminho = _configuracao_da_demonstracao(
                os.path.join(ABSBASE, 'exemplo', 'demo.config'), pasta)
            with open(caminho, encoding='utf-8') as arquivo:
                texto = arquivo.read()

        self.assertIn('global-identificar_producoes_por_termos = nao', texto)
        self.assertIn('global-normalizacao = sim', texto)
        self.assertNotIn('= 0\n', texto)
        self.assertNotIn('= 1\n', texto)

    def test_lista_de_membros_ausente(self):
        with tempfile.TemporaryDirectory() as pasta:
            config = os.path.join(pasta, 'x.config')
            with open(config, 'w', encoding='utf-8') as arquivo:
                arquivo.write('global-arquivo_de_entrada = ./lista-que-nao-existe.list\n'
                              f'global-diretorio_de_saida = {os.path.join(pasta, "saida")}\n')
            resultado = executar([config])
        self.assertEqual(2, resultado.returncode)
        self.assertIn('[ERRO]', resultado.stdout)
        self.assertNotIn('Traceback', resultado.stderr)

    def test_diagnostico_pela_linha_de_comando(self):
        resultado = executar(['--diagnostico'])
        self.assertIn(resultado.returncode, (0, 3))
        self.assertIn('DIAGNÓSTICO DO AMBIENTE', resultado.stdout)

    def test_ajuda_lista_as_opcoes(self):
        resultado = executar(['--help'])
        self.assertEqual(0, resultado.returncode)
        for opcao in ('--diagnostico', '--debug', '--nao-abrir', 'configuracao'):
            self.assertIn(opcao, resultado.stdout)

    def test_debug_mostra_detalhe_tecnico(self):
        resultado = executar(['--debug', 'nao-existe.config'])
        self.assertEqual(2, resultado.returncode)
        self.assertIn('FileNotFoundError', resultado.stderr)

    def test_sem_debug_nao_polui_o_erro_com_detalhe_tecnico(self):
        resultado = executar(['nao-existe.config'])
        self.assertEqual('', resultado.stderr)


class TestEntradaEmUtf8(unittest.TestCase):
    """O .config e o .list com acentos devem ser lidos sem depender do locale do sistema."""

    def _config_de_teste(self, pasta, nome_do_membro):
        pasta_cache = os.path.join(pasta, 'cache')
        os.makedirs(pasta_cache, exist_ok=True)
        lista = os.path.join(pasta, 'grupo.list')
        with open(lista, 'w', encoding='utf-8') as arquivo:
            arquivo.write(f'1234567890123456 , {nome_do_membro}\n')
        config = os.path.join(pasta, 'grupo.config')
        with open(config, 'w', encoding='utf-8') as arquivo:
            arquivo.write(f'global-nome_do_grupo = Grupo com acentuação\n'
                          f'global-arquivo_de_entrada = {lista}\n'
                          f'global-diretorio_de_armazenamento_de_cvs = {pasta_cache}\n'
                          f'global-diretorio_de_saida = {os.path.join(pasta, "saida")}\n')
        return config

    def test_nome_acentuado_no_list_e_no_config(self):
        from scriptLattes.grupo import Grupo
        nome = 'José Antônio Gonçalves Júnior'
        with tempfile.TemporaryDirectory() as pasta:
            config = self._config_de_teste(pasta, nome)
            grupo = Grupo(config)
        self.assertEqual('Grupo com acentuação', grupo.obterParametro('global-nome_do_grupo'))
        self.assertEqual([nome], [membro.nomeInicial for membro in grupo.listaDeMembros])

    def test_aviso_quando_o_arquivo_nao_esta_em_utf8(self):
        import contextlib
        import io
        from scriptLattes.util import lerLinhasDeTexto
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, 'latin1.list')
            with open(caminho, 'wb') as arquivo:
                arquivo.write('José Antônio, João\n'.encode('cp1252'))
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                linhas = lerLinhasDeTexto(caminho)
        self.assertEqual(1, len(linhas))
        self.assertIn('AVISO', saida.getvalue())
        self.assertIn('José Antônio', linhas[0])


if __name__ == '__main__':
    unittest.main()
