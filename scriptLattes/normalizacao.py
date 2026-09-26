#!/usr/bin/env python
# encoding: utf-8
"""Normalização dos textos coletados dos CVs Lattes.

Camadas (todas determinísticas, sem estado global):

L1 estrutura
    ``separar_citacao_de_evento`` / ``estruturar_evento`` decompõem a citação
    do Lattes (``EVENTO, ANO, LOCAL. VEÍCULO``) nos campos corretos, evitando
    que a cauda da citação fique colada no nome do evento.

L2 chave mecânica
    ``normalizar_chave``, ``separar_edicao``, ``detectar_sigla``,
    ``chave_de_evento``, ``chave_de_instituicao`` geram chaves ASCII estáveis
    (idempotentes) a partir do texto bruto.

L3 identidade
    ``partes_de_pessoa`` / ``mesma_pessoa`` para nomes de autores e
    ``Vocabulario`` para as tabelas de aliases versionadas em
    ``dados/aliases/`` (eventos, instituições, periódicos e pares forçados de
    nomes de pesquisadores).

Nada aqui faz merge automático por similaridade difusa: só há casamento exato
(identificador ou chave) ou regras explícitas das tabelas. Candidatos a merge
são apenas *relatados* (``relatorio_de_candidatos``) para revisão humana.

Uso como relatório::

    python -m scriptLattes.normalizacao --saida exemplo/teste-01 --destino dados/aliases
"""
import csv
import difflib
import glob
import json
import os
import re
import unicodedata

try:
    from rapidfuzz import fuzz as _fuzz
except ImportError:  # pragma: no cover - rapidfuzz é dependência do projeto
    _fuzz = None

# --------------------------------------------------------------------------- #
# L2 - chaves mecânicas
# --------------------------------------------------------------------------- #

ROMANOS = (
    'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
    'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx',
    'xxi', 'xxii', 'xxiii', 'xxiv', 'xxv', 'xxvi', 'xxvii', 'xxviii', 'xxix', 'xxx',
    'xxxi', 'xxxii', 'xxxiii', 'xxxiv', 'xxxv', 'xxxvi', 'xxxvii', 'xxxviii', 'xxxix', 'xl',
    'xli', 'xlii', 'xliii', 'xliv', 'xlv',
)

# 'º' (ordinal masculino), '°' (grau, usado no CV como ordinal) e sufixos em inglês
SUFIXO_ORDINAL = r'(?:º|ª|°|o|a|th|nd|rd|st)'
RE_ORDINAL = re.compile(rf'^(\d{{1,3}}\s*{SUFIXO_ORDINAL}?)\s+(?=\S)', re.IGNORECASE)
RE_ORDINAL_COLADO = re.compile(rf'^(\d{{1,3}}{SUFIXO_ORDINAL})(?=[A-Za-zÀ-ÿ])')
RE_ORDINAL_FINAL = re.compile(rf'\s+(\d{{1,3}}\s*{SUFIXO_ORDINAL}?)\s*$', re.IGNORECASE)
RE_ROMANO = re.compile(r'^([IVXLCDM]{1,7})\.?\s+(?=\S)')
RE_SIGLA_PARENTESES = re.compile(
    r'\(\s*([A-Za-z][A-Za-z0-9&./-]{1,14})(?:\s+((?:19|20)\d\d))?\s*\)\s*$')
RE_SIGLA_PREFIXO = re.compile(r'^([A-Z][A-Z0-9&./-]{1,14})\s+((?:19|20)\d\d)\s*:\s*(.+)$')
RE_ROMANO_APOS_SIGLA = re.compile(r'^[A-Z][A-Z0-9&./-]{1,14}\s+(?:19|20)\d\d\s*:\s*([IVXLCDM]{1,7})\.?\s+(?=\S)')
RE_ANO_ENTRE_VIRGULAS = re.compile(r',\s*((?:19|20)\d\d)\s*(?=,|\.|$)')


