"""Testes da normalização dos textos coletados (scriptLattes/normalizacao.py).

Os casos usam strings reais de CVs Lattes (formato da citação de eventos,
grafias de nomes de autores) para travar as regras contra regressões.
"""
import json
import os
import shutil
import tempfile
import unittest

from scriptLattes.normalizacao import (
    Vocabulario,
    chave_de_evento,
    chave_de_instituicao,
    chave_de_pessoa,
    detectar_sigla,
    estruturar_evento,
    estruturar_evento_do_item,
    mesma_pessoa,
    normalizar_chave,
    partes_de_pessoa,
    relatorio_de_candidatos,
    separar_citacao_de_evento,
    separar_edicao,
)


class TestNormalizarChave(unittest.TestCase):
    def test_acentos_caixa_e_pontuacao(self):
        self.assertEqual(normalizar_chave('XV Congresso Brasileiro de Estomaterapia-SC.'),
                         'xv congresso brasileiro de estomaterapia sc')

    def test_idempotente(self):
        for texto in ('Simpósio Brasileiro de Qualidade de Software (SBQS 2018)',
                      '  espaços   múltiplos  ', 'Ação, ção & 42'):
            self.assertEqual(normalizar_chave(normalizar_chave(texto)), normalizar_chave(texto))

    def test_vazio(self):
        self.assertEqual(normalizar_chave(None), '')
        self.assertEqual(normalizar_chave(''), '')


class TestSepararEdicao(unittest.TestCase):
    def test_romano(self):
        self.assertEqual(separar_edicao('XV Congresso Brasileiro de Estomaterapia'),
                         ('Congresso Brasileiro de Estomaterapia', 'XV'))

    def test_ordinal(self):
        self.assertEqual(separar_edicao('22nd Brazilian Symposium on Information Systems'),
                         ('Brazilian Symposium on Information Systems', '22nd'))

    def test_ordinal_com_espaco(self):
        self.assertEqual(separar_edicao('9 th Congress of Nursing'),
                         ('Congress of Nursing', '9 th'))

    def test_sem_edicao(self):
        self.assertEqual(separar_edicao('Congresso Brasileiro de Automática'),
                         ('Congresso Brasileiro de Automática', ''))

    def test_edicao_colada_e_no_fim(self):
        self.assertEqual(separar_edicao('53ocongresso brasileiro de enfermagem'),
                         ('congresso brasileiro de enfermagem', '53o'))
        self.assertEqual(separar_edicao('simposio de iniciacao cientifica da usp 6o'),
                         ('simposio de iniciacao cientifica da usp', '6o'))

    def test_edicao_com_sinal_de_grau(self):
        self.assertEqual(separar_edicao('60° Congresso Brasileiro de Enfermagem'),
                         ('Congresso Brasileiro de Enfermagem', '60°'))
        self.assertEqual(chave_de_evento('60° Congresso Brasileiro de Enfermagem'),
                         chave_de_evento('Congresso Brasileiro de Enfermagem'))

    def test_nao_confunde_palavra_com_romano(self):
        self.assertEqual(separar_edicao('MIX Conference on Testing'), ('MIX Conference on Testing', ''))


class TestDetectarSigla(unittest.TestCase):
    def test_entre_parenteses_com_ano(self):
        self.assertEqual(detectar_sigla('Brazilian Symposium on Software Engineering (SBES 2025)'),
                         ('SBES', '2025'))

    def test_entre_parenteses_sem_ano(self):
        self.assertEqual(detectar_sigla('International Conference (INDUSCON)'), ('INDUSCON', ''))

    def test_prefixo(self):
        self.assertEqual(detectar_sigla('SBES 2023: XXXVII Brazilian Symposium'), ('SBES', '2023'))

    def test_sem_sigla(self):
        self.assertEqual(detectar_sigla('Congresso Brasileiro de Automática'), ('', ''))


