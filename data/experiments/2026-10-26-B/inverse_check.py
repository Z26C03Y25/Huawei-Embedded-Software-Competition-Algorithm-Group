"""Test inverse monotone scale drift as a bounded low-noise audit, on a new holdout."""
from pathlib import Path
import importlib.util,json,subprocess,hashlib
P=Path(__file__).with_name('run.py');spec=importlib.util.spec_from_file_location('batch_b',P);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from tools.local_judge import Case,run_case
from tools.compare_solvers import make_benchmark
from online_judge.jobs import SubmissionLock
D=b.D;ROOT=b.ROOT

def main():
    with SubmissionLock(ROOT/'automation/online_judge/runs/.offline-research.lock'):
        oldhash=hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest();assert oldhash==b.BASEHASH
        extra='''                vector<int> near16,near32;
                for (int x:f.x) {
                    if (abs(x-best)<=16) near16.push_back(x);
                    if (abs(x-best)<=32) near32.push_back(x);
                }
                const auto v16=fittedVertex(near16),v32=fittedVertex(near32);'''
        lo='                    const int modelLo=max(0,min(center-3,static_cast<int>(floor(min(*v1,*v2)))-3));'
        hi='                    const int modelHi=min(rightmost,max(center+3,static_cast<int>(ceil(max(*v1,*v2)))+3));'
        shift='''
                    const int originalLo=modelLo,originalHi=modelHi;
                    if (!f.noisy && v16 && v32 && abs(*v32-*v2)>2.0) {
                        const bool increasing=*v1<=*v16 && *v16<=*v2 && *v2<=*v32;
                        const bool decreasing=*v1>=*v16 && *v16>=*v2 && *v2>=*v32;
                        if (increasing) modelLo=max(0,modelLo-2);
                        else if (decreasing) modelHi=min(rightmost,modelHi+2);
                    }'''
        safe='''                    if (!routeSafe(probe) && (modelLo!=originalLo || modelHi!=originalHi)) {
                        modelLo=originalLo;modelHi=originalHi;probe.clear();
                        for (int x=modelHi;x>=modelLo;--x) if (value[x]<0) probe.push_back(x);
                    }
'''
        item=b.source('low_noise_inverse_scale_drift',[(b.MARK,b.MARK+'\n'+extra),(lo,lo.replace('const int','int')),(hi,hi.replace('const int','int')+shift),('                    if (routeSafe(probe)) {',safe+'                    if (routeSafe(probe)) {')],dict(scale_windows=[16,24,32],raw_vertex_in_order=True,low_noise_only=True,drift_threshold=2.0,inverse_directional_extension=2,unsafe_extension_falls_back=True),'When low-noise vertex estimates drift monotonically with larger windows, audit2 raw points opposite to the drift; retain scored probe if expansion is unsafe. Direction is a bias hypothesis, not a guaranteed target.')
        old_inputs=json.loads((D/'inputs.json').read_text(encoding='utf-8'));old_report=json.loads((ROOT/'dev/build/research/multiscale_B/clean_report.json').read_text(encoding='utf-8'))
        strict=json.loads((D/'post_probe_scale32_gate.json').read_text(encoding='utf-8'));solvers=[dict(name='formal203239',source=str(b.BASE.relative_to(ROOT)),sha256=b.BASEHASH),strict,item]
        data=[(c['set'],Case(c['name'],tuple(c['values']))) for c in old_inputs['cases']]+[('fresh_holdout',i.case) for i in make_benchmark(27102605,84)]
        inputs=dict(seed=27102605,count=84,old_cases_are_observed_validation=True,solvers=solvers,fresh_cases=[dict(name=c.name,values=c.values) for g,c in data if g=='fresh_holdout'],policy_fixed_before_scoring=True)
        p=D/'inverse_inputs.json'
        if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==json.loads(json.dumps(inputs))
        else:b.save(p,inputs)
        report=dict(official=False,source_sha256={s['name']:s['sha256'] for s in solvers},results={});summaries={};baseline=None;build=ROOT/'dev/build/research/multiscale_B'
        for solver in solvers:
            assert hashlib.sha256((ROOT/solver['source']).read_bytes()).hexdigest()==solver['sha256']
            exe=build/(solver['name']+'_inverse.exe');cp=subprocess.run(['g++','-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(ROOT/solver['source']),'-o',str(exe)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
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
            b.save(build/'inverse_report.json',report);b.save(D/'inverse_summary.json',summaries);print(json.dumps(dict(solver=solver['name'],summary=summaries[solver['name']])),flush=True)
        assert hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest()==oldhash
        b.save(D/'inverse_completion.json',dict(complete=True,new_pipe_runs=449,main_preserved=True,online_submissions=0,ranking_network_reads=0))
if __name__=='__main__':main()
