"""Testes do assistente que cria `.config` e `.list` (scriptLattes/assistente.py).

O teste mais importante é o de ponta a ponta: os arquivos gerados pelo assistente precisam
ser aceitos pelo pipeline e produzir relatórios. É isso que garante que um usuário sem
experiência consegue chegar ao `index.html` sem editar nada à mão.
"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest

from scriptLattes.assistente import (PADRAO_ATE, PADRAO_DESDE, Resultado, criar_projeto,
                                     interpretar_entrada, montar_config, montar_lista,
                                     nome_de_arquivo, rodar_assistente)
from scriptLattes.grupo import Grupo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_SINTETICO = os.path.join(RAIZ, 'exemplo', 'demo-lattes', 'cache')

LINHAS_DE_EXEMPLO = """# meus currículos
http://lattes.cnpq.br/1111111111111111 , Ana Beatriz Ferreira Lima
2222222222222222 , Carlos Eduardo Mendes Rocha
3333333333333333
"""


class TestNomeDeArquivo(unittest.TestCase):
    def test_remove_acentos_e_espacos(self):
        self.assertEqual('grupo-de-pesquisa-em-enfermagem',
                         nome_de_arquivo('Grupo de Pesquisa em Enfermagem'))

    def test_remove_simbolos(self):
        self.assertEqual('eerp-usp-2025', nome_de_arquivo('EERP/USP -- 2025!!'))

    def test_vazio_usa_padrao(self):
        self.assertEqual('meu-grupo', nome_de_arquivo(''))
        self.assertEqual('meu-grupo', nome_de_arquivo(None))
        self.assertEqual('meu-grupo', nome_de_arquivo('!!!'))

    def test_tamanho_limitado(self):
        self.assertLessEqual(len(nome_de_arquivo('a' * 100)), 60)


class TestInterpretarEntrada(unittest.TestCase):
    def test_varias_formas_de_identificador(self):
        membros, problemas, repetidos = interpretar_entrada(
            'http://lattes.cnpq.br/1111111111111111 , Ana Beatriz\n'
            '2222222222222222;Carlos Eduardo\n'
            '3333333333333333\n'
            '1234567890\tNome Curto\n'
            'http://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=9999999999999999\n')
        self.assertEqual([], problemas)
        self.assertEqual([], repetidos)
        self.assertEqual([('1111111111111111', 'Ana Beatriz'),
                          ('2222222222222222', 'Carlos Eduardo'),
                          ('3333333333333333', ''),
                          ('1234567890', 'Nome Curto'),
                          ('9999999999999999', '')], membros)

    def test_nome_antes_do_link(self):
        membros, _, _ = interpretar_entrada(
            'Ana Maria Souza - http://lattes.cnpq.br/4444444444444444')
        self.assertEqual([('4444444444444444', 'Ana Maria Souza')], membros)

    def test_ignora_comentarios_e_linhas_vazias(self):
        membros, problemas, _ = interpretar_entrada(
            '# cabeçalho\n\n   \n1111111111111111 # comentário no fim\n')
        self.assertEqual([('1111111111111111', '')], membros)
        self.assertEqual([], problemas)

    def test_linha_invalida_vira_problema_com_numero_da_linha(self):
        membros, problemas, _ = interpretar_entrada('1111111111111111\nsem número nenhum\n')
        self.assertEqual(1, len(membros))
        self.assertEqual(2, problemas[0][0])
        self.assertIn('não encontrei um número', problemas[0][2])

    def test_repetidos_sao_avisados_e_considerados_uma_vez(self):
        membros, _, repetidos = interpretar_entrada(
            '1111111111111111 , Ana\n1111111111111111 , Ana de novo\n')
        self.assertEqual(1, len(membros))
        self.assertEqual(1, len(repetidos))

    def test_identificador_de_16_digitos_nao_e_cortado(self):
        membros, _, _ = interpretar_entrada('http://lattes.cnpq.br/1234567890123456')
        self.assertEqual('1234567890123456', membros[0][0])


class TestArquivosGerados(unittest.TestCase):
    def test_lista_no_formato_do_scriptlattes(self):
        texto = montar_lista([('1111111111111111', 'Ana Beatriz'), ('2222222222222222', '')])
        linhas = [linha for linha in texto.splitlines() if linha and not linha.startswith('#')]
        self.assertEqual(['1111111111111111 , Ana Beatriz', '2222222222222222'], linhas)

    def test_config_tem_os_parametros_essenciais(self):
        texto = montar_config('Meu Grupo', './meu.list', '/tmp/saida', '/tmp/cache',
                              desde='2000', ate='hoje')
        for esperado in ('global-nome_do_grupo                      = Meu Grupo',
                         'global-arquivo_de_entrada                 = ./meu.list',
                         'global-diretorio_de_saida                 = /tmp/saida',
                         'global-diretorio_de_armazenamento_de_cvs  = /tmp/cache',
                         'global-itens_desde_o_ano                  = 2000',
                         'global-itens_ate_o_ano                    = hoje',
                         'global-normalizacao                       = sim'):
            self.assertIn(esperado, texto)

    def test_config_usa_padroes_quando_o_periodo_nao_e_informado(self):
        texto = montar_config('G', './g.list', '/tmp/s', '/tmp/c')
        self.assertIn(f'global-itens_desde_o_ano                  = {PADRAO_DESDE}', texto)
        self.assertIn(f'global-itens_ate_o_ano                    = {PADRAO_ATE}', texto)


class TestCriarProjeto(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix='sl-assistente-')

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_cria_os_dois_arquivos(self):
        resultado = criar_projeto('Grupo de Teste', LINHAS_DE_EXEMPLO, pasta_de_trabalho=self.pasta)
        self.assertTrue(os.path.isfile(os.path.join(self.pasta, 'grupo-de-teste.config')))
        self.assertTrue(os.path.isfile(os.path.join(self.pasta, 'grupo-de-teste.list')))
        self.assertEqual(3, len(resultado.membros))
        self.assertTrue(resultado)

    def test_sem_curriculo_valido_e_erro(self):
        with self.assertRaises(ValueError):
            criar_projeto('G', 'nenhuma linha válida', pasta_de_trabalho=self.pasta)

    def test_nao_sobrescreve_por_engano(self):
        criar_projeto('G', LINHAS_DE_EXEMPLO, pasta_de_trabalho=self.pasta)
        with self.assertRaises(FileExistsError):
            criar_projeto('G', LINHAS_DE_EXEMPLO, pasta_de_trabalho=self.pasta)
        criar_projeto('G', LINHAS_DE_EXEMPLO, pasta_de_trabalho=self.pasta, sobrescrever=True)

    def test_saida_e_cache_ficam_em_caminho_absoluto(self):
        # Relativos de propósito: é o que exercita a conversão. Com o caminho absoluto
        # de entrada o teste não provaria nada, porque ele já sai absoluto daqui.
        resultado = criar_projeto('G', LINHAS_DE_EXEMPLO, pasta_de_trabalho=self.pasta,
                                  pasta_de_saida=os.path.join('rel-saida', 'x'),
                                  pasta_de_cache=os.path.join('rel-cache', 'y'))

        def valor_gravado(parametro):
            with open(resultado.config, encoding='utf-8') as arquivo:
                for linha in arquivo:
                    if linha.startswith(parametro):
                        return linha.split('=', 1)[1].strip()
            self.fail(f'{parametro} não está no .config')

        saida = valor_gravado('global-diretorio_de_saida')
        cache = valor_gravado('global-diretorio_de_armazenamento_de_cvs')

        # O .config grava sempre no formato com '/', que funciona nos dois sistemas:
        # no Windows o separador nativo ('\\') seria interpretado como escape.
        self.assertEqual(os.path.abspath(os.path.join('rel-saida', 'x')).replace(os.sep, '/'),
                         saida)
        self.assertEqual(os.path.abspath(os.path.join('rel-cache', 'y')).replace(os.sep, '/'),
                         cache)
        self.assertTrue(os.path.isabs(saida), f'{saida!r} deveria ser absoluto')
        self.assertTrue(os.path.isabs(cache), f'{cache!r} deveria ser absoluto')
        self.assertNotIn('\\', saida)
        self.assertNotIn('\\', cache)

    def test_pastas_padrao_usam_o_nome_do_grupo(self):
        resultado = criar_projeto('Meu Grupo Acentuado', LINHAS_DE_EXEMPLO,
                                  pasta_de_trabalho=self.pasta)
        self.assertEqual(os.path.join(self.pasta, 'saida-meu-grupo-acentuado'), resultado.saida)
        self.assertEqual(os.path.join(self.pasta, 'cache'), resultado.cache)

    def test_lista_fica_relativa_ao_config(self):
        resultado = criar_projeto('G', LINHAS_DE_EXEMPLO, pasta_de_trabalho=self.pasta)
        with open(resultado.config, encoding='utf-8') as arquivo:
            self.assertIn('global-arquivo_de_entrada                 = ./g.list',
                          arquivo.read())

    def test_config_gerado_e_lido_pelo_grupo(self):
        resultado = criar_projeto('Meu Grupo Acentuado', LINHAS_DE_EXEMPLO,
                                  pasta_de_trabalho=self.pasta)
        grupo = Grupo(resultado.config)
        self.assertEqual('Meu Grupo Acentuado', grupo.obterParametro('global-nome_do_grupo'))
        self.assertEqual(3, len(grupo.listaDeMembros))
        self.assertEqual('1111111111111111', grupo.listaDeMembros[0].idLattes)

    def test_pipeline_roda_com_o_que_o_assistente_gerou(self):
        """Fim a fim, do assistente ao index.html, usando os currículos sintéticos."""
        from scriptLattes.cli import main as executar_pipeline

        saida = os.path.join(self.pasta, 'relatorios')
        resultado = criar_projeto('Grupo Ponta a Ponta', LINHAS_DE_EXEMPLO,
                                  pasta_de_trabalho=self.pasta, pasta_de_saida=saida,
                                  pasta_de_cache=CACHE_SINTETICO)

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            codigo = executar_pipeline([resultado.config, '--nao-abrir'])

        self.assertEqual(0, codigo, buffer.getvalue()[-2000:])
        self.assertTrue(os.path.isfile(os.path.join(saida, 'index.html')))
        self.assertEqual(3, len(os.listdir(os.path.join(saida, 'json'))))


class TestIsolamentoEntreGrupos(unittest.TestCase):
    """Dois grupos no mesmo processo não podem compartilhar membros.

    Isso importa para a interface gráfica, que roda o pipeline mais de uma vez na
    mesma sessão: com atributos de classe, os membros da primeira execução apareciam
    também na segunda."""

    def test_dois_grupos_nao_misturam_membros(self):
        pasta1 = tempfile.mkdtemp(prefix='sl-iso-1-')
        pasta2 = tempfile.mkdtemp(prefix='sl-iso-2-')
        self.addCleanup(shutil.rmtree, pasta1, True)
        self.addCleanup(shutil.rmtree, pasta2, True)

        primeiro = criar_projeto('Grupo Um', '1111111111111111 , Ana\n2222222222222222 , Carlos\n',
                                 pasta_de_trabalho=pasta1)
        segundo = criar_projeto('Grupo Dois', '3333333333333333 , Juliana\n',
                                pasta_de_trabalho=pasta2)

        grupo_um = Grupo(primeiro.config)
        grupo_dois = Grupo(segundo.config)

        self.assertEqual(2, len(grupo_um.listaDeMembros))
        self.assertEqual(1, len(grupo_dois.listaDeMembros))
        self.assertEqual(['3333333333333333'], [m.idLattes for m in grupo_dois.listaDeMembros])

    def test_parametros_nao_se_acumulam_entre_grupos(self):
        pasta = tempfile.mkdtemp(prefix='sl-iso-3-')
        self.addCleanup(shutil.rmtree, pasta, True)
        resultado = criar_projeto('Grupo Um', '1111111111111111 , Ana\n', pasta_de_trabalho=pasta)

        primeiro = Grupo(resultado.config)
        quantidade = len(primeiro.listaDeParametros)
        segundo = Grupo(resultado.config)

        self.assertEqual(quantidade, len(segundo.listaDeParametros))
        self.assertNotIn(segundo.listaDeParametros, primeiro.listaDeParametros[1:])
        self.assertEqual('Grupo Um', segundo.obterParametro('global-nome_do_grupo'))


class TestConversaDoAssistente(unittest.TestCase):
    def _entrada_roteirizada(self, respostas):
        pendentes = list(respostas)

        def entrada():
            if not pendentes:
                raise EOFError
            return pendentes.pop(0)

        return entrada

    def test_conversa_completa_cria_arquivos(self):
        pasta = tempfile.mkdtemp(prefix='sl-conversa-')
        self.addCleanup(shutil.rmtree, pasta, True)
        saida = io.StringIO()

        respostas = ['Grupo Conversado',
                     'http://lattes.cnpq.br/1111111111111111 , Ana Beatriz Ferreira Lima',
                     '2222222222222222',
                     '',                      # termina a lista de currículos
                     '2000', 'hoje',
                     os.path.join(pasta, 'relatorios'), CACHE_SINTETICO, '',
                     '']
        resultado = rodar_assistente(entrada=self._entrada_roteirizada(respostas), saida=saida.write,
                                     pasta_de_trabalho=pasta, rodar=True)
        texto = saida.getvalue()

        self.assertTrue(resultado)
        self.assertIn('[OK] 2 currículo(s) reconhecido(s)', texto)
        self.assertIn('[PRONTO] Arquivos criados', texto)
        self.assertIn('[CONCLUÍDO]', texto)
        self.assertTrue(os.path.isfile(os.path.join(pasta, 'relatorios', 'index.html')))

    def test_conversa_sem_curriculo_avisa_e_nao_cria_nada(self):
        pasta = tempfile.mkdtemp(prefix='sl-conversa-')
        self.addCleanup(shutil.rmtree, pasta, True)
        saida = io.StringIO()

        resultado = rodar_assistente(entrada=self._entrada_roteirizada(['Grupo', 'linha inválida', '']),
                                     saida=saida.write, pasta_de_trabalho=pasta)
        self.assertFalse(resultado)
        self.assertIn('Nenhum currículo válido', saida.getvalue())
        self.assertEqual([], os.listdir(pasta))       # nada foi criado na pasta

    def test_explica_linhas_nao_entendidas(self):
        pasta = tempfile.mkdtemp(prefix='sl-conversa-')
        self.addCleanup(shutil.rmtree, pasta, True)
        saida = io.StringIO()

        respostas = ['Grupo', '1111111111111111', 'lixo', '',
                     '', '', os.path.join(pasta, 'r'), os.path.join(pasta, 'c'), '']
        rodar_assistente(entrada=self._entrada_roteirizada(respostas), saida=saida.write,
                         pasta_de_trabalho=pasta)
        texto = saida.getvalue()
        self.assertIn('Não entendi estas linhas', texto)

    def test_nao_substitui_sem_confirmacao(self):
        pasta = tempfile.mkdtemp(prefix='sl-conversa-')
        self.addCleanup(shutil.rmtree, pasta, True)
        criar_projeto('Grupo', '1111111111111111', pasta_de_trabalho=pasta)

        saida = io.StringIO()
        respostas = ['Grupo', '1111111111111111', '', '', '', '', '', 'n']
        resultado = rodar_assistente(entrada=self._entrada_roteirizada(respostas),
                                     saida=saida.write, pasta_de_trabalho=pasta)
        self.assertFalse(resultado)
        self.assertIn('Nada foi alterado', saida.getvalue())

    def test_fim_de_entrada_nao_quebra(self):
        pasta = tempfile.mkdtemp(prefix='sl-conversa-')
        self.addCleanup(shutil.rmtree, pasta, True)
        saida = io.StringIO()
        resultado = rodar_assistente(entrada=self._entrada_roteirizada([]), saida=saida.write,
                                     pasta_de_trabalho=pasta)
        self.assertFalse(resultado)


class TestResultado(unittest.TestCase):
    def test_verdadeiro_somente_com_config(self):
        self.assertFalse(Resultado())
        self.assertTrue(Resultado(config='/tmp/x.config'))


if __name__ == '__main__':
    unittest.main()
