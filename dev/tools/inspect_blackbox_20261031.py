"""Read-only source, saved-job and live quota inspection; never uploads."""
from pathlib import Path
import sys, json, re, hashlib
from datetime import datetime, timezone, timedelta
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'automation'))
from online_judge.browser import connect, load_config
from online_judge.jobs import JobStore

def main():
    c = load_config()
    s = JobStore(Path(c['runs_directory']))
    jobs = [s.load(p.parent.name) for p in s.root.glob('*/job.json')]
    completed = [j for j in jobs if j.get('state') == 'completed' and type(j.get('score')) is int]
    best = sorted(completed, key=lambda j: j['score'], reverse=True)[:8]
    result = dict(clock=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  main_sha256=hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest(),
                  best_jobs=[{k:j.get(k) for k in ['job_id','score','sha256','snapshot_path','record']} for j in best],
                  unfinished=[{k:j.get(k) for k in ['job_id','state']} for j in jobs
                              if j['state'] not in ['completed','failed','snapshot_ready']])
    with connect(c) as page:
        records=page.records(refresh=True)
        result['quota_text']=re.findall(r'团队已经上传.{0,70}',page.page.locator('body').inner_text())
        result['pending_records']=[r.to_dict() for r in records if r.status=='pending']
    out=ROOT/'data/experiments/blackbox_20261031'
    out.mkdir(parents=True, exist_ok=True)
    (out/'inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
