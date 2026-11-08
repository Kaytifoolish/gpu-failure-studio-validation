#!/bin/zsh
set -eu
cd "${0:A:h}"
[[ -x .venv/bin/python ]] || { echo 'Environnement absent. Préparer les wheels.'; exit 1; }
.venv/bin/python verify_dependencies.py
.venv/bin/python -m pip install --no-index --no-deps --only-binary=:all: --find-links wheelhouse --require-hashes -r requirements.lock
.venv/bin/python -m pip check
printf '\nInstallation locale terminée.\n'