def normalizar_chave(texto):
    """Chave ASCII determinística: sem acentos, minúscula, sem pontuação.

    Idempotente: ``normalizar_chave(normalizar_chave(x)) == normalizar_chave(x)``.
    """
    if texto is None:
        return ''
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[^a-zA-Z0-9]+', ' ', texto.lower())
    return ' '.join(texto.split())


def eh_romano(token):
    return token.strip().rstrip('.').lower() in ROMANOS


def separar_edicao(nome):
    """Retira a edição (romano ou ordinal) do nome do evento.

    Aceita edição no início, colada à palavra (``'53ocongresso ...'``) e no fim
    (``'... da usp 6o'``), pois o CV Lattes varia bastante:

    ``'XV Congresso Brasileiro de Estomaterapia'`` -> ``('Congresso ...', 'XV')``
    ``'22nd Brazilian Symposium ...'``             -> ``('Brazilian Symposium ...', '22nd')``
    ``'53ocongresso brasileiro de enfermagem'``    -> ``('congresso brasileiro de enfermagem', '53o')``
    """
    if not nome:
        return '', ''

    texto = ' '.join(str(nome).split()).strip()
    edicao = ''

    for _ in range(2):
        m = RE_ORDINAL.match(texto)
        if m:
            edicao = (edicao + ' ' + m.group(1).strip()).strip()
            texto = texto[m.end():].strip()
            continue
        m = RE_ORDINAL_COLADO.match(texto)
        if m:
            edicao = (edicao + ' ' + m.group(1).strip()).strip()
            texto = texto[m.end():].strip()
            continue
        m = RE_ROMANO.match(texto)
        if m and eh_romano(m.group(1)):
            edicao = (edicao + ' ' + m.group(1).rstrip('.')).strip()
            texto = texto[m.end():].strip()
            continue
        break

    m = RE_ORDINAL_FINAL.search(texto)
    if m:
        edicao = (edicao + ' ' + m.group(1).strip()).strip()
        texto = texto[:m.start()].strip()

    return texto, edicao


def detectar_sigla(nome):
    """Detecta a sigla do evento e o ano associado a ela.

    Aceita ``'(SBES 2025)'``, ``'(SBES)'`` e ``'SBES 2025: ...'``.
    Devolve ``(sigla, ano)`` sem alterar o nome exibido.
    """
    if not nome:
        return '', ''

    texto = ' '.join(str(nome).split()).strip()

    m = RE_SIGLA_PARENTESES.search(texto)
    if m:
        return m.group(1), (m.group(2) or '')

    m = RE_SIGLA_PREFIXO.match(texto)
    if m:
        return m.group(1), m.group(2)

    return '', ''


def chave_de_evento(nome, sigla=''):
    """Chave de *série* do evento (edições compartilham a mesma chave).

    Usa a sigla informada (ou detectada no próprio nome) quando disponível;
    caso contrário usa o nome sem edição e sem o trecho entre parênteses.
    """
    if not str(sigla or '').strip():
        sigla, _ = detectar_sigla(nome)

    if sigla and str(sigla).strip():
        return normalizar_chave(sigla)

    nome_sem_edicao, _ = separar_edicao(nome)
    nome_sem_edicao = re.sub(r'\([^)]*\)', ' ', nome_sem_edicao)
    return normalizar_chave(nome_sem_edicao)


def chave_de_instituicao(nome):
    """Chave mecânica de instituição (sem acento/caixa/pontuação)."""
    return normalizar_chave(nome)


def _vazio():
    return {'nome': '', 'edicao': '', 'sigla': '', 'ano': '', 'local': '', 'veiculo': ''}


