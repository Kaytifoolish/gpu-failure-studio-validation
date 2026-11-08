# GPU Failure Studio v3 : validation CI expérimentale

Ce dépôt contient le prototype et un protocole de tests synthétiques exécutables sur GitHub Actions, sur une machine macOS ARM64 distante. **Ne pas considérer ce pack comme un logiciel certifié ou sûr pour des RAW non fiables.**

Commencer par `GUIDE_GITHUB_PAS_A_PAS.md`. Le workflow se trouve dans `.github/workflows/validation-apple-silicon.yml`.

Les téléchargements pip du workflow servent **uniquement aux essais CI**. Ils ne sont pas approuvés par `approved_wheels.json`. Le mécanisme d'installation locale reste bloqué sans manifeste indépendant.
