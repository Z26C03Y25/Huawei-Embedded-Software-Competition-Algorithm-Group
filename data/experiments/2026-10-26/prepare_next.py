"""Offline preparation only; no platform calls or uploads after daily quota0."""
from pathlib import Path
import json,sys,importlib.util,hashlib
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
from tools.compare_solvers import make_benchmark
from tools.local_judge import run_case
s=json.loads((D/'session.json').read_text(encoding='utf-8'));assert s['quota']['remaining']==0 and s['quota']['date']=='2026-10-26'
b=max(s['results'],key=lambda r:r['score']);parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
main_hash=hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest();assert main_hash==parent['sha256']
recipes=[]
for tau in (6,12):recipes.append((f'next_tau{tau}', [('abs(*v1-*v2)<10.0',f'abs(*v1-*v2)<{tau}.0')],f'Clean agreement{tau} on formal203239 exact asymmetric verification; previous fixed-radius scores do not isolate this interaction',dict(model_agreement=float(tau))))
recipes.append(('next_fit16',[('for (int x:f.x) if (abs(x-best)<=24) near.push_back(x);','for (int x:f.x) if (abs(x-best)<=16) near.push_back(x);')],'Reduce the current24-grid multi-point fit to16 while preserving the exact vertex interval and disagreement10',dict(model_fit_window=16)))
items=[]
for n,edits,purpose,cfg in recipes:
    item=derive(n,parent,edits,purpose,cfg);item['offline']=d.validate(item);items.append(item);print(json.dumps(dict(name=n,**item['offline'])),flush=True)
cases=[i.case for i in make_benchmark(20261027,84)]
inputs=dict(seed=20261027,count=84,solvers={i['name']:i['sha256'] for i in items},baseline=parent['sha256'])
d.save(D/'next_holdout_inputs.json',inputs)
full=dict(inputs=inputs,cases=[dict(name=c.name,values=c.values) for c in cases],results={})
summary=[];baseline=None
for item in [dict(name='formal203239',sha256=parent['sha256'])]+items:
    exe=ROOT/'dev/build/research'/('day26_'+item['sha256'][:12]+'.exe');out=[]
    for c in cases:
        r=run_case([str(exe)],c)
        assert r['status']=='ok' and r['queries']<=199 and r['oscillations']<=6,(item['name'],c.name,r)
        winner=min(set(r['query_positions']),key=lambda x:(-c.values[x],abs(2*x-(len(c.values)-1)),x));assert r['final_position']==winner
        out.append(r)
    if baseline is None:baseline=out
    full['results'][item['name']]=out
    row=dict(name=item['name'],total=sum(r['score'] for r in out),delta=sum(r['score']-b['score'] for r,b in zip(out,baseline)),new_zero=sum(r['score']==0 and b['score']>0 for r,b in zip(out,baseline)),resolved_zero=sum(r['score']>0 and b['score']==0 for r,b in zip(out,baseline)))
    summary.append(row);print(json.dumps(row),flush=True);d.save(ROOT/'dev/build/research/day26_next_holdout.json',full)
d.save(D/'next_holdout_summary.json',summary)
for item in items:
    item['holdout']=next(r for r in summary if r['name']==item['name']);item.update(earliest_submission_date='2026-10-27',requires_fresh_official_quota_check=True,status='offline_only_not_submitted',official_score=None)
items.sort(key=lambda i:(i['holdout']['new_zero'],-i['holdout']['delta'],i['name']))
for i,item in enumerate(items,1):item['priority']=i
d.save(D/'next_day_queue.json',dict(prepared_at=d.stamp(),earliest_submission_date='2026-10-27',parent_official_score=203239,parent_sha256=parent['sha256'],entries=items,main_preserved=True))
assert hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest()==main_hash
