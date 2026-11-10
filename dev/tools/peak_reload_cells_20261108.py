"""One task-owned, result-bound reload; never creates a new upload itself."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/experiments/main_peak_20261108';TZ=timezone(timedelta(hours=8))
while datetime.now(TZ).date().isoformat()=='2026-11-08':
 p=OUT/'pipeline_state.json'
 if p.exists():
  s=json.loads(p.read_text(encoding='utf-8'))
  if s['status']=='official_failure_requires_review':raise SystemExit(3)
  if s['status']=='stop_requested':
   flag=OUT/'STOP_NEW_UPLOADS'
   if not flag.exists() or flag.read_text(encoding='utf-8')!='Task-owned cell-budget reload after the next official result.\n':raise SystemExit('Not the owned reload flag')
   c=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
   if any(r.get('job_id') and r['state']=='failed' for r in c['rounds']):raise SystemExit(3)
   time.sleep(2);flag.unlink();print('Reloading adaptive allocation after confirmed online data; pending identities remain unchanged.',flush=True)
   raise SystemExit(subprocess.run([sys.executable,'-X','utf8',str(ROOT/'dev/tools/peak_pipeline_20261108.py')],cwd=ROOT).returncode)
 time.sleep(2)
raise SystemExit('Beijing day changed; no new upload')