def separar_citacao_de_evento(texto):
    """Decompõe a citação de evento do CV Lattes.

    Formatos observados no corpus::

        'EVENTO, 2020, Local. Veículo'
        'EVENTO (SIGLA 2013),, 2013, Local, UF. Anais do EVENTO, 2013'
        '22nd EVENTO (SIGLA 2026)'
        'SIGLA 2023: XXXVII EVENTO'

    O nome devolvido mantém a edição (fidelidade de exibição); a chave de série
    é obtida com :func:`chave_de_evento`.
    """
    resultado = _vazio()
    if not texto:
        return resultado

    resto = ' '.join(str(texto).split()).strip()

    # sigla na forma prefixada ('SBES 2023: XXXVII ...')
    m = RE_SIGLA_PREFIXO.match(resto)
    if m:
        resultado['sigla'] = m.group(1)
        resultado['ano'] = m.group(2)

    # edição "escondida" depois da sigla: 'SBES 2023: XXXVII Brazilian ...'
    m = RE_ROMANO_APOS_SIGLA.match(resto)
    if m and eh_romano(m.group(1)):
        resultado['edicao'] = m.group(1)

    # ano da citação: ', 2020,' ou ', 2020.' (evita casar o ano dentro do nome)
    m = RE_ANO_ENTRE_VIRGULAS.search(resto)
    if m:
        resultado['ano'] = resultado['ano'] or m.group(1)
        cauda = resto[m.end():].lstrip(' ,')
        nome = resto[:m.start()].rstrip(' ,')

        local, _, veiculo = cauda.partition('. ')
        resultado['local'] = local.strip().rstrip(',').strip()
        veiculo = veiculo.strip()
        veiculo = re.sub(r',\s*(?:19|20)\d\d\s*$', '', veiculo).strip().rstrip('.')
        resultado['veiculo'] = veiculo
        resto = nome

    resto = resto.rstrip(' ,').rstrip('.').strip()

    # sigla entre parênteses no fim do nome do evento
    if not resultado['sigla']:
        sigla, ano = detectar_sigla(resto)
        resultado['sigla'] = sigla
        resultado['ano'] = resultado['ano'] or ano

    if not resultado['edicao']:
        _, edicao = separar_edicao(resto)
        resultado['edicao'] = edicao

    resultado['nome'] = resto
    return resultado


def estruturar_evento(texto):
    """Como :func:`separar_citacao_de_evento`, removendo antes páginas/volume."""
    texto = ' '.join(str(texto or '').split()).strip()
    if not texto:
        return _vazio()

    texto = re.sub(r'\s*,?\s*p\.\s*[\d\s\-–.]+$', '', texto)          # ', p. 154.'
    texto = re.sub(r'\s*,?\s*v\.\s*[A-Za-z0-9\-–]+\s*,?\s*$', '', texto)  # ', v. 3'
    return separar_citacao_de_evento(texto.strip().rstrip(',').rstrip('.'))


def estruturar_evento_do_item(item):
    """Estrutura o evento a partir do item bruto do CV (texto após ``In:``).

    Devolve o mesmo dicionário de :func:`separar_citacao_de_evento`; se o item
    não tiver a marca ``In:``, devolve campos vazios (o chamador mantém o que
    já havia extraído).
    """
    partes = str(item or '').partition(' In: ')
    if not partes[1]:
        return _vazio()
    return estruturar_evento(partes[2])


# --------------------------------------------------------------------------- #
# L3 - pessoas
# --------------------------------------------------------------------------- #

SUFIXOS = {'jr': 'jr', 'junior': 'jr', 'filho': 'filho', 'neto': 'neto', 'sobrinho': 'sobrinho'}
PARTICULAS = {'de', 'da', 'do', 'das', 'dos', 'e', 'del', 'della', 'di', 'van', 'von', 'der', 'la', 'le'}


