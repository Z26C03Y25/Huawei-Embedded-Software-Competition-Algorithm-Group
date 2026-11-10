"""User-approved continuation around one unconfirmed delivery; no repeat uploads."""
from pathlib import Path
import runpy,sys,hashlib,json
R=Path(__file__).resolve().parents[2]
IGNORED_JOBS={'20261104T064432532409Z_831debfc7899','20261105T061334716758Z_98f6d7520020'}
IGNORED_SERVER={'497612b60ba943ecb77f919d98f3289a'}
APPROVAL=R/'data/experiments/blackbox_20261105/user_delivery_exception.json'
def one(s,a,b):
 if s.count(a)!=1:raise RuntimeError('Continuation interface changed:'+a)
 return s.replace(a,b,1)
if __name__=='__main__':
 proof=json.loads(APPROVAL.read_text(encoding='utf-8'))
 if proof.get('user_reply')!='继续修复，保留未确认记录' or proof.get('quarantined_job') not in IGNORED_JOBS:raise RuntimeError('Explicit exception missing')
 if len(sys.argv)>1 and sys.argv[1]=='--judge':
  sha=sys.argv.pop(2);sys.path[:0]=[str(R/'automation'),str(R/'dev')]
  path=R/'automation/online_judge/judge.py';code=path.read_text(encoding='utf-8')
  code=one(code,'if other_active:',f'if any(j["job_id"] not in {repr(IGNORED_JOBS)} for j in other_active):')
  code=one(code,'if any(row.status == "pending" for row in baseline):',f'if any(row.status == "pending" and row.submission_id not in {repr(IGNORED_SERVER)} for row in baseline):')
  anchor='            state = store.observe(job, records)'
  filter_code='''            # Reject late unrelated works BEFORE identity binding, not only at score registration.
            from tools.submission_attribution import validate_submission_timing
            if job.get("submission_attempt_at"):
                compatible=[]
                for row in records:
                    try: validate_submission_timing(dict(job,record=row.to_dict()))
                    except (ValueError,KeyError): continue
                    compatible.append(row)
                records=compatible
'''+anchor
  code=one(code,anchor,filter_code)
  ns={'__name__':'quarantine_judge','__file__':str(path)};exec(compile(code,str(path),'exec'),ns)
  sys.argv.pop(1)
  if sys.argv[1]=='submit':
   source=Path(sys.argv[sys.argv.index('--file')+1])
   if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:raise RuntimeError('Frozen source mismatch')
   if sha==proof['quarantined_sha256']:raise RuntimeError('Quarantined source must never be retried')
  raise SystemExit(ns['main']())
 source=runpy.run_path(str(R/'dev/tools/blackbox_round_20261105.py'))['source']
 source=one(source,'if any(r["state"] not in {"completed", "failed"} for r in self.state["rounds"]):',f'if any(r["state"] not in {{"completed", "failed"}} and r.get("job_id") not in {repr(IGNORED_JOBS)} for r in self.state["rounds"]):')
 source=one(source,'if active:',f'if any(j["job_id"] not in {repr(IGNORED_JOBS)} for j in active):')
 source=one(source,'if any(row.status == "pending" for row in records):',f'if any(row.status == "pending" and row.submission_id not in {repr(IGNORED_SERVER)} for row in records):')
 source=one(source,'command = [sys.executable, "-X", "utf8", str(self.root / "automation/online_judge/judge.py"), *args]','command = [sys.executable, "-X", "utf8", str(self.root / "dev/tools/continue_repair_20261105.py"), "--judge", entry["sha256"], *args]')
 anchor='            started = time.monotonic()\n            entry["wait_windows"]'
 replacement='            if entry.get("wait_windows",0)>=3:\n                self.attach(entry,job)\n                print("Unconfirmed new task: stop new uploads and resume same job only.",flush=True)\n                return 2\n            started = time.monotonic()\n            entry["wait_windows"]'
 source=one(source,anchor,replacement)
 # Exactly the user-quarantined, unbound attempt is not evidence of a stale quota.
 anchor='        if quota["used"] < len(delivered):'
 replacement='        quarantined=[j for j in delivered if j.get("job_id")=="20261105T061334716758Z_98f6d7520020" and not j.get("bound_submission_id") and not j.get("record")]\n        if quota["used"] < len(delivered)-len(quarantined):'
 source=one(source,anchor,replacement)
 ns={'__name__':'repair_controller','__file__':str(R/'dev/tools/online_round_20261030.py')}
 exec(compile(source,ns['__file__'],'exec'),ns);raise SystemExit(ns['main']())
