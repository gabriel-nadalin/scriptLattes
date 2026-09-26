# scriptLattes

Fork do [jpmenachalco/scriptLattes](https://github.com/jpmenachalco/scriptLattes): programa
GNU-GPL que baixa currículos da Plataforma Lattes e gera os relatórios de produção científica
de um grupo. O original é de Jesús P. Mena-Chalco e Roberto M. Cesar-Jr (IME/USP) e continua
sendo a referência; o que está aqui é a minha cópia, com alterações para customizar alguns comportamentos. Licença GPLv2, veja `COPYING`.

- original (upstream): https://github.com/jpmenachalco/scriptLattes
- este fork (origin): https://github.com/gabriel-nadalin/scriptLattes

## O que mudou em relação ao original

- Correção na exportação JSON: campos que existiam no Lattes mas saíam vazios (`titulo_livro`,
  `jornal`, `natureza` de entrevistas e apresentações, `curso` das orientações) e remoção de
  chaves que nunca eram preenchidas.
- `global-itens_desde_o_ano = hoje` não quebra mais (faltava `import datetime`) e o traceback
  não é mais escondido em caso de erro.
- Assistente de terminal (`--assistente`) e janela gráfica (`--janela`) para quem não quer
  editar `.config` à mão; mensagens de erro explicam o que fazer e `--diagnostico` confere o
  ambiente.
- Lançadores `executar.sh` / `executar.command` / `executar.bat`: criam o ambiente virtual,
  instalam as dependências e executam. Sem argumentos, rodam uma demonstração offline com
  currículos sintéticos.
- Normalização dos dados coletados, em camadas, sem nunca apagar o texto original (detalhes
  abaixo).
- `chromedriver` de 18 MB saiu do versionamento (o Makefile baixa quando precisa) e o programa
  passou a resolver os arquivos que o acompanham pela pasta do projeto, não pela pasta de onde
  foi chamado.
- Empacotamento opcional com PyInstaller (`empacotar.py`) e workflows de CI.

## Como rodar (explicado passo a passo)

Esta seção é para quem nunca usou o terminal. As seções seguintes são as mesmas instruções em
forma curta.

### Em qualquer sistema, antes de tudo: instale o Python

O scriptLattes é um programa em Python, então o Python precisa estar no computador.

- **Windows**: baixe em <https://www.python.org/downloads/> e, na primeira tela do instalador,
  **marque a caixa "Add python.exe to PATH"** antes de clicar em *Install Now*. Esse detalhe é o
  que faz o lançador encontrar o Python depois.
- **macOS**: baixe em <https://www.python.org/downloads/> e clique em *Install Now* (pode precisar
  da sua senha). Esse instalador já traz o Tkinter, que é o que a janela gráfica usa; quem instala
  o Python pelo Homebrew precisa de `brew install python-tk`.
- **Linux (Debian/Ubuntu)**: `sudo apt install python3 python3-tk python3-venv`
  (no Fedora: `sudo dnf install python3 python3-tkinter python3-virtualenv`).

### Baixe o programa

Se você só quer usar: na página do repositório, clique no botão verde **Code → Download ZIP** e
descompacte em uma pasta sua (ex.: `Documentos/scriptlattes`).
Se tem Git: `git clone https://github.com/gabriel-nadalin/scriptLattes.git`.

### Rode a demonstração (Windows, sem digitar nada)

1. Abra a pasta do programa.
2. Clique duas vezes em **`executar.bat`**.
3. Na primeira vez ele instala o que falta — precisa de internet. Nas próximas, começa direto.
4. Ao terminar aparece `Concluido com sucesso`; pressione qualquer tecla para fechar.
5. Abra a pasta `exemplo/demo-lattes/saida` e dê dois cliques em **`index.html`**.

Se a janela fechar na mesma hora ou der erro, o próprio `executar.bat` mostra o motivo (falta de
Python, falta de internet) e espera você ler antes de fechar.

### Rode a demonstração (macOS, sem digitar nada)

1. Abra a pasta do programa no **Finder**.
2. Clique duas vezes em **`executar.command`**.
3. Na primeira vez o macOS pode dizer que o arquivo não pode ser aberto. Vá em
   **Ajustes do Sistema → Privacidade e Segurança**, procure a mensagem sobre o `executar.command`
   e clique em **"Abrir mesmo assim"**, confirmando com a sua senha. Se não aparecer nada lá:
   clique com o botão direito (ou Control+clique) no `executar.command` e escolha **Abrir**.
4. O resultado sai em `exemplo/demo-lattes/saida` — abra o `index.html`.

### Rode a demonstração (Linux, sem digitar nada)

