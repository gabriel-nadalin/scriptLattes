#!/usr/bin/env python
# encoding: utf-8
"""Assistente: cria o `.config` e o `.list` de um grupo sem o usuário editar arquivos.

A ideia é que a pessoa só responda quatro perguntas (nome do grupo, currículos,
período e pasta de saída). O `.config` gerado é curto de propósito: os outros ~70
parâmetros já têm valores padrão sensatos (ver `Grupo.carregarParametrosPadrao`), e os
que costumam ser mexidos ficam comentados no próprio arquivo.

A parte de decisão (`interpretar_entrada`, `criar_projeto`) é separada da conversa para
poder ser testada sem terminal e reaproveitada pela janela gráfica.
"""

import os
import re
import unicodedata

from scriptLattes.util import nome_do_programa

URL_COM_ID = re.compile(r'(?:lattes\.cnpq\.br|visualizacv\.do\?id=)[^\d]*(\d{16}|\d{10})(?!\d)', re.I)
SO_DIGITOS = re.compile(r'^(?:\d{10}|\d{16})$')
ONDE_QUEBRAR = re.compile(r'[,;\t]')

PADRAO_DESDE = '1900'
PADRAO_ATE = 'hoje'


def _sem_acento(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c))


def nome_de_arquivo(nome_do_grupo):
    """'Grupo de Pesquisa em Enfermagem' -> 'grupo-de-pesquisa-em-enfermagem'."""
    texto = _sem_acento(nome_do_grupo or '').lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto).strip('-')
    texto = re.sub(r'-{2,}', '-', texto)
    return texto[:60] or 'meu-grupo'


def interpretar_entrada(texto):
    """Interpreta o que o usuário colou e devolve (membros, problemas, repetidos).

    Aceita, por linha: '1234567890123456', 'http://lattes.cnpq.br/1234567890123456',
    '1234567890123456 , Nome Completo', '1234567890;Nome', com ou sem espaços.
    Linhas iniciadas por '#' são comentários.
    """
    membros, problemas, repetidos = [], [], []
    vistos = set()

    for numero_da_linha, linha in enumerate((texto or '').splitlines(), start=1):
        original = linha.strip()
        if not original or original.startswith('#'):
            continue

        linha = original.partition('#')[0].strip()
        identificador = ''
        resto = ''

        encontrado = URL_COM_ID.search(linha)
        if encontrado:
            identificador = encontrado.group(1)
            resto = linha[:encontrado.start()] + ' ' + linha[encontrado.end():]
            resto = re.sub(r'https?://\S*', ' ', resto)    # sobras do endereço
        else:
            partes = ONDE_QUEBRAR.split(linha, maxsplit=1)
            primeira = partes[0].strip()
            if SO_DIGITOS.match(primeira):
                identificador = primeira
                resto = partes[1].strip() if len(partes) > 1 else ''
            elif SO_DIGITOS.match(linha):
                identificador = linha

        if not identificador:
            problemas.append((numero_da_linha, original,
                              'não encontrei um número de currículo (10 ou 16 dígitos) nessa linha'))
            continue

        nome = re.sub(r'\s{2,}', ' ', resto.strip(' ,;-\t')).strip()
        if re.fullmatch(r'[\d\s,;]*', nome):    # sobrou só pontuação/números: não é nome
            nome = ''

        if identificador in vistos:
            repetidos.append((numero_da_linha, identificador))
            continue
        vistos.add(identificador)
        membros.append((identificador, nome))

    return membros, problemas, repetidos


def montar_lista(membros):
    """Conteúdo do arquivo `.list` no formato esperado pelo scriptLattes."""
    linhas = ['# Lista de membros do grupo - formato: identificador Lattes , nome completo',
              '# Gerado pelo assistente do scriptLattes. Edite à vontade.',
              '']
    for identificador, nome in membros:
        linhas.append(f'{identificador} , {nome}' if nome else identificador)
    return '\n'.join(linhas) + '\n'


