# Changelog - scriptLattes

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

## [Distribuição e localização de arquivos] - 2026-09-25

### ✨ Adicionado
- **Executável por sistema** (`empacotar.py`, PyInstaller): gera um arquivo único com o Python
  e com os dados do projeto embutidos (`css/`, `js/`, `dados/`, `exemplo/`). O workflow
  `.github/workflows/release.yml` produz Windows, Linux e macOS a partir de uma tag `v*`,
  testando o executável (diagnóstico, demonstração offline e janela) antes de publicar, e
  publica também o tarball do código-fonte — exigência da GPLv2 para a distribuição do binário.
- **Sem argumentos, o programa roda a demonstração**: cria `resultado-demonstracao/` na pasta
  do usuário com os relatórios dos currículos de exemplo, o `LEIA-ME.txt` e um `.config`
  pronto, e ao final ensina a rodar o grupo de verdade. É o que acontece com duplo clique.
- `util.diretorio_do_projeto()`, `util.buscarDiretorio()`, `util.nome_do_programa()` e
  `util.esta_empacotado()`: resolvem onde estão os arquivos que acompanham o programa
  (incluindo o `_MEIPASS` de um executável empacotado) e como chamá-lo nas mensagens.

### 🐛 Corrigido
- **`ABSBASE` era a pasta de execução, não a do programa**: rodando de outra pasta, os
  relatórios saíam sem `css`/`js` (`[Errno 2] ... '/tmp/fora/css'`) e as tabelas de
  normalização não eram encontradas. Agora os arquivos estáticos, as tabelas e os exemplos são
  procurados onde o programa está instalado.
- **A pasta de cache relativa podia resolver para dentro do programa**: com `./cache/` no
  `.config`, o `os.chdir` interno de `buscarArquivo` fazia o cache do usuário ser lido de
  `cache/` do projeto — inofensivo em Python, mas no executável significa tentar escrever em
  pasta temporária. Agora a resolução é explícita (`buscarDiretorio`) e o cache do usuário é
  criado onde ele está rodando.
- **`obterParametro` tratava a string `'0'` como ligada**: `'nao'` virava `0`, e se esse `0`
  fosse gravado de volta no `.config` (era o que o gerador de configuração fazia), a releitura
  considerava `'0'` verdadeiro — o filtro por termos era ligado sem lista de termos e o
  programa morria com `FileNotFoundError: ''`. Os valores `0/1/false/true` passaram a ser
  reconhecidos, o `.config` volta a ser gravado como `sim`/`nao`, e o filtro ligado sem lista
  de termos agora apenas avisa.
- O teste dos caminhos absolutos do assistente falhava no Windows: o `.config` grava os
  caminhos com `/` (funciona nos dois sistemas), e o teste comparava com o separador nativo.
  Agora ele exercita caminhos relativos de propósito, então pega de fato a regressão que
  deveria pegar (conferido removendo a conversão).
- O passo do CI "falha previsível deve ser explicada" dependia de o runner ter (ou não)
  Chrome/ChromeDriver/rede — no Windows o download automático do driver fazia o programa
  encerrar com código 3 em vez de 2. Agora ele usa um `.list` inexistente, que falha por
  motivo determinístico no código 2.
- Os passos do CI que criavam pasta temporária (`--adicionar-cv` e a conferência da
  falha previsível) também rodavam `mktemp -d` no Git Bash e conferiam em bash, o que
  falha no Windows pelo mesmo motivo; agora rodam inteiros em Python.
- `--diagnostico` informa se a janela gráfica (`--janela`) está disponível e, quando o Tkinter
  falta, diz o comando de instalação de cada distribuição — antes a janela simplesmente não abria.
- As mensagens passaram a chamar o programa pelo nome do ambiente atual: `scriptlattes` no
  executável, `python scriptLattes.py` a partir do código (antes o executável mandava o usuário
  rodar um comando que não existe naquele contexto).
- `--assistente` pela linha de comando já pergunta se é para gerar os relatórios na sequência
  (antes só criava os arquivos).

## [Assistente e janela] - 2026-09-25