Muitas versões do Linux abrem um aviso ao clicar duas vezes em um arquivo `.sh`. Se abrir, escolha
**Executar**. Se nada acontecer ou o arquivo abrir no editor de textos, use o terminal:

```bash
cd caminho/da/pasta/scriptLattes
./executar.sh
```

O resultado sai em `exemplo/demo-lattes/saida`. Se aparecer `Permissão negada`, rode antes:
`chmod +x executar.sh`.

### Agora com os seus currículos (qualquer sistema)

1. Entre na pasta do programa (`cd caminho/da/pasta/scriptLattes`).
2. Rode o assistente e responda o que ele pergunta:
   - Windows: `executar.bat --assistente`
   - macOS/Linux: `./executar.sh --assistente`
   - Se preferir janela em vez do terminal: troque `--assistente` por `--janela`.
3. Ele pede, em ordem: o nome do grupo; os links ou números dos currículos Lattes; o ano inicial e
   o final; a pasta de saída; a pasta de currículos; o seu e-mail (opcional). Para aceitar a
   sugestão entre `[colchetes]`, basta apertar **Enter**.
4. No fim ele pergunta se pode gerar os relatórios na sequência (responda `s`). Se o computador
   ainda não tiver baixado esses currículos, o programa baixa agora — só nesta parte o Google
   Chrome é necessário, e pode demorar.
5. Abra o `index.html` da pasta de saída que você escolheu.

Um currículo do Lattes é identificado por 16 números. No site, o endereço é
`http://lattes.cnpq.br/1234567890123456` — pode colar o endereço inteiro ou só os números, um por
linha.

### Se der problema

Rode o diagnóstico e leia a última parte da saída, que diz o que está faltando:

- Windows: `executar.bat --diagnostico`
- macOS/Linux: `./executar.sh --diagnostico`

## Como rodar (resumo)

Precisa de Python 3.9 ou mais novo. Nada além disso para processar currículos que já estejam
no cache.

```bash
./executar.sh                            # Linux/macOS: roda a demonstração, sem internet
executar.bat                             # Windows: idem
./executar.sh meu-grupo.config           # roda o seu grupo
```

O lançador cuida do ambiente virtual (`venv/`) e das dependências na primeira execução. Se
preferir fazer isso na mão:

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python scriptLattes.py exemplo/demo.config
```

Há também um Makefile com `make install` (ambiente + dependências + ChromeDriver), `make test`,
`make status` e `make clean`.

### Criar o seu grupo

```bash
./executar.sh --assistente      # pergunta: nome, IDs/links dos currículos, período,
                                # pastas de saída e de cache — e cria o .config e o .list
./executar.sh --janela          # a mesma coisa em uma janela (requer Tkinter instalado)
```

No assistente, cole um currículo por linha (o ID tem 16 dígitos: `http://lattes.cnpq.br/1234567890123456`
ou só `1234567890123456`) e deixe uma linha em branco para terminar. O `.config` e o `.list`
gerados são arquivos de texto comuns — dá para editar à mão depois.

### Baixar currículos novos

Exige Google Chrome ou Chromium instalado; o ChromeDriver compatível é baixado por
`make install` (ou automaticamente, na primeira execução). Sem navegador nenhum, o caminho é
manual: abra o currículo no navegador, salve a página como HTML e importe.

```bash
./executar.sh --adicionar-cv curriculo.html          # um arquivo
./executar.sh --adicionar-cv pasta-de-htmls/         # ou uma pasta inteira
./executar.sh --adicionar-cv x.html --cache ./cache/ --sobrescrever
```

O download em si é retomável: se você interromper com Ctrl+C, o que já foi baixado continua no
cache e uma nova execução segue de onde parou.

## Opções da linha de comando

| Opção | O que faz |
|---|---|
| *(sem argumento)* | roda a demonstração offline (`exemplo/demo.config`) |
| `arquivo.config` | gera os relatórios daquele grupo |
| `--assistente` | cria o `.config` e o `.list` respondendo perguntas |
| `--janela` | interface gráfica |
| `--diagnostico` | confere Python, dependências, Chrome, ChromeDriver, rede e cache |
| `--adicionar-cv CAMINHO` | importa currículos em HTML para o cache |
| `--cache PASTA` | pasta de cache usada por `--adicionar-cv` |
| `--sobrescrever` | em `--adicionar-cv`, substitui o que já existe |
| `--nao-abrir` | não abre o relatório no navegador no final |
| `--debug` | mostra o traceback completo quando algo dá errado |

## O que sai

Na pasta de `global-diretorio_de_saida`:

- `index.html` — por onde começar
- `LEIA-ME.txt` — resumo do que foi gerado e o aviso sobre dados pessoais (LGPD)
- `scriptlattes-log.txt` — registro da execução; anexe ao pedir ajuda
- `json/` — um arquivo por pesquisador
- `grafo_de_colaboracoes.gexf` e páginas de grafo, `css/`, `js/`

Códigos de saída: `0` sucesso, `1` erro inesperado (rode com `--debug`), `2` problema no
`.config`/`.list`, `3` problema de ambiente ou algum currículo de fora dos relatórios, `130`
interrompido com Ctrl+C.

Exemplos com os JSONs:

```bash
jq '.estatisticas' json/*.json
jq '.areas_de_atuacao[] | {area, subarea, especialidade}' json/*.json
jq '.projetos_desenvolvimento[].nome' json/*.json
```

## Configuração principal

```
global-nome_do_grupo                      = Meu grupo
global-arquivo_de_entrada                 = ./meu-grupo.list
global-diretorio_de_saida                 = ./saida/
global-diretorio_de_armazenamento_de_cvs  = ./cache/
global-itens_desde_o_ano                  = 2000
global-itens_ate_o_ano                    = hoje
```

Caminhos relativos são resolvidos em relação ao arquivo `.config`, depois à pasta de execução e
por fim à pasta do programa.

## Normalização dos dados coletados

Os textos vêm do Lattes e variam muito entre pessoas (grafia de eventos, nomes de autores,
instituições). A normalização é determinística e nunca destrói o texto original — os campos
brutos continuam nos JSONs, e as chaves são adicionadas ao lado deles.

| Camada | O que faz |
|---|---|
| L1 | separa a citação do evento em `evento`, `evento_edicao`, `evento_sigla`, `evento_local`, `evento_veiculo` |
| L2 | `normalizar_chave`, `separar_edicao`, `detectar_sigla`, `chave_de_evento`, `chave_de_instituicao` |
| L3 | identidade de autores (`mesma_pessoa`) e tabelas de aliases preenchidas à mão |

As tabelas ficam em `dados/aliases/` (`eventos.csv: chave,serie,sigla,nome_canonico`,
`instituicoes.csv: chave,nome_canonico`, `periodicos.csv: issn,nome_canonico`,
`pesquisadores.csv: nome_a,nome_b`). Depois de rodar o scriptLattes, o relatório de candidatos
lista o que ainda está sem alias, ordenado por frequência:

```bash
python -m scriptLattes.normalizacao --saida ./saida --destino dados/aliases
```

Gera `pendentes_eventos.csv`, `pendentes_instituicoes.csv`, `pendentes_periodicos.csv`,
`pendentes_pesquisadores.csv` (derivados, não versionados) e `pendentes_similares.csv` com
grafias parecidas para revisar. Preencher as tabelas e rodar de novo é o ciclo completo.
`global-normalizacao = nao` desliga L2/L3 e volta ao comportamento anterior.

## Gerar o executável

```bash
pip install pyinstaller
python empacotar.py           # dist/scriptlattes (dist/scriptlattes.exe no Windows)
```

O binário leva junto `css/`, `js/`, `dados/` e `exemplo/`, e funciona sem instalação para
processar currículos já em cache. O workflow `.github/workflows/release.yml` gera os três
sistemas (Windows, Linux, macOS) e o tarball do código-fonte ao publicar uma tag `v*`.

## Testes

```bash
venv/bin/python -m unittest discover -s tests
```

## Sincronizar com o original

```bash
git fetch upstream
git merge upstream/main
```

`upstream` aponta para `jpmenachalco/scriptLattes`; `origin` é este fork.

## Créditos e citação

O scriptLattes foi idealizado e desenvolvido por Jesús P. Mena-Chalco e Roberto M. Cesar-Jr. Para
citar, use os trabalhos abaixo (ou veja a seção correspondente no repositório original, que
também mantém um Discord para dúvidas):

- J. P. Mena-Chalco e R. M. Cesar-Jr. *scriptLattes: An open-source knowledge extraction system
  from the Lattes platform.* Journal of the Brazilian Computer Society, v. 15, n. 4, p. 31–39,
  2009. https://doi.org/10.1007/BF03194511
- J. P. Mena-Chalco e R. M. Cesar-Jr. *Prospecção de dados acadêmicos de currículos Lattes
  através do scriptLattes.* In: Bibliometria e Cientometria: reflexões teóricas e interfaces.
  São Carlos: Pedro & João, p. 109–128, 2013.

O scriptLattes não tem vínculo com o CNPq: é um esforço independente para automatizar a
compilação de informações que já são públicas nos currículos Lattes.
