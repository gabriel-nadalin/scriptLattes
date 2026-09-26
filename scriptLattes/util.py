#!/usr/bin/env python 
# encoding: utf-8

import os
import shutil
import sys
import re
import unicodedata
try:
    from rapidfuzz.distance import Levenshtein
except ImportError:
    Levenshtein = None


SEP     = os.path.sep
BASE    = 'scriptLattes' + SEP


def diretorio_do_projeto():
    """Pasta onde estão os arquivos que acompanham o programa (css, js, dados, exemplo).

    Não é a pasta de onde o programa foi executado: rodando de outra pasta, os arquivos
    estáticos (css/js) têm de vir de onde o projeto está instalado — senão os relatórios
    saem sem estilo. Em executável empacotado (PyInstaller), é a pasta extraída do pacote.
    """
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ABSBASE = diretorio_do_projeto() + SEP


def esta_empacotado():
    """Verdadeiro quando roda como executável gerado pelo PyInstaller."""
    return bool(getattr(sys, 'frozen', False))


def nome_do_programa():
    """Como o usuário chama o programa neste ambiente, para as mensagens de ajuda."""
    if esta_empacotado():
        return os.path.basename(sys.executable)
    return 'python scriptLattes.py'



def buscarArquivo(filepath, arquivoConfiguracao=None):
    """Localiza um arquivo de entrada informado no .config.

    Procura, nesta ordem: o caminho como informado (a partir da pasta atual, que é o
    comportamento histórico), relativo à pasta do .config e, por fim, com o nome do
    arquivo ao lado do .config. Não muda a pasta atual do processo: isso é importante
    porque a interface gráfica executa o pipeline em outra thread.
    """
    if not filepath:
        return ''

    if os.path.isabs(filepath):
        candidatos = [filepath]
    else:
        candidatos = [os.path.join(os.getcwd(), filepath)]
        if arquivoConfiguracao:
            pasta_do_config = os.path.dirname(os.path.abspath(arquivoConfiguracao))
            candidatos.append(os.path.join(pasta_do_config, filepath))
            candidatos.append(os.path.join(pasta_do_config, os.path.basename(filepath)))
        # arquivos que vêm junto com o programa (ex.: exemplo/demo-lattes/demo.list)
        candidatos.append(os.path.join(ABSBASE, filepath))

    for candidato in candidatos:
        if os.path.isfile(candidato):
            return os.path.abspath(candidato)
    return os.path.abspath(candidatos[0])


def buscarDiretorio(caminho, arquivoConfiguracao=None):
    """Localiza (ou decide onde criar) um diretório de trabalho, como a pasta de cache.

    Procura, nesta ordem: como informado (pasta de execução), relativo à pasta do
    `.config` e junto dos arquivos que acompanham o programa. Se não existir em lugar
    nenhum, devolve o caminho informado (relativo à pasta de execução) — assim o cache
    do usuário fica ao lado de onde ele está rodando, e não dentro do programa.
    """
    if not caminho:
        return caminho

    if os.path.isabs(caminho):
        return os.path.normpath(caminho)

    candidatos = [os.path.join(os.getcwd(), caminho)]
    if arquivoConfiguracao:
        candidatos.append(os.path.join(os.path.dirname(os.path.abspath(arquivoConfiguracao)), caminho))
    candidatos.append(os.path.join(ABSBASE, caminho))

    for candidato in candidatos:
        if os.path.isdir(candidato):
            return os.path.normpath(candidato)
    return os.path.normpath(candidatos[0])


def copiarArquivos(dir):
    base = ABSBASE
    try:
        dst = os.path.join(dir, 'css')
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(os.path.join(base, 'css'), dst)
    except OSError as e:
        print(f"[AVISO] Não foi possível copiar os arquivos estáticos: {e}")

    try:
        dst = os.path.join(dir, 'js')
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(os.path.join(base, 'js'), dst)
    except OSError as e:
        print(f"[AVISO] Não foi possível copiar os arquivos estáticos: {e}")
    # shutil.copy2(os.path.join(base, 'js', 'jquery.min.js'), dir)
    # shutil.copy2(os.path.join(base, 'js', 'highcharts.js'), dir)
    # shutil.copy2(os.path.join(base, 'js', 'exporting.js'), dir)
    # shutil.copy2(os.path.join(base, 'js', 'drilldown.js'), dir)
    # shutil.copy2(os.path.join(base, 'js', 'jquery.dataTables.min.js'), dir)
    # shutil.copy2(os.path.join(base, 'js', 'jquery.dataTables.rowGrouping.js'), dir)

    print(f"\n[ARQUIVOS SALVOS NO SEGUINTE DIRETÓRIO]\n{format(os.path.abspath(dir))}")

