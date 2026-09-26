#!/usr/bin/python
# encoding: utf-8


import datetime
import json
import re
import os
from scriptLattes.util import *
from scriptLattes.baixaLattes import fechar_driver
from scriptLattes.erros import classificar
from scriptLattes.normalizacao import (Vocabulario, chave_de_evento, chave_de_instituicao,
                                       estruturar_evento, normalizar_chave)

def inferir_tipo_de_trabalho(curso):
    """Deduz o tipo de trabalho a partir do nome do curso (ex.: TCCs)."""
    if curso.startswith('Graduação') or curso.startswith('Graduando'):
        return 'Trabalho de Conclusão de Curso'
    if curso.startswith('Mestrado'):
        return 'Dissertação'
    if curso.startswith('Doutorado'):
        return 'Tese'
    if 'Especialização' in curso:
        return 'Monografia'
    return 'Trabalho'


TIPOS_DE_TRABALHO_CONHECIDOS = (
    'orientacao de outra natureza', 'supervisao', 'iniciacao cientifica', 'trabalho de conclusao',
    'tese', 'dissertacao', 'monografia', 'aperfeicoamento', 'especializacao',
)


def _fechamento_do_parentese(texto, abertura):
    """Índice do ``)`` que fecha o ``(`` em ``abertura`` (aceita parênteses aninhados)."""
    profundidade = 0
    for indice in range(abertura, len(texto)):
        if texto[indice] == '(':
            profundidade += 1
        elif texto[indice] == ')':
            profundidade -= 1
            if profundidade == 0:
                return indice
    return -1


def separar_tipo_instituicao(instituicao_completa):
    """Separa tipo de trabalho, curso e instituição.

    Ex: 'Tese (Doutorado em Ciências) - Universidade X'
        -> ('Tese', 'Doutorado em Ciências', 'Universidade X')
    Ex: '(Graduação em Sistemas) - Faculdade Y'
        -> ('Trabalho de Conclusão de Curso', 'Graduação em Sistemas', 'Faculdade Y')
    Ex: 'Orientação de outra natureza - Escola Z'
        -> ('Orientação de outra natureza', '', 'Escola Z')
    Ex: 'Dissertação (Mestrado em X (PPGEFE)) - Universidade W'
        -> ('Dissertação', 'Mestrado em X (PPGEFE)', 'Universidade W')
    """
    if not instituicao_completa:
        return '', '', ''

    texto = ' '.join(str(instituicao_completa).split()).strip()

    # (Tipo) (Curso) - Instituição, aceitando parênteses aninhados no curso
    abertura = texto.find('(')
    if abertura != -1:
        fechamento = _fechamento_do_parentese(texto, abertura)
        if fechamento != -1:
            resto = texto[fechamento + 1:].strip()
            separador = re.match(r'^[-–]\s*(.+)$', resto)
            if separador:
                tipo_trabalho = texto[:abertura].strip().rstrip('-.')
                curso = texto[abertura + 1:fechamento].strip()
                instituicao = separador.group(1).strip()
                if not tipo_trabalho:
                    tipo_trabalho = inferir_tipo_de_trabalho(curso)
                return tipo_trabalho, curso, instituicao

    # 'Tipo de trabalho - Instituição' / 'Tipo de trabalho. Instituição'
    separador = re.match(r'^(.{3,60}?)\s*[-.]\s+(.+)$', texto)
    if separador:
        candidato = normalizar_chave(separador.group(1))
        if any(candidato.startswith(tipo) or candidato == tipo for tipo in TIPOS_DE_TRABALHO_CONHECIDOS):
            return separador.group(1).strip().rstrip('.'), '', separador.group(2).strip()

    return '', '', texto


def parse_area_de_atuacao(descricao):
    """Decompõe a descrição de uma área de atuação no Lattes.

    Ex: 'Grande área: Ciências Exatas... / Área: Ciência da Computação / Especialidade: X.'
        -> ('Ciências Exatas...', 'Ciência da Computação', '', 'X')
    """
    grande_area = ''
    area = ''
    subarea = ''
    especialidade = ''

    if not descricao:
        return grande_area, area, subarea, especialidade

    match = re.search(r'Grande área:\s*([^/]+)', descricao)
    if match:
        grande_area = match.group(1).strip().rstrip('.')

    match = re.search(r'(?:^|/)?\s*Área:\s*([^/]+)', descricao)
    if match:
        area = match.group(1).strip().rstrip('.')

    match = re.search(r'(?:^|/)?\s*Subárea:\s*([^/]+?)\s*(?:/\s*Especialidade|$)', descricao)
    if match:
        subarea = match.group(1).strip().rstrip('.')

    match = re.search(r'Especialidade:\s*([^.]+?)(?:\.|$)', descricao)
    if match:
        especialidade = match.group(1).strip()

    return grande_area, area, subarea, especialidade


