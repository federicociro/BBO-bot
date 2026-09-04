#!/usr/bin/env bash
# Re-copia el corpus desde el vault. La fuente es el vault; esto es una copia
# para que el container sea autocontenido.
set -euo pipefail
VAULT="${VAULT:-$HOME/notes_sync/bbo-project}"
cd "$(dirname "$0")/.."
cp -v "$VAULT"/docs/0[0-4]*.md content/corpus/
echo "Recordá re-medir los tokens si cambió el tamaño."