def partes_de_pessoa(nome):
    """Decompõe um nome de autor no formato Lattes.

    Usa a vírgula como pista forte de onde termina o sobrenome
    (``'SANTOS JUNIOR, Paulo Sergio dos'``), com heurística de fallback quando
    ela não existe (``'Paulo Sergio dos Santos Junior'``).
    """
    original = str(nome or '')
    if ',' in original:
        parte_sobrenome, _, parte_prenomes = original.partition(',')
    else:
        parte_sobrenome, parte_prenomes = '', original

    sufixo = ''
    tokens_sobrenome = []
    for token in normalizar_chave(parte_sobrenome).split():
        if token in SUFIXOS and not sufixo:
            sufixo = SUFIXOS[token]
        elif token in PARTICULAS and len(token) > 1:
            continue
        else:
            tokens_sobrenome.append(token)

    prenomes = []
    for token in normalizar_chave(parte_prenomes).split():
        if token in SUFIXOS and not sufixo:
            sufixo = SUFIXOS[token]
        elif token in PARTICULAS and len(token) > 1:
            continue
        else:
            prenomes.append(token)

    if tokens_sobrenome:
        sobrenome = tokens_sobrenome[-1]
    else:
        # sem sobrenome explícito (ex.: 'JR., PAULO S. SANTOS' ou
        # 'Paulo Sergio dos Santos Junior'): o sobrenome é o último token
        # significativo da parte dos prenomes
        significativos = [t for t in prenomes if len(t) > 1]
        sobrenome = significativos[-1] if significativos else (prenomes[-1] if prenomes else '')
        if sobrenome in prenomes:
            prenomes = list(prenomes)
            prenomes.remove(sobrenome)

    return {'sobrenome': sobrenome, 'sufixo': sufixo, 'prenomes': prenomes}


def chave_de_pessoa(nome):
    """Chave conservadora: sobrenome + sufixo + iniciais dos prenomes."""
    p = partes_de_pessoa(nome)
    iniciais = ''.join(t[0] for t in p['prenomes'])
    return ' '.join(x for x in (p['sobrenome'], p['sufixo'], iniciais) if x)


def _prenomes_compativeis(a, b):
    if not a or not b:
        return False  # sem prenome nos dois lados não arriscamos um merge

    for x, y in zip(a, b):
        if len(x) == 1 and len(y) == 1:
            if x != y:
                return False
        elif len(x) == 1:
            if x != y[0]:
                return False
        elif len(y) == 1:
            if y != x[0]:
                return False
        elif x != y:
            return False
    return True


def mesma_pessoa(nome_a, nome_b):
    """Heurística conservadora de identidade para nomes de autores.

    Exige mesmo sobrenome, mesmo sufixo (jr/filho/...) e prenomes compatíveis
    (iniciais expandem nomes completos; nomes completos precisam ser iguais).
    """
    if not nome_a or not nome_b:
        return False
    if normalizar_chave(nome_a) == normalizar_chave(nome_b):
        return True

    a, b = partes_de_pessoa(nome_a), partes_de_pessoa(nome_b)
    if not a['sobrenome'] or a['sobrenome'] != b['sobrenome']:
        return False
    if a['sufixo'] != b['sufixo']:
        return False
    return _prenomes_compativeis(a['prenomes'], b['prenomes'])


# --------------------------------------------------------------------------- #
# L3 - vocabulário (tabelas de aliases versionadas)
# --------------------------------------------------------------------------- #

TABELAS = {
    'eventos': ('eventos.csv', ('chave', 'serie', 'sigla', 'nome_canonico')),
    'instituicoes': ('instituicoes.csv', ('chave', 'nome_canonico')),
    'periodicos': ('periodicos.csv', ('issn', 'nome_canonico')),
    'pesquisadores': ('pesquisadores.csv', ('nome_a', 'nome_b')),
}