class TestSepararCitacaoDeEvento(unittest.TestCase):
    def test_cauda_de_citacao(self):
        resultado = separar_citacao_de_evento(
            'I Simpósio Internacional de Pesquisa em Cuidados Paliativos, 2020, Ribeirão Preto. '
            'Archives of Health Investigation')
        self.assertEqual(resultado['nome'], 'I Simpósio Internacional de Pesquisa em Cuidados Paliativos')
        self.assertEqual(resultado['edicao'], 'I')
        self.assertEqual(resultado['ano'], '2020')
        self.assertEqual(resultado['local'], 'Ribeirão Preto')
        self.assertEqual(resultado['veiculo'], 'Archives of Health Investigation')

    def test_virgula_dupla_e_local_com_uf(self):
        resultado = separar_citacao_de_evento(
            'International Workshop on ADVANCEs in ICT Infrastructures and Services (ADVANCE 2013),, '
            '2013, Morro de São Paulo, BA. Anais do ADVANCED 2013, 2013')
        self.assertEqual(resultado['nome'],
                         'International Workshop on ADVANCEs in ICT Infrastructures and Services (ADVANCE 2013)')
        self.assertEqual(resultado['sigla'], 'ADVANCE')
        self.assertEqual(resultado['ano'], '2013')
        self.assertEqual(resultado['local'], 'Morro de São Paulo, BA')
        self.assertEqual(resultado['veiculo'], 'Anais do ADVANCED 2013')

    def test_sem_cauda(self):
        resultado = separar_citacao_de_evento('22nd Brazilian Symposium on Information Systems (SBSI 2026)')
        self.assertEqual(resultado['nome'], '22nd Brazilian Symposium on Information Systems (SBSI 2026)')
        self.assertEqual(resultado['sigla'], 'SBSI')
        self.assertEqual(resultado['ano'], '2026')
        self.assertEqual(resultado['local'], '')
        self.assertEqual(resultado['veiculo'], '')

    def test_forma_prefixada(self):
        resultado = estruturar_evento(
            'SBES 2023: XXXVII Brazilian Symposium on Software Engineering, 2023, Campo Grande Brazil. '
            'Proceedings of the XXXVII Brazilian Symposium on Software Engineering. p. 154.')
        self.assertEqual(resultado['sigla'], 'SBES')
        self.assertEqual(resultado['edicao'], 'XXXVII')
        self.assertEqual(resultado['local'], 'Campo Grande Brazil')
        self.assertEqual(resultado['veiculo'],
                         'Proceedings of the XXXVII Brazilian Symposium on Software Engineering')

    def test_vazio(self):
        self.assertEqual(separar_citacao_de_evento('')['nome'], '')


class TestEstruturarEvento(unittest.TestCase):
    def test_remove_paginas_e_volume(self):
        resultado = estruturar_evento(
            'Congresso Brasileiro de Cardiologia, 2015, Curitiba. Arquivos Brasileiros de Cardiologia, v. , '
            'p. 10-20.')
        self.assertEqual(resultado['nome'], 'Congresso Brasileiro de Cardiologia')
        self.assertEqual(resultado['local'], 'Curitiba')

    def test_item_bruto(self):
        item = ('SILVA, J.; SOUZA, M. . Um artigo. In: I Simpósio Brasileiro de Testes, 2019, Salvador. '
                'Anais do I Simpósio Brasileiro de Testes, p. 5.')
        resultado = estruturar_evento_do_item(item)
        self.assertEqual(resultado['nome'], 'I Simpósio Brasileiro de Testes')
        self.assertEqual(resultado['ano'], '2019')
        self.assertEqual(resultado['local'], 'Salvador')

    def test_item_sem_in(self):
        self.assertEqual(estruturar_evento_do_item('Titulo qualquer, sem evento')[ 'nome'], '')


class TestChaveDeEvento(unittest.TestCase):
    def test_edicoes_compartilham_a_chave(self):
        chaves = {
            chave_de_evento('Congresso Brasileiro de Automática'),
            chave_de_evento('XVI Congresso Brasileiro de Automática'),
            chave_de_evento('XXIV Congresso Brasileiro de Automática'),
        }
        self.assertEqual(chaves, {'congresso brasileiro de automatica'})

    def test_sigla_tem_precedencia(self):
        self.assertEqual(chave_de_evento('39th Brazilian Symposium on Software Engineering (SBES 2025)'),
                         'sbes')
        self.assertEqual(chave_de_evento('SBES 2023: XXXVII Brazilian Symposium'), 'sbes')

    def test_instituicao(self):
        self.assertEqual(chave_de_instituicao('Universidade Federal do Espírito Santo'),
                         'universidade federal do espirito santo')


