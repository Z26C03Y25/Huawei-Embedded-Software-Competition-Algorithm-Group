"""Separate absent-wide-fit and positive scale-disagreement evidence; new holdout."""
from pathlib import Path
import importlib.util,json,subprocess,hashlib
P=Path(__file__).with_name('run.py');spec=importlib.util.spec_from_file_location('batch_b',P);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from tools.local_judge import Case,run_case
from tools.compare_solvers import make_benchmark
from online_judge.jobs import SubmissionLock
D=b.D;ROOT=b.ROOT

def main():
    with SubmissionLock(ROOT/'automation/online_judge/runs/.offline-research.lock'):
        main_hash=hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest();assert main_hash==b.BASEHASH
        extra='''                vector<int> near32;
                for (int x:f.x) if (abs(x-best)<=32) near32.push_back(x);
                const auto v32=fittedVertex(near32);'''
        gate='best>modelLo && best<modelHi'
        additions=[(b.MARK,b.MARK+'\n'+extra)]
        drift=b.source('post_probe_drift_only',additions+[(gate,gate+' && (!v32 || abs(*v32-*v2)<=2.0)')],dict(audit_window=32,post_probe_agreement=2.0,null_wide_fit_passes=True,retains_original_queries=True),'After original raw verification veto only a valid32-radius prediction disagreeing by>2; absent32 prediction leaves the original behavior')
        valid=b.source('post_probe_wide_valid',additions+[(gate,gate+' && v32')],dict(audit_window=32,require_valid_wide_fit=True,retains_original_queries=True),'After original raw verification veto only failure to fit32-radius data, separating missing wider concavity from finite prediction drift')
        strict=json.loads((D/'post_probe_scale32_gate.json').read_text(encoding='utf-8'))
        solvers=[dict(name='formal203239',source=str(b.BASE.relative_to(ROOT)),sha256=b.BASEHASH),strict,drift,valid]
        old_inputs=json.loads((D/'inputs.json').read_text(encoding='utf-8'));old_report=json.loads((ROOT/'dev/build/research/multiscale_B/clean_report.json').read_text(encoding='utf-8'))
        data=[(c['set'],Case(c['name'],tuple(c['values']))) for c in old_inputs['cases']]
        fresh=[('fresh_holdout',i.case) for i in make_benchmark(27102604,84)];data+=fresh
        inputs=dict(seed=27102604,fresh_count=84,old_cases_are_observed_validation=True,parent_sha256=b.BASEHASH,solvers=solvers,fresh_cases=[dict(name=c.name,values=c.values) for g,c in fresh],fixed_before_scoring=True)
        p=D/'branch_inputs.json'
        if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==json.loads(json.dumps(inputs))
        else:b.save(p,inputs)
        report=dict(official=False,inputs_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),results={});summaries={};baseline=None
        build=ROOT/'dev/build/research/multiscale_B';output=build/'branch_report.json'
        for solver in solvers:
            assert hashlib.sha256((ROOT/solver['source']).read_bytes()).hexdigest()==solver['sha256']
            exe=build/(solver['name']+'_branch.exe');cp=subprocess.run(['g++','-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(ROOT/solver['source']),'-o',str(exe)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            if cp.returncode or cp.stderr:raise RuntimeError(cp.stderr)
            cached=old_report['results'].get(solver['name']) if old_report['source_sha256'].get(solver['name'])==solver['sha256'] else None
            rows=list(cached) if cached else []
            for group,c in data[len(rows):]:
                r=run_case([str(exe)],c);assert r['status']=='ok' and r['queries']<=199 and r['oscillations']<=6,(solver['name'],c.name,r)
                winner=min(set(r['query_positions']),key=lambda x:(-c.values[x],abs(2*x-(len(c.values)-1)),x));assert r['final_position']==winner
                rows.append(dict(set=group,**r))
            report['results'][solver['name']]=rows
            if baseline is None:baseline=rows
            summaries[solver['name']]={}
            for group in ['smoke','development','holdout','known_counterexample','fresh_holdout']:
                pairs=[(r,a) for r,a in zip(rows,baseline) if r['set']==group]
                summaries[solver['name']][group]=dict(cases=len(pairs),delta=sum(r['score']-a['score'] for r,a in pairs),new_zero=sum(r['score']==0 and a['score']>0 for r,a in pairs),resolved_zero=sum(r['score']>0 and a['score']==0 for r,a in pairs),max_queries=max(r['queries'] for r,a in pairs),max_turns=max(r['oscillations'] for r,a in pairs))
            b.save(output,report);b.save(D/'branch_summary.json',summaries);print(json.dumps(dict(solver=solver['name'],summary=summaries[solver['name']])),flush=True)
        assert hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest()==main_hash
        b.save(D/'branch_completion.json',dict(complete=True,main_preserved=True,solvers=4,case_count=281,new_pipe_runs=730,queries_le199=True,turns_le6=True,observed_winner_parked=True,online_submissions=0,ranking_network_reads=0))
if __name__=='__main__':main()
