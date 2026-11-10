"""Reload the task's own paused batch once; never uploads or requeues itself."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/experiments/main_peak_20261108'
TZ=timezone(timedelta(hours=8))
while datetime.now(TZ).date().isoformat()=='2026-11-08':
 p=OUT/'adaptive_state.json'
 if p.exists():
  state=json.loads(p.read_text(encoding='utf-8'))
  if state['status']=='official_failure_requires_review':raise SystemExit(3)
  if state['status']=='stop_requested':
   stop=OUT/'STOP_NEW_UPLOADS'
   if not stop.exists() or not stop.read_text(encoding='utf-8').startswith('Created by current task solely to reload'):raise SystemExit('Not the task-owned reload flag')
   current=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
   if any(r['state']=='failed' for r in current['rounds']):raise SystemExit(3)
   time.sleep(2)
   stop.unlink()
   print('Reloading serial wave optimizer after the existing task was settled; no source is retransmitted.',flush=True)
   raise SystemExit(subprocess.run([sys.executable,'-X','utf8',str(ROOT/'dev/tools/peak_batch_20261108.py')],cwd=ROOT).returncode)
 time.sleep(2)
raise SystemExit('Day changed; new uploads remain prohibited')
