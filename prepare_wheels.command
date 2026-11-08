#!/bin/zsh
set -eu
cd "${0:A:h}"
PYTHON="$(command -v python3)"
"$PYTHON" -c 'import tkinter' || { echo 'Python avec Tkinter requis'; exit 1; }
"$PYTHON" -m venv .venv
mkdir -p wheelhouse
.venv/bin/python -m pip download --only-binary=:all: --dest wheelhouse -r requirements.txt
printf '\nWheels téléchargés mais NON APPROUVÉS. Vérifier indépendamment les SHA256, puis créer approved_wheels.json depuis le modèle.\n'