def montar_config(nome_do_grupo, caminho_do_list, pasta_de_saida, pasta_de_cache,
                  desde=PADRAO_DESDE, ate=PADRAO_ATE, email=''):
    """Conteúdo do arquivo `.config`.

    São poucos parâmetros porque todos os outros têm padrão; os mais procurados ficam
    comentados no fim do arquivo, prontos para descomentar."""
    arquivo_do_config = os.path.basename(caminho_do_list).replace('.list', '.config')
    return f"""# ---------------------------------------------------------------------------- #
# Configuração do grupo "{nome_do_grupo}"
# Gerada pelo assistente do scriptLattes
#
# Para rodar:   {nome_do_programa()} {arquivo_do_config}
#            ou ./executar.sh {arquivo_do_config}
#
# Todos os relatórios já vêm ligados. Só mexa aqui se souber o que quer mudar.
# ---------------------------------------------------------------------------- #

global-nome_do_grupo                      = {nome_do_grupo}
global-arquivo_de_entrada                 = {caminho_do_list}
global-diretorio_de_saida                 = {pasta_de_saida}
global-diretorio_de_armazenamento_de_cvs  = {pasta_de_cache}
global-email_do_admin                     = {email}

# Período considerado nos relatórios ('hoje' = ano atual)
global-itens_desde_o_ano                  = {desde}
global-itens_ate_o_ano                    = {ate}

# Normalização de nomes de eventos, instituições e periódicos
# (tabelas editáveis em ./dados/aliases/)
global-normalizacao                       = sim

# ---------------------------------------------------------------------------- #
# Opções que costumam ser alteradas - remova o '#' da linha para ativar
# ---------------------------------------------------------------------------- #
# relatorio-incluir_metricas              = sim   # planilha de métricas do grupo
# grafo-incluir_grau_de_colaboracao       = sim   # cor dos vértices pelo grau
# global-identificar_producoes_por_termos = sim   # filtrar por palavras-chave
# global-arquivo_de_termos_de_busca       = ./meus-termos.txt
# global-caminho_do_chromedriver          = ./chromedriver  # só se o download automático falhar
#
# Para desligar um tipo de relatório, troque 'sim' por 'nao', por exemplo:
# relatorio-incluir_artigo_aceito_para_publicacao = nao
"""


def _caminho_para_o_config(alvo):
    """Caminho gravado no .config: absoluto.

    A pasta de saída e a de cache são usadas como estão (relativas à pasta de onde o
    programa é executado), então gravar o caminho absoluto evita que os relatórios
    acabem em outro lugar quando o programa é rodado de uma pasta diferente."""
    return os.path.abspath(alvo).replace(os.sep, '/')


def _caminho_do_list_no_config(caminho_do_list, pasta_do_config):
    """O .list pode ficar relativo: é procurado também ao lado do .config."""
    pasta = os.path.dirname(os.path.abspath(caminho_do_list))
    if pasta == os.path.abspath(pasta_do_config):
        return './' + os.path.basename(caminho_do_list)
    return os.path.abspath(caminho_do_list).replace(os.sep, '/')


class Resultado:
    """O que o assistente (ou a janela) produziu."""

    def __init__(self, config='', lista='', membros=(), problemas=(), repetidos=(), saida='', cache=''):
        self.config = config
        self.lista = lista
        self.membros = list(membros)
        self.problemas = list(problemas)
        self.repetidos = list(repetidos)
        self.saida = saida
        self.cache = cache

    def __bool__(self):
        return bool(self.config)


