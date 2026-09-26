#!/usr/bin/env python
# encoding: utf-8
"""Gera os currículos Lattes SINTÉTICOS usados pelo exemplo offline do scriptLattes.

Por que sintéticos: a pasta `cache/` com currículos reais não é versionada (são dados
pessoais de terceiros). Estes três currículos são inventados, imitam a estrutura da
página do Lattes e permitem que o exemplo do projeto rode sem internet e sem navegador,
além de servir de smoke test no CI e de teste de regressão do parser sem dados pessoais.

Uso:  python exemplo/demo-lattes/gerar_cvs_sinteticos.py
Os arquivos gerados (cache/*, demo.list) são versionados; rode este script apenas para
alterá-los.

Escopo: cobrem identificação, formação, atuação, áreas de atuação, idiomas, prêmios e
produção bibliográfica (artigos, trabalhos e resumos em congresso, com coautoria entre
os membros, o que produz arestas no grafo). Orientações, bancas, eventos e projetos não
foram incluídos: o parser dessas seções depende de detalhes da página real que não são
fielmente reproduzíveis em um currículo sintético pequeno.
"""

import os

RAIZ = os.path.dirname(os.path.abspath(__file__))

CABECALHO = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Currículo Lattes - {nome}</title></head><body>
<div class="infpessoa"><h2 class="nome" tabindex="0">{nome}</h2></div>
<div class="title-wrapper"><a name="Identificacao" tabindex="0"><h1 tabindex="0">Identificação</h1></a></div>
<div class="layout-cell layout-cell-12 data-cell">
  <div class="layout-cell layout-cell-3 text-align-right"><div class="layout-cell-pad-5 text-align-right"><b>Nome em citações bibliográficas</b></div></div>
  <div class="layout-cell layout-cell-9"><div class="layout-cell-pad-5">{citacoes}</div></div>
  <div class="layout-cell layout-cell-3 text-align-right"><div class="layout-cell-pad-5 text-align-right"><b>Identificador Lattes</b></div></div>
  <div class="layout-cell layout-cell-9"><div class="layout-cell-pad-5"><span style="font-weight: bold; color: #326C99;">{identificador}</span></div></div>
</div>
<div class="title-wrapper"><a name="Endereco" tabindex="0"><h1 tabindex="0">Endereço</h1></a></div>
<div class="layout-cell layout-cell-12 data-cell">
  <div class="layout-cell layout-cell-3 text-align-right"><div class="layout-cell-pad-5 text-align-right"><b>Endereço Profissional</b></div></div>
  <div class="layout-cell layout-cell-9"><div class="layout-cell-pad-5">{endereco}</div></div>
</div>
"""

RODAPE = """<div class="title-wrapper"><a name="OutrasInformacoesRelevantes" tabindex="0"><h1 tabindex="0">Outras informações relevantes</h1></a></div>
<div class="layout-cell layout-cell-12 data-cell">
  <div class="layout-cell layout-cell-9"><div class="layout-cell-pad-5">Currículo sintético, sem dados reais, gerado por exemplo/demo-lattes/gerar_cvs_sinteticos.py.</div></div>
