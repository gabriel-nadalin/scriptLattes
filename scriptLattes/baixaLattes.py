#!/usr/bin/python
# encoding: utf-8
"""Baixa (ou importa) os currículos Lattes em HTML para a pasta de cache.

Três caminhos possíveis, do mais simples ao mais manual:

1. **Selenium Manager** (padrão): o próprio Selenium baixa o ChromeDriver compatível
   com o Chrome instalado. Basta ter o Google Chrome.
2. **ChromeDriver local**: informe `global-caminho_do_chromedriver` no `.config`
   (ou deixe um binário `chromedriver` na raiz do projeto) para uso sem internet.
3. **Sem navegador**: coloque o HTML do currículo na pasta de cache com o nome do
   identificador; nada é baixado. É o que o comando `--adicionar-cv` automatiza.
"""

import atexit
import os
import platform
import re
import socket
import sys
import time
import urllib.parse
import urllib.request, urllib.error

try:
    import bs4
except ImportError:
    bs4 = None

try:
    from selenium import webdriver
    from selenium.common.exceptions import InvalidArgumentException, TimeoutException, WebDriverException
    from selenium.webdriver.chrome.service import Service
except ImportError:
    webdriver = None
    InvalidArgumentException = None
    TimeoutException = None
    WebDriverException = None
    Service = None

RESULTS_DIR = os.environ.get('DATA_DIR', 'htmls')
URL = 'http://buscatextual.cnpq.br/buscatextual/preview.do?metodo=apresentar&id={0}'
URL_LATTES_ID10 = 'http://buscatextual.cnpq.br/buscatextual/visualizacv.do?id={0}'
URL_LATTES_ID16 = 'http://lattes.cnpq.br/{0}'

RAIZ_DO_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST_LATTES = 'lattes.cnpq.br'
PORTA_LATTES = 443

# Marcadores que só existem em uma página de currículo Lattes
MARCADORES_DE_CV = ('inst_back', 'Nome em citações bibliográficas', 'visualizacv',
                    'buscatextual', 'Formação acadêmica', 'Produção bibliográfica')

_driver_compartilhado = None
_descricao_do_driver = ''


class CurriculoInvalidoError(ValueError):
    """O arquivo de currículo no cache não é uma página de CV Lattes aproveitável."""


def nome_do_driver_no_sistema():
    return 'chromedriver.exe' if platform.system() == 'Windows' else 'chromedriver'


def resolver_chromedriver(caminho_informado=''):
    """Caminho do ChromeDriver local, se informado explicitamente.

    Vazio (padrão) significa "usar o Selenium Manager", que baixa o ChromeDriver
    compatível com o Chrome instalado. O binário local na raiz do projeto é usado
    como plano B por `_iniciar_chrome`, para quem não tem internet.
    """
    if not caminho_informado:
        return ''

    if os.path.isfile(caminho_informado):
        return os.path.abspath(caminho_informado)
    candidato = os.path.join(RAIZ_DO_PROJETO, caminho_informado)
    if os.path.isfile(candidato):
        return os.path.abspath(candidato)
    raise FileNotFoundError(f'ChromeDriver não encontrado em: {caminho_informado}')


def tem_internet(host=HOST_LATTES, porta=PORTA_LATTES, timeout=5):
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except OSError:
        return False


def _opcoes_do_chrome(results_dir):
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument('start-maximized')
    opcoes.add_argument('--blink-settings=imagesEnabled=false')
    opcoes.add_argument('headless')
    opcoes.add_argument('--disable-gpu')
    # evita travar em máquinas com /dev/shm pequeno (contêineres e alguns Linux)
    opcoes.add_argument('--disable-dev-shm-usage')
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        # o Chrome se recusa a iniciar como root sem esta opção
        opcoes.add_argument('--no-sandbox')
    opcoes.add_experimental_option('excludeSwitches', ['enable-automation'])
    opcoes.add_experimental_option('useAutomationExtension', False)
    opcoes.add_experimental_option('prefs', {'download.default_directory': results_dir})
    return opcoes