class Vocabulario:
    """Tabelas de aliases preenchidas manualmente (``dados/aliases/*.csv``).

    Todas as decisões de agrupamento ficam auditáveis no CSV: nada é agrupado
    automaticamente por similaridade.
    """

    def __init__(self, diretorio=None):
        self.diretorio = diretorio
        self.eventos = {}        # chave -> {'serie', 'sigla', 'nome_canonico'}
        self.instituicoes = {}   # chave -> nome_canonico
        self.periodicos = {}     # issn -> nome_canonico
        self.pessoas = set()     # frozenset({chave_a, chave_b}) forçados
        if diretorio:
            self.carregar(diretorio)

    # -- carga -------------------------------------------------------------- #
    @staticmethod
    def _ler(caminho):
        if not os.path.isfile(caminho):
            return []
        with open(caminho, encoding='utf-8-sig', newline='') as arquivo:
            return [linha for linha in csv.DictReader(arquivo)]

    @staticmethod
    def _ler_linhas(caminho):
        """Linhas cruas (sem cabeçalho), tolerantes a vírgulas não citadas."""
        if not os.path.isfile(caminho):
            return []
        with open(caminho, encoding='utf-8-sig', newline='') as arquivo:
            linhas = list(csv.reader(arquivo))
        return linhas[1:] if linhas else []

    def carregar(self, diretorio):
        self.diretorio = diretorio

        for linha in self._ler(os.path.join(diretorio, 'eventos.csv')):
            chave = normalizar_chave(linha.get('chave', ''))
            if not chave:
                continue
            serie = normalizar_chave(linha.get('serie', '')) or chave
            self.eventos[chave] = {
                'serie': serie,
                'sigla': (linha.get('sigla') or '').strip(),
                'nome_canonico': (linha.get('nome_canonico') or '').strip(),
            }

        for linha in self._ler(os.path.join(diretorio, 'instituicoes.csv')):
            chave = normalizar_chave(linha.get('chave', ''))
            if chave:
                self.instituicoes[chave] = (linha.get('nome_canonico') or '').strip()

        for linha in self._ler(os.path.join(diretorio, 'periodicos.csv')):
            issn = (linha.get('issn') or '').strip()
            if issn:
                self.periodicos[issn] = (linha.get('nome_canonico') or '').strip()

        for linha in self._ler_linhas(os.path.join(diretorio, 'pesquisadores.csv')):
            # nomes de autores contêm vírgulas: tudo depois da primeira coluna é
            # o segundo nome (aceita tanto "A,B" quanto "A,B, C")
            if len(linha) < 2:
                continue
            a = normalizar_chave(linha[0])
            b = normalizar_chave(','.join(linha[1:]))
            if a and b:
                self.pessoas.add(frozenset((a, b)))

        return self

    # -- consultas ---------------------------------------------------------- #
    def resolver_evento(self, chave):
        """Devolve ``(serie, nome_canonico, sigla)`` para a chave de evento."""
        registro = self.eventos.get(chave)
        if not registro:
            return chave, '', ''
        return registro['serie'], registro['nome_canonico'], registro['sigla']

    def resolver_instituicao(self, chave):
        return self.instituicoes.get(chave, '')

    def resolver_periodico(self, issn):
        return self.periodicos.get((issn or '').strip(), '')

    def pessoas_equivalentes(self, nome_a, nome_b):
        par = frozenset((normalizar_chave(nome_a), normalizar_chave(nome_b)))
        if len(par) < 2:
            return True
        return par in self.pessoas

    def mesma_pessoa(self, nome_a, nome_b):
        """Equivalência forçada pela tabela ou heurística conservadora."""
        if self.pessoas_equivalentes(nome_a, nome_b):
            return True
        return mesma_pessoa(nome_a, nome_b)


# --------------------------------------------------------------------------- #
# Relatório de candidatos (revisão humana)
# --------------------------------------------------------------------------- #

SECOES_COM_EVENTO = (
    ('trabalhos_completos_congressos', 'produção bibliográfica / trabalhos completos'),
    ('resumos_expandidos', 'produção bibliográfica / resumos expandidos'),
    ('resumos_congressos', 'produção bibliográfica / resumos em congresso'),
)


def _escrever_csv(caminho, colunas, linhas):
    os.makedirs(os.path.dirname(caminho) or '.', exist_ok=True)
    with open(caminho, 'w', encoding='utf8', newline='') as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(colunas)
        escritor.writerows(linhas)


