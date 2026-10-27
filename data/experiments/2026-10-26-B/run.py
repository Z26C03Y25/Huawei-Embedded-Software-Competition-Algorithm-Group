"""Multiscale follow-up on scored203239. Offline only after today's quota0."""
from pathlib import Path
import json,hashlib,sys,os,subprocess
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'dev'),str(ROOT/'automation')]
os.environ['PATH']=r'D:\application\mingw64\app\mingw64\bin'+os.pathsep+os.environ.get('PATH','')
os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTHONIOENCODING']='utf-8'
from tools.local_judge import make_suite,Case,run_case
from tools.compare_solvers import make_benchmark
from online_judge.jobs import SubmissionLock
BASE=ROOT/'data/versions/main_online_203239.cpp';BASEHASH='b9f585fcbc25c3428ce7d9dd92f22e6e1d0cf88534c3244e0017b2eb222311cc'
EXTRA='''                vector<int> near16;
                for (int x:f.x) if (abs(x-best)<=16) near16.push_back(x);
                const auto v16=fittedVertex(near16);
'''
MARK='                auto v2=fittedVertex(near);'

def save(p,value):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)
def source(name,edits,parameters,purpose):
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASEHASH
    s=BASE.read_text(encoding='utf-8')
    for old,new in edits:
        if s.count(old)!=1:raise RuntimeError('Nonunique mutation '+old)
        s=s.replace(old,new)
    cfg=json.loads((ROOT/'data/experiments/2026-10-26/final_summary.json').read_text(encoding='utf-8'))
    config=dict(parent_official_score=203239,parent_sha256=BASEHASH,**parameters)
    raw=('// Multiscale experiment: '+json.dumps(config,sort_keys=True)+'\n'+s.split('\n',1)[1]).encode()
    p=D/(name+'.cpp')
    if p.exists():assert p.read_bytes()==raw
    else:p.write_bytes(raw)
    item=dict(name=name,source=str(p.relative_to(ROOT)).replace('\\','/'),sha256=hashlib.sha256(raw).hexdigest(),parent_sha256=BASEHASH,parent_official_score=203239,changes=parameters,purpose=purpose,official_score=None,status='offline_only_not_submitted')
    save(p.with_suffix('.json'),item);return item

def candidates():
    guarded=EXTRA+'''                // Never enable a finish that the scored24-radius model rejected.
                if (v1 && v2 && v16 && abs(*v1-*v2)<10.0 && abs(*v16-*v2)<=1.0 && abs(*v1-*v16)<10.0)
                    v2=v16;
'''
    a=source('guarded_fit16_v2',[(MARK,MARK+'\n'+guarded)],dict(adaptive_fit_window=16,baseline_fit_window=24,scale_agreement=1.0,requires_baseline_eligibility=True),'Use16-radius estimate only if the existing24-radius model was eligible and the two estimates agree within1; otherwise exactly retain24')
    extra32='''                vector<int> near32;
                for (int x:f.x) if (abs(x-best)<=32) near32.push_back(x);
                const auto v32=fittedVertex(near32);'''
    hi='                    const int modelHi=min(rightmost,max(center+3,static_cast<int>(ceil(max(*v1,*v2)))+3));'
    lo='                    const int modelLo=max(0,min(center-3,static_cast<int>(floor(min(*v1,*v2)))-3));'
    shift='''
                    const int originalLo=modelLo,originalHi=modelHi;
                    if (v32 && abs(*v32-*v2)>2.0) {
                        if (*v32<*v2) modelLo=max(0,modelLo-2);
                        else modelHi=min(rightmost,modelHi+2);
                    }'''
    safe='''                    if (!routeSafe(probe) && (modelLo!=originalLo || modelHi!=originalHi)) {
                        modelLo=originalLo;modelHi=originalHi;probe.clear();
                        for (int x=modelHi;x>=modelLo;--x) if (value[x]<0) probe.push_back(x);
                    }
'''
    b=source('drift32_directional2',[(MARK,MARK+'\n'+extra32),(lo,lo.replace('const int','int')),(hi,hi.replace('const int','int')+shift),('                    if (routeSafe(probe)) {',safe+'                    if (routeSafe(probe)) {')],dict(audit_window=32,drift_threshold=2.0,directional_extension=2,unsafe_extension_falls_back=True),'Extend only the drift-side endpoint by2 when32- versus24-radius prediction differs by>2; preserve original probe if expanded route is unsafe')
    c=source('post_probe_scale32_gate',[(MARK,MARK+'\n'+extra32),('best>modelLo && best<modelHi','best>modelLo && best<modelHi && v32 && abs(*v32-*v2)<=2.0')],dict(audit_window=32,post_probe_agreement=2.0,retains_original_queries=True),'Always execute original raw verification; allow early finish only if32-radius model exists and agrees within2, otherwise refine retaining the observed champion')
    return [a,b,c]
