"""Resume one existing pending work. Uploads resume only after fresh official success."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'dev/tools'),str(ROOT/'dev'),str(ROOT/'automation')]
import peak_pipeline_20261108 as pipeline
OUT=pipeline.OUT;DAY=pipeline.DAY;core=pipeline.core

def stamp(row):
 value=row.get('finished_at')
 if not value:raise RuntimeError('Terminal work has no confirmation timestamp')
 return datetime.fromisoformat(value.replace('Z','+00:00'))

def main():
 resume=False
 with core['SubmissionLock'](OUT/'.recovery.lock'),core['SubmissionLock'](OUT/'.round.lock'):
  ctl=core['Controller']()
  with pipeline.legacy.connect(ctl.config) as page:
   batch=pipeline.legacy.Batch(ctl,page,600);batch.check_foreign_jobs()
   while True:
    quota,_=batch.poll();pipeline.research.report(ctl)
    jobs=[ctl.store.load(r['job_id']) for r in ctl.state['rounds'] if r.get('job_id')]
    failed=[j for j in jobs if j['state']=='failed']
    complete=[j for j in jobs if j['state']=='completed' and type(j.get('score')) is int]
    later=[j for j in complete if not failed or stamp(j)>max(stamp(f) for f in failed)]
    state=pipeline.read(OUT/'pipeline_state.json')
    if later:
     healthy=max(later,key=stamp)
     if (healthy.get('record') or {}).get('submitted_at','')[:10]!=DAY:raise RuntimeError('Recovery evidence is not from this authorized day')
     reviewed=state.setdefault('reviewed_service_failures',{})
     for j in failed:reviewed[j['job_id']]=dict(recovered_by=healthy['job_id'],official_score=healthy['score'],confirmed_at=healthy['finished_at'],reason='Numeric official terminal result confirmed after this exact prior failure; no failed source is retried.')
     state.update(status='official_score_recovered',last_recovery_job=healthy['job_id']);pipeline.save(OUT/'pipeline_state.json',state)
     stop=OUT/'STOP_NEW_UPLOADS'
     if stop.exists():
      if stop.read_text(encoding='utf-8')!='Task-owned cell-budget reload after the next official result.\n':raise RuntimeError('A different stop instruction is present')
      stop.unlink()
     resume=core['now']()[:10]==DAY and quota['remaining']>0
     pipeline.event(official_service_recovered=True,job=healthy['job_id'],score=healthy['score'],actual_used=quota['used'],continue_new_uploads=resume)
     break
    active=batch.active()
    snapshot=dict(checked_at=core['now'](),quota=quota,best_score=ctl.state['best_score'],pending=[r['job_id'] for r in active],failed=[j['job_id'] for j in failed],new_numeric_results=[dict(job_id=j['job_id'],score=j['score']) for j in complete])
    pipeline.save(OUT/'recovery_snapshot.json',snapshot)
    if not active:
     state['status']='official_failure_requires_review';pipeline.save(OUT/'pipeline_state.json',state);pipeline.event(no_usable_official_score=True,actual_used=quota['used'],failed=len(failed));return 3
    if core['now']()[:10]!=DAY:pipeline.event(day_changed=True,pending=len(active));return 0
    confirming=any(time.monotonic()-seen<3 for _,seen in batch.signatures.values())
    page.page.wait_for_timeout(3000 if confirming else 20000)
 if resume:return subprocess.run([sys.executable,'-X','utf8',str(ROOT/'dev/tools/peak_pipeline_20261108.py')],cwd=ROOT).returncode
 return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except KeyboardInterrupt:print('Interrupted; preserve and resume original works only.',flush=True);raise
 except Exception:traceback.print_exc();raise SystemExit(5)