PALAVRAS_GENERICAS = {
    'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'em', 'the', 'of', 'on', 'for', 'and',
    'internacional', 'international', 'ibero', 'americano', 'america', 'latino', 'latin',
    'usp', 'universidade', 'university', 'sao', 'paulo', 'anual', 'annual',
}


def _similaridade(a, b):
    if _fuzz is not None:
        return _fuzz.ratio(a, b)
    return difflib.SequenceMatcher(None, a, b).ratio() * 100


def _candidato_a_mesma_serie(chave_a, chave_b, limiar=92):
    """Diz se duas chaves são fortes candidatas à mesma entidade.

    Só dois casos, ambos conservadores:

    * uma chave difere da outra apenas por palavras genéricas
      (``'simposio de iniciacao cientifica da usp'`` vs
      ``'simposio internacional de iniciacao cientifica da universidade de sao paulo'``);
    * as chaves são quase idênticas caractere a caractere (erros de digitação:
      ``'invetigacion'`` vs ``'investigacion'``).
    """
    tokens_a, tokens_b = set(chave_a.split()), set(chave_b.split())
    diferenca = tokens_a ^ tokens_b
    if diferenca and all(token in PALAVRAS_GENERICAS or len(token) <= 2 for token in diferenca):
        return True

    return _similaridade(chave_a, chave_b) >= limiar


def agrupar_similares(ocorrencias, limiar=92):
    """Sugere grupos de chaves que podem ser a mesma entidade (sem fazer merge).

    Devolve uma lista de grupos (cada grupo é uma decisão a tomar), ordenada por
    total de ocorrências: ``{'chaves': [...], 'total': n, 'nota_minima': x}``.
    Nada é agrupado no resultado do scriptLattes por causa disso.
    """
    chaves = sorted(ocorrencias)
    pai = {chave: chave for chave in chaves}

    def raiz(chave):
        while pai[chave] != chave:
            pai[chave] = pai[pai[chave]]
            chave = pai[chave]
        return chave

    notas = {}
    for i, chave_a in enumerate(chaves):
        for chave_b in chaves[i + 1:]:
            if not _candidato_a_mesma_serie(chave_a, chave_b, limiar):
                continue
            notas[frozenset((chave_a, chave_b))] = round(_similaridade(chave_a, chave_b), 1)
            raiz_a, raiz_b = raiz(chave_a), raiz(chave_b)
            if raiz_a != raiz_b:
                pai[max(raiz_a, raiz_b)] = min(raiz_a, raiz_b)

    grupos = {}
    for chave in chaves:
        grupos.setdefault(raiz(chave), []).append(chave)

    resultado = []
    for membros in grupos.values():
        if len(membros) < 2:
            continue
        membros = sorted(membros, key=lambda c: (-ocorrencias[c], c))
        do_grupo = [nota for par, nota in notas.items() if set(par) <= set(membros)]
        resultado.append({
            'chaves': membros,
            'total': sum(ocorrencias[c] for c in membros),
            'nota_minima': min(do_grupo) if do_grupo else limiar,
        })

    resultado.sort(key=lambda grupo: (-grupo['total'], grupo['chaves'][0]))
    return resultado


