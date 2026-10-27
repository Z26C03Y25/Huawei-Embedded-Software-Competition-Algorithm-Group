"""Single-factor hypotheses on the formal 199291 parent; no uploads."""
import importlib.util,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('daily',Path(__file__).with_name('session.py'));daily=importlib.util.module_from_spec(spec);spec.loader.exec_module(daily)
BASE=ROOT/'data/versions/main_online_199291.cpp'
PARENT=hashlib.sha256(BASE.read_bytes()).hexdigest()
BASECFG=json.loads((ROOT/'data/versions/online_search/r03_model_finish_best.json').read_text(encoding='utf-8'))['config']
def propose(name,changes,purpose,params):
    s=BASE.read_text(encoding='utf-8')
    for old,new in changes:
        if s.count(old)!=1:raise ValueError('Nonunique mutation '+old)
        s=s.replace(old,new)
    cfg=BASECFG|params
    s='// Day26 single-factor experiment: '+json.dumps(cfg,sort_keys=True)+'\n'+s.split('\n',1)[1]
    path=Path(__file__).with_name(name+'.cpp');data=s.encode('utf-8')
    if path.exists() and path.read_bytes()!=data:raise ValueError('Never overwrite candidate')
    path.write_bytes(data)
    info=dict(name=name,source=str(path.relative_to(ROOT)).replace('\\','/'),sha256=hashlib.sha256(data).hexdigest(),parent_sha256=PARENT,purpose=purpose,config=cfg,official_score=None)
    path.with_suffix('.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    return info

def recipes():
    out=[]
    for r in (3,4,5,8):
        out.append((f'model_probe{r}', [('center+6);x>=max(0,center-6)',f'center+{r});x>=max(0,center-{r})'),('abs(best-center)<=5',f'abs(best-center)<={r-1}')],f'Model validation radius {r}; preserve interior-best stopping and true parking',dict(model_probe_radius=r)))
    for r in (8,10,14,18):
        out.append((f'fine_radius{r}', [('for (int x=best-12;x<=best+12;++x)',f'for (int x=best-{r};x<=best+{r};++x)')],f'Clean fine radius {r}; model validation and all other controls fixed',dict(radius=r)))
    for noise in (0.001,0.01,0.02):
        out.append((f'model_noise{str(noise).replace(".","p")}', [('f.noise<0.005*f.contrast',f'f.noise<{noise}*f.contrast')],f'Test model finish eligibility at noise/contrast {noise}; raw champion unchanged',dict(model_noise_fraction=noise)))
    for scout in (64,80,112):
        out.append((f'early_scout{scout}', [('clamp(static_cast<int>(f.halfLeft*1.2),96,144)',f'clamp(static_cast<int>(f.halfLeft*1.2),{scout},144)')],f'Early-peak scouting lower clamp {scout}; late clamp16 unchanged',dict(scout_min=scout)))
    for late in (8,24,32):
        out.append((f'late_scout{late}', [('if (best>=(n-1)/2) scout=min(scout,16);',f'if (best>=(n-1)/2) scout=min(scout,{late});')],f'Late-peak scouting {late}; test overrun versus second-peak risk',dict(late_scout=late)))
    for group in (0.05,0.15,0.2):
        out.append((f'cluster{str(group).replace(".","p")}', [('value[p]<bestValue-max(6*f.noise,0.1*f.contrast)',f'value[p]<bestValue-max(6*f.noise,{group}*f.contrast)')],f'Competitive cluster retention tolerance {group}; test missed secondary basins',dict(group=group)))
    for reserve in (24,32,64):
        out.append((f'reserve{reserve}', [('available-min(48,available/3)',f'available-min({reserve},available/3)')],f'Change first-round fine reserve to {reserve}; unified total budget unchanged',dict(reserve=reserve)))
    for frac in (0.02,0.06):
        out.append((f'band{str(frac).replace(".","p")}', [('max({1.0,3*f.noise+0.02*f.contrast,0.04*f.contrast})',f'max({{1.0,3*f.noise+0.02*f.contrast,{frac}*f.contrast}})')],f'High-value candidate band contrast fraction {frac}',dict(band_contrast=frac)))
    return out
if __name__=='__main__':
    records=[]
    for name,changes,purpose,params in recipes():
        info=propose(name,changes,purpose,params)
        info['offline']=daily.validate(info);records.append(info)
        print(json.dumps(dict(name=name,**info['offline'])),flush=True)
        daily.save(Path(__file__).with_name('screening.json'),records)
