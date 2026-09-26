"""Testes da exportação JSON individual (scriptLattes/grupo.py).

Cobrem o mapeamento entre os atributos preenchidos pelo parser e as chaves
exportadas em <diretorio_de_saida>/json/<membro>.json.
"""
import unittest

from scriptLattes.grupo import (
    TIPOS_DE_BANCA,
    dados_do_pesquisador,
    parse_area_de_atuacao,
    separar_tipo_instituicao,
)
from scriptLattes.producoesBibliograficas.capituloDeLivroPublicado import CapituloDeLivroPublicado
from scriptLattes.producoesBibliograficas.textoEmJornalDeNoticia import TextoEmJornalDeNoticia
from scriptLattes.producoesTecnicas.entrevista import Entrevista
from scriptLattes.orientacoes.orientacaoConcluida import OrientacaoConcluida
from scriptLattes.producoesUnitarias.participacaoEmBanca import ParticipacaoEmBanca

# Itens reais (extraídos de CVs Lattes) usados como entrada dos testes.
CAPITULO_ITEM = ('BARCELLOS, M. P.. My Path experiencing Falbo?s Approach. In: Almeida, J.P.; '
                 'Guizzardi, G.. (Org.). Engineering Ontologies and Ontologies for Engineering. '
                 '1ed.: , 2020, v. , p. 42-61.')
JORNAL_ITEM = ('BARCELLOS, M. P.. Medição de Software: Um Importante Pilar da Melhoria de Processos '
               'de Software. Engenharia de Software Magazine, p. 31 - 36, 01 maio 2010.')
ENTREVISTA_ITEM = ('BARCELLOS, M. P.; NETO, A. ; EMER, M. C. . Medição de Software. 2023. '
                   '(Programa de rádio ou TV/Entrevista).')
TCC_ITEM = ('Amanda Brito Apolinário. CaLMo: A Tool to support the use of Causal Loop Diagram in '
            'Software Engineering. 2025. Trabalho de Conclusão de Curso. (Graduação em Ciência da '
            'Computação) - Universidade Federal do Espírito Santo. Orientador: Monalessa Perini Barcellos.')
BANCA_ITEM = ('MOURA, E. S.; BARCELLOS, M. P.; NASCIMENTO, E. L.. Participação em banca de SILVA, N. D., '
              'PAULA, Z. E., MORAES, R. F..Sistema de Orçamento de Obra Distribuído. 2003. Trabalho de '
              'Conclusão de Curso (Graduação em Sistemas de Informação) - Faculdade Vitoriana de Ensino Superior.')


class MembroFalso:
    """Membro mínimo aceito por dados_do_pesquisador (listas não informadas ficam vazias)."""

    def __init__(self, **listas):
        self.idLattes = '0000000000000000'
        self.nomeCompleto = 'Pesquisador de Teste'
        self.nomeEmCitacoesBibliograficas = 'TESTE, P.'
        self.sexo = 'Masculino'
        self.rotulo = '* Sem rótulo'
        self.periodo = ''
        self.bolsaProdutividade = ''
        self.enderecoProfissional = ''
        self.atualizacaoCV = ''
        self.url = ''
        self.textoResumo = ''
        for nome, valor in listas.items():
            setattr(self, nome, valor)

    def __getattr__(self, nome):
        if nome.startswith('lista'):
            return []
        raise AttributeError(nome)


class TestSepararTipoInstituicao(unittest.TestCase):
    def test_separa_tipo_curso_e_instituicao(self):
        self.assertEqual(
            separar_tipo_instituicao('Tese (Doutorado em Ciências) - Universidade X'),
            ('Tese', 'Doutorado em Ciências', 'Universidade X'))

    def test_infere_tipo_quando_ausente(self):
        self.assertEqual(
            separar_tipo_instituicao('(Graduação em Sistemas) - Faculdade Y'),
            ('Trabalho de Conclusão de Curso', 'Graduação em Sistemas', 'Faculdade Y'))

    def test_sem_parenteses_mantem_instituicao(self):
        self.assertEqual(separar_tipo_instituicao('Universidade Z'), ('', '', 'Universidade Z'))

    def test_vazio(self):
        self.assertEqual(separar_tipo_instituicao(''), ('', '', ''))


class TestParseAreaDeAtuacao(unittest.TestCase):
    def test_componentes(self):
        # Formato real do CV Lattes (sem espaço antes de "/Especialidade")
        descricao = ('Grande área: Ciências Exatas e da Terra / Área: Ciência da Computação / '
                     'Subárea: Metodologia e Técnicas da Computação/Especialidade: Engenharia de '
                     'Software.')
        self.assertEqual(
            parse_area_de_atuacao(descricao),
            ('Ciências Exatas e da Terra', 'Ciência da Computação',
             'Metodologia e Técnicas da Computação', 'Engenharia de Software'))

    def test_componentes_com_espacos_extras(self):
        descricao = ('Grande área: Ciências Exatas e da Terra / Área: Ciência da Computação / '
                     'Subárea: Metodologia e Técnicas da Computação / Especialidade: Engenharia de '
                     'Software.')
        self.assertEqual(
            parse_area_de_atuacao(descricao),
            ('Ciências Exatas e da Terra', 'Ciência da Computação',
             'Metodologia e Técnicas da Computação', 'Engenharia de Software'))

    def test_sem_especialidade(self):
        descricao = 'Grande área: Ciências Exatas e da Terra / Área: Ciência da Computação.'
        self.assertEqual(
            parse_area_de_atuacao(descricao),
            ('Ciências Exatas e da Terra', 'Ciência da Computação', '', ''))

    def test_vazio(self):
        self.assertEqual(parse_area_de_atuacao(''), ('', '', '', ''))


