# Validation gratuite sur GitHub Actions : guide pas à pas

## Ce que valide ce pack

Le workflow exécute des tests synthétiques sur un runner GitHub `macos-26`, architecture ARM64, Apple M1 et 7 Go de RAM d'après la documentation GitHub (au 8 novembre 2026). Ce n'est **pas** une validation de ton M4 / 24 Go / macOS 27.2, ni un audit de sécurité, ni une notarisation Apple. Aucun programme n'est exécuté sur ton Mac personnel.

## Attention à la chaîne d'approvisionnement

Le workflow installe les **versions épinglées** depuis l'index pip pour un test CI expérimental. Il **ne contourne pas le verrouillage** de `install.command` du logiciel : ce dernier refuse toujours les wheels non approuvés. Toutefois les téléchargements CI ne sont **pas indépendamment approuvés cryptographiquement**. Ne pas interpréter un test vert comme une approbation des dépendances. Le test `approval_gate_denies_missing_manifest` vérifie le refus d'une installation sans manifeste.

## Publier depuis un navigateur uniquement

1. Sur https://github.com, créer un compte si nécessaire.
2. Créer un nouveau dépôt **Public** nommé `gpu-failure-studio-validation`, sans ajouter de README initial.
3. Décompresser l'archive ZIP sur ton ordinateur. La décompression ne lance pas le programme, mais si tu souhaites éviter toute manipulation locale, demande une livraison fichier par fichier directement dans le navigateur.
4. Dans le dépôt GitHub, sélectionner **Add file > Upload files**. Déposer les fichiers du pack (hors `.github` si le navigateur ignore les dossiers cachés), puis **Commit changes**. Ne déposer aucune photographie personnelle, wheel, `.venv`, archive privée, clé ou token.
5. Dans GitHub, **Add file > Create new file**. Saisir exactement `.github/workflows/validation-apple-silicon.yml` dans le champ de nom. Copier le contenu du fichier de ce nom depuis le pack et valider **Commit changes**.
6. Vérifier que `ci/run_validation.py` a bien été publié au chemin indiqué. Si nécessaire, créer ce fichier via **Add file > Create new file** en copiant son contenu.
7. Ouvrir l'onglet **Actions**, sélectionner **Validation experimentale Apple Silicon**, puis **Run workflow**. Un premier lancement peut aussi avoir lieu après le commit sur `main`.
8. Ouvrir l'exécution et vérifier la machine (`uname -m` doit afficher `arm64`). Consulter les logs et le tableau récapitulatif.
9. Télécharger l'artefact `rapport-validation-apple-silicon` dans la page de l'exécution : il contient `validation.json` et `validation.md`.
10. Conserver l'URL de l'exécution, l'identifiant du commit, les versions des dépendances et les rapports. Transmettre les résultats pour analyse.

## Résultats attendus

- Tests existants : succès de `python -m unittest discover -v`.
- Contrôle des dépendances déclarées : succès de `pip check`.
- Contrôle d'approbation : refus attendu si `approved_wheels.json` absent.
- Architecture : `arm64`.
- SHA-256 des fichiers source enregistrés dans le rapport.
- Aucun RAW réel ni photographie personnelle dans les tests.

## Interprétation

- **Vert** : tests automatisés réussis sur le runner utilisé, uniquement.
- **Rouge** : problème à analyser dans les journaux. Ne pas contourner les protections pour obtenir du vert.
- **Non couvert** : interface graphique interactive, validation M4/24 Go, macOS 27.2, mesure RAM sous charge lourde, sandbox, vulnérabilités natives, provenance cryptographique initiale des wheels, absence de trafic réseau, notarisation.

## Gratuité et sécurité du dépôt

GitHub indique que les runners standards sont gratuits et illimités pour les dépôts publics. Vérifier les conditions en vigueur. Les fichiers, journaux et artefacts d'un dépôt public peuvent être consultés par des tiers. Ne jamais publier de données confidentielles.

Sources : https://docs.github.com/en/actions/reference/runners/github-hosted-runners et https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