### ✨ Adicionado
- **Assistente no terminal** (`python scriptLattes.py --assistente`, código em
  `scriptLattes/assistente.py`): quatro perguntas (nome do grupo, currículos, período, pasta de
  saída) e ele cria o `.config` e o `.list` — ninguém precisa editar arquivo de configuração.
  Aceita os currículos como link (`http://lattes.cnpq.br/...`), número de 10 ou 16 dígitos, com o
  nome opcional depois de `,` `;` ou tabulação; avisa sobre linhas incompreendidas e repetidas.
  O `.config` gerado tem 8 parâmetros e as opções mais procuradas ficam comentadas no fim.
- **Janela gráfica** (`python scriptLattes.py --janela`, código em `scriptLattes/janela.py`):
  Tkinter (biblioteca padrão, sem dependência nova). Campos de nome, currículos, período e pasta;
  botões "Gerar relatórios", "Verificar ambiente", "Como conseguir os currículos?" e
  "Abrir pasta de relatórios"; barra de progresso e caixa de log com tudo o que o scriptLattes
  escreve. A execução roda em uma thread e a janela continua respondendo.
- Coluna `--sem-avisos` em `python -m scriptLattes.janela` para execução não assistida.
- `scriptLattes/cli.py`: a linha de comando passou a ser um módulo do pacote (o `scriptLattes.py`
  da raiz continua funcionando e apenas chama `main()`), para que o assistente e a janela possam
  executar o pipeline sem abrir um processo novo.
- Testes: `tests/test_assistente.py` (interpretação da entrada, arquivos gerados, conversa
  completa e fim a fim até o `index.html`) e `tests/test_janela.py` (abre a janela de verdade,
  clica em gerar e confere a saída; pulado quando não há servidor gráfico).

### 🐛 Corrigido
- **`buscarArquivo` dependia de `sys.argv[1]`** e trocava o diretório atual do processo para
  localizar o `.list`. Em qualquer chamada que não fosse `python scriptLattes.py x.config`
  (assistente, interface gráfica, opções antes do arquivo) a busca falhava ou apontava para o
  lugar errado — e o `os.chdir` global era inseguro com a janela rodando o pipeline em thread.
  Agora procura na pasta atual, na pasta do `.config` e ao lado dele, sem mudar o diretório.
- **`Grupo` guardava estado em atributos de classe** (`listaDeMembros`, `listaDeParametros`,
  `listaDeTermos`, `dicionarioDeTermos`): dois grupos criados no mesmo processo compartilhavam as
  mesmas listas, então a segunda execução pela janela somava os membros da primeira. Agora são
  atributos de instância, com teste de regressão.
- O assistente gravava `./relatorios` e `./cache` relativos: rodando o pipeline de outra pasta os
  relatórios iam para o lugar errado. Agora os caminhos de saída e cache são absolutos no
  `.config` (o `.list` continua relativo, ao lado do `.config`).

## [Download e modo offline] - 2026-09-25

### ✨ Adicionado
- **ChromeDriver automático (Selenium Manager)**: sem caminho informado, o Selenium baixa o
  ChromeDriver compatível com o Chrome instalado. O binário local na raiz do projeto passa a ser
  apenas plano B (quando o download automático não é possível) e pode ser fixado com a nova chave
  `global-caminho_do_chromedriver` no `.config` (vazio = automático).
- **Modo manual, sem navegador** (`--adicionar-cv CAMINHO`, `--cache PASTA`, `--sobrescrever`):
  importa currículos em HTML salvos pelo navegador (um arquivo ou uma pasta), valida que é um
  currículo Lattes, descobre o identificador dentro do HTML e guarda no cache com o nome correto.
- **`exemplo/demo.config` + `exemplo/demo-lattes/`**: demonstração offline com três currículos
  **sintéticos** (inventados, versionados no repositório) e o gerador
  `exemplo/demo-lattes/gerar_cvs_sinteticos.py`. O lançador, sem argumentos, roda esta demonstração:
  funciona sem internet, sem Chrome e sem baixar nada.
- **Relatório de falhas parciais**: um currículo problemático não derruba os outros membros; no fim
  a execução lista quem ficou de fora e termina com código 3. Mensagem orienta a rodar de novo
  (o cache é reaproveitado e a execução continua de onde parou).
