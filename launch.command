#!/bin/zsh
set -eu
cd "${0:A:h}"
[[ -x .venv/bin/python ]] || { echo 'Installer le logiciel avant lancement.'; exit 1; }
exec .venv/bin/python app.py
