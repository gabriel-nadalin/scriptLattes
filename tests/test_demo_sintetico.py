"""Testes de regressão do parser usando os currículos SINTÉTICOS do exemplo.

Vantagem sobre usar um currículo real: sem dados pessoais no repositório e sem
depender de um arquivo que muda quando o pesquisador atualiza o CV Lattes.
"""
import os
import unittest

from scriptLattes.parserLattes import ParserLattes

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_CACHE = os.path.join(RAIZ, 'exemplo', 'demo-lattes', 'cache')

# o que cada currículo sintético deve produzir
ESPERADO = {
    '1111111111111111': {
        'nome': 'Ana Beatriz Ferreira Lima',
        'formacao': 2, 'atuacao': 2, 'areas': 2, 'idiomas': 2, 'premios': 1,
        'artigos': 2, 'congressos': 1, 'resumos': 1,
        'artigo_titulo': 'Cuidado de enfermagem em doenças crônicas: revisão integrativa',
        'artigo_ano': '2025',
    },
    '2222222222222222': {
        'nome': 'Carlos Eduardo Mendes Rocha',
        'formacao': 1, 'atuacao': 2, 'areas': 2, 'idiomas': 1, 'premios': 1,
        'artigos': 1, 'congressos': 1, 'resumos': 0,
    },
    '3333333333333333': {
        'nome': 'Juliana Prado Nogueira',
        'formacao': 1, 'atuacao': 2, 'areas': 1, 'idiomas': 1, 'premios': 0,
        'artigos': 1, 'congressos': 0, 'resumos': 1,
    },
}


def interpretar(identificador):
    with open(os.path.join(PASTA_CACHE, identificador), encoding='utf-8') as arquivo:
        return ParserLattes(0, arquivo.read())


class TestCurriculosSinteticos(unittest.TestCase):
    def test_arquivos_do_exemplo_existem(self):
        for identificador in ESPERADO:
            self.assertTrue(os.path.isfile(os.path.join(PASTA_CACHE, identificador)),
                            f'currículo sintético ausente: {identificador}')

    def test_identificacao_de_cada_membro(self):
        for identificador, esperado in ESPERADO.items():
            with self.subTest(identificador=identificador):
                parser = interpretar(identificador)
                self.assertEqual(esperado['nome'], parser.nomeCompleto)
                self.assertTrue(parser.nomeEmCitacoesBibliograficas)
                self.assertTrue(parser.enderecoProfissional)

    def test_listas_de_dados_gerais(self):
        for identificador, esperado in ESPERADO.items():
            with self.subTest(identificador=identificador):
                parser = interpretar(identificador)
                self.assertEqual(esperado['formacao'], len(parser.listaFormacaoAcademica))
                self.assertEqual(esperado['atuacao'], len(parser.listaAtuacaoProfissional))
                self.assertEqual(esperado['areas'], len(parser.listaAreaDeAtuacao))
                self.assertEqual(esperado['idiomas'], len(parser.listaIdioma))
                self.assertEqual(esperado['premios'], len(parser.listaPremioOuTitulo))

    def test_producao_bibliografica(self):
        for identificador, esperado in ESPERADO.items():
            with self.subTest(identificador=identificador):
                parser = interpretar(identificador)
                self.assertEqual(esperado['artigos'], len(parser.listaArtigoEmPeriodico))
                self.assertEqual(esperado['congressos'], len(parser.listaTrabalhoCompletoEmCongresso))
                self.assertEqual(esperado['resumos'], len(parser.listaResumoEmCongresso))

    def test_campos_do_artigo_sao_extraidos(self):
        esperado = ESPERADO['1111111111111111']
        artigo = interpretar('1111111111111111').listaArtigoEmPeriodico[0]
        self.assertEqual(esperado['artigo_titulo'], artigo.titulo)
        self.assertEqual(esperado['artigo_ano'], artigo.ano)
        self.assertTrue(artigo.revista)
        self.assertTrue(artigo.autores)

    def test_coautores_do_lattes_sao_identificados(self):
        # os links de coautor dentro do item alimentam o grafo de colaborações
        self.assertIn('2222222222222222', interpretar('1111111111111111').listaIDLattesColaboradores)
        self.assertIn('1111111111111111', interpretar('3333333333333333').listaIDLattesColaboradores)

    def test_nenhum_dado_dos_curriculos_reais_vaza_para_o_exemplo(self):
        """Os sintéticos falam de pessoas e instituições inventadas."""
        for identificador in ESPERADO:
            with open(os.path.join(PASTA_CACHE, identificador), encoding='utf-8') as arquivo:
                texto = arquivo.read().lower()
            # 'lattes.cnpq.br' aparece nos links de coautor e é o endereço da plataforma,
            # não dado pessoal; os nomes e instituições reais é que não podem aparecer
            for marca_real in ('usp', 'ribeirão', 'silveira', 'kusumota', 'bernardes'):
                self.assertNotIn(marca_real, texto)


if __name__ == '__main__':
    unittest.main()