def criar_projeto(nome_do_grupo, texto_dos_membros, pasta_de_trabalho=None,
                  pasta_de_saida=None, pasta_de_cache=None, desde='', ate='', email='',
                  sobrescrever=False):
    """Cria `<slug>.config` e `<slug>.list`. Devolve (config, lista, membros, problemas).

    Levanta `ValueError` se nenhum currículo válido foi informado ou se os arquivos já
    existem e `sobrescrever` é falso.
    """
    pasta_de_trabalho = os.path.abspath(pasta_de_trabalho or os.getcwd())
    nome_do_grupo = (nome_do_grupo or '').strip() or 'Meu Grupo'
    slug = nome_de_arquivo(nome_do_grupo)

    membros, problemas, repetidos = interpretar_entrada(texto_dos_membros)
    if not membros:
        raise ValueError('nenhum currículo válido foi informado')

    caminho_do_list = os.path.join(pasta_de_trabalho, slug + '.list')
    caminho_do_config = os.path.join(pasta_de_trabalho, slug + '.config')

    if not sobrescrever:
        for caminho in (caminho_do_config, caminho_do_list):
            if os.path.exists(caminho):
                raise FileExistsError(caminho)

    pasta_de_saida = pasta_de_saida or os.path.join(pasta_de_trabalho, 'saida-' + slug)
    pasta_de_cache = pasta_de_cache or os.path.join(pasta_de_trabalho, 'cache')

    os.makedirs(pasta_de_trabalho, exist_ok=True)
    with open(caminho_do_list, 'w', encoding='utf-8') as arquivo:
        arquivo.write(montar_lista(membros))

    lista_para_o_config = _caminho_do_list_no_config(caminho_do_list, pasta_de_trabalho)
    config = montar_config(
        nome_do_grupo,
        lista_para_o_config,
        _caminho_para_o_config(pasta_de_saida),
        _caminho_para_o_config(pasta_de_cache),
        desde=desde or PADRAO_DESDE,
        ate=ate or PADRAO_ATE,
        email=email)
    with open(caminho_do_config, 'w', encoding='utf-8') as arquivo:
        arquivo.write(config)

    return Resultado(config=caminho_do_config, lista=caminho_do_list, membros=membros,
                     problemas=problemas, repetidos=repetidos,
                     saida=os.path.abspath(pasta_de_saida), cache=os.path.abspath(pasta_de_cache))


# ---------------------------------------------------------------------------- #
# Conversa no terminal
# ---------------------------------------------------------------------------- #
def _perguntar(entrada, saida, pergunta, padrao=''):
    sufixo = f' [{padrao}]' if padrao else ''
    saida(f'{pergunta}{sufixo}: ')
    try:
        resposta = (entrada() or '').strip()
    except EOFError:
        return padrao
    return resposta or padrao


def _ler_membros(entrada, saida):
    """Lê linhas de currículos até uma linha vazia."""
    linhas = []
    saida('\nCole os links ou os números dos currículos Lattes, um por linha.')
    saida('(dica: no site do Lattes o endereço é http://lattes.cnpq.br/1234567890123456)')
    saida('Para terminar, deixe uma linha em branco e pressione Enter:\n')
    while True:
        try:
            linha = entrada()
        except EOFError:
            break
        if linha is None or not linha.strip():
            break
        linhas.append(linha)
    return '\n'.join(linhas)


def _ler_periodo(entrada, saida):
    resposta = _perguntar(entrada, saida,
                          '\nAno inicial dos relatórios (Enter = desde 1900)', PADRAO_DESDE)
    desde = resposta if re.fullmatch(r'\d{4}', resposta) else PADRAO_DESDE
    if desde != resposta:
        saida('  (não entendi o ano; vou considerar todos os anos)')

    resposta = _perguntar(entrada, saida, 'Ano final (Enter = ano atual)', PADRAO_ATE)
    ate = resposta if re.fullmatch(r'(\d{4}|hoje)', resposta, re.I) else PADRAO_ATE
    return desde, ate