- Progresso por membro (`[3/10] Nome (decorrido: 1m05s)`) durante a leitura dos currículos.

### 🐛 Corrigido
- `LattesRobot.create_driver` **engolia** a exceção ao abrir o Chrome: o programa seguia e falhava
  depois com `AttributeError: 'NoneType' object has no attribute 'get'`. Agora o erro sobe com
  mensagem acionável.
- `chrome_driver_path` era usado sem ser definido em sistemas que não fossem Windows/Linux
  (`UnboundLocalError` no macOS) e o caminho era resolvido a partir do diretório atual — agora é
  resolvido a partir da raiz do projeto.
- Cada currículo abria **uma nova sessão** do Chrome (≈4 s de navegador por CV) e não fechava a aba
  extra do currículo, acumulando abas. Agora existe uma única sessão por execução, com a aba extra
  fechada a cada item.
- `identificador_do_cv` procurava `lattes.cnpj.br` (domínio inexistente): os links reais usam
  `lattes.cnpq.br`, então a extração do identificador nunca funcionava por essa via.
- Sem internet e sem currículos em cache, o programa
  falhava com erro genérico; agora explica que não há de onde obter currículos e aponta o
  `--adicionar-cv`.
- Currículo inválido no cache (download interrompido, página de erro) gerava relatórios vazios sem
  aviso; agora é detectado (`CurriculoInvalidoError`) com instruções de correção.

### 🔧 Mudado
- `baixaCVLattes` reduz de 5 para 3 tentativas, com espera entre elas em vez de repetição imediata;
  a espera de 5 minutos por `ERR_CONNECTION_REFUSED` foi para 5 s por tentativa (evitando travar a
  execução por horas em um grupo grande).
- CI: além dos testes, roda a demonstração offline e o `--adicionar-cv` em Linux e Windows.
- `--diagnostico` compara as versões do Chrome e do ChromeDriver local e avisa quando elas não
  combinam (situação que faz todo download falhar) com a instrução de correção; a mensagem de erro
  correspondente ganhou um caso próprio em vez de cair no genérico "falha ao abrir o navegador".

## [Experiência de uso] - 2026-09-25

### ✨ Adicionado
- **Lançadores `executar.sh`, `executar.bat` e `executar.command`**: criam o ambiente virtual,
  instalam as dependências e executam o projeto com o interpretador correto. Sem `make`, `jq`,
  `wget` ou `unzip`. Sem argumentos, rodam o exemplo do projeto.
- **`python scriptLattes.py --diagnostico`** (`scriptLattes/diagnostico.py`): verifica Python,
  dependências, Chrome, ChromeDriver, internet, pasta de cache, `.config`/`.list` e permissão de
  escrita; termina dizendo o que corrigir, com códigos de saída estáveis (0/2/3).
- **Mensagens de erro acionáveis** (`scriptLattes/erros.py`): todo erro é traduzido para
  *o que aconteceu* + *o que fazer*, em português. Traceback só com `--debug`.
- **Log de execução** (`scriptlattes-log.txt` na pasta de saída) e **`LEIA-ME.txt`** em toda pasta
  de saída, com o aviso de dados pessoais (LGPD).
- Novas opções de linha de comando: `--diagnostico`, `--debug`, `--nao-abrir`, `--help`.
- Abertura automática do relatório no navegador ao final (execução interativa).
- CI em matriz **ubuntu-latest + windows-latest**, executando os testes, o lançador e um caso de
  falha previsível (sem currículos e sem ChromeDriver) que precisa ser explicado, não quebrado.

### 🐛 Corrigido
- **Leitura de `.config`, `.list` e lista de termos em UTF-8** (`util.lerLinhasDeTexto`): no Windows
  o Python usava a codificação local (cp1252) e nomes acentuados quebravam com `UnicodeDecodeError`.
  Se o arquivo não estiver em UTF-8, ele é relido na codificação local com aviso explícito.
- `tests/test_participacao_em_banca.py` substituía `bs4`, `selenium` e `networkx` no `sys.modules`
  por `MagicMock` no momento do import, contaminando todos os outros testes do processo.

