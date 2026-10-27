"""Scale raw verification to cover both vertex predictions plus a 3-grid margin."""
from pathlib import Path
import json,sys,importlib.util,hashlib
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
s=json.loads((D/'session.json').read_text(encoding='utf-8'));b=max(s['results'],key=lambda x:x['score']);assert b['score']==202686
parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
marker='const int center=static_cast<int>(llround((*v1+*v2)/2));'
changes=[(marker,marker+'\n                    const int modelRadius=max(6,static_cast<int>(ceil(max(abs(center-*v1),abs(center-*v2))))+3);'),('center+6);x>=max(0,center-6)','center+modelRadius);x>=max(0,center-modelRadius)'),('abs(best-center)<=5','abs(best-center)<=modelRadius-1')]
item=derive('a10_uncertainty_radius',parent,changes,'Fix known model disagreement false finish: cover both predicted vertices with three-grid raw verification margin; keep real Q/O and parking checks',dict(model_radius_mode='both_vertices_plus3_min6'))
item['offline']=d.validate(item);d.save(D/'uncertainty_screening.json',[item]);print(json.dumps(item['offline']),flush=True)
from tools.compare_solvers import make_benchmark
case=next(i.case for i in make_benchmark(261026,28) if i.case.name=='s261026_0008_rippled_peak')
C=D/'counterexamples';C.mkdir(exist_ok=True)
d.save(C/'model_disagreement_ripple.json',dict(name=case.name,source='synthetic make_benchmark(261026,28)',values=case.values,values_sha256=hashlib.sha256(json.dumps(case.values).encode()).hexdigest(),parent_agreement6_score=2278,agreement10_fixed_radius6_score=0,zero_reason='distance8; true target513 omitted below model verification interval514..526',candidate_sha256=item['sha256'],warning='A formal best may still fail this synthetic case; preserve the case and judge new candidates honestly'))
q=json.loads((D/'queue.json').read_text(encoding='utf-8'));done={r['name'] for r in s['results']};q=[r for r in q if r['name'] in done];q.append(item)
(D/'queue.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
p=D/'submission_rejections.json';r=json.loads(p.read_text(encoding='utf-8'));r['a6_agree10']='Submitted before rejection marker. Official202686 is the highest and remains protected despite the retained new synthetic zero (offline delta-2291). Do not repeat this hash; prioritize uncertainty-scaled verification before expanding agreement further.';d.save(p,r)
