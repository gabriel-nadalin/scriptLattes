#!/usr/bin/env python
# encoding: utf-8
"""Diagnóstico do ambiente: responde "por que não roda?" sem executar o pipeline.

Uso:  python scriptLattes.py --diagnostico [arquivo.config]
Códigos de saída: 0 pode rodar | 2 problema no .config/.list | 3 problema de ambiente.
"""

import importlib.metadata
import importlib.util
import locale
import os
import platform
import re
import shutil
import socket
import subprocess
import sys

from scriptLattes.util import lerLinhasDeTexto

# (distribuição no pip, módulo, para que serve, é essencial?)
DEPENDENCIAS = [
    ('beautifulsoup4', 'bs4',       'leitura dos currículos',             True),
    ('networkx',       'networkx',  'grafo de colaborações',              True),
    ('tqdm',           'tqdm',      'barra de progresso',                 True),
    ('scipy',          'scipy',     'matrizes; opcional',                 False),
    ('rapidfuzz',      'rapidfuzz', 'casamento de nomes; opcional',       False),
    ('selenium',       'selenium',  'baixar currículos; opcional',        False),
]

HOST_LATTES = 'lattes.cnpq.br'
PORTA_LATTES = 443


def versao_instalada(distribuicao):
    try:
        return importlib.metadata.version(distribuicao)
    except importlib.metadata.PackageNotFoundError:
        return None


def modulo_disponivel(modulo):
    try:
        return importlib.util.find_spec(modulo) is not None
    except (ImportError, ValueError):
        return False


def eh_ambiente_virtual():
    return sys.prefix != getattr(sys, 'base_prefix', sys.prefix)


def procurar_chrome():
    """Devolve o caminho do executável do Chrome/Chromium, se existir."""
    sistema = platform.system()
    candidatos = []

    if sistema == 'Windows':
        bases = [os.environ.get('PROGRAMFILES'), os.environ.get('PROGRAMFILES(X86)'),
                 os.environ.get('LOCALAPPDATA')]
        for base in bases:
            if base:
                candidatos.append(os.path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'))
                candidatos.append(os.path.join(base, 'Chromium', 'Application', 'chrome.exe'))
    elif sistema == 'Darwin':
        candidatos += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                       '/Applications/Chromium.app/Contents/MacOS/Chromium']
    else:
        for nome in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'):
            caminho = shutil.which(nome)
            if caminho:
                candidatos.append(caminho)

    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return None


def versao_do_chrome(caminho):
    """Obtém a versão do Chrome para comparar com a do ChromeDriver."""
    if platform.system() == 'Windows':
        # 'chrome.exe --version' abre o navegador no Windows; a versão está no nome da pasta
        try:
            pasta = os.path.dirname(caminho)
            versoes = [d for d in os.listdir(pasta) if re.fullmatch(r'\d+(\.\d+){2,3}', d)]
            if versoes:
                return sorted(versoes, key=lambda v: [int(p) for p in v.split('.')])[-1]
        except OSError:
            pass
        return None

    try:
        saida = subprocess.run([caminho, '--version'], capture_output=True, text=True, timeout=15)
        encontrado = re.search(r'(\d+(?:\.\d+){2,3})', saida.stdout or '')
        return encontrado.group(1) if encontrado else None
    except (OSError, subprocess.SubprocessError):
        return None


def versao_do_chromedriver(caminho):
    """Versão do ChromeDriver, para comparar com a do Chrome."""
    try:
        saida = subprocess.run([caminho, '--version'], capture_output=True, text=True, timeout=15)
        encontrado = re.search(r'(\d+(?:\.\d+){2,3})', saida.stdout or '')
        return encontrado.group(1) if encontrado else None
    except (OSError, subprocess.SubprocessError):
        return None


def procurar_chromedriver():
    caminho = shutil.which('chromedriver')
    if caminho:
        return caminho
    for local in ('chromedriver', 'chromedriver.exe',
                  os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'chromedriver')):
        if os.path.exists(local):
            return os.path.abspath(local)
    return None


