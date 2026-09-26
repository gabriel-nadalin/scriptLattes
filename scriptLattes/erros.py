#!/usr/bin/env python
# encoding: utf-8
"""Traduz erros técnicos em mensagens acionáveis, em português.

Cada erro recebe: o que aconteceu, o que fazer (passos concretos) e um código de saída.
Códigos: 0 sucesso | 1 erro inesperado | 2 problema de arquivo/configuração |
         3 problema de ambiente (dependências, Chrome, internet) | 130 interrompido.
"""

import os
import sys

from scriptLattes.util import nome_do_programa

# demonstração que roda sem internet, sem Chrome e sem configurar nada
EXEMPLO_OFFLINE = os.path.join('exemplo', 'demo.config')

CODIGO_INESPERADO = 1
CODIGO_ENTRADA = 2
CODIGO_AMBIENTE = 3
CODIGO_INTERROMPIDO = 130


class ErroAmigavel:
    def __init__(self, titulo, causa, solucoes, codigo=CODIGO_INESPERADO):
        self.titulo = titulo
        self.causa = causa
        self.solucoes = list(solucoes)
        self.codigo = codigo


def _nome(excecao):
    return type(excecao).__name__


def classificar(excecao, contexto=None):
    """Mapeia uma exceção para uma explicação em português com passos de correção."""
    nome = _nome(excecao)
    detalhe = str(excecao) or ''

    if nome == 'FileNotFoundError' and 'chromedriver' in detalhe.lower():
        return ErroAmigavel(
            'ChromeDriver não encontrado',
            f'O scriptLattes precisa do ChromeDriver para baixar currículos novos: {detalhe}',
            ['Instale o Google Chrome (https://www.google.com/chrome/) e rode de novo',
             'No Linux, rode:  make install   (baixa o ChromeDriver da sua versão do Chrome)',
             'Alternativa sem navegador: coloque o HTML de cada currículo em  cache/<id_lattes>',
             f'Rode  {nome_do_programa()} --diagnostico  para ver o que está faltando'],
            CODIGO_AMBIENTE)

    if nome == 'FileNotFoundError':
        return ErroAmigavel(
            'Arquivo não encontrado',
            detalhe,
            ['Confira se o caminho está escrito corretamente (maiúsculas/minúsculas importam)',
             f'Um teste rápido que já funciona:  {nome_do_programa()} {EXEMPLO_OFFLINE}',
             f'Rode  {nome_do_programa()} --diagnostico  para checar o arquivo .list e a pasta de cache'],
            CODIGO_ENTRADA)

    if nome == 'PermissionError':
        return ErroAmigavel(
            'Sem permissão para escrever',
            detalhe or f'Sem permissão de escrita no diretório informado.',
            ['Escolha outra pasta de saída em  global-diretorio_de_saida  no arquivo .config',
             'Evite pastas do sistema (C:\\Program Files, /usr); use Documentos ou a pasta do projeto',
             'Se o arquivo estiver aberto em outro programa (Excel, Word), feche-o e rode de novo'],
            CODIGO_ENTRADA)

    if nome == 'UnicodeDecodeError':
        return ErroAmigavel(
            'Arquivo com codificação diferente de UTF-8',
            f'Não foi possível ler o arquivo de texto: {detalhe}',
            ['Abra o arquivo .config ou .list em um editor e salve como UTF-8',
             'No Bloco de Notas: Arquivo > Salvar como > Codificação: UTF-8',
             'No VS Code: canto inferior direito > Reabrir com codificação > UTF-8'],
            CODIGO_ENTRADA)

    if nome == 'ModuleNotFoundError':
        modulo = getattr(excecao, 'name', detalhe)
        return ErroAmigavel(
            f'Dependência ausente: {modulo}',
            f'O módulo "{modulo}" não está instalado no interpretador que está executando '
            f'({sys.executable}).',
            ['Use o lançador do projeto (executar.sh / executar.bat), que cuida do ambiente sozinho',
             'Ou ative o ambiente virtual e instale as dependências:',
             '   Linux/macOS:  source venv/bin/activate && pip install -r requirements.txt',
             '   Windows:      venv\\Scripts\\activate && pip install -r requirements.txt',
             f'Rode  {nome_do_programa()} --diagnostico  para ver o que está faltando'],
            CODIGO_AMBIENTE)

    if nome in ('CurriculoInvalidoError',):
        return ErroAmigavel(
            'Arquivo de currículo inválido no cache',
            detalhe,
            ['Apague o arquivo indicado da pasta de cache e rode de novo para baixá-lo',
             'Ou salve a página do currículo no navegador (lattes.cnpq.br/<id>) e importe com:',
             f'   {nome_do_programa()} --adicionar-cv arquivo.html',
             f'Rode  {nome_do_programa()} --diagnostico  para ver a pasta de cache em uso'],
            CODIGO_ENTRADA)

    if nome == 'RuntimeError' and 'data' in detalhe and 'infrastructure' in detalhe.lower():
        return ErroAmigavel(
            'Não foi possível baixar o ChromeDriver',
            detalhe,
            ['Confira a conexão com a internet (o Selenium Manager baixa o ChromeDriver)',
             'Se você já tem um ChromeDriver, informe o caminho em '
             'global-caminho_do_chromedriver no arquivo .config'],
            CODIGO_AMBIENTE)

    if nome == 'RuntimeError' and 'Selenium' in detalhe:
        return ErroAmigavel(
            'Selenium não instalado (necessário para baixar currículos)',
            detalhe,
            ['Instale as dependências com o lançador:  ./executar.sh  (ou executar.bat no Windows)',
             'Se você já tem os currículos em  cache/, nada a fazer: rode de novo com a pasta cache presente'],
            CODIGO_AMBIENTE)

    if nome in ('WebDriverException', 'TimeoutException', 'InvalidArgumentException',
                'SessionNotCreatedException', 'NoSuchDriverException'):
        if 'only supports Chrome version' in detalhe or 'session not created' in detalhe.lower():
            return ErroAmigavel(
                'Chrome e ChromeDriver em versões diferentes',
                f'O ChromeDriver em uso não combina com o Google Chrome instalado: {detalhe}',
                ['Apague o arquivo "chromedriver" que está na pasta do projeto e rode de novo: '
                 'sem ele o scriptLattes baixa o ChromeDriver certo automaticamente',
                 'Ou atualize o ChromeDriver para a versão do seu Chrome:  make update-chromedriver',
                 'Ou remova global-caminho_do_chromedriver do arquivo .config',
                 f'Rode  {nome_do_programa()} --diagnostico  para ver as versões do Chrome e do ChromeDriver'],
                CODIGO_AMBIENTE)
        return ErroAmigavel(
            'Falha ao abrir o navegador para baixar currículos',
            f'{nome}: {detalhe}',
            ['Verifique se o Google Chrome está instalado e atualizado',
             'Atualize o ChromeDriver (uma versão por Chrome): no Linux,  make update-chromedriver',
             'Se o computador estiver sem internet, use os currículos já em  cache/',
             f'Rode  {nome_do_programa()} --diagnostico  para ver Chrome, ChromeDriver e rede'],
            CODIGO_AMBIENTE)

    if nome in ('URLError', 'HTTPError', 'ConnectionError', 'gaierror', 'ConnectTimeout',
                'ReadTimeout', 'ConnectionResetError'):
        return ErroAmigavel(
            'Falha de conexão com a internet',
            f'{nome}: {detalhe}',
            ['Confira a conexão e o proxy/firewall da sua instituição',
             'Se os currículos já estão em  cache/, rode de novo: o cache é usado sem internet',
             'A plataforma Lattes pode estar fora do ar; teste acessar http://lattes.cnpq.br no navegador'],
            CODIGO_AMBIENTE)

    if nome in ('JSONDecodeError',):
        return ErroAmigavel(
            'Arquivo JSON inválido na pasta de saída',
            detalhe,
            ['Apague os arquivos JSON incompletos da pasta de saída e rode de novo',
             'Se o erro persistir, rode com --debug e envie o log'],
            CODIGO_ENTRADA)

    return ErroAmigavel(
        'Erro inesperado',
        f'{nome}: {detalhe}',
        ['Rode novamente com --debug para ver o detalhe técnico',
         'Envie o arquivo de log junto com o relato do problema',
         f'Enquanto isso, o exemplo que já funciona é:  {nome_do_programa()} {EXEMPLO_OFFLINE}'],
        CODIGO_INESPERADO)


def imprimir_erro(excecao, caminho_do_log=None, debug=False):
    """Mostra a mensagem amigável (e o traceback, se --debug) e devolve o código de saída."""
    if isinstance(excecao, KeyboardInterrupt):
        print('\n[INTERROMPIDO] Execução cancelada por você.')
        print('Os currículos já baixados continuam guardados: rode de novo para continuar de onde parou.')
        return CODIGO_INTERROMPIDO

    erro = classificar(excecao)

    linhas = [
        '',
        '=' * 72,
        f' [ERRO] {erro.titulo}',
        '=' * 72,
        f' O que aconteceu: {erro.causa}',
        ' O que fazer:',
    ]
    linhas += [f'   {i}) {solucao}' for i, solucao in enumerate(erro.solucoes, 1)]
    if caminho_do_log:
        linhas.append(f' Log completo: {os.path.abspath(caminho_do_log)}')
    if not debug:
        linhas.append(' Detalhe técnico: rode novamente com --debug e envie o log.')
    linhas.append('=' * 72)
    print('\n'.join(linhas))

    if debug:
        import traceback
        traceback.print_exception(type(excecao), excecao, excecao.__traceback__)

    return erro.codigo