class TestDadosDoPesquisador(unittest.TestCase):
    def test_chaves_de_topo_documentadas(self):
        dados = dados_do_pesquisador(MembroFalso())
        for chave in ('informacoes_pessoais', 'formacao_academica', 'atuacao_profissional',
                      'projetos_pesquisa', 'projetos_extensao', 'projetos_desenvolvimento',
                      'areas_de_atuacao', 'idiomas', 'premios_titulos', 'linhas_de_pesquisa',
                      'producao_bibliografica', 'producao_tecnica', 'patentes_registros',
                      'producao_artistica', 'orientacoes', 'eventos', 'bancas', 'estatisticas'):
            self.assertIn(chave, dados)

    def test_capitulo_exporta_titulo_do_livro(self):
        capitulo = CapituloDeLivroPublicado('id', ['1', CAPITULO_ITEM], False)
        self.assertTrue(capitulo.livro, 'o parser deveria preencher .livro')

        dados = dados_do_pesquisador(MembroFalso(listaCapituloDeLivroPublicado=[capitulo]))
        registro = dados['producao_bibliografica']['capitulos_livros'][0]

        self.assertEqual(registro['titulo_livro'], capitulo.livro)
        self.assertEqual(registro['titulo'], capitulo.titulo)
        self.assertEqual(registro['ano'], capitulo.ano)

    def test_texto_em_jornal_exporta_nome_do_jornal(self):
        texto = TextoEmJornalDeNoticia('id', ['1', JORNAL_ITEM], False)
        dados = dados_do_pesquisador(MembroFalso(listaTextoEmJornalDeNoticia=[texto]))
        registro = dados['producao_bibliografica']['textos_jornais'][0]

        self.assertEqual(registro['jornal'], texto.nomeJornal)
        self.assertEqual(registro['data'], texto.data)
        self.assertEqual(registro['paginas'], texto.paginas)

    def test_entrevista_exporta_natureza(self):
        entrevista = Entrevista('id', ['1', ENTREVISTA_ITEM], False)
        dados = dados_do_pesquisador(MembroFalso(listaEntrevista=[entrevista]))
        registro = dados['producao_tecnica']['entrevistas'][0]

        self.assertEqual(registro['natureza'], entrevista.natureza)
        self.assertEqual(registro['titulo'], entrevista.titulo)

    def test_orientacao_concluida_exporta_curso_e_ano_de_conclusao(self):
        tcc = OrientacaoConcluida('id', ['1', TCC_ITEM], '')
        dados = dados_do_pesquisador(MembroFalso(listaOCTCC=[tcc]))
        registro = dados['orientacoes']['concluidas']['tcc'][0]

        self.assertEqual(registro['curso'], 'Graduação em Ciência da Computação')
        self.assertEqual(registro['tipo_trabalho'], 'Trabalho de Conclusão de Curso')
        self.assertEqual(registro['instituicao'], 'Universidade Federal do Espírito Santo')
        self.assertEqual(registro['ano_conclusao'], tcc.ano)
        self.assertNotIn('ano_inicio', registro)
        self.assertEqual(registro['tipo_orientacao'], 'Orientador')

    def test_bancas_agrupadas_por_tipo(self):
        banca = ParticipacaoEmBanca('id', ['1', BANCA_ITEM])
        dados = dados_do_pesquisador(MembroFalso(listaParticipacaoEmBancaTrabalho=[banca]))
        bancas = dados['bancas']

        self.assertEqual([chave for chave, _ in TIPOS_DE_BANCA], list(bancas))
        total = sum(len(lista) for lista in bancas.values())
        self.assertEqual(total, 1)
        self.assertEqual(len(bancas['graduacao']), 1)

    def test_campos_sem_fonte_no_cv_nao_sao_exportados(self):
        capitulo = CapituloDeLivroPublicado('id', ['1', CAPITULO_ITEM], False)
        entrevista = Entrevista('id', ['1', ENTREVISTA_ITEM], False)
        dados = dados_do_pesquisador(MembroFalso(
            listaCapituloDeLivroPublicado=[capitulo],
            listaEntrevista=[entrevista]))

        capitulo_exportado = dados['producao_bibliografica']['capitulos_livros'][0]
        self.assertNotIn('cidade', capitulo_exportado)
        self.assertNotIn('isbn', capitulo_exportado)

        artigo_exportado = dados['producao_bibliografica']['artigos_periodicos']
        self.assertEqual(artigo_exportado, [])

        self.assertNotIn('veiculo', dados['producao_tecnica']['entrevistas'][0])

    def test_orientacao_em_andamento_exporta_ano_de_inicio(self):
        # OrientacaoEmAndamento usa o mesmo contrato de chaves das concluídas
        from scriptLattes.orientacoes.orientacaoEmAndamento import OrientacaoEmAndamento
        item = ('Fulano de Tal. Um Sistema. 2024. Dissertação (Mestrado em Computação) - Universidade X. '
                'Orientador: Monalessa Perini Barcellos.')
        orientacao = OrientacaoEmAndamento('id', ['1', item], '')
        dados = dados_do_pesquisador(MembroFalso(listaOADissertacaoDeMestrado=[orientacao]))
        registro = dados['orientacoes']['em_andamento']['mestrado'][0]

        self.assertEqual(registro['ano_inicio'], orientacao.ano)
        self.assertNotIn('ano_conclusao', registro)


if __name__ == '__main__':
    unittest.main()