def relatorio_de_candidatos(diretorio_saida, destino, vocabulario=None):
    """Gera as listas de candidatos a revisão a partir dos JSONs gerados.

    Escreve em ``destino`` (nunca sobrescreve as tabelas preenchidas à mão):

    * ``pendentes_eventos.csv``      - chaves de evento ainda sem alias
    * ``pendentes_instituicoes.csv`` - instituições de orientação sem alias
    * ``pendentes_periodicos.csv``   - artigos sem ISSN (sem chave forte)
    * ``pendentes_pesquisadores.csv``- nomes de autores não atribuídos a membros
    """
    vocabulario = vocabulario or Vocabulario()

    eventos = {}
    instituicoes = {}
    periodicos_sem_issn = {}
    autores = {}
    membros = []

    arquivos = sorted(glob.glob(os.path.join(diretorio_saida, 'json', '*.json')))
    for caminho in arquivos:
        with open(caminho, encoding='utf8') as arquivo:
            dados = json.load(arquivo)
        membros.append(dados['informacoes_pessoais'])

        for secao, _ in SECOES_COM_EVENTO:
            for registro in dados['producao_bibliografica'][secao]:
                nome = registro.get('evento') or ''
                if not nome:
                    continue
                sigla = registro.get('evento_sigla', '') or detectar_sigla(nome)[0]
                chave = registro.get('evento_chave') or chave_de_evento(nome, sigla)
                registro_evento = eventos.setdefault(chave, {'ocorrencias': 0, 'edicoes': set(), 'exemplos': set()})
                registro_evento['ocorrencias'] += 1
                if registro.get('evento_edicao'):
                    registro_evento['edicoes'].add(registro['evento_edicao'])
                if len(registro_evento['exemplos']) < 3:
                    registro_evento['exemplos'].add(nome)

        for grupo in dados['orientacoes'].values():
            for lista in grupo.values():
                for registro in lista:
                    instituicao = (registro.get('instituicao') or '').strip()
                    chave = chave_de_instituicao(instituicao)
                    if not chave:
                        continue
                    registro_inst = instituicoes.setdefault(chave, {'ocorrencias': 0, 'exemplos': set()})
                    registro_inst['ocorrencias'] += 1
                    if len(registro_inst['exemplos']) < 3:
                        registro_inst['exemplos'].add(instituicao)

        for registro in dados['producao_bibliografica']['artigos_periodicos']:
            if not (registro.get('issn') or '').strip():
                nome = (registro.get('revista') or '').strip()
                if nome:
                    periodicos_sem_issn[nome] = periodicos_sem_issn.get(nome, 0) + 1

    # autores: renderizações que não casam com nenhum membro
    membros_por_sobrenome = {}
    for membro in membros:
        variantes = [membro.get('nome_completo')]
        variantes += [v.strip() for v in (membro.get('nome_citacoes') or '').split(';')]
        for variante in variantes:
            if variante:
                membros_por_sobrenome.setdefault(partes_de_pessoa(variante)['sobrenome'], []).append(variante)

    for caminho in arquivos:
        with open(caminho, encoding='utf8') as arquivo:
            dados = json.load(arquivo)
        for secao in dados['producao_bibliografica'].values():
            if not isinstance(secao, list):
                continue
            for registro in secao:
                for autor in (registro.get('autores') or '').split(';'):
                    autor = ' '.join(autor.split())
                    if len(autor) < 5:
                        continue
                    candidatos = membros_por_sobrenome.get(partes_de_pessoa(autor)['sobrenome'], [])
                    if any(vocabulario.mesma_pessoa(autor, candidato) for candidato in candidatos):
                        continue
                    registro_autor = autores.setdefault(autor, {'ocorrencias': 0, 'candidatos': set()})
                    registro_autor['ocorrencias'] += 1
                    for candidato in candidatos[:3]:
                        registro_autor['candidatos'].add(candidato)

    linhas_eventos = [(chave, r['ocorrencias'], '|'.join(sorted(r['edicoes'])), ' || '.join(sorted(r['exemplos'])))
                      for chave, r in eventos.items()]
    _escrever_csv(os.path.join(destino, 'pendentes_eventos.csv'),
                  ('chave', 'ocorrencias', 'edicoes', 'exemplos'),
                  sorted(linhas_eventos, key=lambda linha: (-linha[1], linha[0])))

    linhas_instituicoes = [(chave, r['ocorrencias'], ' || '.join(sorted(r['exemplos'])))
                           for chave, r in instituicoes.items()]
    _escrever_csv(os.path.join(destino, 'pendentes_instituicoes.csv'),
                  ('chave', 'ocorrencias', 'exemplos'),
                  sorted(linhas_instituicoes, key=lambda linha: (-linha[1], linha[0])))

    _escrever_csv(os.path.join(destino, 'pendentes_periodicos.csv'),
                  ('revista', 'ocorrencias'),
                  sorted(((nome, ocorrencias) for nome, ocorrencias in periodicos_sem_issn.items()),
                         key=lambda linha: (-linha[1], linha[0])))

    # apenas autores que podem ser de um membro (mesmo sobrenome): o restante é
    # coautoria externa e não é acionável para identidade do grupo
    linhas_autores = [(nome, r['ocorrencias'], ' || '.join(sorted(r['candidatos'])))
                      for nome, r in autores.items() if r['candidatos']]
    _escrever_csv(os.path.join(destino, 'pendentes_pesquisadores.csv'),
                  ('nome_no_cv', 'ocorrencias', 'candidatos_membros'),
                  sorted(linhas_autores, key=lambda linha: (-linha[1], linha[0])))

    # sugestões de agrupamento (uma decisão por grupo; nada é agrupado automaticamente)
    sugestoes = []
    for tipo, ocorrencias in (('evento', {chave: r['ocorrencias'] for chave, r in eventos.items()}),
                              ('instituicao', {chave: r['ocorrencias'] for chave, r in instituicoes.items()})):
        for grupo in agrupar_similares(ocorrencias):
            sugestoes.append((tipo, grupo['total'], grupo['nota_minima'],
                              ' || '.join(grupo['chaves']),
                              ' || '.join(f"{chave} ({ocorrencias[chave]})" for chave in grupo['chaves'])))
    sugestoes.sort(key=lambda linha: (linha[0], -linha[1], linha[3]))
    _escrever_csv(os.path.join(destino, 'pendentes_similares.csv'),
                  ('tipo', 'total', 'similaridade_minima', 'chaves', 'chaves_com_ocorrencias'),
                  sugestoes)

    return {
        'arquivos': len(arquivos),
        'eventos_distintos': len(eventos),
        'eventos_sem_alias': sum(1 for chave in eventos if chave not in vocabulario.eventos),
        'instituicoes_distintas': len(instituicoes),
        'instituticoes_sem_alias': sum(1 for chave in instituicoes if chave not in vocabulario.instituicoes),
        'periodicos_sem_issn': len(periodicos_sem_issn),
        'autores_nao_atribuidos': len(autores),
        'autores_com_candidato': sum(1 for r in autores.values() if r['candidatos']),
        'pares_sugeridos': len(sugestoes),
        'destino': os.path.abspath(destino),
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description='Normalização dos dados coletados dos CVs Lattes.')
    parser.add_argument('--saida', required=True, help='diretório de saída do scriptLattes (com a subpasta json/)')
    parser.add_argument('--destino', default='dados/aliases', help='diretório das tabelas de aliases')
    argumentos = parser.parse_args(argv)

    vocabulario = Vocabulario(argumentos.destino)
    resumo = relatorio_de_candidatos(argumentos.saida, argumentos.destino, vocabulario)

    print('[RELATÓRIO DE NORMALIZAÇÃO]')
    print(f"  arquivos JSON lidos            : {resumo['arquivos']}")
    print(f"  eventos distintos (chave série): {resumo['eventos_distintos']} "
          f"({resumo['eventos_sem_alias']} sem alias em eventos.csv)")
    print(f"  instituições distintas         : {resumo['instituicoes_distintas']} "
          f"({resumo['instituticoes_sem_alias']} sem alias em instituicoes.csv)")
    print(f"  periódicos sem ISSN            : {resumo['periodicos_sem_issn']}")
    print(f"  autores não atribuídos         : {resumo['autores_nao_atribuidos']} "
          f"({resumo['autores_com_candidato']} com candidato a membro)")
    print(f"  pares parecidos a revisar      : {resumo['pares_sugeridos']} (pendentes_similares.csv)")
    print(f"  candidatos escritos em         : {resumo['destino']}")
    return resumo


if __name__ == '__main__':
    main()
