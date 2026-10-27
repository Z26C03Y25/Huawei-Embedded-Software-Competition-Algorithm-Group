"""Single-factor continuation on formal203110 with explicit paired-risk screening."""
from pathlib import Path
import json,sys,importlib.util
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
s=json.loads((D/'session.json').read_text(encoding='utf-8'));b=max(s['results'],key=lambda r:r['score']);assert b['score']==203110
parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
baseline=json.loads((ROOT/'dev/build/research/day26_dyn_min3.json').read_text(encoding='utf-8'))['results']
recipes=[]
for margin in (4,5):recipes.append((f'm3_margin{margin}', [('max(abs(center-*v1),abs(center-*v2))))+3',f'max(abs(center-*v1),abs(center-*v2))))+{margin}')],f'On formal203110 retain reduced minimum3 and test uncertainty margin{margin} for boundary-winner fallback',dict(model_prediction_margin=margin)))
recipes += [('m3_late8',[('if (best>=(n-1)/2) scout=min(scout,16);','if (best>=(n-1)/2) scout=min(scout,8);')],'On formal203110 test late-half scouting8 versus16; early-half guard and strong prominence remain unchanged',dict(late_scout=8)),('m3_cluster03',[('value[p]<bestValue-max(6*f.noise,0.1*f.contrast)','value[p]<bestValue-max(6*f.noise,0.03*f.contrast)')],'On formal203110 prune weak separated clusters below3 percent raw contrast while preserving6-noise tolerance',dict(group=0.03)),('m3_fit24',[('for (int x:f.x) if (abs(x-best)<=32) near.push_back(x);','for (int x:f.x) if (abs(x-best)<=24) near.push_back(x);')],'On formal203110 use nearer24-radius multi-point model; uncertainty verification follows actual vertex disagreement',dict(model_fit_window=24))]
rows=[];approved=[]
for name,edits,purpose,params in recipes:
    item=derive(name,parent,edits,purpose,params);item['offline']=d.validate(item)
    result=json.loads((ROOT/'dev/build/research'/('day26_'+name+'.json')).read_text(encoding='utf-8'))['results']
    item['offline']['paired_new_zero']=sum(a['score']==0 and b['score']>0 for a,b in zip(result,baseline))
    item['offline']['paired_parent_delta']=sum(a['score']-b['score'] for a,b in zip(result,baseline))
    rows.append(item);d.save(D/'m3_screening.json',rows)
    if not item['offline']['paired_new_zero']:approved.append(item)
    print(json.dumps(dict(name=name,**item['offline'])),flush=True)
q=json.loads((D/'queue.json').read_text(encoding='utf-8'));done={r['name'] for r in s['results']};q=[r for r in q if r['name'] in done];q+=approved;d.save(D/'queue.json',q)