def testar_rede(host=HOST_LATTES, porta=PORTA_LATTES, timeout=5):
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except OSError:
        return False


def _linha(rotulo, valor):
    print(f'  {rotulo:<34} {valor}')


def _parametro_do_config(caminho, chave):
    """Lê um parâmetro de um .config sem depender de o arquivo estar válido."""
    try:
        for linha in lerLinhasDeTexto(caminho):
            sem_comentario = linha.partition('#')[0]
            if '=' in sem_comentario:
                nome, _, valor = sem_comentario.partition('=')
                if nome.strip() == chave:
                    return valor.strip()
    except (OSError, UnicodeDecodeError):
        return ''
    return ''


def _contar_cvs(diretorio):
    if not diretorio or not os.path.isdir(diretorio):
        return 0
    total = 0
    for nome in os.listdir(diretorio):
        if re.fullmatch(r'\d{10}|\d{16}', nome):
            total += 1
    return total


def executar_diagnostico(arquivo_configuracao=None):
    print('\n[DIAGNÓSTICO DO AMBIENTE - scriptLattes]\n')
    bloqueios = []   # (codigo, descricao)
    avisos = []

    print('Interpretador Python')
    _linha('executável', sys.executable)
    _linha('versão', platform.python_version())
    _linha('ambiente virtual', 'sim' if eh_ambiente_virtual() else 'NÃO (recomendado usar o venv do projeto)')
    _linha('codificação local', locale.getpreferredencoding(False))
    if not eh_ambiente_virtual():
        avisos.append('Não é um ambiente virtual: use ./executar.sh (Linux/macOS) ou executar.bat (Windows) '
                      'para o projeto montar e usar o venv automaticamente.')

    print('\nDependências')
    for distribuicao, modulo, para_que_serve, essencial in DEPENDENCIAS:
        disponivel = modulo_disponivel(modulo)
        versao = versao_instalada(distribuicao) if disponivel else None
        estado = versao or ('instalado' if disponivel else 'AUSENTE')
        _linha(f'{distribuicao} ({para_que_serve})', estado)
        if not disponivel and essencial:
            bloqueios.append((3, f'{distribuicao} não instalado; rode o lançador do projeto para instalar'))

    print('\nNavegador (necessário apenas para baixar currículos novos)')
    chrome = procurar_chrome()
    if chrome:
        _linha('Chrome/Chromium', chrome)
        _linha('versão do Chrome', versao_do_chrome(chrome) or 'não identificada')
    else:
        _linha('Chrome/Chromium', 'NÃO ENCONTRADO')

    driver = procurar_chromedriver()
    _linha('ChromeDriver local', driver or 'nenhum (o Selenium baixa o correto automaticamente)')
    driver_incompativel = ''
    if driver and chrome:
        versao_do_driver = versao_do_chromedriver(driver)
        versao_do_navegador = versao_do_chrome(chrome)
        _linha('versão do ChromeDriver', versao_do_driver or 'não identificada')
        if versao_do_driver and versao_do_navegador \
                and versao_do_driver.split('.')[0] != versao_do_navegador.split('.')[0]:
            driver_incompativel = (f'o ChromeDriver local ({driver}) é da versão {versao_do_driver} '
                                   f'e o Chrome é {versao_do_navegador}: eles precisam ser da mesma '
                                   f'versão principal. Apague esse arquivo (o Selenium baixa o '
                                   f'ChromeDriver certo automaticamente) ou rode '
                                   f'"make update-chromedriver".')
            avisos.append(driver_incompativel)

    selenium_ok = modulo_disponivel('selenium')
    cache_dir = './cache/'
    config_lido = None
    if arquivo_configuracao:
        cache_dir = _parametro_do_config(arquivo_configuracao, 'global-diretorio_de_armazenamento_de_cvs') or cache_dir
    cvs_no_cache = _contar_cvs(cache_dir)
    _linha('currículos no cache', f'{cvs_no_cache} em {os.path.abspath(cache_dir)}')

    impedimentos = []
    if not selenium_ok:
        impedimentos.append('a biblioteca Selenium (pip)')
    if not chrome:
        impedimentos.append('o Google Chrome')
    if driver_incompativel:
        impedimentos.append('um ChromeDriver compatível com o seu Chrome')

    if impedimentos:
        if cvs_no_cache:
            avisos.append(f'Sem {" e ".join(impedimentos)}: só será possível usar os currículos já '
                          f'presentes em {cache_dir} (que já são {cvs_no_cache}, suficiente para reprocessar).')
        else:
            bloqueios.append((3, f'não há {" nem ".join(impedimentos)} e o cache está vazio: '
                                 'não há de onde obter currículos'))

    print('\nRede')
    rede_ok = testar_rede()
    _linha(f'conexão com {HOST_LATTES}', 'OK' if rede_ok else 'SEM CONEXÃO')
    if not rede_ok and cvs_no_cache == 0:
        bloqueios.append((3, 'sem internet e sem currículos no cache: não há de onde obter currículos'))

    print('\nEntrada e saída')
    if arquivo_configuracao:
        config_lido = os.path.abspath(arquivo_configuracao)
        if os.path.isfile(config_lido):
            _linha('arquivo .config', config_lido)
            lista = _parametro_do_config(config_lido, 'global-arquivo_de_entrada')
            saida = _parametro_do_config(config_lido, 'global-diretorio_de_saida')
            _linha('lista de membros (.list)', lista or 'não definida (usa listaDeMembros)')
            if lista:
                caminho_lista = lista if os.path.isabs(lista) else os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), '..', lista)
                existe = os.path.isfile(lista) or os.path.isfile(caminho_lista)
                _linha('  .list encontrado', 'sim' if existe else 'NÃO')
                if not existe:
                    bloqueios.append((2, f'arquivo .list não encontrado: {lista}'))
            _linha('pasta de saída', saida or 'não definida')
            if saida:
                destino = os.path.abspath(saida)
                if os.path.isdir(destino):
                    _linha('  pode escrever nela', 'sim' if os.access(destino, os.W_OK) else 'NÃO')
                    if not os.access(destino, os.W_OK):
                        bloqueios.append((2, f'sem permissão de escrita em {destino}'))
                else:
                    pai = os.path.dirname(destino) or '.'
                    pode = os.access(pai, os.W_OK)
                    _linha('  será criada (pasta pai gravável)', 'sim' if pode else 'NÃO')
                    if not pode:
                        bloqueios.append((2, f'não será possível criar a pasta de saída {destino}'))
        else:
            _linha('arquivo .config', f'NÃO ENCONTRADO: {config_lido}')
            bloqueios.append((2, f'arquivo de configuração não encontrado: {arquivo_configuracao}'))
    else:
        _linha('arquivo .config', 'não informado (diagnóstico parcial)')

    print('\nArquivos de normalização')
    tabelas = './dados/aliases/'
    _linha('tabelas de aliases', os.path.abspath(tabelas) if os.path.isdir(tabelas) else 'não encontradas (opcional)')

    print('\n' + '=' * 72)
    if avisos:
        print(' AVISOS (não impedem a execução):')
        for aviso in avisos:
            print(f'   - {aviso}')
    if bloqueios:
        print(' NÃO PODE RODAR AINDA:')
        for _, descricao in bloqueios:
            print(f'   - {descricao}')
        print('=' * 72)
        return bloqueios[0][0]

    if cvs_no_cache or not bloqueios:
        print(f' PODE RODAR: {cvs_no_cache} currículos já guardados em cache para processar.')
    if not selenium_ok:
        print(' Para BAIXAR currículos novos: instale as dependências com o lançador do projeto '
              '(./executar.sh ou executar.bat).')
    if not chrome:
        print(' Para BAIXAR currículos novos: instale o Google Chrome (https://www.google.com/chrome/).')
    if driver_incompativel:
        print(' Para BAIXAR currículos novos: resolva o ChromeDriver antigo descrito nos avisos acima.')
    if selenium_ok and chrome and not driver_incompativel:
        print(' TUDO PRONTO: pode baixar e processar currículos.')
    print('=' * 72)
    return 0