### 🔧 Mudado
- `executar_scriptLattes()` agora propaga erro de criação da pasta de saída e devolve o `Grupo`
  (necessário para escrever o `LEIA-ME.txt` e abrir o relatório).
- Códigos de saída documentados no README: 0 sucesso, 1 inesperado, 2 entrada/configuração,
  3 ambiente, 130 interrompido.

## [Normalização] - 2026-09-25

### ✨ Adicionado
- **`scriptLattes/normalizacao.py`**: normalização em camadas, determinística e testável
  - L1: `separar_citacao_de_evento` / `estruturar_evento_do_item` decompõem
    `EVENTO, ANO, LOCAL. VEÍCULO` (a cauda da citação não fica mais colada ao nome do evento)
  - L2: `normalizar_chave`, `separar_edicao`, `detectar_sigla`, `chave_de_evento`,
    `chave_de_instituicao`
  - L3: `partes_de_pessoa` / `mesma_pessoa` e `Vocabulario` (tabelas de aliases)
  - `relatorio_de_candidatos` + CLI: `python -m scriptLattes.normalizacao --saida <dir> [--destino dados/aliases]`
- **Campos aditivos no JSON**: `evento_sigla`, `evento_edicao`, `evento_local`, `evento_veiculo`,
  `evento_chave` (chave de *série*), `evento_serie`, `evento_nome_canonico`,
  `instituicao_chave`, `instituicao_canonica`, `periodico_canonico`. O campo `evento` continua
  sendo o texto bruto.
- **Tabelas de aliases versionadas** em `dados/aliases/` (`eventos.csv`, `instituicoes.csv`,
  `periodicos.csv`, `pesquisadores.csv`) — todo agrupamento passa a ser auditável no histórico.
- **Chaves de configuração**: `global-normalizacao` (padrão `sim`) e
  `global-normalizacao-tabelas` (padrão `./dados/aliases/`).
- **Atribuição de coautoria sem CV** (`0000000000000000`) passa a reconhecer grafias diferentes
  do mesmo nome. Verificado em A/B com 10 CVs reais: *sem* normalização o coautor citado como
  `BRAGA, CARLOS` não era atribuído a nenhuma publicação; *com* normalização recebeu 3 vínculos.

### 🔧 Corrigido
- **Nomes de evento em resumos**: 734/787 resumos (93%) e 28/29 resumos expandidos (97%) tinham a
  cauda da citação dentro de `nomeDoEvento` (ex.: `..., 2020, Ribeirão Preto. Archives of Health
  Investigation`). Agora a contaminação é 0 e local/veículo viram campos próprios.
- **Sigla do evento**: extração passou de 63 para 75 de 215 trabalhos completos e agora também
  em resumos (formas `(SIGLA ANO)` e `SIGLA ANO: ...`).
- **`mesma_pessoa`**: iniciais de uma letra (ex.: `GIR, E`) não são mais descartadas como
  partículas (`de/da/dos/e`), o que impedia reconhecer `GIR, E` = `Elucir Gir`.
- **`Nome em citações bibliográficas`**: o campo pode listar várias grafias separadas por `;`;
  todas passam a ser usadas como referência na identificação de autores.
- `Vocabulario` aceita vírgulas não citadas em `pesquisadores.csv` (nomes de autor contêm vírgula).

### 🧪 Testes
- `tests/test_normalizacao.py` (29 testes) com strings reais de CVs: edição/ordinal, sigla,
  citação de evento, chave de série, grafias de autor (positivas e negativas), tabelas de aliases
  e o relatório de candidatos. Suíte total: 59 testes.

## [Correções] - 2026-09-24

### 🐛 Corrigido
- **`global-itens_desde_o_ano`/`global-itens_ate_o_ano = hoje` falhava** com
  `NameError: name 'datetime' is not defined` (`grupo.py` não importava `datetime`).
- **Exportação JSON**: campos que eram sempre vazios agora leem o atributo correto do parser
  (`capitulos_livros.titulo_livro`, `textos_jornais.jornal`, `entrevistas.natureza`,
  `apresentacoes_trabalhos.natureza`) e `orientacoes.*.curso` é extraído da instituição.
