# GPU Failure Studio v3 · macOS Apple Silicon · prototype expérimental

## IMPORTANT : sécurité

- **Pas de sandbox macOS**. Le worker partage les droits de l'utilisateur.
- **Pas de limite mémoire absolue**. Le seuil RSS est vérifié périodiquement et peut être dépassé entre deux mesures ; macOS peut subir une pression mémoire.
- Les limites CPU et de taille de fichier du worker sont des protections partielles, pas une barrière contre les vulnérabilités de LibRaw/Pillow.
- Les 12 effets sont des **simulations CPU**, pas des pannes GPU réelles.
- Ne pas utiliser de RAW d'origine inconnue. Première utilisation uniquement dans un **compte macOS dédié**, avec copies non confidentielles et fichiers synthétiques. Ne pas utiliser de photos originales irremplaçables.
- Aucun accès réseau n'est prévu par le code applicatif. **La préparation des dépendances nécessite Internet**. Les bibliothèques tierces ne sont pas auditées ici.
- Le code n'est ni signé ni notarié Apple. Aucun test n'a été exécuté sur macOS Apple Silicon dans cet environnement.

## Installation contrôlée (sans administrateur)

1. Installer un Python compatible Tkinter depuis une source de confiance ; ouvrir Terminal.
2. Décompresser le dossier dans un **compte macOS dédié**.
3. Dans Terminal : `cd ~/Downloads/GPU_Failure_Studio_v3` (adapter le chemin réel).
4. Exécuter `zsh prepare_wheels.command` : crée `.venv`, télécharge les wheels dans `wheelhouse/`, crée `requirements.lock` avec les SHA-256 de **ces téléchargements**.
5. **Contrôler manuellement** noms, versions, provenance, compatibilité et vulnérabilités connues des wheels. Les SHA-256 créés localement **ne prouvent pas** que les packages téléchargés sont sûrs ; ils empêchent seulement une modification silencieuse après préparation.
6. Exécuter `zsh install.command` : installation **hors ligne** depuis `wheelhouse/`, avec `--require-hashes`.
7. Exécuter `zsh launch.command`.

Versions demandées : numpy 2.2.6, Pillow 11.3.0, rawpy 0.25.1, tifffile 2025.6.11, psutil 7.0.0. Leur disponibilité et compatibilité sur ta version exacte de macOS/Python **ne sont pas validées**. En cas d'échec, ne pas supprimer les protections de pip pour forcer l'installation.

## Usage

1. Ouvrir **une copie non confidentielle** de JPEG/PNG/TIFF/RAW de confiance.
2. Choisir l'un des 12 effets, l'intensité et la graine, puis Actualiser aperçu.
3. Exporter en TIFF RGB uint16 ou JPEG RGB 8 bits (qualité 95).
4. Export à la résolution décodée, maximum 36 MP. Les RAW dépassant 36 MP sont refusés ; un A3 à 300 ppp requiert environ 17,4 MP avec cadrage adapté.
5. Aucun profil ICC n'est incorporé : **ne pas considérer le TIFF comme prêt pour un flux d'impression colorimétrique professionnel**.
6. Les effets sont recalculés sur la pleine résolution, donc leur disposition peut différer de l'aperçu.

## Protections et limites

- `safety.py` : vérifie fichier ordinaire, extension, taille ; refuse les liens symboliques directs. Ce n'est pas une validation exhaustive de format, et les chemins peuvent changer entre vérification et ouverture (TOCTOU).
- `worker.py` : vérifie les dimensions RAW avant dématriçage, quand les métadonnées sont disponibles. La lecture de métadonnées et l'ouverture RAW peuvent déjà déclencher des allocations et du code natif.
- `app.py` : surveille périodiquement la mémoire RSS et la durée du worker ; termine son groupe de processus lors d'un dépassement détecté. Cette surveillance n'empêche pas tous les pics de mémoire et n'est pas une sandbox.
- Export temporaire dans le dossier cible ; `os.link()` crée la destination sans écrasement. Sur un volume sans liens durs, **l'export échoue sans remplacement automatique**. Le fichier temporaire est nettoyé sur les erreurs gérées ; un arrêt brutal peut laisser un temporaire.
- `validate_export` vérifie les métadonnées du TIFF/JPEG. Cela ne prouve pas l'intégrité pixel par pixel ni la fidélité ICC.
- Fermer la fenêtre pendant un traitement est refusé. Une fermeture forcée peut laisser des temporaires ou des sous-processus.

## Tests

Dans le dossier, après installation :

`./.venv/bin/python -m unittest discover -v`

Vérifier sur le Mac cible : conservation SHA-256 des originaux, non-écrasement, TIFF uint16 RGB, JPEG RGB, fermeture forcée, gestion des temporaires, mémoire via Moniteur d'activité, absence de trafic réseau non autorisé et désinstallation. Ne pas effectuer de tests agressifs sur le Mac principal.

## Désinstallation

Fermer l'application puis **supprimer uniquement le dossier du logiciel dans Finder**. Le script `uninstall.command` explique les étapes, sans suppression automatique. Les exports enregistrés ailleurs restent présents. Vérifier manuellement les éventuels fichiers temporaires `gpu_studio_*` dans le répertoire temporaire macOS ; ne pas effacer des fichiers dont la provenance n'est pas certaine.

## Fichiers

`app.py` interface Tkinter ; `worker.py` décodage/export ; `engine.py` effets ; `safety.py` protections ; `requirements.txt` versions demandées ; `make_lock.py` empreintes locales ; scripts `.command` ; `test_engine.py` et `test_safety.py` tests.

## Addendum : vérification renforcée des dépendances (révision)

**Cette procédure remplace les étapes 4 à 6 de l'installation décrites plus haut.**

1. `zsh prepare_wheels.command` télécharge les wheels, sans les approuver. Cette étape nécessite Internet.
2. Vérifier indépendamment chaque wheel et son empreinte SHA-256 auprès d'une source de confiance. Examiner également la compatibilité macOS ARM64, les dépendances transitives et les vulnérabilités connues. Une empreinte publiée ne constitue pas une preuve d'innocuité.
3. Copier `approved_wheels.EXAMPLE.json` vers `approved_wheels.json`, puis remplacer chaque nom et empreinte par les valeurs **vérifiées indépendamment**. Ne jamais copier automatiquement les empreintes calculées sur les téléchargements pour les déclarer approuvées.
4. `zsh install.command` refuse l'installation si un nom, une version, une empreinte ou le nombre de wheels ne correspond pas. Installation hors ligne avec `--no-deps` et `--require-hashes`. `pip check` vérifie les dépendances déclarées.
5. **Limite :** la vérification n'atteste ni la provenance cryptographique initiale ni l'absence de vulnérabilités. La compatibilité ARM64/macOS et les dépendances transitives doivent être revues avant approbation. En cas de wheel manquant ou supplémentaire, l'installation échoue. Ne pas désactiver les contrôles pour la forcer.

Le fichier `make_lock.py` historique ne doit plus servir à approuver les dépendances ; seul `verify_dependencies.py` peut produire le verrou d'installation après confrontation au manifeste externe.
