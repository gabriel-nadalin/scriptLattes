# scriptLattes
O CNPq realiza um enérgico trabalho na integração de bases de currículos acadêmicos de instituições públicas e privadas em uma única plataforma denominada Lattes. Os chamados ``Currículos Lattes'' são considerados um padrão nacional de avaliação representando um histórico das atividades científicas / acadêmicas / profissionais de pesquisadores cadastrados. Os currículos Lattes foram projetados para mostrar informação pública, embora, individual de cada usuário cadastrado na plataforma. Muitas vezes, realizar uma compilação ou sumarização de produções bibliográficas para um grupo de usuários cadastrados de médio ou grande porte (e.g. grupo de professores, departamento de pós-graduação) realmente requer um grande esforço mecânico que muitas vezes é suscetível a falhas.

O scriptLattes é um script GNU-GPL desenvolvido para a extração e compilação automática de: (1) produções bibliográficas, (2) produções técnicas, (3) produções artísticas, (4) orientações, (5) projetos de pesquisa, (6) projetos de extensão, **(7) projetos de desenvolvimento**, (8) áreas de atuação com especialidades, (9) prêmios e títulos, e (10) grafo de colaborações de um conjunto de pesquisadores cadastrados na plataforma Lattes. **Associações de Qualis não estão implementadas nesta versão em Python** (nenhum campo `qualis` é preenchido).

O scriptLattes baixa automaticamente os currículos Lattes em formato HTML (livremente disponíveis na rede) de um grupo de pessoas de interesse, compila as listas de produções, tratando apropriadamente as produções duplicadas e similares. São geradas páginas HTML com listas de produções e orientações separadas por tipo e colocadas em ordem cronológica invertida. **Além dos relatórios HTML tradicionais, o sistema agora gera automaticamente arquivos JSON individuais para cada pesquisador, facilitando a análise de dados e integração com outras ferramentas.** Adicionalmente são criadas automaticamente vários grafos (redes) de co-autoria entre os membros do grupo de interesse e um mapa de geolocalização dos membros e alunos (de pós-doutorado, doutorado e mestrado) com orientação concluída. Os relatórios gerados permitem avaliar, analisar ou documentar a produção de grupos de pesquisa. Este projeto de software livre foi idealizado por Jesús P. Mena-Chalco e Roberto M. Cesar-Jr em 2005 (IME/USP).

O scriptLattes atualmente permite filtrar as produções científicas usando termos de pesquisa (Veja os exemplo teste-03).

## 🚀 Comece aqui (sem experiência com terminal)

### Opção mais simples: baixe o executável