def _iniciar_chrome(opcoes, caminho_do_driver):
    """Abre o Chrome pelo Selenium Manager ou pelo binário local, com plano B."""
    tentativas = []
    if caminho_do_driver:
        tentativas.append((caminho_do_driver, f'ChromeDriver local ({caminho_do_driver})'))
    else:
        tentativas.append((None, 'ChromeDriver baixado automaticamente (Selenium Manager)'))
        local = os.path.join(RAIZ_DO_PROJETO, nome_do_driver_no_sistema())
        if os.path.isfile(local):
            tentativas.append((local, f'ChromeDriver local ({local})'))

    ultimo_erro = None
    for caminho, descricao in tentativas:
        try:
            if caminho:
                driver = webdriver.Chrome(service=Service(caminho), options=opcoes)
            else:
                driver = webdriver.Chrome(options=opcoes)
            return driver, descricao
        except Exception as excecao:                     # tentamos o próximo caminho
            ultimo_erro = excecao
            if len(tentativas) > 1:
                print(f'[AVISO] Não foi possível usar {descricao}: {excecao}')
    raise ultimo_erro


def obter_driver(results_dir, caminho_do_driver=''):
    """Uma única sessão de navegador para toda a execução (abrir o Chrome é caro)."""
    global _driver_compartilhado, _descricao_do_driver

    if _driver_compartilhado is not None:
        return _driver_compartilhado

    if webdriver is None:
        raise RuntimeError(
            'Selenium não está instalado, mas é necessário para baixar currículos do Lattes. '
            'Instale as dependências e use o interpretador do ambiente virtual do projeto '
            '(ex.: source venv/bin/activate && python -m pip install -r requirements.txt).')

    if not tem_internet() and not caminho_do_driver:
        raise ConnectionError(
            f'Sem conexão com {HOST_LATTES}: não é possível baixar currículos novos agora. '
            f'Os currículos já baixados continuam na pasta de cache e serão reaproveitados. '
            f'Para incluir um currículo sem internet, salve a página no navegador e use '
            f'--adicionar-cv.')

    opcoes = _opcoes_do_chrome(results_dir)
    _driver_compartilhado, _descricao_do_driver = _iniciar_chrome(opcoes, caminho_do_driver)
    print(f'[INFO] Navegador iniciado: {_descricao_do_driver}')
    return _driver_compartilhado


def fechar_driver():
    global _driver_compartilhado, _descricao_do_driver
    if _driver_compartilhado is not None:
        try:
            _driver_compartilhado.quit()
        except Exception:
            pass
        _driver_compartilhado = None
        _descricao_do_driver = ''


atexit.register(fechar_driver)


# ---------------------------------------------------------------------------- #
# Currículos obtidos manualmente (sem navegador)
# ---------------------------------------------------------------------------- #
def parece_um_cv_lattes(texto):
    """Heurística: o arquivo é uma página de currículo Lattes?"""
    if not texto or len(texto) < 1500:
        return False
    encontrados = sum(1 for marcador in MARCADORES_DE_CV if marcador in texto)
    return encontrados >= 2


def identificador_do_cv(texto):
    """Extrai o identificador Lattes (16 ou 10 dígitos) de dentro do HTML, se possível."""
    for padrao in (r'font-weight:\s*bold;\s*color:\s*#326C99;?">\s*(\d{16})',
                   r'lattes\.cnpq\.br/(\d{16})',
                   r'[?&]id=(\d{16})',
                   r'[?&]id=(\d{10})',
                   r'lattes\.cnpq\.br/(\d{10})'):
        encontrado = re.search(padrao, texto)
        if encontrado:
            return encontrado.group(1)
    return ''


