"""Fresh holdout fixed before observing outcomes; never uploads."""
from pathlib import Path
import importlib.util,json,hashlib
p=Path(__file__).with_name('session.py');spec=importlib.util.spec_from_file_location('daily',p);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
from tools.compare_solvers import make_benchmark
from tools.local_judge import run_case
D=p.parent;R=d.ROOT
names=['raw_concavity3','raw_concavity4','edge_scenarios1','edge_scenarios2']
rows=json.loads((D/'operator_validation_candidates.json').read_text(encoding='utf-8'))
solvers=[dict(name='formal201049',sha256=hashlib.sha256((R/'data/versions/online_search/scored_201049_ab47f62f3fee.cpp').read_bytes()).hexdigest())]+[next(r for r in rows if r['name']==n) for n in names]
cases=[item.case for item in make_benchmark(2026102620,84)]
inputs=dict(seed=2026102620,count=84,names=[s['name'] for s in solvers],hashes=[s['sha256'] for s in solvers])
manifest=D/'operator_holdout_inputs.json'
if manifest.exists():assert json.loads(manifest.read_text(encoding='utf-8'))==inputs
else:d.save(manifest,inputs)
full=dict(inputs=inputs,cases=[dict(name=c.name,values=c.values,family=c.family) for c in cases],results={})
summary=[];baseline=None
for s in solvers:
    exe=R/'dev/build/research'/('day26_'+s['sha256'][:12]+'.exe')
    out=[]
    for c in cases:
        r=run_case([str(exe)],c)
        assert r['status']=='ok' and r['queries']<=199 and r['oscillations']<=6,(s['name'],c.name,r)
        expected=min(set(r['query_positions']),key=lambda x:(-c.values[x],abs(2*x-(len(c.values)-1)),x))
        assert r['final_position']==expected
        out.append(r)
    if baseline is None:baseline=out
    full['results'][s['name']]=out
    report=dict(name=s['name'],total=sum(r['score'] for r in out),delta=sum(r['score']-b['score'] for r,b in zip(out,baseline)),resolved_zero=sum(r['score']>0 and b['score']==0 for r,b in zip(out,baseline)),new_zero=sum(r['score']==0 and b['score']>0 for r,b in zip(out,baseline)))
    summary.append(report);print(json.dumps(report),flush=True)
    d.save(R/'dev/build/research/day26_operator_holdout.json',full)
d.save(D/'operator_holdout_summary.json',summary)