</div>
</body></html>
"""


def _secao(rotulo, conteudo, nome_da_ancora=''):
    """Cada seção do CV Lattes é anunciada por <div class="title-wrapper"> + <h1>."""
    ancora = nome_da_ancora or rotulo.replace(' ', '').replace('/', '')
    return (f'<div class="title-wrapper"><a name="{ancora}" tabindex="0">'
            f'<h1 tabindex="0">{rotulo}</h1></a></div>\n'
            f'<br class="clear"><br class="clear">\n{conteudo}\n<br class="clear"><br class="clear">')


def _itens(rotulo, itens):
    partes = [f'<div class="layout-cell layout-cell-12 data-cell">',
              f'  <div class="cita-artigos"><b>{rotulo}</b></div>']
    for numero, texto in enumerate(itens, start=1):
        partes.append(
            f'  <div class="layout-cell layout-cell-1 text-align-right">'
            f'<div class="layout-cell-pad-6 text-align-right"><b>{numero}. </b></div></div>\n'
            f'  <div class="layout-cell layout-cell-11"><span class="transform">{texto}</span></div>\n'
            f'  <br class="clear">')
    partes.append('</div>')
    return '\n'.join(partes)


def _itens_de_producao(rotulo, itens, nome_do_ancora):
    """Produções usam o rótulo dentro de <div class="cita-artigos"> e metadados em spans."""
    partes = [f'<div id="{nome_do_ancora}"><div class="cita-artigos"><b>'
              f'<a name="{nome_do_ancora}"></a>{rotulo}</b></div><br class="clear"><br class="clear">']
    for numero, item in enumerate(itens, start=1):
        partes.append(
            f'  <div class="layout-cell layout-cell-1 text-align-right">'
            f'<div class="layout-cell-pad-6 text-align-right"><b>{numero}. </b></div></div>\n'
            f'  <div class="layout-cell layout-cell-11"><span class="transform">'
            f'<span class="informacao-artigo" data-tipo-ordenacao="importancia"></span>'
            f'<span class="informacao-artigo" data-tipo-ordenacao="autor">{item["autores"]}</span>'
            f'<span class="informacao-artigo" data-tipo-ordenacao="ano">{item["ano"]}</span>'
            f'<a class="icone-producao icone-doi" href="{item.get("doi", "")}" target="_blank"></a>'
            f'{item["texto"]}'
            + ''.join(f'<a class="tooltip" href="http://lattes.cnpq.br/{c}" target="_blank"></a>'
                      for c in item.get('colaboradores', []))
            + '</span></div>\n  <br class="clear">')
    partes.append('</div>')
    return '\n'.join(partes)


def montar_cv(pessoa):
    html = [CABECALHO.format(nome=pessoa['nome'], citacoes=pessoa['citacoes'],
                             endereco=pessoa['endereco'],
                             identificador=pessoa['identificador'])]

    html.append(_secao('Formação acadêmica/titulação', _itens('Formação acadêmica/titulação', pessoa['formacao'])))
    html.append(_secao('Atuação Profissional', _itens('Atuação Profissional', pessoa['atuacao'])))
    html.append(_secao('Áreas de atuação', _itens('Áreas de atuação', pessoa['areas'])))
    html.append(_secao('Idiomas', _itens('Idiomas', pessoa['idiomas'])))
    if pessoa['premios']:
        html.append(_secao('Prêmios e títulos', _itens('Prêmios e títulos', pessoa['premios'])))

    producoes = ['<div class="cita-artigos"><b>Produção bibliográfica</b></div>']
    producoes.append(_itens_de_producao('Artigos completos publicados em periódicos',
                                        pessoa['artigos'], 'ArtigosCompletos'))
    producoes.append(_itens_de_producao('Trabalhos completos publicados em anais de congressos',
                                        pessoa['congressos'], 'TrabalhosCompletos'))
    producoes.append(_itens_de_producao('Resumos publicados em anais de congressos',
                                        pessoa['resumos'], 'Resumos'))
    html.append(_secao('Produções', '\n'.join(producoes)))

    html.append(RODAPE)
    return '\n'.join(html)

# Publicações coautoradas: aparecem no CV de dois membros, como na vida real.
# O compilador funde as duplicatas e é daí que saem as arestas do grafo de colaborações.
ARTIGO_ANA_CARLOS = {
    'autores': 'LIMA, A. B. F. ; ROCHA, Carlos Eduardo Mendes',
    'ano': '2025',
    'doi': 'http://dx.doi.org/10.0000/exemplo.2025.001',
    'colaboradores': ['2222222222222222'],
    'texto': 'LIMA, A. B. F. ; ROCHA, Carlos Eduardo Mendes . Cuidado de enfermagem em '
             'doenças crônicas: revisão integrativa . Revista Brasileira de Enfermagem '
             'Exemplo, v. 78, n. 2, p. 101-112, 2025. ',
}

ARTIGO_ANA_JULIANA = {
    'autores': 'NOGUEIRA, Juliana Prado ; LIMA, A. B. F.',
    'ano': '2024',
    'doi': '',
    'colaboradores': ['1111111111111111'],
    'texto': 'NOGUEIRA, Juliana Prado ; LIMA, A. B. F. . Tecnologias educacionais na '
             'formação em saúde . Revista de Educação Exemplo, v. 15, n. 3, p. 220-233, 2024. ',
}


PESSOAS = [
    {
        'identificador': '1111111111111111',
        'nome': 'Ana Beatriz Ferreira Lima',
        'citacoes': 'LIMA, A. B. F.;Lima, Ana Beatriz Ferreira;FERREIRA LIMA, ANA BEATRIZ',
        'endereco': ('Universidade Federal de Exemplo, Centro de Ciências da Saúde. '
                     'Avenida das Amostras, 1000. Bairro Inventado. 12345-000 Cidade Exemplo - EX.'),
        'formacao': [
            'Doutorado em Enfermagem. Universidade Federal de Exemplo, UFEX, Brasil. '
            'Título: Cuidado de enfermagem em doenças crônicas, Ano de obtenção: 2016. '
            'Orientador: Carlos Eduardo Mendes Rocha.',
            'Mestrado em Enfermagem. Universidade Federal de Exemplo, UFEX, Brasil. '
            'Título: Adesão ao tratamento medicamentoso, Ano de obtenção: 2012.',
        ],
        'atuacao': [
            'Vínculo: Servidor Público, Enquadramento Funcional: Professora Associada, '
            'Carga horária: 40. Universidade Federal de Exemplo, UFEX, Brasil.',
        ],
        'areas': ['Enfermagem / Área: Enfermagem em Doenças Crônicas.',
                  'Enfermagem / Área: Educação em Saúde.'],
        'idiomas': ['Inglês - Compreende Bem, Fala Razoavelmente, Lê Bem, Escreve Bem.',
                    'Espanhol - Compreende Razoavelmente, Fala Pouco, Lê Bem, Escreve Pouco.'],
        'premios': ['Prêmio de Excelência em Pesquisa, Sociedade Brasileira de Enfermagem, 2023.'],
        'artigos': [ARTIGO_ANA_CARLOS, ARTIGO_ANA_JULIANA],
        'congressos': [
            {'autores': 'LIMA, A. B. F. ; ROCHA, Carlos Eduardo Mendes', 'ano': '2025',
             'doi': '', 'texto': 'LIMA, A. B. F. ; ROCHA, Carlos Eduardo Mendes . '
                                 'Tecnologias de cuidado em doenças crônicas . In: 15º '
                                 'Congresso Brasileiro de Enfermagem Exemplo, 2025, Cidade '
                                 'Exemplo. Anais do 15º Congresso Brasileiro de Enfermagem '
                                 'Exemplo. Cidade Exemplo: Editora Exemplo, 2025. p. 200-205. '},
        ],
        'resumos': [
            {'autores': 'LIMA, A. B. F.', 'ano': '2024', 'doi': '',
             'texto': 'LIMA, A. B. F. . Educação em saúde para doenças crônicas . In: 20º '
                      'Seminário de Pesquisa Exemplo, 2024, Cidade Exemplo. Anais do 20º '
                      'Seminário de Pesquisa Exemplo. Cidade Exemplo: Editora Exemplo, 2024. '},
        ],
    },
    {
        'identificador': '2222222222222222',
        'nome': 'Carlos Eduardo Mendes Rocha',
        'citacoes': 'ROCHA, Carlos Eduardo Mendes;ROCHA, C. E. M.;Mendes Rocha, Carlos Eduardo',
        'endereco': ('Universidade Federal de Exemplo, Centro de Ciências Exatas. '
                     'Rua das Amostras, 500. Bairro Inventado. 12345-000 Cidade Exemplo - EX.'),
        'formacao': [
            'Doutorado em Ciência da Computação. Universidade Federal de Exemplo, UFEX, '
            'Brasil. Título: Análise de redes de colaboração científica, Ano de obtenção: 2014.',
        ],
        'atuacao': [
            'Vínculo: Servidor Público, Enquadramento Funcional: Professor Titular, '
            'Carga horária: 40. Universidade Federal de Exemplo, UFEX, Brasil.',
        ],
        'areas': ['Ciência da Computação / Área: Redes de Computadores.',
                  'Ciência da Computação / Área: Análise de Dados.'],
        'idiomas': ['Inglês - Compreende Bem, Fala Bem, Lê Bem, Escreve Bem.'],
        'premios': ['Melhor artigo, Simpósio Brasileiro de Redes Exemplo, 2022.'],
        'artigos': [ARTIGO_ANA_CARLOS],
        'congressos': [
            {'autores': 'ROCHA, Carlos Eduardo Mendes', 'ano': '2024', 'doi': '',
             'texto': 'ROCHA, Carlos Eduardo Mendes . Análise de coautorias . In: 10º '
                      'Simpósio Brasileiro de Redes Exemplo, 2024, Cidade Exemplo. Anais do '
                      '10º Simpósio Brasileiro de Redes Exemplo. Cidade Exemplo: Editora '
                      'Exemplo, 2024. p. 33-40. '},
        ],
        'resumos': [],
    },
    {
        'identificador': '3333333333333333',
        'nome': 'Juliana Prado Nogueira',
        'citacoes': 'NOGUEIRA, Juliana Prado;NOGUEIRA, J. P.',
        'endereco': ('Universidade Federal de Exemplo, Centro de Ciências Humanas. '
                     'Avenida das Amostras, 2000. Bairro Inventado. 12345-000 Cidade Exemplo - EX.'),
        'formacao': [
            'Mestrado em Educação. Universidade Federal de Exemplo, UFEX, Brasil. Título: '
            'Formação docente e tecnologias, Ano de obtenção: 2018.',
        ],
        'atuacao': [
            'Vínculo: Servidor Público, Enquadramento Funcional: Professora Adjunta, '
            'Carga horária: 40. Universidade Federal de Exemplo, UFEX, Brasil.',
        ],
        'areas': ['Educação / Área: Ensino-Aprendizagem.'],
        'idiomas': ['Inglês - Compreende Razoavelmente, Fala Pouco, Lê Bem, Escreve Pouco.'],
        'premios': [],
        'artigos': [ARTIGO_ANA_JULIANA],
        'congressos': [],
        'resumos': [
            {'autores': 'NOGUEIRA, Juliana Prado', 'ano': '2023', 'doi': '',
             'texto': 'NOGUEIRA, Juliana Prado . Formação docente e tecnologias digitais . '
                      'In: 5º Encontro de Educação Exemplo, 2023, Cidade Exemplo. Anais do '
                      '5º Encontro de Educação Exemplo. Cidade Exemplo: Editora Exemplo, 2023. '},
        ],
    },
]


def main():
    pasta_cache = os.path.join(RAIZ, 'cache')
    os.makedirs(pasta_cache, exist_ok=True)

    linhas_da_lista = []
    for pessoa in PESSOAS:
        html = montar_cv(pessoa)
        destino = os.path.join(pasta_cache, pessoa['identificador'])
        with open(destino, 'w', encoding='utf-8') as arquivo:
            arquivo.write(html)
        linhas_da_lista.append(f"{pessoa['identificador']} , {pessoa['nome']}")
        print(f'gerado: {destino} ({len(html)} bytes)')

    lista = os.path.join(RAIZ, 'demo.list')
    with open(lista, 'w', encoding='utf-8') as arquivo:
        arquivo.write('# Lista de membros do grupo de demonstração (currículos sintéticos)\n')
        arquivo.write('# Formato: identificador Lattes , nome completo\n')
        arquivo.write('\n'.join(linhas_da_lista) + '\n')
    print(f'gerado: {lista}')


if __name__ == '__main__':
    main()