- **Campos sem fonte no CV Lattes removidos do JSON** (ver README, seção "Correções de Campos
  do JSON"): `qualis`, `cidade`, `isbn`, `veiculo`, `evento` (apresentações), `instituicao`
  e `finalidade` (produção técnica), `data`/`instituicao` (patentes e registros).
- **Orientações concluídas** não duplicam mais o ano de conclusão em `ano_inicio`.
- **Filtro por termos** (`membro.contemAlgumTermoDeBusca`) não lança mais `UnboundLocalError`
  quando o item não possui `titulo`/`descricao`/`tituloDoTrabalho`/`item`.
- **Área de atuação**: o regex de subárea aceita espaços antes de `/Especialidade`.

### 🔥 Removido (código morto ou duplicado)
- `similaridade_entre_cadeias` duplicada em `util.py` (a primeira definição continha
  `ratio = ...` e seria inválida se executada).
- `baixaCVLattes` duplicada em `baixaLattes.py`; `exit(1)` virou `FileNotFoundError`;
  `warnings.filterwarnings("ignore")` global removido.
- `Grupo.gerarArquivoGDF`, `Grupo.gerarArquivoJSON`, `Grupo.HTMLColorToRGB`,
  `Grupo.gerarGraficosDeBarras`, `Grupo.gerarGraficoDeProporcoes` e demais escritores
  (`salvarMatriz*`, `imprimeCSV*`, `salvarVetorDeProducoes`, `salvarListaInternalizacaoTXT`)
  sem chamadores; `GraficoDeBarras`/`GraficoDeProporcoes` não existiam.
- Fluxo RIS (`arquivoRis`, `salvarPublicacaoEmFormatoRIS`, argumento `ris=`) — nunca era
  acionado porque o parâmetro `relatorio-salvar_publicacoes_em_formato_ris` não era registrado.
  Os métodos `ris()` e `csv()` dos itens (e de `Membro`) ficaram sem chamadores e foram removidos;
  `artigoEmPeriodico.csv()`, por exemplo, leria `self.qualis`, atributo que nunca é preenchido.
- Renderização de internacionalização (`gerarPaginasDeInternacionalizacao`,
  `gerarPaginaDeInternacionalizacao`): nunca era chamada e dependia da classe inexistente
  `GraficoDeInternacionalizacao`. O link de menu e a chave de configuração
  `relatorio-incluir_internacionalizacao` (que só produzia um link para uma seção inexistente)
  também foram removidos — configs que ainda usem a chave receberão o aviso de parâmetro
  desconhecido.
- Atributos de classe nunca atribuídos/consultados em `Grupo` (`matriz*` duplicados,
  `listaDeRotulosCores`, `listaDePublicacoesEinternacionalizacao`, `diretorioDoi`,
  `geradorDeXml`, `vectorRank`, `nomes`, `rotulos`) e em `CompiladorDeListas`.
- `CompiladorDeListas.compilarListaDeProjetos` e `imprimirMatrizesDeFrequencia` (declarações
  `matriz*` associadas eram sempre `None`).
- `sys.tracebacklimit = 0` (suprimia stack traces do processo inteiro).
- Ramificações inalcançáveis em `Membro.estaDentroDoPeriodo`
  (`objeto.__module__ == 'orientacaoEmAndamento'`/`'projetoDePesquisa'` nunca era verdadeiro,
  pois `__module__` é o nome totalmente qualificado).
- `print("DEBUG: ...")` de `atuacaoProfissional.py` e `parserLattes.py`.
- Importações, linhas e chamadas duplicadas (`htmlentitydecode`, `cvPath`,
  `listaParticipacaoEmEvento`, `adicionarCoautorNaLista`, `organizacaoDeEvento`).

### 🧪 Testes
- `tests/test_atuacao_profissional.py` convertido de `pytest` para `unittest` (pytest não é
  dependência do projeto).
- Novo `tests/test_exportacao_json.py` cobrindo o mapeamento parser → JSON, incluindo as
  correções acima. Suíte: `python -m unittest discover -s tests`.
- Novo workflow de CI (`.github/workflows/ci.yml`).

### 📝 Documentação
- README: removidas as promessas de saída CSV/Excel/GDF, da flag `--somente-json` e da
  associação de Qualis (não implementadas neste port).

## [Versão Atual] - 2024-12-06

### ✨ Adicionado
- **Nova funcionalidade**: Extração de Projetos de Desenvolvimento
  - Implementação completa da classe `ProjetoDeDesenvolvimento`
  - Parser atualizado para detectar seção "Projetos de desenvolvimento"
  - Export JSON com campo `projetos_desenvolvimento`
  - Estatísticas atualizadas com `total_projetos_desenvolvimento`

### 🔧 Corrigido
- **Bug crítico**: Contaminação de dados entre pesquisadores diferentes
  - Problema: Dados de um membro vazavam para outros membros
  - Solução: Estado isolado para cada membro durante o processamento
  - Afeta: Projetos, áreas de atuação, idiomas, etc.

- **Áreas de Atuação**: Extração de múltiplas áreas por pesquisador
  - Problema: Apenas primeira área sendo extraída
  - Solução: Remoção incorreta do reset de flags durante processamento
  - Resultado: Todas as áreas de atuação agora extraídas

- **Especialidades em Áreas de Atuação**: Regex melhorado
  - Problema: Especialidades com espaços não eram capturadas
  - Solução: Regex otimizado `r'Especialidade:\s*([^.]+?)(?:\.|$)'`
  - Exemplo: "Processamento de Sinais Biológicos" agora funciona

- **Múltiplos Idiomas**: Correção similar às áreas de atuação
  - Problema: Apenas primeiro idioma extraído por pesquisador
  - Solução: Flags de idioma não resetadas prematuramente
  - Resultado: Todos os idiomas e proficiências extraídos

### 🚀 Melhorado
- **Parser HTML**: Condições de processamento otimizadas
  - Adicionada flag `achouProjetoDeDesenvolvimento` nas condições principais
  - Padrão `salvarParte3` implementado para projetos de desenvolvimento
  - Tratamento de "Projeto certificado" adicionado

- **Exportação JSON**: Estrutura de dados aprimorada
  - Campo `areas_de_atuacao` padronizado (antes `areas_atuacao`)
  - Estrutura completa: grande_area, area, subarea, especialidade
  - Descrição completa preservada para compatibilidade

- **Estatísticas**: Contadores expandidos
  - Todos os tipos de projetos agora contabilizados
  - Estatísticas automáticas para desenvolvimento
  - Dados consistentes entre HTML e JSON

## Detalhes Técnicos

### Arquivos Modificados
- `scriptLattes/parserLattes.py`: Correções principais de parser
- `scriptLattes/producoesUnitarias/projetoDeDesenvolvimento.py`: Nova classe
- `scriptLattes/membro.py`: Adição de lista de projetos de desenvolvimento
- `scriptLattes/grupo.py`: Melhorias no parsing e export JSON
- `scriptLattes/compiladorDeListas.py`: Compilação de projetos de desenvolvimento

### Testes Realizados
- **Paulo**: 9 pesquisa + 2 extensão + 7 desenvolvimento + 6 áreas + 1 idioma
- **Daniel**: 5 pesquisa + 0 extensão + 5 desenvolvimento + 4 áreas + 3 idiomas

### Compatibilidade
- ✅ Backward compatible: JSONs antigos continuam funcionando
- ✅ Novos campos são adicionais, não substituem existentes
- ✅ HTML tradicional não afetado pelas mudanças

## Versões Anteriores

### [Baseline] - Versão Original
- Extração básica de produções bibliográficas
- Projetos de pesquisa e extensão
- Export HTML tradicional
- Funcionalidades básicas do scriptLattes original

---

## Como Contribuir

Se você encontrar bugs ou quiser sugerir melhorias:

1. Verifique se o problema já foi reportado
2. Teste com dados de exemplo primeiro
3. Forneça exemplos específicos do problema
4. Inclua informações do ambiente (Python, OS, etc.)

Para desenvolvedores:
- Siga o padrão existente de classes para novos tipos de dados
- Teste com múltiplos pesquisadores para evitar contaminação
- Mantenha compatibilidade com JSONs existentes
- Documente mudanças significativas neste changelog