Nas [releases](https://github.com/jpmenachalco/scriptLattes/releases) há um arquivo por sistema
(Windows, Linux, macOS) que **já inclui o Python e tudo o que o programa precisa**:

1. baixe o arquivo do seu sistema e descompacte;
2. clique duas vezes no programa (`scriptlattes.exe`, `scriptlattes` ou `scriptlattes.command`);
3. sem indicar nenhum grupo, ele roda a **demonstração** (currículos de exemplo, nada é baixado
   da internet) e cria a pasta `resultado-demonstracao` com os relatórios e um `LEIA-ME.txt`;
4. para os seus dados, rode o mesmo programa com `--assistente` (responde 4 perguntas) ou
   `--janela` (janela gráfica).

O programa é GPLv2: o código-fonte correspondente a cada release é publicado junto aos
executáveis.

Você **não** precisa saber programar, criar ambiente virtual nem baixar ChromeDriver: o lançador faz isso por você.

- **Windows**: clique duas vezes em `executar.bat`
- **Linux/macOS**: `./executar.sh` — no macOS também funciona clicar duas vezes em `executar.command`

Na primeira execução ele encontra o Python, cria o ambiente virtual `venv/`, instala as dependências (precisa de internet) e roda o projeto. Das próximas vezes é só executar.

Para rodar o **seu** grupo:

```bash
./executar.sh meu-grupo.config     # Linux/macOS
executar.bat meu-grupo.config      # Windows
```

Se algo der errado, comece por aqui — o diagnóstico diz exatamente o que está faltando:

```bash
./executar.sh --diagnostico        # ou: python scriptLattes.py --diagnostico
```

Ele verifica Python, dependências, Chrome, ChromeDriver, internet, pasta de cache e permissões de escrita, e termina com `PODE RODAR` ou com a lista do que corrigir.

### Rodando a partir do código-fonte

Se você baixou o código (ou clonou o repositório), use os lançadores abaixo — eles criam o
ambiente virtual e instalam as dependências sozinhos.

### Prefere não mexer em arquivos de configuração?

Duas formas de criar o `.config` e o `.list` sem editar nada:

| Forma | Como | Para quem |
|-------|------|-----------|
| Assistente no terminal | `python scriptLattes.py --assistente` | quem está no terminal |
| Janela gráfica | `python scriptLattes.py --janela` | quem prefere clicar |

Nos dois casos você responde apenas: nome do grupo, currículos Lattes (cole os links ou os
números, um por linha), período e pasta de saída. Os arquivos são criados e os relatórios já
podem ser gerados na sequência. No Linux, a janela precisa do pacote `python3-tk`
(`sudo apt install python3-tk`); sem ele, use o assistente.

### Onde estão os resultados?

Na pasta indicada por `global-diretorio_de_saida` no `.config`. Abra o `index.html` dela. Toda pasta de saída recebe:

- `LEIA-ME.txt` — o que foi gerado, por onde começar e o aviso de dados pessoais (LGPD)
- `scriptlattes-log.txt` — registro completo da execução; **anexe este arquivo ao pedir ajuda**

### Códigos de saída

| Código | Significado |
|--------|-------------|
| 0 | sucesso |
| 1 | erro inesperado — rode com `--debug` e envie o log |
| 2 | problema no `.config`/`.list` ou permissão de escrita |
| 3 | problema de ambiente (dependências, Chrome/ChromeDriver, internet) **ou** algum currículo que ficou de fora dos relatórios |
| 130 | interrompido com Ctrl+C — o que já foi baixado continua no cache |

### Sobre o exemplo que vem no projeto

Há dois exemplos:

- **`exemplo/demo.config`** (usado pelo lançador, sem argumentos): roda em segundos, **sem
  internet, sem Chrome e sem baixar nada**, porque usa três currículos *sintéticos* (inventados)
  que ficam versionados em `exemplo/demo-lattes/cache/`. É a forma mais rápida de ver o programa
  funcionando de ponta a ponta. Para regerar esses currículos:
  `python exemplo/demo-lattes/gerar_cvs_sinteticos.py`.
- **`exemplo/teste-01.config`**: usa 3 currículos reais; se não estiverem em `cache/`, eles são
  baixados (precisa do Google Chrome instalado).

### Sem navegador? Modo manual

Dá para processar currículos sem Chrome/ChromeDriver: abra `http://lattes.cnpq.br/SEU_ID` no navegador, salve a página como HTML e importe com `python scriptLattes.py --adicionar-cv arquivo.html` (veja a seção acima). O arquivo pode também ser colocado direto na pasta de cache com o nome do ID (16 dígitos), por exemplo `cache/1234567890123456`.

## ✨ Principais Funcionalidades Implementadas

### 🔄 Extração Aprimorada de Projetos
- **Projetos de Pesquisa**: Extração completa com padrão `salvarParte3`
- **Projetos de Extensão**: Suporte completo para múltiplos projetos
- **Projetos de Desenvolvimento**: **Nova funcionalidade** - extração completa de projetos de desenvolvimento/tecnológicos
- **Correção de Bugs**: Resolvido problema de contaminação de dados entre membros

### 🎯 Áreas de Atuação Melhoradas
- **Múltiplas Áreas**: Extração correta de todas as áreas de atuação de cada pesquisador
- **Estrutura Completa**: Grande área, área, subárea e **especialidade** quando disponível
- **Parsing Inteligente**: Regex otimizado para capturar especialidades com espaços e caracteres especiais

### 📄 Exportação JSON Abrangente
- **Arquivos Individuais**: JSON separado para cada pesquisador
- **Estrutura Completa**: Todos os tipos de dados disponibilizados
- **Estatísticas Atualizadas**: Contadores automáticos para todos os tipos de produção

### 🔧 Melhorias Técnicas
- **Parser Robusto**: Correções na lógica de parsing HTML
- **Estado Isolado**: Cada membro processado independentemente
- **Flags Corrigidas**: Reset apropriado de flags de seção
- **Tratamento de Idiomas**: Suporte para múltiplos idiomas por pesquisador

## Gerar o executável (para quem vai distribuir)

```bash
pip install pyinstaller
python empacotar.py           # gera dist/scriptlattes (ou dist/scriptlattes.exe no Windows)
dist/scriptlattes --diagnostico
```

O executável leva junto as páginas modelo (`css/`, `js/`), as tabelas de normalização
(`dados/`) e os currículos de exemplo (`exemplo/`), e funciona sem internet para processar
currículos já em cache. O workflow `.github/workflows/release.yml` gera os três executáveis
(Windows, Linux, macOS) mais o tarball do código-fonte ao publicar uma tag `v*`.

## Pré-requisitos
- **Python 3**: Certifique-se de ter o Python 3 instalado no seu computador. 
  Se não tiver, você pode baixá-lo em [python.org](https://www.python.org/downloads/).
- **Google Chrome ou Chromium**: Necessário para o funcionamento do ChromeDriver.
- **jq**: Utilitário para processamento JSON (necessário apenas para o Makefile):
  - Ubuntu/Debian: `sudo apt-get install jq`
  - CentOS/RHEL/Fedora: `sudo yum install jq` ou `sudo dnf install jq`
  - macOS: `brew install jq`
- **wget**: Para download do ChromeDriver pelo Makefile (geralmente já instalado)

> O lançador (`executar.sh` / `executar.bat` / `executar.command`) **não precisa** de `make`, `jq`, `wget` nem de
> `unzip`: ele usa apenas o Python e o `pip`.

### Baixar currículos novos (ChromeDriver automático)

Para baixar currículos que ainda não estão em `cache/`, basta ter o **Google Chrome instalado**:
o próprio Selenium baixa a versão correta do ChromeDriver (por isso o Selenium Manager aparece
no log). Você **não precisa** baixar o ChromeDriver na mão.

Se a sua rede não permite esse download automático, informe um ChromeDriver já instalado no
`.config`:

```
global-caminho_do_chromedriver = ./chromedriver
```

O binário na raiz do projeto também é usado como plano B se o download automático falhar.
Para baixá-lo manualmente, `make setup-chromedriver` (Linux) continua disponível.

### Sem navegador nenhum: modo manual

Dá para usar o scriptLattes sem Chrome e sem ChromeDriver:

1. Abra `http://lattes.cnpq.br/<id-do-curriculo>` no navegador;
2. salve a página completa (Ctrl+S / "Salvar como…", tipo "Página da Web completa" ou HTML);
3. importe o arquivo (ou a pasta inteira de arquivos) para o cache:

```bash
python scriptLattes.py --adicionar-cv "/caminho/do/curriculo.html"          # um arquivo
python scriptLattes.py --adicionar-cv "/caminho/da/pasta-de-htmls"          # a pasta toda
```

O comando confere se o arquivo é mesmo um currículo Lattes, descobre o número do currículo
dentro do HTML e guarda no cache com o nome certo. Use `--cache PASTA` para escolher outra
pasta de cache e `--sobrescrever` para substituir um currículo já existente.

### Baixar muitos currículos: paciência e retomada

Cada currículo leva alguns segundos. A execução **mostra o progresso** (`[3/10] Nome`), e o que
já foi baixado fica em `cache/`. Se a execução parar no meio (falta de internet, Ctrl+C, erro em
um currículo), **basta rodar o mesmo comando de novo**: o que já está no cache não é baixado outra
vez. Se algum currículo falhar, o programa termina com código 3 e lista quem ficou de fora dos
relatórios — os demais membros são processados normalmente.

## Instalação Rápida (Recomendada)

Para uma instalação completa automatizada, use o Makefile incluído:

```bash
# Clone o repositório
git clone https://github.com/jpmenachalco/scriptLattes.git
cd scriptLattes

# Instalação completa (ambiente virtual + dependências + ChromeDriver)
make install
```

Este comando irá:
1. Criar um ambiente virtual Python
2. Instalar todas as dependências
3. Detectar automaticamente a versão do seu Chrome/Chromium
4. Baixar e configurar a versão correta do ChromeDriver (opcional: o Selenium Manager já faz
   isso sozinho quando há Chrome instalado; este passo serve para uso sem internet)

### Outros comandos úteis do Makefile:

```bash
make help                    # Mostra todos os comandos disponíveis
make status                  # Verifica o status da instalação
make test                    # Executa o exemplo de teste
make clean                   # Limpa arquivos temporários e cache
make update-chromedriver     # Atualiza o ChromeDriver
```

## Instalação Manual (Alternativa)

### 1. Clone este repositório para o seu computador
```bash
git clone https://github.com/jpmenachalco/scriptLattes.git
```

### 2. Navegue até o diretório do projeto
```bash
cd scriptLattes
```

### 3. Crie um ambiente virtual
```bash
python -m venv venv
```

#### Ative o ambiente virtual no Windows
```cmd
venv\Scripts\activate
```

#### Ative o ambiente virtual no Linux/Mac
```bash
source venv/bin/activate
```

### 4. Instale as dependências
```bash
pip install -r requirements.txt
```

### 5. Configure o ChromeDriver manualmente
Baixe o ChromeDriver correspondente à versão do seu navegador em [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/). É importante que as versões sejam compatíveis.

## Execução do Programa

### Com Makefile (ambiente virtual gerenciado automaticamente):
```bash
make test
```

### Manual (certifique-se de que o ambiente virtual está ativado):
```bash
source venv/bin/activate  # Linux/Mac
python3 scriptLattes.py exemplo/teste-01.config
```

## Estrutura de Saída

O scriptLattes gera vários tipos de saída para análise dos dados extraídos:

### Relatórios HTML
- Páginas HTML interativas com tabelas organizadas por tipo de produção
- Gráficos de colaboração e visualizações em rede
- Mapas de geolocalização dos pesquisadores e orientandos

### **Novidade: Exportação JSON Individual Completa**
A partir da versão atual, o scriptLattes gera automaticamente **arquivos JSON individuais para cada pesquisador** na pasta `json/` do diretório de saída.

**Estrutura Completa do JSON por pesquisador:**
- `informacoes_pessoais`: Dados básicos do pesquisador (Nome, ID Lattes, endereço profissional, etc.)
- `formacao_academica`: Histórico completo de formação acadêmica
- `projetos_pesquisa`: Lista completa de projetos de pesquisa com detalhes
- `projetos_extensao`: **Projetos de extensão universitária** - completo com descrições
- `projetos_desenvolvimento`: **🆕 NOVO - Projetos de desenvolvimento e tecnológicos** - totalmente implementado
- `areas_de_atuacao`: **Melhorado** - Múltiplas áreas com grande área, área, subárea e **especialidade** quando disponível
- `producao_bibliografica`: Artigos, livros, capítulos, trabalhos em congressos
- `producao_tecnica`: Softwares, produtos tecnológicos, trabalhos técnicos
- `patentes_registros`: Patentes, programas de computador, desenhos industriais
- `producao_artistica`: Produções artísticas e culturais
- `orientacoes`: Orientações em andamento e concluídas (todas as modalidades)
- `eventos`: Participações e organizações de eventos
- `premios_titulos`: Prêmios e títulos recebidos
- `idiomas`: **Melhorado** - Múltiplos idiomas com proficiências detalhadas
- `estatisticas`: **Atualizado** - Resumo quantitativo incluindo projetos de desenvolvimento

**Exemplos práticos de uso dos dados JSON:**

```bash
# Listar todos os projetos de desenvolvimento (nova funcionalidade)
jq '.projetos_desenvolvimento[].nome' json/00_Paulo-Sergio-*.json

# Verificar todas as áreas de atuação com especialidades
jq '.areas_de_atuacao[] | {area: .area, subarea: .subarea, especialidade: .especialidade}' json/*.json

# Obter estatísticas completas incluindo projetos de desenvolvimento
jq '.estatisticas' json/00_Paulo-Sergio-*.json

# Extrair projetos de extensão
jq '.projetos_extensao[].nome' json/*.json

# Verificar todos os idiomas conhecidos pelos pesquisadores
jq '.idiomas[] | {nome: .nome, proficiencia_completa: .proficiencia_completa}' json/*.json

# Comparar tipos de projetos por pesquisador
jq '{nome: .informacoes_pessoais.nome_completo, projetos_pesquisa: (.estatisticas.total_projetos_pesquisa), projetos_extensao: (.estatisticas.total_projetos_extensao), projetos_desenvolvimento: (.estatisticas.total_projetos_desenvolvimento)}' json/*.json
```

**Melhorias na Estrutura de Dados:**

1. **Áreas de Atuação Aprimoradas:**
   ```json
   {
     "grande_area": "Ciências Exatas e da Terra",
     "area": "Ciência da Computação", 
     "subarea": "Metodologia e Técnicas da Computação",
     "especialidade": "Engenharia de Software",
     "descricao_completa": "Grande área: Ciências Exatas... / Especialidade: Engenharia de Software."
   }
   ```

2. **Projetos de Desenvolvimento (NOVO):**
   ```json
   {
     "nome": "ES Na Palma da Mão: Uma Plataforma baseado em serviços...",
     "ano_inicio": "2019",
     "ano_conclusao": "2020", 
     "descricao": ["Descrição completa do projeto..."],
     "tipo": "Projeto de desenvolvimento"
   }
   ```

3. **Estatísticas Expandidas:**
   ```json
   {
     "total_projetos_pesquisa": 9,
     "total_projetos_extensao": 2,
     "total_projetos_desenvolvimento": 7,
     "total_artigos_periodicos": 5
   }
   ```

### Correções de Campos do JSON

A exportação JSON foi alinhada aos atributos que o parser realmente preenche. Campos que nunca
eram populados (por não terem fonte no CV Lattes) foram removidos, e campos já disponíveis no
parser passaram a ser exportados:

**Removidos:** `artigos_periodicos.qualis`, `*.cidade` e `*.isbn` (livros, capítulos,
trabalhos em congresso, resumos, textos em jornal), `apresentacoes_trabalhos.evento`,
`producao_tecnica.*.instituicao`, `producao_tecnica.*.finalidade`, `entrevistas.veiculo`,
`patentes_registros.*.instituicao`, `patentes_registros.*.data`.

**Corrigidos:** `capitulos_livros.titulo_livro` (título do livro), `textos_jornais.jornal`
(nome do jornal), `entrevistas.natureza`, `apresentacoes_trabalhos.natureza` e
`orientacoes.*.curso` (extraído do formato `Curso (...) - Instituição`).

**Adicionados:** `volume`/`doi` em trabalhos e resumos, `edicao` em livros e capítulos,
`pais`, `tipo_patente` e `data_deposito` em patentes e registros, `tipo_orientacao` e
`agencia_fomento` em orientações, e `complemento` em produção artística.

**Orientações:** registros de orientações concluídas passam a ter apenas `ano_conclusao` — o
único ano disponível no CV Lattes (antes era duplicado em `ano_inicio`); as orientações em
andamento continuam a expor `ano_inicio`.

### Arquivos de Dados Estruturados
- **JSON**: um arquivo por pesquisador em `json/` (estrutura descrita acima)
- **GEXF/HTML**: grafo de colaborações em `grafo_de_colaboracoes.gexf` e `grafoDeColaboracoes.html`
- **TXT**: lista de colaboradores identificados (sem CV Lattes) em `colaboradores.txt`

*Nota:* versões anteriores do scriptLattes geravam também CSV, GDF e RIS; **este port em Python
não gera esses formatos**.

## 🔧 Melhorias Técnicas Implementadas

### Correções Críticas de Parser
1. **Bug de Contaminação de Estado**: Corrigido problema onde dados de um pesquisador eram misturados com outros
2. **Flags de Seção**: Reset adequado de flags (`achouAreaDeAtuacao`, `achouIdioma`, etc.) para permitir múltiplos itens
3. **Padrão salvarParte3**: Projetos de desenvolvimento agora seguem o padrão correto usado por outros tipos de projetos
4. **Condições de Processamento**: Adicionada flag `achouProjetoDeDesenvolvimento` nas condições principais do parser

### Melhorias no Processamento de Dados
1. **Regex Aprimorado**: Especialidades agora capturadas corretamente com textos contendo espaços
2. **Múltiplas Seções**: Suporte completo para múltiplas áreas de atuação e múltiplos idiomas
3. **Parsing Robusto**: Melhor tratamento de caracteres especiais e formatação inconsistente
4. **Estado Isolado**: Cada membro processado independentemente sem vazamento de dados

### Validações e Testes
- ✅ Paulo: 9 projetos pesquisa + 2 projetos extensão + **7 projetos desenvolvimento** + 6 áreas atuação  
- ✅ Daniel: 5 projetos pesquisa + 0 projetos extensão + **5 projetos desenvolvimento** + 4 áreas atuação
- ✅ Especialidades extraídas: "Engenharia de Software", "Processamento de Sinais Biológicos", etc.
- ✅ Múltiplos idiomas por pesquisador funcionando corretamente

## Solução de Problemas Comuns

### Erro de incompatibilidade do ChromeDriver
Se você receber um erro como "This version of ChromeDriver only supports Chrome version X", execute:
```bash
make update-chromedriver
```

### Verificar status da instalação
```bash
make status
```

### Problemas com Extração de Dados Específicos

#### Projetos de desenvolvimento não aparecem
Se você não estiver vendo projetos de desenvolvimento no JSON, verifique:
1. Se o pesquisador realmente possui projetos na seção "Projetos de desenvolvimento" do Lattes
2. Inspecione o JSON gerado (não existe flag adicional na linha de comando; o script recebe
   apenas o arquivo de configuração):
```bash
jq '.estatisticas.total_projetos_desenvolvimento' exemplo/teste-01/json/*.json
jq '.projetos_desenvolvimento[].nome' exemplo/teste-01/json/*.json
```

#### Áreas de atuação incompletas
Se especialidades não estão sendo extraídas:
1. Verifique se as áreas no Lattes seguem o formato: "Grande área: ... / Especialidade: ..."
2. O sistema agora suporta múltiplas áreas por pesquisador automaticamente

#### Dados misturados entre pesquisadores
Este problema foi corrigido na versão atual. Se ainda ocorrer:
1. Limpe o cache: `make clean`
2. Execute novamente: `make test`

### Verificar dados extraídos
```bash
# Verificar estrutura completa de um pesquisador
jq keys json/00_Paulo-Sergio-*.json

# Verificar se projetos de desenvolvimento foram extraídos
jq '.estatisticas.total_projetos_desenvolvimento' json/*.json

# Verificar quantas áreas de atuação foram encontradas
jq '.areas_de_atuacao | length' json/*.json

# Listar todos os tipos de projetos
jq '{pesquisa: (.estatisticas.total_projetos_pesquisa), extensao: (.estatisticas.total_projetos_extensao), desenvolvimento: (.estatisticas.total_projetos_desenvolvimento)}' json/*.json
```

### Chrome/Chromium não encontrado
Certifique-se de ter o Google Chrome ou Chromium instalado:
- Ubuntu/Debian: `sudo apt-get install google-chrome-stable` ou `sudo apt-get install chromium-browser`
- CentOS/RHEL/Fedora: Baixe do site oficial do Google Chrome
- macOS: Baixe do site oficial do Google Chrome

### Problemas com dependências
Se houver problemas com as dependências Python:
```bash
make clean-all  # Remove tudo
make install    # Reinstala do zero
```

## Normalização dos dados coletados

Os textos vêm do CV Lattes e variam muito (grafias de eventos, nomes de autores, instituições).
A normalização é determinística, em camadas, e **nunca destrói o texto original**:

| Camada | O que faz | Onde |
|---|---|---|
| L1 estrutura | decompõe a citação `EVENTO, ANO, LOCAL. VEÍCULO` e extrai `evento`, `evento_edicao`, `evento_sigla`, `evento_local`, `evento_veiculo` | `scriptLattes/normalizacao.py` + classes de produção |
| L2 chave | `normalizar_chave` (sem acento/caixa/pontuação), `separar_edicao`, `detectar_sigla`, `chave_de_evento` | idem |
| L3 identidade | `mesma_pessoa` (nomes de autores) e tabelas de aliases | `dados/aliases/*.csv` |

### Chaves de evento

`evento` continua sendo o texto bruto (exibição). Ao lado dele o JSON traz:

```json
{
  "evento": "XV Congresso Brasileiro de Estomaterapia, 2025, Florianópolis-SC. Anais do XV Congresso",
  "evento_chave": "congresso brasileiro de estomaterapia",
  "evento_serie": "congresso brasileiro de estomaterapia",
  "evento_edicao": "XV",
  "evento_sigla": "",
  "evento_local": "Florianópolis-SC",
  "evento_veiculo": "Anais do XV Congresso",
  "evento_nome_canonico": ""
}
```

A `evento_chave` é a **chave de série**: todas as edições de um mesmo evento compartilham a chave
(`SBES 2018`, `SBES 2023` → `sbes`), a edição/ano continuam como atributos. Preenchidos
`evento_serie` / `evento_nome_canonico` / `evento_sigla` vêm de `dados/aliases/eventos.csv`.

Demais campos normalizados adicionados ao JSON: `instituicao_chave`/`instituicao_canonica`
(orientações), `periodico_canonico` (artigos, quando há linha em `periodicos.csv`) e
`issn` (já existente, e a chave forte de periódico).

### Tabelas de aliases (preenchidas à mão, versionadas)

`dados/aliases/` — só há agrupamento quando existe linha na tabela; **nenhum merge automático
por similaridade**:

| Arquivo | Colunas | Para que serve |
|---|---|---|
| `eventos.csv` | `chave,serie,sigla,nome_canonico` | agrupar grafias/siglas do mesmo evento |
| `instituicoes.csv` | `chave,nome_canonico` | nome canônico de instituição |
| `periodicos.csv` | `issn,nome_canonico` | nome canônico do periódico (a chave é o ISSN) |
| `pesquisadores.csv` | `nome_a,nome_b` | força equivalência de duas grafias do mesmo autor |

Exemplo de linha forçando a equivalência que a heurística conservadora recusa:

```csv
nome_a,nome_b
SANTOS JR,"SANTOS JUNIOR, Paulo Sergio dos"
```

### Relatório de candidatos

```bash
# depois de rodar o scriptLattes (usa os JSONs gerados)
python -m scriptLattes.normalizacao --saida exemplo/teste-01 --destino dados/aliases
```

Gera em `dados/aliases/` (nunca sobrescreve as tabelas manuais):

- `pendentes_eventos.csv` — séries de evento ainda sem alias, ordenadas por ocorrências, com as
  edições agregadas (ex.: `10º|11º|12|12º|…`) e exemplos de texto bruto
- `pendentes_instituicoes.csv`, `pendentes_periodicos.csv`
- `pendentes_pesquisadores.csv` — apenas grafias de autores que **podem** ser de um membro
  (mesmo sobrenome), com os candidatos: são as decisões de identidade a revisar

### Configuração

```
global-normalizacao            = sim               # nao desliga L2/L3
global-normalizacao-tabelas    = ./dados/aliases/  # relativo ao arquivo .config
```

## Comunicação
- Temos uma área no Discord que pode ser útil para compartilhar dúvidas/sugestões [https://discord.gg/Xz8NZ3kBc3]
- Contato direto: [jesus.mena@ufabc.edu.br]

## Como referenciar este software
- J. P. Mena-Chalco e R. M. Cesar-Jr. scriptLattes: An open-source knowledge extraction system from the Lattes platform. Journal of the Brazilian Computer Society, vol. 15, n. 4, páginas 31--39, 2009. [http://dx.doi.org/10.1007/BF03194511]
- J. P. Mena-Chalco e R. M. Cesar-Jr. Prospecção de dados acadêmicos de currículos Lattes através de scriptLattes. Capítulo do livro Bibliometria e Cientometria: reflexões teóricas e interfaces São Carlos: Pedro & João, páginas 109-128, 2013. [http://dx.doi.org/10.13140/RG.2.1.5183.8561]

## Notas:
- O scriptLattes não está vinculado ao CNPq. A ferramenta é o resultado de um esforço (independente) realizado com o único intuito de auxiliar as tarefas mecânicas de compilação de informações cadastradas nos Currículos Lattes (publicamente disponíveis). Portanto, o CNPq não é responsável por nenhuma assessoria técnica sobre esta ferramenta.
- O repositorio antigo, no sourceforge não está sendo atualizado.

## 📋 Changelog - Principais Melhorias

### ✨ Nova Funcionalidade - Projetos de Desenvolvimento
- **Implementado**: Extração completa de projetos de desenvolvimento/tecnológicos
- **Estrutura**: Mesma estrutura dos projetos de pesquisa e extensão
- **JSON**: Campo `projetos_desenvolvimento` adicionado ao JSON
- **Estatísticas**: Contador `total_projetos_desenvolvimento` nas estatísticas

### 🔧 Correções Críticas de Parser
- **Bug Contaminação**: Corrigido vazamento de dados entre pesquisadores diferentes
- **Estado Isolado**: Cada membro agora é processado independentemente
- **Flags Reset**: Correção do reset de flags para permitir múltiplos itens por seção

### 🎯 Áreas de Atuação Melhoradas
- **Múltiplas Áreas**: Suporte para todos as áreas de atuação de um pesquisador
- **Especialidades**: Extração correta de especialidades com regex otimizado
- **Parsing Robusto**: Melhor tratamento de textos com espaços e caracteres especiais
- **Estrutura Completa**: Grande área, área, subárea e especialidade quando disponível

### 🌐 Idiomas Aprimorados
- **Múltiplos Idiomas**: Correção para extrair todos os idiomas de um pesquisador
- **Proficiências**: Extração detalhada das habilidades em cada idioma
- **Reset de Flags**: Corrigido problema que impedia múltiplos idiomas

### 📊 Melhorias na Exportação JSON
- **Campos Padronizados**: Nomenclatura consistente (`areas_de_atuacao` vs `areas_atuacao`)
- **Dados Completos**: Todos os tipos de dados agora incluídos no JSON
- **Estatísticas Expandidas**: Contadores para todos os tipos de produção e projetos

### 🛠️ Melhorias Técnicas
- **Padrão salvarParte3**: Projetos de desenvolvimento agora seguem padrão correto
- **Condições de Processamento**: Flags adicionadas nas condições principais
- **Tratamento de Certificação**: Suporte para "Projeto certificado" em desenvolvimento
- **Parsing HTML**: Melhor tratamento da estrutura HTML do Lattes

### 📈 Resultados Validados
- **Paulo**: 9 pesquisa + 2 extensão + 7 desenvolvimento + 6 áreas
- **Daniel**: 5 pesquisa + 0 extensão + 5 desenvolvimento + 4 áreas  
- **Especialidades**: Corretamente extraídas (ex: "Engenharia de Software")
- **Múltiplos Itens**: Idiomas e áreas de atuação funcionando corretamente

### 🔍 Para Desenvolvedores
As principais melhorias no código incluem:
- `parserLattes.py`: Correção de flags e condições de processamento
- `projetoDeDesenvolvimento.py`: Nova classe seguindo padrão existente
- `membro.py`: Adição de lista de projetos de desenvolvimento
- `grupo.py`: Melhorias no parsing de áreas de atuação e export JSON
- Correção em múltiplos pontos para evitar contaminação de estado entre membros

## 📚 Documentação Adicional

Para histórico completo de mudanças, versões e detalhes técnicos, consulte:
- **[CHANGELOG.md](CHANGELOG.md)** - Histórico detalhado de mudanças e correções
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guia completo para contribuições e desenvolvimento
- **[exemplo/](exemplo/)** - Arquivos de configuração e exemplos de uso
- **[README.md](README.md)** - Documentação principal (este arquivo)

### Como Contribuir
Se você encontrar problemas ou quiser melhorar o sistema, consulte nosso [Guia de Contribuição](CONTRIBUTING.md) para:
1. **Processo completo** de reportar bugs e sugerir melhorias
2. **Templates padronizados** para issues e pull requests  
3. **Diretrizes de código** e melhores práticas
4. **Processo de testing** e validação
5. **Workflow de desenvolvimento** e deployment

**Quick Start para Contribuições:**
```bash
# Verificação rápida
python scriptLattes.py exemplo/teste-01.config
jq keys json/*.json  # Verificar estrutura JSON

# Teste de regressão  
make clean && make test  # Limpar cache e testar
```