def extrair_habilidade_idioma(proficiencia_completa, habilidade):
    """Extrai o nível de uma habilidade de idioma.

    Ex: ('Compreende Bem, Fala Razoavelmente.', 'Fala') -> 'Razoavelmente'
    """
    if not proficiencia_completa:
        return ''

    # Remove pontos finais e espaços desnecessários
    texto = proficiencia_completa.strip().rstrip('.')

    match = re.search(rf'{habilidade}\s+([^,]+)', texto)
    if match:
        return match.group(1).strip()

    return ''


def campo(item, atributo):
    """Lê um atributo de um item do parser devolvendo '' quando ausente/vazio."""
    valor = getattr(item, atributo, '')
    return valor if valor is not None else ''


TIPOS_DE_BANCA = (
    ('mestrado', 'Mestrado'),
    ('doutorado', 'Tese de Doutorado'),
    ('qualificacao_doutorado', 'Qualificação de Doutorado'),
    ('qualificacao_mestrado', 'Qualificação de Mestrado'),
    ('graduacao', 'Trabalho de Conclusão de Curso de Graduação'),
    ('outras', 'Participação em banca'),
)


def registro_de_orientacao(item, concluida=False, vocabulario=None):
    """Serializa uma orientação (em andamento ou concluída).

    Para orientações concluídas o único ano disponível no CV é o de conclusão;
    para as em andamento, o de início.
    """
    tipo_trabalho, curso, instituicao = separar_tipo_instituicao(campo(item, 'instituicao'))
    chave_instituicao = chave_de_instituicao(instituicao)

    registro = {}
    if concluida:
        registro['ano_conclusao'] = campo(item, 'ano')
    else:
        registro['ano_inicio'] = campo(item, 'ano')

    registro.update({
        'titulo': campo(item, 'tituloDoTrabalho'),
        'orientando': campo(item, 'nome'),
        'tipo_trabalho': tipo_trabalho,
        'instituicao': instituicao,
        'instituicao_chave': chave_instituicao,
        'instituicao_canonica': vocabulario.resolver_instituicao(chave_instituicao) if vocabulario else '',
        'curso': curso,
        'tipo_orientacao': campo(item, 'tipoDeOrientacao'),
        'agencia_fomento': campo(item, 'agenciaDeFomento'),
    })
    return registro


def bancas_por_tipo(membro):
    bancas = membro.listaParticipacaoEmBancaTrabalho + membro.listaParticipacaoEmBancaComissao
    return {
        chave: [item.json() for item in bancas if item.obter_tipo() == tipo]
        for chave, tipo in TIPOS_DE_BANCA
    }


def campos_de_evento(nome, sigla, edicao, local, veiculo, vocabulario=None):
    """Campos normalizados de um evento (aditivos em relação ao texto bruto).

    ``nome`` é mantido intacto no campo ``evento``; aqui ficam a chave de série
    (edições compartilham a chave), a edição, o local, o veículo e o nome
    canônico quando houver alias em ``dados/aliases/eventos.csv``.
    """
    chave = chave_de_evento(nome, sigla)
    serie, nome_canonico, sigla_canonica = chave, '', ''
    if vocabulario is not None and chave:
        serie, nome_canonico, sigla_canonica = vocabulario.resolver_evento(chave)

    return {
        'evento_sigla': sigla or sigla_canonica,
        'evento_edicao': edicao,
        'evento_local': local,
        'evento_veiculo': veiculo,
        'evento_chave': chave,
        'evento_serie': serie,
        'evento_nome_canonico': nome_canonico,
    }


def campos_do_item_de_evento(item, vocabulario=None):
    return campos_de_evento(campo(item, 'nomeDoEvento'), campo(item, 'sigla'),
                            campo(item, 'edicaoDoEvento'), campo(item, 'localDoEvento'),
                            campo(item, 'veiculoDoEvento'), vocabulario)


