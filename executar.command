#!/bin/bash
# scriptLattes - lançador para macOS (clique duplo no Finder).
# Faz exatamente o que o executar.sh faz; existe apenas para o duplo clique funcionar.
cd "$(dirname "$0")" || exit 1
exec ./executar.sh "$@"
