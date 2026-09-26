#!/usr/bin/env bash
# scriptLattes - lançador para Linux/macOS.
# Cuida de tudo: encontra o Python, cria o ambiente virtual, instala as dependências
# e executa o scriptLattes com o interpretador correto.
#
# Uso:
#   ./executar.sh                          -> roda o exemplo que vem no projeto (sem configurar nada)
#   ./executar.sh meu-grupo.config         -> roda o seu grupo
#   ./executar.sh --assistente             -> pergunta os dados e cria o seu .config e .list
#   ./executar.sh --janela                 -> abre a interface grafica (se houver tela)
#   ./executar.sh --diagnostico            -> verifica o ambiente (Python, Chrome, rede, cache)
set -u

cd "$(dirname "$0")" || exit 1

verde=$'\033[0;32m'; amarelo=$'\033[0;33m'; vermelho=$'\033[0;31m'; normal=$'\033[0m'
[ -t 1 ] || { verde=''; amarelo=''; vermelho=''; normal=''; }

echo "======================================================================"
echo " scriptLattes - assistente de execução"
echo "======================================================================"

# 1) Python -------------------------------------------------------------------
PY=""
for candidato in python3 python; do
    if command -v "$candidato" >/dev/null 2>&1; then
        if "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
            PY="$candidato"; break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "${vermelho}Nao encontrei o Python 3 neste computador.${normal}"
    echo "Instale o Python 3.9 ou mais novo e rode este arquivo de novo:"
    echo "  https://www.python.org/downloads/"
    exit 3
fi
echo "${verde}[1/4]${normal} Python encontrado: $($PY --version 2>&1)"

# 2) Ambiente virtual ---------------------------------------------------------
if [ -x "venv/bin/python" ]; then
echo "${verde}[2/4]${normal} Ambiente virtual do projeto ja existe (venv/)"
else
    echo "${verde}[2/4]${normal} Criando o ambiente virtual (venv/)... isso acontece so na primeira vez"
    if ! "$PY" -m venv venv; then
        echo "${vermelho}Nao consegui criar o ambiente virtual.${normal}"
        echo "No Debian/Ubuntu pode faltar o pacote:  sudo apt install python3-venv"
        exit 3
    fi
fi
if [ ! -x "venv/bin/python" ]; then
    echo "${vermelho}O ambiente virtual ficou incompleto (venv/bin/python nao existe).${normal}"
    echo "Apague a pasta venv/ e rode este arquivo de novo."
    exit 3
fi
PYVENV="venv/bin/python"

# 3) Dependencias -------------------------------------------------------------
if "$PYVENV" -c 'import bs4, tqdm, networkx' >/dev/null 2>&1 \
   && [ -f venv/.dependencias-ok ] \
   && [ venv/.dependencias-ok -nt requirements.txt ]; then
    echo "${verde}[3/4]${normal} Dependencias ja instaladas"
else
    echo "${verde}[3/4]${normal} Instalando as dependencias (precisa de internet; so na primeira vez)"
    if ! "$PYVENV" -m pip install --quiet --upgrade pip \
       || ! "$PYVENV" -m pip install --quiet -r requirements.txt; then
        echo "${vermelho}Falha ao instalar as dependencias.${normal}"
        echo "Confira a conexao com a internet e tente de novo."
        echo "Se a sua rede usa proxy, configure as variaveis HTTP_PROXY/HTTPS_PROXY."
        exit 3
    fi
    touch venv/.dependencias-ok
fi

# 4) scriptLattes ------------------------------------------------------------
if [ "$#" -eq 0 ]; then
    echo "${amarelo}[4/4]${normal} Nenhum arquivo .config indicado: rodando a demonstracao offline do projeto"
    echo "      Para rodar o seu grupo:   ./executar.sh seu-arquivo.config"
    echo "      Para criar o seu grupo:   ./executar.sh --assistente"
    set -- exemplo/demo.config
else
    echo "${verde}[4/4]${normal} Executando o scriptLattes"
fi
echo "----------------------------------------------------------------------"

"$PYVENV" scriptLattes.py "$@"
codigo=$?

echo "----------------------------------------------------------------------"
if [ $codigo -eq 0 ]; then
    echo "${verde}Concluido com sucesso.${normal} Abra o arquivo index.html da pasta de saida."
    echo "Duvidas? Rode:  ./executar.sh --diagnostico"
else
    echo "${vermelho}A execucao terminou com erro (codigo $codigo).${normal}"
    echo "Siga as instrucoes do bloco [ERRO] acima. Para ver o detalhe tecnico:"
    echo "  ./executar.sh --debug $( [ "$#" -gt 0 ] && echo "$1" )"
fi
exit $codigo
