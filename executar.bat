@echo off
rem scriptLattes - lancador para Windows.
rem Cuida de tudo: encontra o Python, cria o ambiente virtual, instala as dependencias
rem e executa o scriptLattes com o interpretador correto.
rem
rem Uso (clique duas vezes ou use o Prompt de Comando):
rem   executar.bat                    - roda o exemplo que vem no projeto (sem configurar nada)
rem   executar.bat meu-grupo.config   - roda o seu grupo
rem   executar.bat --assistente       - pergunta os dados e cria o seu .config e .list
rem   executar.bat --janela           - abre a interface grafica
rem   executar.bat --diagnostico      - verifica o ambiente (Python, Chrome, rede, cache)
setlocal
cd /d "%~dp0"

echo ======================================================================
echo  scriptLattes - assistente de execucao
echo ======================================================================

rem 1) Python ------------------------------------------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)

if not defined PY (
    echo [ERRO] Nao encontrei o Python 3 neste computador.
    echo Instale o Python 3.9 ou mais novo em https://www.python.org/downloads/
    echo IMPORTANTE: marque a opcao "Add python.exe to PATH" durante a instalacao.
    goto fim
)
echo [1/4] Python encontrado:
%PY% --version
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Este Python e antigo demais. Instale o Python 3.9 ou mais novo:
    echo   https://www.python.org/downloads/
    goto fim
)

rem 2) Ambiente virtual --------------------------------------------------------
if exist "venv\Scripts\python.exe" (
    echo [2/4] Ambiente virtual do projeto ja existe ^(venv\^)
) else (
    echo [2/4] Criando o ambiente virtual ^(venv\^)... isso acontece so na primeira vez
    %PY% -m venv venv
    if errorlevel 1 (
        echo [ERRO] Nao consegui criar o ambiente virtual.
        goto fim
    )
)
set "PYVENV=venv\Scripts\python.exe"
if not exist "%PYVENV%" (
    echo [ERRO] O ambiente virtual ficou incompleto: %PYVENV% nao existe.
    echo Apague a pasta venv e rode este arquivo de novo.
    goto fim
)

rem 3) Dependencias ------------------------------------------------------------
set "INSTALAR=1"
"%PYVENV%" -c "import bs4, tqdm, networkx" >nul 2>&1 || set "INSTALAR=1"
if exist "venv\.dependencias-ok" (
    for /f %%i in ('powershell -NoProfile -Command "(Get-Item 'venv\.dependencias-ok').LastWriteTime -lt (Get-Item 'requirements.txt').LastWriteTime" 2^>nul') do (
        if /i "%%i"=="False" set "INSTALAR="
    )
)
if defined INSTALAR (
    echo [3/4] Instalando as dependencias ^(precisa de internet; so na primeira vez^)
    "%PYVENV%" -m pip install --quiet --upgrade pip
    "%PYVENV%" -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar as dependencias.
        echo Confira a conexao com a internet e tente de novo.
        goto fim
    )
    echo ok> "venv\.dependencias-ok"
) else (
    echo [3/4] Dependencias ja instaladas
)

rem 4) scriptLattes -----------------------------------------------------------
if "%~1"=="" (
    echo [4/4] Nenhum arquivo .config indicado: rodando a demonstracao offline do projeto
    echo       Para rodar o seu grupo:  executar.bat seu-arquivo.config
    echo       Para criar o seu grupo:  executar.bat --assistente
    "%PYVENV%" scriptLattes.py exemplo\demo.config
) else (
    echo [4/4] Executando o scriptLattes
    "%PYVENV%" scriptLattes.py %*
)
set "CODIGO=%ERRORLEVEL%"

echo ----------------------------------------------------------------------
if "%CODIGO%"=="0" (
    echo Concluido com sucesso. Abra o arquivo index.html da pasta de saida.
    echo Duvidas? Rode:  executar.bat --diagnostico
) else (
    echo A execucao terminou com erro ^(codigo %CODIGO%^).
    echo Siga as instrucoes do bloco [ERRO] acima. Para ver o detalhe tecnico:
    echo   executar.bat --debug %*
)

:fim
if not defined CI (
    echo.
    echo Pressione qualquer tecla para fechar esta janela...
    pause >nul
)
endlocal