def dataset():
    sets=[('smoke',c) for c in make_suite('smoke')]
    for label,seed in [('development',26102603),('holdout',27102603)]:sets += [(label,i.case) for i in make_benchmark(seed,84)]
    for file in ['model_disagreement_ripple.json','fit16_holdout_failures.json']:
        raw=json.loads((ROOT/'data/experiments/2026-10-26/counterexamples'/file).read_text(encoding='utf-8-sig'))
        for item in raw if isinstance(raw,list) else [raw]:sets.append(('known_counterexample',Case(item['name'],tuple(item['values']),'known_counterexample','challenging')))
    return sets

def main():
    with SubmissionLock(ROOT/'automation/online_judge/runs/.offline-research.lock'):
        main_hash=hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest();assert main_hash==BASEHASH
        cand=candidates();solvers=[dict(name='formal203239',source=str(BASE.relative_to(ROOT)),sha256=BASEHASH)]+cand
        data=dataset();inputs=dict(parent_sha256=BASEHASH,solvers=solvers,cases=[dict(set=g,name=c.name,values=c.values) for g,c in data],fixed_before_scoring=True)
        p=D/'inputs_clean.json'
        if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==json.loads(json.dumps(inputs))
        else:save(p,inputs)
        report=dict(official=False,inputs_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_sha256={s['name']:s['sha256'] for s in solvers},results={})
        build=ROOT/'dev/build/research/multiscale_B';build.mkdir(parents=True,exist_ok=True)
        output=build/'clean_report.json';baseline=None;summaries={}
        previous=json.loads((build/'report.json').read_text(encoding='utf-8'))
        old_inputs=json.loads((D/'inputs.json').read_text(encoding='utf-8'))
        assert old_inputs['cases']==json.loads(json.dumps(inputs['cases']))
        for solver in solvers:
            exe=build/(solver['name']+'.exe');p=subprocess.run(['g++','-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(ROOT/solver['source']),'-o',str(exe)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            if p.returncode or p.stderr:raise RuntimeError('Compilation failed/warned '+solver['name']+': '+p.stderr)
            if previous['source_sha256'].get(solver['name'])==solver['sha256']:
                rows=previous['results'][solver['name']]  # Same bytecode source and fixed inputs; compile checked above.
            else:
                rows=[]
                for group,c in data:
                    r=run_case([str(exe)],c)
                    assert r['status']=='ok' and r['queries']<=199 and r['oscillations']<=6,(solver['name'],c.name,r)
                    winner=min(set(r['query_positions']),key=lambda x:(-c.values[x],abs(2*x-(len(c.values)-1)),x));assert r['final_position']==winner
                    rows.append(dict(set=group,**r))
                if solver['name']=='guarded_fit16_v2':
                    for clean,draft in zip(rows,previous['results']['guarded_fit16']):
                        for key in ('query_positions','score','distance','travel','queries','oscillations','final_position'):assert clean[key]==draft[key],key
            report['results'][solver['name']]=rows
            if baseline is None:baseline=rows
            summaries[solver['name']]={}
            for group in ['smoke','development','holdout','known_counterexample']:
                pairs=[(r,b) for r,b in zip(rows,baseline) if r['set']==group]
                summaries[solver['name']][group]=dict(cases=len(pairs),total=sum(r['score'] for r,b in pairs),delta=sum(r['score']-b['score'] for r,b in pairs),new_zero=sum(r['score']==0 and b['score']>0 for r,b in pairs),resolved_zero=sum(r['score']>0 and b['score']==0 for r,b in pairs),max_queries=max(r['queries'] for r,b in pairs),max_turns=max(r['oscillations'] for r,b in pairs))
            save(output,report);save(D/'summary_clean.json',summaries);print(json.dumps(dict(solver=solver['name'],summary=summaries[solver['name']])),flush=True)
        assert hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest()==main_hash
        save(D/'completion_clean.json',dict(complete=True,source_parent=BASEHASH,main_preserved=True,online_submissions=0,ranking_network_reads=0,case_count=len(data),solvers=len(solvers),pipe_runs_represented=len(data)*len(solvers),new_pipe_runs=len(data),unchanged_source_results_reused=True,clean_compile=True,draft_cleanup_query_equivalent=True))
if __name__=='__main__':main()
