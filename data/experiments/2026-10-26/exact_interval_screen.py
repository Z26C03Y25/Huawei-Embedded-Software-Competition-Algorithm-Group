"""Exact integer hull of two vertex predictions plus the existing raw margin."""
from pathlib import Path
import json,sys,importlib.util,re
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
s=json.loads((D/'session.json').read_text(encoding='utf-8'));b=max(s['results'],key=lambda r:r['score'])
parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
body=(ROOT/parent['source']).read_text(encoding='utf-8');line=re.search(r'const int modelRadius=max\((\d+),[^\n]*\+(\d+)\);',body)
if not line:raise RuntimeError('Unsupported parent verification formula')
minimum,margin=map(int,line.groups())
new=f'''const int modelLo=max(0,min(center-{minimum},static_cast<int>(floor(min(*v1,*v2)))-{margin}));
                    const int modelHi=min(rightmost,max(center+{minimum},static_cast<int>(ceil(max(*v1,*v2)))+{margin}));'''
changes=[(line[0],new),('for (int x=min(rightmost,center+modelRadius);x>=max(0,center-modelRadius);--x)','for (int x=modelHi;x>=modelLo;--x)'),('abs(best-center)<=modelRadius-1','best>modelLo && best<modelHi')]
name='exact_vertex_hull_'+parent['sha256'][:8]
item=derive(name,parent,changes,'Use exact outward-rounded integer vertex hull plus the same margin/central minimum; remove symmetric rounding overcoverage, retain interior raw winner and shared limits',dict(model_radius_mode='asymmetric_vertex_interval',model_prediction_margin=margin,model_min_radius=minimum))
item['offline']=d.validate(item);d.save(D/'exact_interval_screening.json',[item]);print(json.dumps(dict(candidate=name,**item['offline'])),flush=True)
q=json.loads((D/'queue.json').read_text(encoding='utf-8'));done={r['name'] for r in s['results']};q=[r for r in q if r['name'] in done];q.append(item);d.save(D/'queue.json',q)
