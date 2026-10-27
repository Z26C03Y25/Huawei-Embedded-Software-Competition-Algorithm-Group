"""Explain scale-induced false finishes using only the solver's observed samples."""
from pathlib import Path
import importlib.util,json,subprocess,hashlib
P=Path(__file__).with_name('run.py');spec=importlib.util.spec_from_file_location('batch_b',P);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from tools.local_judge import Case,run_case
D=b.D;ROOT=b.ROOT;inputs=json.loads((D/'inputs.json').read_text(encoding='utf-8'));report=json.loads((ROOT/'dev/build/research/multiscale_B/clean_report.json').read_text(encoding='utf-8'))
base=report['results']['formal203239'];guard=report['results']['post_probe_scale32_gate'];chosen=[]
for c,a,r in zip(inputs['cases'],base,guard):
    if c['set']=='known_counterexample' or (a['score']==0 and r['score']>0):chosen.append((c,a,r))
insert='''
                if (trace) {
                    vector<int> dbg16,dbg32;
                    for (int x:f.x) {
                        if (abs(x-best)<=16) dbg16.push_back(x);
                        if (abs(x-best)<=32) dbg32.push_back(x);
                    }
                    const auto small=fittedVertex(dbg16),wide=fittedVertex(dbg32);
                    cerr<<"MODEL_CHECK {\\"q\\":"<<q<<",\\"observed_best\\":"<<best
                        <<",\\"noise\\":"<<f.noise<<",\\"contrast\\":"<<f.contrast
                        <<",\\"v1\\":"<<(v1?to_string(*v1):"null")<<",\\"v24\\":"<<(v2?to_string(*v2):"null")
                        <<",\\"v16\\":"<<(small?to_string(*small):"null")<<",\\"v32\\":"<<(wide?to_string(*wide):"null")<<"}\\n";
                }'''
s=b.BASE.read_text(encoding='utf-8');marker='                auto v2=fittedVertex(near);';assert s.count(marker)==1;s=s.replace(marker,marker+insert)
p=D/'diagnostic_models.cpp';raw=s.encode('utf-8')
if p.exists():assert p.read_bytes()==raw
else:p.write_bytes(raw)
exe=ROOT/'dev/build/research/multiscale_B/diagnostic_models.exe';compile_result=subprocess.run(['g++','-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(p),'-o',str(exe)],capture_output=True,text=True,encoding='utf-8',errors='replace')
if compile_result.returncode or compile_result.stderr:raise RuntimeError(compile_result.stderr)
rows=[];frozen=[]
for c,a,r in chosen:
    actual=run_case([str(exe),'--trace'],Case(c['name'],tuple(c['values'])))
    for key in ('query_positions','score','queries','distance','travel','oscillations'):assert actual[key]==a[key],(c['name'],key)
    models=[json.loads(line[len('MODEL_CHECK '):]) for line in actual['stderr'].splitlines() if line.startswith('MODEL_CHECK ')]
    row=dict(name=c['name'],models=models,baseline_score=a['score'],candidate_score=r['score'],baseline_distance=a['distance'],candidate_distance=r['distance']);rows.append(row);print(json.dumps(row),flush=True)
    if a['score']==0 and r['score']>0:frozen.append(dict(**c,parent_official_score=203239,synthetic_only=True,parent_sha256=b.BASEHASH,candidate_sha256=report['source_sha256']['post_probe_scale32_gate'],baseline=a,candidate=r))
(D/'counterexamples').mkdir(exist_ok=True);b.save(D/'counterexamples/rippled_early_finish.json',frozen[0]);b.save(D/'model_diagnostics.json',rows)
