"""At most two acknowledged jobs; all performance decisions use official totals."""
from pathlib import Path
from datetime import datetime,timedelta
import itertools,json,sys,time,traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'dev/tools'),str(ROOT/'dev'),str(ROOT/'automation')]
import wave_batch_20261106 as legacy
import peak_batch_20261108 as research
from peak_round_20261108 import runtime
OUT=ROOT/'data/experiments/main_peak_20261108';DAY='2026-11-08'
core=runtime();core['AUTHORIZATION']=['优化30次，全部根据线上数据，你打表的数据可以参考总结规律，但是不能写死参数']
# Preserve the existing tested identity/two-confirmation logic and change only
# the day, current-wave parent class, maximum outstanding count and selection.
legacy.core=core;legacy.Controller=core['Controller'];legacy.OUT=OUT;legacy.DAY=DAY
legacy.BATCH_IN_FLIGHT=2;legacy.connect=core['connect'];legacy.parse_quota=core['parse_quota']
legacy.now=core['now'];legacy.save=core['save'];legacy.read=core['read'];legacy.digest=core['digest']
legacy.Batch.accept_wave=lambda self,entry:None

def save(p,v):research.save(p,v)
def read(p,default=None):return research.read(p,default)
def event(**data):print(json.dumps(data,ensure_ascii=False),flush=True)
def run():
 auth=read(OUT/'authorization.json')
 if auth['date']!=DAY or auth['authorization']!='优化30次，全部根据线上数据，你打表的数据可以参考总结规律，但是不能写死参数':raise RuntimeError('Explicit date/authorization mismatch')
 with core['SubmissionLock'](OUT/'.pipeline.lock'),core['SubmissionLock'](OUT/'.round.lock'):
  ctl=core['Controller']();state=read(OUT/'pipeline_state.json',dict(date=DAY,plan_index=0,preparations=0,experiments=[],behaviors={},status='running',created_at=core['now']()))
  state['status']='running';state['maximum_acknowledged_outstanding']=2;save(OUT/'pipeline_state.json',state)
  cases=research.diagnostic_cases();save(OUT/'branch_diagnostic_cases.json',[dict(name=c.name,family=c.family,values=c.values) for c in cases])
  order=['evidencescout','cellbudget']+[op for op in research.OPS if op not in {'evidencescout','cellbudget'}]
  plan=[(op,) for op in order]+list(itertools.combinations(order,2))
  if state.get('test_plan'):plan=[tuple(item) for item in state['test_plan']]
  minutes=max(1,(datetime(2026,11,9,tzinfo=core['TZ'])-datetime.now(core['TZ'])).total_seconds()/60)
  with legacy.connect(ctl.config) as page:
   batch=legacy.Batch(ctl,page,minutes);batch.check_foreign_jobs()
   while time.monotonic()<batch.stop_at:
    quota,records=batch.poll();research.report(ctl)
    reviewed=set(state.get('reviewed_service_failures',{}))
    failed=[r for r in ctl.state['rounds'] if r.get('job_id') and r['state']=='failed' and r['job_id'] not in reviewed]
    if failed:
     state['status']='official_failure_requires_review';state['failed_jobs']=[r['job_id'] for r in failed];save(OUT/'pipeline_state.json',state);event(stopped_for_official_failure=state['failed_jobs'],pending=len(batch.active()),quota=quota['used']);return 3
    if quota['remaining']==0 and not batch.active():
     state['status']='complete_actual30';save(OUT/'pipeline_state.json',state);event(completed=True,actual_used=quota['used'],best=ctl.state['best_score'],pending=0);return 0
    can_new=quota['remaining']>0 and core['now']()[:10]==DAY and batch.can_send(records)
    if can_new:
     if state.get('pause_after_plan_index') is not None and state['plan_index']>=state['pause_after_plan_index']:state['status']='planned_review_checkpoint';save(OUT/'pipeline_state.json',state);return 0
     if (OUT/'STOP_NEW_UPLOADS').exists():state['status']='stop_requested';save(OUT/'pipeline_state.json',state);return 0
     if state['plan_index']>=len(plan):raise RuntimeError('No distinct untried waveform hypothesis remains')
     ops=plan[state['plan_index']];state['plan_index']+=1;state['preparations']+=1;save(OUT/'pipeline_state.json',state)
     strategy=None;rejection=None
     try:strategy,rejection=research.prepare(ctl,state['preparations'],ops,state,cases)
     except Exception as exc:
      rejection=repr(exc);(OUT/f"pipeline_local_rejection_{state['preparations']:03d}.txt").write_text(traceback.format_exc(),encoding='utf-8')
     note=dict(operators=ops,preparation=state['preparations'],official_reference=ctl.state['best_score'],rejection=rejection,time=core['now']());state['experiments'].append(note);save(OUT/'pipeline_state.json',state)
     if rejection:event(local_only_skip=note);continue
     raw=Path(strategy['source']).read_bytes();core['candidate_review'](raw)
     if any(j['sha256']==strategy['sha256'] for j in ctl.jobs()) or any(r.get('sha256')==strategy['sha256'] for r in read(ctl.manifest_path,{})['files']):
      note['rejection']='historical_source_hash';save(OUT/'pipeline_state.json',state);continue
     entry=ctl.new_metadata(strategy['name'],raw,strategy['rationale']+'; direct online comparison; no case lookups.',strategy['source'])
     note['sha256']=entry['sha256'];note['name']=entry['name'];save(OUT/'pipeline_state.json',state)
     try:ctl.preflight(entry)
     except Exception as exc:
      entry.update(state='preflight_failed',last_error=str(exc));ctl.persist();note['rejection']='local_preflight: '+str(exc);save(OUT/'pipeline_state.json',state);event(local_only_skip=note);continue
     if not batch.upload(entry):raise RuntimeError('Upload preconditions changed; inspect before any retry')
     note['job_id']=entry['job_id'];save(OUT/'pipeline_state.json',state);research.report(ctl)
     event(actual_used=ctl.state['last_quota']['used'],pending=len(batch.active()),best=ctl.state['best_score'])
    else:
     # Two fresh terminal observations must be separated in time.
     confirming=any(time.monotonic()-seen<3 for _,seen in batch.signatures.values())
     page.page.wait_for_timeout(3000 if confirming else 20000)
   state['status']='date_window_ended';save(OUT/'pipeline_state.json',state);research.report(ctl);event(day_ended=True,pending=len(batch.active()),best=ctl.state['best_score']);return 0
if __name__=='__main__':
 try:raise SystemExit(run())
 except KeyboardInterrupt:event(interrupted=True,resume_saved_jobs_only=True);raise
 except Exception:traceback.print_exc();raise SystemExit(5)