# ---------------------------------------------------------------------------- #
def criarDiretorio(dir):
    if not os.path.exists(dir):
        try:
            os.makedirs(dir)
        except OSError as exc:
            print(f"\n[ERRO] Não foi possível criar ou atualizar o diretório: {dir}")
            print(f"[ERRO] Você conta com as permissões de escrita? ({exc})\n")
            return 0
    return 1

# Combining Dictionaries Of Lists
def merge_dols(dol1, dol2):
    if type(dol1) == list:
        #print(f"LISTA: {dol1}")
        result = {**dol2}
    else:
        result = {**dol1, **dol2}
    # result = dict(dol1, **dol2)
    # result = dict()
    result.update((k, dol1[k] + dol2[k]) for k in set(dol1).intersection(dol2))
    return result


def eliminar_acentuacao(texto: str) -> str:
    """
    Remove a acentuação de uma string, mantendo apenas os caracteres base.
    """
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(
        c for c in nfkd
        if not unicodedata.combining(c)
    )

def normalizar_texto(texto: str) -> str:
    """
    Normaliza uma string para comparação:
      1. Remove acentuação.
      2. Converte para minúsculas.
      3. Remove tudo que não for letra (a–z) ou dígito (0–9).
    """
    # 1) retirar acentos
    texto_sem_acentos = eliminar_acentuacao(texto)
    # 2) caixa baixa
    texto_minusculo = texto_sem_acentos.lower()
    # 3) remove pontuação, espaços e demais caracteres
    texto_limpo = re.sub(r'[^a-z0-9]', '', texto_minusculo)
    return texto_limpo


def distancia_levenshtein(a: str, b: str) -> int:
    """
    Calcula a distância de Levenshtein entre as cadeias a e b
    (algoritmo de Wagner–Fischer).
    Complexidade: O(n·m) em tempo e O(min(n, m)) em espaço.
    """
    n, m = len(a), len(b)
    # garante que n >= m
    if n < m:
        return distancia_levenshtein(b, a)

    anterior = list(range(m + 1))
    for i, ca in enumerate(a, start=1):
        atual = [i] + [0] * m
        for j, cb in enumerate(b, start=1):
            custo_inserir    = anterior[j] + 1
            custo_deletar    = atual[j - 1] + 1
            custo_substituir = anterior[j - 1] + (ca != cb)
            atual[j] = min(custo_inserir, custo_deletar, custo_substituir)
        anterior = atual

    return anterior[m]


def similaridade_entre_cadeias(cadeia1: str, cadeia2: str, qualis: bool = False) -> int:
    """
    Retorna 1 se as cadeias são consideradas similares, caso contrário 0.
    Critérios:
      - Se uma das cadeias normalizadas for 'apresentacao', 'introducao' ou 'prefacio', retorna 0.
      - Se ambas tiverem len >= 50 e uma contida na outra, retorna 1.
      - Caso contrário, calcula distância e ratio:
         ratio = 1 - (distância / max_len)
      - Se len(cadeia) >= 10 e (ratio >= 0.93 ou distância <= 5), retorna 1.
    """
    # 1) normalização
    c1 = normalizar_texto(cadeia1)
    c2 = normalizar_texto(cadeia2)

    # caso especial
    especiais = {'apresentacao', 'introducao', 'prefacio'}
    if c1 in especiais or c2 in especiais:
        return 0

    # cadeias vazias falham
    if not c1 or not c2:
        return 0

    # contenção para textos longos: um prefixo de outro
    if len(c1) >= 50 and len(c2) >= 50 and (c1 in c2 or c2 in c1):
        return 1

    # cálculo de distância e ratio
    if Levenshtein:
        distancia = Levenshtein.distance(c1, c2)
    else:
        distancia = distancia_levenshtein(c1, c2)
    max_len   = max(len(c1), len(c2))
    ratio     = 1.0 - distancia / max_len if max_len > 0 else 0.0

    # critério final para cadeias longas
    if len(c1) >= 10 and len(c2) >= 10 and (ratio >= 0.93 or distancia <= 5):
        return 1

    return 0