def dados_do_pesquisador(membro, vocabulario=None):
    """Monta o dicionário exportado em json/ para um membro.

    Cada lista é serializada a partir dos atributos que o parser realmente
    preenche; campos sem fonte no CV não são inventados.
    """
    return {
        'informacoes_pessoais': {
            'id_lattes': membro.idLattes,
            'nome_completo': membro.nomeCompleto,
            'nome_citacoes': membro.nomeEmCitacoesBibliograficas,
            'sexo': membro.sexo,
            'rotulo': membro.rotulo,
            'periodo': membro.periodo,
            'bolsa_produtividade': membro.bolsaProdutividade,
            'endereco_profissional': membro.enderecoProfissional,
            'atualizacao_cv': membro.atualizacaoCV,
            'url': membro.url,
            'texto_resumo': membro.textoResumo,
        },
        'formacao_academica': [{
            'tipo': campo(item, 'tipo'),
            'nome_instituicao': campo(item, 'nomeInstituicao'),
            'ano_inicio': campo(item, 'anoInicio'),
            'ano_conclusao': campo(item, 'anoConclusao'),
            'descricao': campo(item, 'descricao'),
        } for item in membro.listaFormacaoAcademica],
        'atuacao_profissional': [item.json() for item in membro.listaAtuacaoProfissional],
        'projetos_pesquisa': [item.json() for item in membro.listaProjetoDePesquisa],
        'projetos_extensao': [item.json() for item in membro.listaProjetoDeExtensao],
        'projetos_desenvolvimento': [item.json() for item in membro.listaProjetoDeDesenvolvimento],
        'areas_de_atuacao': [
            {
                'grande_area': parsed[0],
                'area': parsed[1],
                'subarea': parsed[2],
                'especialidade': parsed[3],
                'descricao_completa': campo(item, 'descricao'),
            }
            for item in membro.listaAreaDeAtuacao
            for parsed in [parse_area_de_atuacao(campo(item, 'descricao'))]
        ],
        'idiomas': [{
            'nome': campo(item, 'nome'),
            'compreende': extrair_habilidade_idioma(campo(item, 'proficiencia'), 'Compreende'),
            'fala': extrair_habilidade_idioma(campo(item, 'proficiencia'), 'Fala'),
            'le': extrair_habilidade_idioma(campo(item, 'proficiencia'), 'Lê'),
            'escreve': extrair_habilidade_idioma(campo(item, 'proficiencia'), 'Escreve'),
            'proficiencia_completa': campo(item, 'proficiencia'),
        } for item in membro.listaIdioma],
        'premios_titulos': [{
            'descricao': campo(item, 'descricao'),
            'ano': campo(item, 'ano'),
        } for item in membro.listaPremioOuTitulo],
        'linhas_de_pesquisa': [
            item.json() for item in membro.listaLinhaDePesquisa if item.json() is not None
        ],
        'producao_bibliografica': {
            'artigos_periodicos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'revista': campo(item, 'revista'),
                'volume': campo(item, 'volume'),
                'numero': campo(item, 'numero'),
                'paginas': campo(item, 'paginas'),
                'issn': campo(item, 'issn'),
                'doi': campo(item, 'doi'),
                'periodico_canonico': (vocabulario.resolver_periodico(campo(item, 'issn'))
                                       if vocabulario else ''),
            } for item in membro.listaArtigoEmPeriodico],
            'livros_publicados': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'edicao': campo(item, 'edicao'),
                'editora': campo(item, 'editora'),
                'paginas': campo(item, 'paginas'),
            } for item in membro.listaLivroPublicado],
            'capitulos_livros': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'titulo_livro': campo(item, 'livro'),
                'edicao': campo(item, 'edicao'),
                'editora': campo(item, 'editora'),
                'paginas': campo(item, 'paginas'),
            } for item in membro.listaCapituloDeLivroPublicado],
            'trabalhos_completos_congressos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'evento': campo(item, 'nomeDoEvento'),
                'volume': campo(item, 'volume'),
                'paginas': campo(item, 'paginas'),
                'doi': campo(item, 'doi'),
                **campos_do_item_de_evento(item, vocabulario),
            } for item in membro.listaTrabalhoCompletoEmCongresso],
            'resumos_expandidos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'evento': campo(item, 'nomeDoEvento'),
                'paginas': campo(item, 'paginas'),
                'doi': campo(item, 'doi'),
                **campos_do_item_de_evento(item, vocabulario),
            } for item in membro.listaResumoExpandidoEmCongresso],
            'resumos_congressos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'evento': campo(item, 'nomeDoEvento'),
                'volume': campo(item, 'volume'),
                'paginas': campo(item, 'paginas'),
                'doi': campo(item, 'doi'),
                **campos_do_item_de_evento(item, vocabulario),
            } for item in membro.listaResumoEmCongresso],
            'artigos_aceitos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'revista': campo(item, 'revista'),
                'volume': campo(item, 'volume'),
                'numero': campo(item, 'numero'),
                'paginas': campo(item, 'paginas'),
                'issn': campo(item, 'issn'),
                'doi': campo(item, 'doi'),
            } for item in membro.listaArtigoAceito],
            'apresentacoes_trabalhos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'natureza': campo(item, 'natureza'),
            } for item in membro.listaApresentacaoDeTrabalho],
            'textos_jornais': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'jornal': campo(item, 'nomeJornal'),
                'data': campo(item, 'data'),
                'volume': campo(item, 'volume'),
                'paginas': campo(item, 'paginas'),
            } for item in membro.listaTextoEmJornalDeNoticia],
            'outras_producoes': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'tipo': campo(item, 'tipo'),
                'natureza': campo(item, 'natureza'),
            } for item in membro.listaOutroTipoDeProducaoBibliografica],
        },
        'producao_tecnica': {
            'softwares_com_patente': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'tipo': campo(item, 'tipo'),
            } for item in membro.listaSoftwareComPatente],
            'softwares_sem_patente': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'tipo': campo(item, 'tipo'),
            } for item in membro.listaSoftwareSemPatente],
            'produtos_tecnologicos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'tipo': campo(item, 'tipo'),
            } for item in membro.listaProdutoTecnologico],
            'processos_tecnicas': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'tipo': campo(item, 'tipo'),
                'natureza': campo(item, 'natureza'),
            } for item in membro.listaProcessoOuTecnica],
            'trabalhos_tecnicos': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'tipo': campo(item, 'tipo'),
            } for item in membro.listaTrabalhoTecnico],
            'outras_producoes_tecnicas': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'tipo': campo(item, 'tipo'),
                'natureza': campo(item, 'natureza'),
            } for item in membro.listaOutroTipoDeProducaoTecnica],
            'entrevistas': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'natureza': campo(item, 'natureza'),
            } for item in membro.listaEntrevista],
        },
        'patentes_registros': {
            'patentes': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'numero_registro': campo(item, 'numeroRegistro'),
                'pais': campo(item, 'pais'),
                'tipo_patente': campo(item, 'tipoPatente'),
                'data_deposito': campo(item, 'dataDeposito'),
            } for item in membro.listaPatente],
            'programas_computador': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'numero_registro': campo(item, 'numeroRegistro'),
                'pais': campo(item, 'pais'),
                'tipo_patente': campo(item, 'tipoPatente'),
                'data_deposito': campo(item, 'dataDeposito'),
            } for item in membro.listaProgramaComputador],
            'desenhos_industriais': [{
                'titulo': campo(item, 'titulo'),
                'ano': campo(item, 'ano'),
                'autores': campo(item, 'autores'),
                'numero_registro': campo(item, 'numeroRegistro'),
                'pais': campo(item, 'pais'),
                'tipo_patente': campo(item, 'tipoPatente'),
                'data_deposito': campo(item, 'dataDeposito'),
            } for item in membro.listaDesenhoIndustrial],
        },
        'producao_artistica': [{
            'titulo': campo(item, 'titulo'),
            'ano': campo(item, 'ano'),
            'autores': campo(item, 'autores'),
            'tipo': campo(item, 'tipo'),
            'complemento': campo(item, 'complemento'),
        } for item in membro.listaProducaoArtistica],
        'orientacoes': {
            'em_andamento': {
                'pos_doutorado': [registro_de_orientacao(i, vocabulario=vocabulario) for i in membro.listaOASupervisaoDePosDoutorado],
                'doutorado': [registro_de_orientacao(i, vocabulario=vocabulario) for i in membro.listaOATeseDeDoutorado],
                'mestrado': [registro_de_orientacao(i, vocabulario=vocabulario) for i in membro.listaOADissertacaoDeMestrado],
                'especializacao': [registro_de_orientacao(i, vocabulario=vocabulario) for i in membro.listaOAMonografiaDeEspecializacao],
                'tcc': [registro_de_orientacao(i, vocabulario=vocabulario) for i in membro.listaOATCC],
                'iniciacao_cientifica': [registro_de_orientacao(i, vocabulario=vocabulario) for i in membro.listaOAIniciacaoCientifica],
                'outros': [registro_de_orientacao(i, vocabulario=vocabulario) for i in membro.listaOAOutroTipoDeOrientacao],
            },
            'concluidas': {
                'pos_doutorado': [registro_de_orientacao(i, concluida=True, vocabulario=vocabulario) for i in membro.listaOCSupervisaoDePosDoutorado],
                'doutorado': [registro_de_orientacao(i, concluida=True, vocabulario=vocabulario) for i in membro.listaOCTeseDeDoutorado],
                'mestrado': [registro_de_orientacao(i, concluida=True, vocabulario=vocabulario) for i in membro.listaOCDissertacaoDeMestrado],
                'especializacao': [registro_de_orientacao(i, concluida=True, vocabulario=vocabulario) for i in membro.listaOCMonografiaDeEspecializacao],
                'tcc': [registro_de_orientacao(i, concluida=True, vocabulario=vocabulario) for i in membro.listaOCTCC],
                'iniciacao_cientifica': [registro_de_orientacao(i, concluida=True, vocabulario=vocabulario) for i in membro.listaOCIniciacaoCientifica],
                'outros': [registro_de_orientacao(i, concluida=True, vocabulario=vocabulario) for i in membro.listaOCOutroTipoDeOrientacao],
            },
        },
        'eventos': {
            'participacoes': [{
                'evento': campo(item, 'evento'),
                'apresentacao': campo(item, 'apresentacao'),
                'ano': campo(item, 'ano'),
                'tipo_evento': campo(item, 'tipo_evento'),
                'tipo': campo(item, 'tipo'),
                **campos_de_evento(campo(item, 'evento'), '', '', '', '', vocabulario),
            } for item in membro.listaParticipacaoEmEvento],
            'organizacoes': [{
                'autores': campo(item, 'autores'),
                'evento': campo(item, 'nomeDoEvento'),
                'ano': campo(item, 'ano'),
                'natureza': campo(item, 'natureza'),
                'tipo': campo(item, 'tipo'),
                **campos_de_evento(campo(item, 'nomeDoEvento'), '', '', '', '', vocabulario),
            } for item in membro.listaOrganizacaoDeEvento],
        },
        'bancas': bancas_por_tipo(membro),
        'estatisticas': {
            'total_artigos_periodicos': len(membro.listaArtigoEmPeriodico),
            'total_livros': len(membro.listaLivroPublicado),
            'total_capitulos': len(membro.listaCapituloDeLivroPublicado),
            'total_trabalhos_congressos': len(membro.listaTrabalhoCompletoEmCongresso),
            'total_projetos_pesquisa': len(membro.listaProjetoDePesquisa),
            'total_projetos_extensao': len(membro.listaProjetoDeExtensao),
            'total_projetos_desenvolvimento': len(membro.listaProjetoDeDesenvolvimento),
            'total_orientacoes_concluidas': (len(membro.listaOCSupervisaoDePosDoutorado) +
                                             len(membro.listaOCTeseDeDoutorado) +
                                             len(membro.listaOCDissertacaoDeMestrado) +
                                             len(membro.listaOCIniciacaoCientifica)),
            'total_orientacoes_andamento': (len(membro.listaOASupervisaoDePosDoutorado) +
                                            len(membro.listaOATeseDeDoutorado) +
                                            len(membro.listaOADissertacaoDeMestrado) +
                                            len(membro.listaOAIniciacaoCientifica)),
        },
    }