def rodar_assistente(entrada=input, saida=print, pasta_de_trabalho=None, rodar=False):
    """Conversa com o usuário e cria os arquivos. Devolve `Resultado` (vazio se falhou)."""
    pasta_de_trabalho = os.path.abspath(pasta_de_trabalho or os.getcwd())

    saida('=' * 70)
    saida(' Assistente do scriptLattes')
    saida('=' * 70)
    saida('Vou criar dois arquivos para o seu grupo. É só responder e apertar Enter.')
    saida('(para aceitar a sugestão entre colchetes, aperte Enter direto)\n')

    nome_do_grupo = _perguntar(entrada, saida, 'Nome do grupo', 'Meu Grupo')
    slug = nome_de_arquivo(nome_do_grupo)

    linhas = _ler_membros(entrada, saida)
    membros, problemas, repetidos = interpretar_entrada(linhas)

    if problemas:
        saida('\n[AVISO] Não entendi estas linhas (vou ignorá-las):')
        for numero, conteudo, motivo in problemas:
            saida(f'  linha {numero}: {conteudo[:60]} ({motivo})')
    if repetidos:
        saida(f'\n[AVISO] {len(repetidos)} currículo(s) repetido(s) foram considerados uma vez só.')
    if not membros:
        saida('\n[ERRO] Nenhum currículo válido foi informado.')
        saida('       O número/endereço do currículo Lattes tem 16 dígitos, por exemplo:')
        saida('       http://lattes.cnpq.br/1234567890123456')
        return Resultado()

    saida(f'\n[OK] {len(membros)} currículo(s) reconhecido(s).')

    desde, ate = _ler_periodo(entrada, saida)

    padrao_saida = os.path.join(pasta_de_trabalho, 'saida-' + slug)
    pasta_de_saida = _perguntar(entrada, saida, f'\nPasta dos relatórios', padrao_saida)
    pasta_de_cache = _perguntar(entrada, saida,
                                'Pasta onde os currículos ficam guardados (cache)',
                                os.path.join(pasta_de_trabalho, 'cache'))
    email = _perguntar(entrada, saida, 'Seu e-mail (aparece nos relatórios, opcional)', '')

    argumentos = dict(pasta_de_trabalho=pasta_de_trabalho, pasta_de_saida=pasta_de_saida,
                      pasta_de_cache=pasta_de_cache, desde=desde, ate=ate, email=email)
    try:
        resultado = criar_projeto(nome_do_grupo, linhas, **argumentos)
    except FileExistsError as existente:
        saida(f'\n[AVISO] O arquivo {existente} já existe.')
        resposta = _perguntar(entrada, saida, 'Substituir? (s/n)', 'n')
        if resposta.lower() not in ('s', 'sim', 'y'):
            saida('Nada foi alterado. Rode o assistente de novo quando quiser.')
            return Resultado()
        resultado = criar_projeto(nome_do_grupo, linhas, sobrescrever=True, **argumentos)

    caminho_do_config, caminho_do_list = resultado.config, resultado.lista

    saida('\n' + '-' * 70)
    saida('[PRONTO] Arquivos criados:')
    saida(f'  {caminho_do_config}')
    saida(f'  {caminho_do_list}')
    saida(f'  relatórios serão gerados em: {os.path.abspath(pasta_de_saida)}')
    saida(f'  currículos ficarão guardados em: {os.path.abspath(pasta_de_cache)}')
    saida('-' * 70)
    saida(f'\nPara gerar os relatórios depois:  {nome_do_programa()} {caminho_do_config}')

    if rodar:
        resposta = _perguntar(entrada, saida, '\nGerar os relatórios agora? (S/n)', 's')
        if resposta.lower() in ('s', 'sim', 'y', ''):
            saida('\n' + '=' * 70)
            from scriptLattes.cli import main as executar_pipeline
            codigo = executar_pipeline([caminho_do_config, '--nao-abrir'])
            if codigo == 0:
                saida('\n[CONCLUÍDO] Abra o arquivo index.html da pasta de relatórios.')
            else:
                saida(f'\nA execução terminou com código {codigo}. Veja as instruções acima.')
        else:
            saida('Ok. Quando quiser, rode o comando acima.')

    return resultado


def main(argv=None):
    """Entrada de `python -m scriptLattes.assistente`."""
    import argparse
    import sys

    analisador = argparse.ArgumentParser(
        prog='python -m scriptLattes.assistente',
        description='Cria o .config e o .list do seu grupo conversando com você.')
    analisador.add_argument('--pasta', default=os.getcwd(),
                            help='pasta onde os arquivos serão criados (padrão: pasta atual)')
    analisador.add_argument('--rodar', action='store_true',
                            help='gerar os relatórios logo depois de criar os arquivos')
    argumentos = analisador.parse_args(argv)

    try:
        resultado = rodar_assistente(pasta_de_trabalho=argumentos.pasta, rodar=argumentos.rodar)
    except (KeyboardInterrupt, EOFError):
        print('\n[INTERROMPIDO] Nada foi alterado.')
        return 130
    if not resultado:
        print('\nO assistente não conseguiu criar os arquivos. Rode novamente quando quiser.')
        return 2
    return 0


if __name__ == '__main__':
    import sys

    sys.exit(main())