# ---------------------------------------------------------------------------- #
def lerTextoDeArquivo(caminho):
    """Lê um arquivo de texto assumindo UTF-8.

    No Windows o Python usaria a codificação local (cp1252/ANSI) e um .config, .list
    ou currículo salvo em outra codificação quebraria com UnicodeDecodeError. Aqui o
    UTF-8 é o padrão e, se falhar, relemos na codificação local avisando o usuário."""
    try:
        with open(caminho, encoding='utf-8') as arquivo:
            return arquivo.read()
    except UnicodeDecodeError:
        pass

    import locale
    candidatos = [locale.getpreferredencoding(False), 'cp1252', 'latin-1']
    for codificacao in candidatos:
        if not codificacao or codificacao.lower().replace('-', '') == 'utf8':
            continue
        try:
            with open(caminho, encoding=codificacao) as arquivo:
                texto = arquivo.read()
        except (UnicodeDecodeError, LookupError):
            continue
        print(f"[AVISO] O arquivo '{caminho}' não está em UTF-8. "
              f"Foi lido como {codificacao}; salve como UTF-8 para não perder acentuação.")
        return texto

    with open(caminho, encoding='utf-8', errors='replace') as arquivo:
        texto = arquivo.read()
    print(f"[AVISO] O arquivo '{caminho}' tem caracteres inválidos; "
          f"parte da acentuação pode ter sido perdida.")
    return texto


def lerLinhasDeTexto(caminho):
    return lerTextoDeArquivo(caminho).splitlines(keepends=True)


def formatar_duracao(tempo_decorrido):
    """Duração compacta para barras de progresso: '8s', '2m03s', '1h05m'."""
    segundos = int(tempo_decorrido.total_seconds())
    if segundos < 60:
        return f'{segundos}s'
    if segundos < 3600:
        return f'{segundos // 60}m{segundos % 60:02d}s'
    return f'{segundos // 3600}h{(segundos % 3600) // 60:02d}m'

# ---------------------------------------------------------------------------- #
def escreverLeiaMe(dir, nome_do_grupo=''):
    """Explica, dentro da própria pasta de saída, o que foi gerado e por onde começar."""
    caminho = os.path.join(dir, 'LEIA-ME.txt')
    texto = f"""O QUE É ESTA PASTA
=================
Relatórios gerados pelo scriptLattes para o grupo "{nome_do_grupo}".

POR ONDE COMEÇAR
================
1) Abra o arquivo  index.html  neste navegador (ou clique duas vezes nele).
2) Os relatórios individuais de cada pesquisador estão em  json/  e  *.html.

O QUE TEM AQUI
==============
index.html              página inicial com a lista de membros e os relatórios
*.html                  um relatório por tipo de produção (artigos, congressos, ...)
json/                   os mesmos dados em formato JSON (para planilhas e programas)
grafo_de_colaboracoes.gexf   grafo de coautorias (abra no Gephi)
scriptlattes-log.txt    registro da execução; envie este arquivo ao pedir suporte

COMO RODAR DE NOVO
==================
Rode o mesmo comando usado agora. Os currículos já baixados ficam guardados e são
reaproveitados: a segunda execução é bem mais rápida e funciona sem internet.
Para mudar o período ou os relatórios, edite o arquivo .config do grupo.

CURRÍCULOS GUARDADOS
====================
A pasta de cache (por padrão  cache/ ) guarda uma cópia de cada currículo baixado.
Faça backup dela: com a pasta em mãos você regenera tudo sem baixar de novo.

AVISO SOBRE DADOS PESSOAIS (LGPD)
=================================
Estes relatórios reúnem dados públicos de currículos Lattes de terceiros
(pesquisadores que não são necessariamente membros do grupo). Use-os para fins
de pesquisa e gestão; não publique em site aberto nem compartilhe além do
necessário sem consentimento dos titulares.
"""
    try:
        with open(caminho, 'w', encoding='utf-8') as arquivo:
            arquivo.write(texto)
    except OSError as exc:
        print(f"[AVISO] Não foi possível escrever {caminho}: {exc}")

