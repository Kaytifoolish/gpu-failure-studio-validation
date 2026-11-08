"""Fail-closed wheel verifier. Approved hashes must come from independent review."""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from pip._vendor.packaging.utils import parse_wheel_filename, canonicalize_name

ROOT = Path(__file__).resolve().parent
PINNED = {}
for line in (ROOT / 'requirements.txt').read_text().splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    if not re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.!+\-]+', line):
        raise SystemExit('Exigence non épinglée ou non reconnue : ' + line)
    name, version = line.split('==', 1)
    PINNED[canonicalize_name(name)] = version

approved_file = ROOT / 'approved_wheels.json'
if not approved_file.is_file():
    raise SystemExit('approved_wheels.json absent. Ne pas installer sans approbation indépendante.')
approved = json.loads(approved_file.read_text(encoding='utf-8'))
if not isinstance(approved, dict) or set(approved) != set(PINNED):
    raise SystemExit('La liste approuvée ne correspond pas aux dépendances exigées.')

wheel_dir = ROOT / 'wheelhouse'
wheels = list(wheel_dir.iterdir()) if wheel_dir.exists() else []
if not wheels or any(p.is_symlink() or not p.is_file() or p.suffix != '.whl' for p in wheels):
    raise SystemExit('wheelhouse absent, vide ou contient des éléments non autorisés.')
if len(wheels) != len(PINNED):
    raise SystemExit('Nombre de wheels inattendu (dépendance transitive ou doublon).')

rows = []
seen = set()
for wheel in wheels:
    name, version, _, tags = parse_wheel_filename(wheel.name)
    name = canonicalize_name(name)
    if name in seen or name not in PINNED or str(version) != PINNED[name]:
        raise SystemExit('Wheel inattendu : ' + wheel.name)
    seen.add(name)
    record = approved[name]
    if not isinstance(record, dict) or record.get('filename') != wheel.name:
        raise SystemExit('Nom non approuvé : ' + wheel.name)
    expected = record.get('sha256', '')
    if not isinstance(expected, str) or not re.fullmatch('[a-fA-F0-9]{64}', expected):
        raise SystemExit('SHA-256 approuvé manquant ou invalide : ' + name)
    with wheel.open('rb') as fh:
        digest = hashlib.file_digest(fh, 'sha256').hexdigest()
    if digest.lower() != expected.lower():
        raise SystemExit('Empreinte non conforme : ' + wheel.name)
    with zipfile.ZipFile(wheel) as z:
        if z.testzip() is not None:
            raise SystemExit('Wheel ZIP corrompu : ' + wheel.name)
        if not any(n.endswith('.dist-info/METADATA') for n in z.namelist()):
            raise SystemExit('METADATA manquant : ' + wheel.name)
    rows.append(f'{name}=={version} --hash=sha256:{digest}')
if seen != set(PINNED):
    raise SystemExit('Dépendances manquantes.')
(ROOT / 'requirements.lock').write_text('\n'.join(sorted(rows))+'\n', encoding='utf-8')
print('OK : wheels conformes au manifeste approuvé. Cela ne certifie pas leur innocuité.')
