"""Derive isolated candidates from an explicitly scored immutable parent."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[3]
DIR=Path(__file__).resolve().parent

def derive(name,parent,changes,purpose,parameters):
    path=ROOT/parent['source'];raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=parent['sha256']:raise ValueError('Parent hash mismatch')
    s=raw.decode('utf-8').replace('\r\n','\n')
    for old,new in changes:
        if s.count(old)!=1:raise ValueError('Nonunique mutation '+old)
        s=s.replace(old,new)
    config=parent['config']|parameters
    actual=re.search(r'const int modelRadius=max\((\d+),[^\n]*\+(\d+)\);',s)
    if actual:config.update(model_radius_mode='two_vertex_uncertainty',model_min_radius=int(actual[1]),model_prediction_margin=int(actual[2]))
    s='// Day26 derived experiment: '+json.dumps(config,sort_keys=True)+'\n'+s.split('\n',1)[1]
    data=s.encode('utf-8');out=DIR/(name+'.cpp')
    if out.exists() and out.read_bytes()!=data:raise ValueError('Existing candidate differs')
    out.write_bytes(data)
    item=dict(name=name,source=str(out.relative_to(ROOT)).replace('\\','/'),sha256=hashlib.sha256(data).hexdigest(),parent_sha256=parent['sha256'],parent_official_score=parent['score'],purpose=purpose,config=config,official_score=None)
    out.with_suffix('.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
    return item