from . import util
from scriptLattes.membro import Membro
from scriptLattes.compiladorDeListas import CompiladorDeListas
from scriptLattes.geradorDePaginasWeb import GeradorDePaginasWeb
from scriptLattes.grafoDeColaboracoes import *


class Grupo:
    compilador = None
    # Coleções mutáveis ficam como atributos de instância (ver __init__): declaradas aqui
    # como atributos de classe, todos os grupos do mesmo processo compartilhariam a mesma
    # lista — o que somaria os membros de duas execuções no mesmo processo (é o caso da
    # interface gráfica, que roda o pipeline mais de uma vez).
    listaDeParametros = None
    listaDeMembros = None
    listaDeRotulos = None
    vocabulario = None

    arquivoConfiguracao = None
    itemsDesdeOAno = None
    itemsAteOAno = None
    diretorioCache = None



    matrizDeAdjacencia = None
    matrizDeFrequencia = None
    matrizDeFrequenciaNormalizada = None
    vetorDeCoAutoria = None
    grafoDeColaboracoes = None


    colaboradores_endogenos = None
    listaDeColaboracoes = None

    
    listaDeTermos = None
    dicionarioDeTermos = None


    def __init__(self, arquivo):
        self.arquivoConfiguracao = arquivo
        self.membrosComFalha = []
        self.listaDeParametros = []
        self.listaDeMembros = []
        self.listaDeRotulos = []
        self.listaDeTermos = []
        self.dicionarioDeTermos = {}
        self.carregarParametrosPadrao()


        # atualizamos a lista de parametros
        for linha in lerLinhasDeTexto(self.arquivoConfiguracao):
            linha = linha.replace("\r", "")
            linha = linha.replace("\n", "")

            linhaPart = linha.partition("#")  # eliminamos os comentários
            linhaDiv = linhaPart[0].split("=", 1)

            if len(linhaDiv) == 2:
                self.atualizarParametro(linhaDiv[0], linhaDiv[1])

        # carregamos o periodo global
        ano1 = self.obterParametro('global-itens_desde_o_ano')
        ano2 = self.obterParametro('global-itens_ate_o_ano')
        if ano1.lower() == 'hoje':
            ano1 = str(datetime.datetime.now().year)
        if ano2.lower() == 'hoje':
            ano2 = str(datetime.datetime.now().year)
        if ano1 == '':
            ano1 = '0'
        if ano2 == '':
            ano2 = '10000'
        self.itemsDesdeOAno = int(ano1)
        self.itemsAteOAno = int(ano2)

        self.diretorioCache = buscarDiretorio(
            self.obterParametro('global-diretorio_de_armazenamento_de_cvs'), self.arquivoConfiguracao)
        if not self.diretorioCache == '':
            util.criarDiretorio(self.diretorioCache)

        # tabelas de aliases para normalização (dados/aliases/*.csv)
        if self.obterParametro('global-normalizacao'):
            diretorioTabelas = self.obterParametro('global-normalizacao-tabelas')
            if not os.path.isdir(diretorioTabelas):
                # relativo ao arquivo de configuração (não ao diretório de execução) e,
                # por fim, às tabelas que acompanham o programa
                for alternativa in (os.path.join(os.path.dirname(os.path.abspath(self.arquivoConfiguracao)),
                                                 diretorioTabelas),
                                    os.path.join(ABSBASE, diretorioTabelas)):
                    if os.path.isdir(alternativa):
                        diretorioTabelas = alternativa
                        break
            self.vocabulario = Vocabulario(diretorioTabelas)
            print(f"[NORMALIZACAO] tabelas de aliases em {os.path.normpath(diretorioTabelas)}: "
                  f"{len(self.vocabulario.eventos)} eventos, "
                  f"{len(self.vocabulario.instituicoes)} instituições, "
                  f"{len(self.vocabulario.pessoas)} pares de nomes")
        else:
            self.vocabulario = None


        if self.obterParametro('global-identificar_producoes_por_termos') \
                and not self.obterParametro('global-arquivo_de_termos_de_busca'):
            print('[AVISO] O filtro por termos está ligado, mas nenhuma lista de termos foi '
                  'informada em global-arquivo_de_termos_de_busca. O filtro será ignorado.')

        if self.obterParametro('global-identificar_producoes_por_termos') \
                and self.obterParametro('global-arquivo_de_termos_de_busca'):
            # carregamos a lista de termos
            entrada = buscarArquivo(self.obterParametro('global-arquivo_de_termos_de_busca'),
                                    self.arquivoConfiguracao)
            for linha in lerLinhasDeTexto(entrada):
                linha = linha.replace("\r", "")
                linha = linha.replace("\n", "")

                linhaPart = linha.partition("#")  # eliminamos os comentários
                t = linhaPart[0].strip()

                if len(t) > 0:
                    self.listaDeTermos.append(t)
                    nt = eliminar_acentuacao(t)
                    partes = nt.split(" AND ")
                    partes = [x.strip(' ').lower() for x in partes]  # tiramos os espacos
                    self.dicionarioDeTermos[t] = partes 


        # carregamos a lista de membros
        entrada = buscarArquivo(self.obterParametro('global-arquivo_de_entrada'),
                                self.arquivoConfiguracao)

        idSequencial = 0
        for linha in lerLinhasDeTexto(entrada):
            linha = linha.replace("\r", "")
            linha = linha.replace("\n", "")

            linhaPart = linha.partition("#")  # eliminamos os comentários
            linhaDiv = linhaPart[0].split(",")
            if ';' in linhaPart[0] and len(linhaDiv) < 2:
                linhaDiv = linhaPart[0].split(";")
            if '\t' in linhaPart[0] and len(linhaDiv) < 2:
                linhaDiv = linhaPart[0].split("\t")

            if linhaDiv[0].strip():
                identificador = linhaDiv[0].strip() if len(linhaDiv) > 0 else ''
                nome = linhaDiv[1].strip() if len(linhaDiv) > 1 else ''
                periodo = linhaDiv[2].strip() if len(linhaDiv) > 2 else ''
                rotulo = linhaDiv[3].strip() if len(linhaDiv) > 3 and linhaDiv[3].strip() else '* Sem rótulo'

                self.listaDeMembros.append( Membro(idSequencial, identificador, nome, periodo, rotulo, self.itemsDesdeOAno, self.itemsAteOAno, self.diretorioCache, self.dicionarioDeTermos))
                self.listaDeRotulos.append(rotulo)
                idSequencial += 1

        self.listaDeRotulos = list(set(self.listaDeRotulos))  # lista unica de rotulos
        self.listaDeRotulos.sort()



    def gerarArquivosTemporarios(self):
        print ("\n[CRIANDO ARQUIVOS TEMPORARIOS: TXT]")


        # (4) lista unica de colaboradores (orientadores, ou qualquer outro tipo de parceiros...)
        rawIDsColaboradores = list([])
        rawIDsMembros       = list([])
        for membro in self.listaDeMembros:
            rawIDsMembros.append(membro.idLattes)
        for membro in self.listaDeMembros:
            for idColaborador in membro.listaIDLattesColaboradoresUnica:
                if not idColaborador in rawIDsMembros:
                    rawIDsColaboradores.append(idColaborador)
        rawIDsColaboradores = list(set(rawIDsColaboradores))
        self.salvarListaTXT(rawIDsColaboradores, "colaboradores.txt")





    def gerarArquivosJSONIndividuais(self):
        """Exporta um arquivo JSON por pesquisador em <diretorio_de_saida>/json."""
        dir_saida = self.obterParametro('global-diretorio_de_saida')
        json_dir = os.path.join(dir_saida, 'json')
        util.criarDiretorio(json_dir)

        print('\n[GERANDO ARQUIVOS JSON INDIVIDUAIS POR PESQUISADOR]')

        for membro in self.listaDeMembros:
            # Nome do arquivo baseado no nome do pesquisador (sanitizado)
            nome_arquivo = re.sub(r'[^\w\s-]', '', membro.nomeCompleto.strip())
            nome_arquivo = re.sub(r'[-\s]+', '-', nome_arquivo)
            nome_arquivo = f"{membro.idMembro:02d}_{nome_arquivo}_{membro.idLattes}.json"

            caminho_arquivo = os.path.join(json_dir, nome_arquivo)
            try:
                with open(caminho_arquivo, 'w', encoding='utf-8') as arquivo:
                    json.dump(dados_do_pesquisador(membro, self.vocabulario), arquivo, ensure_ascii=False, indent=2)
                print(f'   \u2192 {nome_arquivo}')
            except OSError as e:
                print(f'   \u2717 Erro ao gerar {nome_arquivo}: {e}')

        print(f'\n[ARQUIVOS JSON GERADOS EM: {json_dir}]')

    def carregarDadosCVLattes(self):
        total = len(self.listaDeMembros)
        falhas = []
        inicio = datetime.datetime.now()
        caminho_do_driver = self.obterParametro('global-caminho_do_chromedriver')

        try:
            for indice, membro in enumerate(self.listaDeMembros, start=1):
                membro.caminhoDoChromeDriver = caminho_do_driver
                decorrido = formatar_duracao(datetime.datetime.now() - inicio)
                print(f'\n[{indice}/{total}] {membro.nomeInicial or membro.idLattes} '
                      f'(decorrido: {decorrido})')
                try:
                    membro.carregarDadosCVLattes()
                    membro.filtrarItemsPorPeriodoOuTermos()
                    print(membro)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as excecao:
                    # um currículo problemático não pode derrubar os outros membros
                    falhas.append((membro.nomeInicial or membro.idLattes, membro.idLattes, excecao))
                    print(f'[AVISO] Não foi possível carregar o currículo de '
                          f'{membro.nomeInicial or membro.idLattes} ({membro.idLattes}): {excecao}')
                    print('[AVISO] Os demais membros continuam sendo processados.')
        finally:
            fechar_driver()          # a sessão do navegador não é mais necessária

        if falhas:
            print('\n[ATENÇÃO] Os relatórios abaixo NÃO incluem os seguintes currículos:')
            for nome, identificador, excecao in falhas:
                print(f'  - {nome} ({identificador}): {excecao}')
                erro = classificar(excecao)
                if erro.solucoes and erro.titulo != 'Erro inesperado':
                    print(f'    {erro.titulo}. {erro.solucoes[0]}')
            print('Reexecute o mesmo comando para tentar de novo: os currículos já baixados '
                  'são reaproveitados e a execução continua de onde parou.')
        self.membrosComFalha = falhas


    def gerarPaginasWeb(self):
        paginasWeb = GeradorDePaginasWeb(self)


    def compilarListasDeItems(self):
        self.compilador = CompiladorDeListas(self)  # compilamos todo e criamos 'listasCompletas'

        # Grafos de coautoria
        self.compilador.criarMatrizesDeColaboracao()

        [self.matrizDeAdjacencia, self.matrizDeFrequencia, self.listaDeColaboracoes] = self.compilador.uniaoDeMatrizesDeColaboracao()
        self.vetorDeCoAutoria = self.matrizDeFrequencia.sum(axis=1)  # soma das linhas = num. de items feitos em co-autoria (parceria) com outro membro do grupo
        self.matrizDeFrequenciaNormalizada = self.matrizDeFrequencia.copy()

        for i in range(0, self.numeroDeMembros()):
            if not self.vetorDeCoAutoria[i].item() == 0:
                self.matrizDeFrequenciaNormalizada[i, :] /= float(self.vetorDeCoAutoria[i].item())



    def salvarListaTXT(self, lista, nomeArquivo):
        dir = self.obterParametro('global-diretorio_de_saida')
        arquivo = open(dir + "/" + nomeArquivo, 'w', encoding='utf8')

        for i in range(0, len(lista)):
            elemento = lista[i]
            if not type(elemento) == type(str()):
                elemento = str(elemento)
            arquivo.write(elemento + '\n')
        arquivo.close()

    def gerarGrafosDeColaboracoes(self):
        if self.obterParametro('grafo-mostrar_grafo_de_colaboracoes'):
            grafoDeColaboracoes = GrafoDeColaboracoes(self)
            self.grafoDeColaboracoes = grafoDeColaboracoes.criar_grafo_com_pesos()
            self.identificar_lista_de_colaboradores_endogenos()



    def numeroDeMembros(self):
        return len(self.listaDeMembros)

    def imprimirListaDeRotulos(self):
        print()
        for (i, r) in enumerate(self.listaDeRotulos):
            print(f"[ROTULO] {i+1}\t{r}")
    
    def imprimirListaDeTermos(self):
        print()
        for (i, t) in enumerate(self.listaDeTermos):
            print(f"[TERMO] {i+1}\t{t:40s}\t{self.dicionarioDeTermos[t]}")

    def atualizarParametro(self, parametro, valor):
        parametro = parametro.strip().lower()
        valor = valor.strip()

        for i in range(0, len(self.listaDeParametros)):
            if parametro == self.listaDeParametros[i][0]:
                self.listaDeParametros[i][1] = valor
                return
        print(("[AVISO IMPORTANTE] Nome de parametro desconhecido: ") + parametro)

    def obterParametro(self, parametro):
        for i in range(0, len(self.listaDeParametros)):
            if parametro == self.listaDeParametros[i][0]:
                if self.listaDeParametros[i][1].lower() in ('sim', '1', 'true', 'yes'):
                    return 1
                if self.listaDeParametros[i][1].lower() in ('nao', 'não', '0', 'false', 'no'):
                    return 0

                return self.listaDeParametros[i][1]

    def carregarParametrosPadrao(self):
        self.listaDeParametros.append(['global-nome_do_grupo', ''])
        self.listaDeParametros.append(['global-arquivo_de_entrada', ''])
        self.listaDeParametros.append(['global-diretorio_de_saida', ''])
        self.listaDeParametros.append(['global-email_do_admin', ''])
        self.listaDeParametros.append(['global-idioma', 'PT'])
        self.listaDeParametros.append(['global-itens_desde_o_ano', ''])
        self.listaDeParametros.append(['global-itens_ate_o_ano', ''])  # hoje
        self.listaDeParametros.append(['global-itens_por_pagina', '5000'])
        self.listaDeParametros.append(['global-diretorio_de_armazenamento_de_cvs', './cache/'])
        # caminho do ChromeDriver. Vazio (padrão) = usar o ChromeDriver baixado
        # automaticamente pelo Selenium Manager, conforme o Chrome instalado.
        self.listaDeParametros.append(['global-caminho_do_chromedriver', ''])

        self.listaDeParametros.append(['global-identificar_producoes_por_termos', 'nao'])
        self.listaDeParametros.append(['global-arquivo_de_termos_de_busca', ''])

        # normalização dos textos coletados (ver scriptLattes/normalizacao.py)
        self.listaDeParametros.append(['global-normalizacao', 'sim'])
        self.listaDeParametros.append(['global-normalizacao-tabelas', './dados/aliases/'])

        self.listaDeParametros.append(['relatorio-incluir_artigo_em_periodico', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_livro_publicado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_capitulo_de_livro_publicado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_texto_em_jornal_de_noticia', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_trabalho_completo_em_congresso', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_resumo_expandido_em_congresso', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_resumo_em_congresso', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_artigo_aceito_para_publicacao', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_apresentacao_de_trabalho', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_outro_tipo_de_producao_bibliografica', 'sim'])

        self.listaDeParametros.append(['relatorio-incluir_software_com_registro', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_software_sem_registro', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_produto_tecnologico', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_processo_ou_tecnica', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_trabalho_tecnico', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_outro_tipo_de_producao_tecnica', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_entrevista_mesas_e_comentarios', 'sim'])

        self.listaDeParametros.append(['relatorio-incluir_patente', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_programa_computador', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_desenho_industrial', 'sim'])

        self.listaDeParametros.append(['relatorio-incluir_producao_artistica', 'sim'])

        self.listaDeParametros.append(['relatorio-mostrar_orientacoes', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_em_andamento_pos_doutorado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_em_andamento_doutorado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_em_andamento_mestrado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_em_andamento_monografia_de_especializacao', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_em_andamento_tcc', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_em_andamento_iniciacao_cientifica', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_em_andamento_outro_tipo', 'sim'])

        self.listaDeParametros.append(['relatorio-incluir_orientacao_concluida_pos_doutorado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_concluida_doutorado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_concluida_mestrado', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_concluida_monografia_de_especializacao', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_concluida_tcc', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_concluida_iniciacao_cientifica', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_orientacao_concluida_outro_tipo', 'sim'])

        self.listaDeParametros.append(['relatorio-incluir_projeto', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_premio', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_participacao_em_evento', 'sim'])
        self.listaDeParametros.append(['relatorio-incluir_organizacao_de_evento', 'sim'])

        self.listaDeParametros.append(['grafo-mostrar_grafo_de_colaboracoes', 'sim'])
        self.listaDeParametros.append(['grafo-mostrar_todos_os_nos_do_grafo', 'sim'])
        self.listaDeParametros.append(['grafo-considerar_rotulos_dos_membros_do_grupo', 'sim'])

        self.listaDeParametros.append(['grafo-incluir_artigo_em_periodico', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_livro_publicado', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_capitulo_de_livro_publicado', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_texto_em_jornal_de_noticia', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_trabalho_completo_em_congresso', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_resumo_expandido_em_congresso', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_resumo_em_congresso', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_artigo_aceito_para_publicacao', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_apresentacao_de_trabalho', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_outro_tipo_de_producao_bibliografica', 'sim'])

        self.listaDeParametros.append(['grafo-incluir_software_com_registro', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_software_sem_registro', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_produto_tecnologico', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_processo_ou_tecnica', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_trabalho_tecnico', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_outro_tipo_de_producao_tecnica', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_entrevista_mesas_e_comentarios', 'sim'])

        self.listaDeParametros.append(['grafo-incluir_patente', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_programa_computador', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_desenho_industrial', 'sim'])

        self.listaDeParametros.append(['grafo-incluir_producao_artistica', 'sim'])
        self.listaDeParametros.append(['grafo-incluir_grau_de_colaboracao', 'nao'])


        # metricas
        self.listaDeParametros.append(['relatorio-incluir_metricas', 'nao'])

    def identificar_lista_de_colaboradores_endogenos(self):
        self.colaboradores_endogenos = (list([]))
        for i in range(0, self.numeroDeMembros()):
            self.colaboradores_endogenos.append(list([]))
        for i in range(0, self.numeroDeMembros()):
            for j in range(0, self.numeroDeMembros()):
                if i!=j and self.matrizDeAdjacencia[i,j]>0:
                    self.colaboradores_endogenos[i].append( (j, self.matrizDeAdjacencia[i,j]) )
        
        #for i in range(0, self.numeroDeMembros()):
        #    print ( self.colaboradores_endogenos[i] )