def adicionar_cv_local(origem, diretorio_cache, sobrescrever=False):
    """Copia um HTML salvo pelo usuário para a pasta de cache.

    `origem` pode ser um arquivo .html ou uma pasta com vários. Devolve
    (adicionados, problemas): listas de (caminho, identificador) e (caminho, motivo).
    """
    adicionados, problemas = [], []

    if os.path.isdir(origem):
        arquivos = [os.path.join(origem, nome) for nome in sorted(os.listdir(origem))
                    if os.path.isfile(os.path.join(origem, nome))
                    and os.path.splitext(nome)[1].lower() in ('.html', '.htm', '.xhtml', '')]
    elif os.path.isfile(origem):
        arquivos = [origem]
    else:
        problemas.append((origem, 'arquivo ou pasta não encontrado'))
        return adicionados, problemas

    if not arquivos:
        problemas.append((origem, 'nenhum arquivo .html encontrado'))
        return adicionados, problemas

    os.makedirs(diretorio_cache, exist_ok=True)

    for caminho in arquivos:
        try:
            with open(caminho, encoding='utf-8', errors='replace') as arquivo:
                texto = arquivo.read()
        except OSError as excecao:
            problemas.append((caminho, f'não foi possível ler: {excecao}'))
            continue

        if not parece_um_cv_lattes(texto):
            problemas.append((caminho, 'não parece um currículo Lattes '
                                       '(salve a página completa de lattes.cnpq.br/<id>)'))
            continue

        identificador = identificador_do_cv(texto)
        if not identificador:
            nome_base = os.path.splitext(os.path.basename(caminho))[0]
            if re.fullmatch(r'\d{10}|\d{16}', nome_base):
                identificador = nome_base
        if not identificador:
            problemas.append((caminho, 'não consegui identificar o número do currículo dentro do arquivo'))
            continue

        destino = os.path.join(diretorio_cache, identificador)
        if os.path.exists(destino) and not sobrescrever:
            problemas.append((caminho, f'o currículo {identificador} já está no cache (use --sobrescrever para substituir)'))
            continue

        try:
            with open(destino, 'w', encoding='utf-8') as arquivo:
                arquivo.write(texto)
        except OSError as excecao:
            problemas.append((caminho, f'não foi possível gravar em {destino}: {excecao}'))
            continue
        adicionados.append((caminho, identificador))

    return adicionados, problemas


