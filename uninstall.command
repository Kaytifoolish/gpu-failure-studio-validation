#!/bin/zsh
set -eu
cd "${0:A:h}"
echo 'Fermer GPU Failure Studio et ses terminaux avant désinstallation.'
echo 'Supprimer ce dossier avec Finder, sans lancer de commande destructive.'
echo 'Les exports sauvegardés ailleurs restent intacts.'
echo 'Vérifier manuellement les éventuels fichiers temporaires gpu_studio_* dans le dossier temporaire macOS.'