class TestMesmaPessoa(unittest.TestCase):
    REFERENCIA = 'SANTOS JUNIOR, Paulo Sergio dos'

    def test_grafias_do_mesmo_autor(self):
        for variante in ('SANTOS JUNIOR, Paulo Sergio dos',
                         'JR., PAULO S. SANTOS',
                         'SANTOS JR, PAULO',
                         'SANTOS JÚNIOR, PAULO SÉRGIO',
                         'JÚNIOR, PAULO SÉRGIO SANTOS',
                         'DOS SANTOS JÚNIOR, PAULO SÉRGIO',
                         'Santos Jr, Paulo Sérgio',
                         'Paulo Sergio dos Santos Junior'):
            self.assertTrue(mesma_pessoa(variante, self.REFERENCIA), variante)

    def test_grafias_ambiguas_nao_sao_agrupadas(self):
        # sem prenome ou sem o sufixo: decisão explícita via pesquisadores.csv
        for variante in ('SANTOS JR', 'SANTOS, PAULO SÉRGIO DOS', 'Santos, Paulo Sergio'):
            self.assertFalse(mesma_pessoa(variante, self.REFERENCIA), variante)

    def test_pessoas_diferentes(self):
        self.assertFalse(mesma_pessoa('SILVA, Jose', 'SILVA, Joao'))
        self.assertFalse(mesma_pessoa('SANTOS, Maria', 'SANTOS, Paulo'))
        self.assertFalse(mesma_pessoa('SANTOS JUNIOR, Paulo Sergio dos', 'SANTOS, Paulo Sergio dos'))

    def test_partes(self):
        self.assertEqual(partes_de_pessoa('SANTOS JUNIOR, Paulo Sergio dos'),
                         {'sobrenome': 'santos', 'sufixo': 'jr', 'prenomes': ['paulo', 'sergio']})
        self.assertEqual(chave_de_pessoa('Santos Jr, Paulo Sérgio'), 'santos jr ps')


class TestVocabulario(unittest.TestCase):
    def setUp(self):
        self.diretorio = tempfile.mkdtemp()
        with open(os.path.join(self.diretorio, 'eventos.csv'), 'w', encoding='utf8') as arquivo:
            arquivo.write('chave,serie,sigla,nome_canonico\n'
                          'congresso brasileiro de automatica,cba,CBA,Congresso Brasileiro de Automação\n')
        with open(os.path.join(self.diretorio, 'instituicoes.csv'), 'w', encoding='utf8') as arquivo:
            arquivo.write('chave,nome_canonico\n'
                          'instituto federal de educacao,Instituto Federal de Educação, Ciência e Tecnologia\n')
        with open(os.path.join(self.diretorio, 'periodicos.csv'), 'w', encoding='utf8') as arquivo:
            arquivo.write('issn,nome_canonico\n1234-5678,Revista Brasileira de Testes\n')
        with open(os.path.join(self.diretorio, 'pesquisadores.csv'), 'w', encoding='utf8') as arquivo:
            arquivo.write('nome_a,nome_b\nSANTOS JR,SANTOS JUNIOR, Paulo Sergio dos\n')
        self.vocabulario = Vocabulario(self.diretorio)
        self.addCleanup(shutil.rmtree, self.diretorio)

    def test_carrega_tabelas(self):
        self.assertEqual(len(self.vocabulario.eventos), 1)
        self.assertEqual(len(self.vocabulario.instituicoes), 1)
        self.assertEqual(self.vocabulario.resolver_periodico('1234-5678'), 'Revista Brasileira de Testes')

    def test_resolver_evento(self):
        self.assertEqual(self.vocabulario.resolver_evento('congresso brasileiro de automatica'),
                         ('cba', 'Congresso Brasileiro de Automação', 'CBA'))

    def test_evento_sem_alias_devolve_a_propria_chave(self):
        self.assertEqual(self.vocabulario.resolver_evento('evento desconhecido'),
                         ('evento desconhecido', '', ''))

    def test_par_forcado_de_pesquisadores(self):
        self.assertTrue(self.vocabulario.mesma_pessoa('SANTOS JR', 'SANTOS JUNIOR, Paulo Sergio dos'))
        self.assertTrue(self.vocabulario.mesma_pessoa('Santos Jr', 'Santos Junior, Paulo Sergio dos'))

    def test_diretorio_inexistente(self):
        vazio = Vocabulario('/diretorio/que/nao/existe')
        self.assertEqual(vazio.eventos, {})
        self.assertEqual(vazio.resolver_evento('x'), ('x', '', ''))


