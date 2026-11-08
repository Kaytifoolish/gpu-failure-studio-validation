"""Synthetic CI tests and auditable JSON/Markdown report. No user photographs."""
import hashlib, json, os, platform, subprocess, sys, tempfile, time, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports'; REPORT.mkdir(exist_ok=True)
results={"platform":platform.platform(),"machine":platform.machine(),"python":sys.version.split()[0],"macos":platform.mac_ver()[0],"tests":{},"dependencies":{},"limitations":["No macOS sandbox", "RSS sampling cannot guarantee a hard memory limit", "No real RAW tests", "No interactive GUI test", "No M4/24GB validation", "No Apple notarization", "CI package downloads are not an independently approved supply chain"]}

def run(name, cmd, timeout=180):
 t=time.monotonic()
 try:
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
  status='PASS' if p.returncode==0 else 'FAIL'
  output=(p.stdout+'\n'+p.stderr)[-16000:]
 except subprocess.TimeoutExpired as e:
  status='FAIL';output=f'TIMEOUT after {timeout}s'
 results['tests'][name]={"status":status,"seconds":round(time.monotonic()-t,2),"output":output}
 return status=='PASS'

# Fail-closed verification must reject a missing independent approval manifest.
# Test in an isolated temp copy so repository files remain untouched.
with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 for name in ('verify_dependencies.py','requirements.txt'):
  (p/name).write_bytes((ROOT/name).read_bytes())
 r=subprocess.run([sys.executable,str(p/'verify_dependencies.py')],capture_output=True,text=True,timeout=20)
 ok=r.returncode!=0 and 'approved_wheels.json absent' in (r.stderr+r.stdout)
 results['tests']['approval_gate_denies_missing_manifest']={"status":"PASS" if ok else "FAIL", "output":(r.stdout+r.stderr)[-3000:]}

run('unit_tests',[sys.executable,'-m','unittest','discover','-v'],timeout=180)
run('dependency_consistency',[sys.executable,'-m','pip','check'],timeout=30)
# Check source archive integrity with no need for sample images.
sha={}
for name in ['app.py','worker.py','engine.py','safety.py','verify_dependencies.py','requirements.txt']:
 sha[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
results['source_sha256']=sha
for pkg in ['numpy','Pillow','rawpy','tifffile','psutil']:
 try:
  import importlib.metadata as md
  results['dependencies'][pkg]=md.version(pkg)
 except Exception as exc:results['dependencies'][pkg]=f'ERROR {exc}'
results['overall']='PASS' if all(v['status']=='PASS' for v in results['tests'].values()) and results['machine']=='arm64' else 'FAIL'
(REPORT/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# GPU Failure Studio v3 - rapport CI Apple Silicon','',f"**Statut tests : {results['overall']}**",'',f"- Architecture : `{results['machine']}`",f"- macOS : `{results['macos']}`",f"- Python : `{results['python']}`",'', '## Résultats','', '| Test | Statut | Durée (s) |','|---|---|---:|']
for k,v in results['tests'].items():lines.append(f"| {k} | {v['status']} | {v.get('seconds','-')} |")
lines+=['','## Versions de dépendances','']+[f'- {k}: `{v}`' for k,v in results['dependencies'].items()]
lines+=['','## SHA-256 des sources','']+[f'- `{k}`: `{v}`' for k,v in sha.items()]
lines+=['','## Limites de validation','']+[f'- {x}' for x in results['limitations']]
(REPORT/'validation.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
summary=os.environ.get('GITHUB_STEP_SUMMARY')
if summary:
 with open(summary,'a',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
print('\n'.join(lines))
sys.exit(0 if results['overall']=='PASS' else 1)