# ---------------------------------------------------------------------------- #
class LattesRobot:
    def __init__(self, driver_path='', results_dir='', tentativas=3):
        self.driver_path = driver_path
        self.results_dir = results_dir
        self.driver = None
        self.identifiers = set()
        self.downloaded_identifiers = set()
        self.sleep_time = 4
        self.lid_type = -1
        self.tentativas = tentativas
        self.initialize()

    def initialize(self):
        if webdriver is None:
            raise RuntimeError(
                'Selenium não está instalado, mas é necessário para baixar currículos do Lattes. '
                'Instale as dependências e use o interpretador do ambiente virtual do projeto '
                '(ex.: source venv/bin/activate && python -m pip install -r requirements.txt).')

        # um caminho informado explicitamente precisa existir; sem caminho, o Selenium
        # Manager resolve o ChromeDriver sozinho
        self.caminho_do_driver = resolver_chromedriver(self.driver_path)

        if self.results_dir and not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

    def load_codes(self, id_lattes):
        self.identifiers.add(id_lattes)
        self.lid_type = len(id_lattes)

    def check_downloaded_cvs(self):
        if not os.path.isdir(self.results_dir):
            self.downloaded_identifiers = set()
            return
        self.downloaded_identifiers = {h for h in os.listdir(self.results_dir) if len(h) == self.lid_type}

    def create_driver(self):
        self.driver = obter_driver(self.results_dir, self.caminho_do_driver)
        return self.driver

    def collect_html_cvs(self, start, end):
        for identifier in sorted(self.identifiers)[start:end]:
            lids = self._get_lids_10_16(identifier)

            if lids[10]:
                if lids[self.lid_type] not in self.downloaded_identifiers:
                    self._execute_js(lids)

    def store_html(self, lid, page):
        with open(os.path.join(self.results_dir, lid), 'wb') as fout:
            try:
                #data = page.encode('iso-8859-1', 'replace').strip()
                data = page.encode('utf-8', 'replace').strip()
            except UnicodeEncodeError:
                data = page.encode('utf-8').strip()

            if data:
                fout.write(data)

    def _execute_js(self, lids):
        self.driver.get(URL.format(lids[10]))
        time.sleep(self.sleep_time)

        cmd_open_cv = 'abreCV()'
        self.driver.execute_script(cmd_open_cv)
        time.sleep(self.sleep_time)

        janelas = self.driver.window_handles
        self.driver.switch_to.window(janelas[-1])

        try:
            if not lids[16]:
                lids[16] = self._extract_lid16(self.driver.page_source)

                if self.lid_type == 16 and (not lids[16] or len(lids[16]) != 16):
                    return

            self.store_html(lids[self.lid_type], self.driver.page_source)
        finally:
            # a janela extra (a do currículo) é fechada aqui: sem isso o navegador
            # acumularia uma aba por currículo baixado
            if len(janelas) > 1:
                try:
                    self.driver.close()
                    self.driver.switch_to.window(janelas[0])
                except WebDriverException:
                    pass

    def _get_lids_10_16(self, lid):
        lids = {10: '', 16: ''}

        if len(lid) == 10:
            lids[10] = lid

        if len(lid) == 16:
            lids[16] = lid

            self.driver.get(URL_LATTES_ID16.format(lid))
            lid10 = urllib.parse.parse_qs(urllib.parse.urlparse(self.driver.current_url.encode()).query)
            if b'id' in lid10:
                lid10 = lid10[b'id'][0].decode('utf-8')
                if len(lid10) == 10:
                    lids[10] = lid10

        return lids

    def _extract_lid16(self, page_source):
        if bs4:
            soup = bs4.BeautifulSoup(page_source, 'html.parser')
            span = soup.find('span', attrs={'style': 'font-weight: bold; color: #326C99;'})
            lid16 = span.text.encode() if span and span.text else b''
        else:
            match = re.search(r'<span style="font-weight: bold; color: #326C99;">(.*?)</span>', page_source)
            lid16 = match.group(1).encode() if match else b''

        if len(lid16) == 16 and lid16.isdigit():
            return lid16
        return None

    def _set_lid_type(self):
        if len(self.identifiers) > 0:
            ld = len(list(self.identifiers)[0])
            self.lid_type = ld


def __get_data(id_lattes, diretorio, caminho_do_driver=''):
    rob = LattesRobot(driver_path=caminho_do_driver, results_dir=diretorio)
    print(f"Baixando CV Lattes: {id_lattes}. Este processo pode demorar alguns segundos.")
    rob.load_codes(id_lattes)
    rob.check_downloaded_cvs()
    rob.create_driver()

    # a sessão do navegador é compartilhada entre os membros e fechada no fim da execução
    rob.collect_html_cvs(0, None)


def baixaCVLattes(id_lattes, diretorio, caminho_do_driver='', max_tentativas=3, espera=5):
    """Garante que o CV esteja no cache. Levanta erro explicativo se não conseguir."""
    destino = os.path.join(diretorio, id_lattes)

    for tentativa in range(1, max_tentativas + 1):
        if os.path.exists(destino):
            return destino

        try:
            __get_data(id_lattes, diretorio, caminho_do_driver)
        except WebDriverException as excecao:
            if 'ERR_CONNECTION_REFUSED' in str(excecao) or 'ERR_INTERNET_DISCONNECTED' in str(excecao):
                print(f'[AVISO] A plataforma Lattes recusou a conexão (possível limite de acessos). '
                      f'Aguardando {espera}s antes de tentar de novo...')
                time.sleep(espera)
                continue
            raise

        if os.path.exists(destino):
            return destino

        if tentativa < max_tentativas:
            print(f'[AVISO] O currículo {id_lattes} não foi salvo (tentativa {tentativa} '
                  f'de {max_tentativas}). Tentando de novo em {espera}s...')
            time.sleep(espera)

    raise RuntimeError(f'Não foi possível baixar o CV Lattes de {id_lattes} após {max_tentativas} '
                       f'tentativas. Verifique a conexão ou use --adicionar-cv para incluir '
                       f'o currículo salvo pelo navegador.')
