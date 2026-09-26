#!/usr/bin/env python
"""Gera o executável do scriptLattes com PyInstaller (um arquivo por sistema).

Uso:  python empacotar.py            (precisa do PyInstaller instalado)

O executável leva junto o que o programa precisa para funcionar sem instalação:
as páginas modelo (css/js), as tabelas de aliases (dados/) e os currículos de exemplo
(exemplo/). Por isso `python scriptLattes.py` empacotado roda a demonstração offline.
"""

import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTAS_DE_DADOS = ('css', 'js', 'dados', 'exemplo')
SEPARADOR = ';' if os.name == 'nt' else ':'
NOME = 'scriptlattes'


def montar_comando():
    comando = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onefile',
        '--name', NOME,
        # nada de console escondido: quem usa precisa ver as mensagens de erro
        '--distpath', os.path.join(RAIZ, 'dist'),
        '--workpath', os.path.join(RAIZ, 'build'),
        '--specpath', os.path.join(RAIZ, 'build'),
    ]
    for pasta in PASTAS_DE_DADOS:
        origem = os.path.join(RAIZ, pasta)
        if os.path.isdir(origem):
            comando += ['--add-data', f'{origem}{SEPARADOR}{pasta}']
    comando += ['--paths', RAIZ]
    comando.append(os.path.join(RAIZ, 'scriptLattes.py'))
    return comando


def main():
    for temporaria in ('build', 'dist'):
        shutil.rmtree(os.path.join(RAIZ, temporaria), ignore_errors=True)

    comando = montar_comando()
    print(' '.join(comando))
    resultado = subprocess.run(comando, cwd=RAIZ)
    if resultado.returncode != 0:
        print('\n[ERRO] O PyInstaller falhou.', file=sys.stderr)
        return resultado.returncode

    executavel = os.path.join(RAIZ, 'dist', NOME + ('.exe' if os.name == 'nt' else ''))
    if not os.path.isfile(executavel):
        print(f'\n[ERRO] O executável não foi gerado em {executavel}', file=sys.stderr)
        return 1

    tamanho = os.path.getsize(executavel) / (1024 * 1024)
    print(f'\n[OK] {executavel} ({tamanho:.1f} MB)')
    print('Para conferir:  dist/scriptlattes --diagnostico')
    return 0


if __name__ == '__main__':
    sys.exit(main())