class TestRelatorioDeCandidatos(unittest.TestCase):
    def setUp(self):
        self.raiz = tempfile.mkdtemp()
        self.saida = os.path.join(self.raiz, 'saida')
        os.makedirs(os.path.join(self.saida, 'json'))
        dados = {
            'informacoes_pessoais': {'nome_completo': 'Paulo Sergio dos Santos Junior',
                                     'nome_citacoes': 'SANTOS JUNIOR, Paulo Sergio dos'},
            'producao_bibliografica': {
                'trabalhos_completos_congressos': [{
                    'titulo': 'T', 'ano': '2023',
                    'autores': 'SANTOS JUNIOR, Paulo Sergio dos; SANTOS, Maria; OUTRO, A.',
                    'evento': 'XV Congresso Brasileiro de Estomaterapia, 2025, Florianópolis-SC. Anais do XV Congresso',
                    'evento_sigla': '', 'evento_edicao': 'XV', 'evento_chave': '',
                }],
                'resumos_expandidos': [], 'resumos_congressos': [],
                'artigos_periodicos': [{'revista': 'Revista Sem Issn', 'issn': ''}],
            },
            'orientacoes': {'concluidas': {'tcc': [
                {'instituicao': 'Instituto Federal de Educação'}]}, 'em_andamento': {}},
        }
        with open(os.path.join(self.saida, 'json', '00_x.json'), 'w', encoding='utf8') as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False)
        self.destino = os.path.join(self.raiz, 'aliases')
        self.addCleanup(shutil.rmtree, self.raiz)

    def test_escreve_candidatos(self):
        resumo = relatorio_de_candidatos(self.saida, self.destino)

        self.assertEqual(resumo['arquivos'], 1)
        self.assertEqual(resumo['eventos_distintos'], 1)
        self.assertEqual(resumo['instituicoes_distintas'], 1)
        self.assertEqual(resumo['periodicos_sem_issn'], 1)

        with open(os.path.join(self.destino, 'pendentes_eventos.csv'), encoding='utf8') as arquivo:
            linhas = arquivo.read().splitlines()
        self.assertEqual(linhas[0], 'chave,ocorrencias,edicoes,exemplos')
        self.assertIn('congresso brasileiro de estomaterapia', linhas[1])
        self.assertIn('XV', linhas[1])

        # o autor do próprio membro não aparece como candidato; só autores com
        # sobrenome de membro (decisão humana) são listados
        with open(os.path.join(self.destino, 'pendentes_pesquisadores.csv'), encoding='utf8') as arquivo:
            texto = arquivo.read()
        self.assertNotIn('SANTOS JUNIOR, Paulo Sergio dos;', texto)
        self.assertIn('SANTOS, Maria', texto)
        self.assertNotIn('OUTRO, A.', texto)
        self.assertEqual(resumo['autores_nao_atribuidos'], 2)
        self.assertEqual(resumo['autores_com_candidato'], 1)

    def test_nao_sobrescreve_tabelas_manuais(self):
        os.makedirs(self.destino)
        caminho = os.path.join(self.destino, 'eventos.csv')
        with open(caminho, 'w', encoding='utf8') as arquivo:
            arquivo.write('chave,serie,sigla,nome_canonico\nmeu evento,minha serie,ME,Meu Evento\n')

        relatorio_de_candidatos(self.saida, self.destino, Vocabulario(self.destino))

        with open(caminho, encoding='utf8') as arquivo:
            self.assertIn('meu evento', arquivo.read())


if __name__ == '__main__':
    unittest.main()
