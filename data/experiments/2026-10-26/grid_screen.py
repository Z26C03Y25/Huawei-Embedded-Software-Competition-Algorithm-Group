"""Non-flat coarse-grid ablation on the scored 200494 parent; never uploads."""
from pathlib import Path
import json,sys,importlib.util
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D))
from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
parent=dict(source='data/versions/main_online_200494.cpp',sha256='7500dffc130ef08a208f86661bfe5e3b42776ab606a19fb85c4a373cba0bcb72',config=json.loads((D/'fine_radius8.json').read_text(encoding='utf-8'))['config'],score=200494)
recipes=[]
for step in (7,9,10,12):
    edits=[('step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;',f'step=f.curvature<-max(0.1,f.noise/12) ? {step} : {step};'),('if (f.noisy) step=8;',f'if (f.noisy) step={step};'),('else step=f.noisy || state==Shape::Rough ? 8 : 8;',f'else step=f.noisy || state==Shape::Rough ? {step} : {step};'),('if (f.rebound) { use(Op::K05); step=8; }',f'if (f.rebound) {{ use(Op::K05); step={step}; }}')]
    recipes.append((f'r8_nonflat_step{step}',edits,f'Clean nonflat coarse stride {step}; flat-prefix grid, prominence24 and coarse budget128 fixed',dict(nonflat_step=step)))
for step in (10,12):
    edits=[('int next=min({n-1,rightmost+step,limit});',f'if (!f.flat && f.significant && !f.noisy && f.rises>=2 && f.falls==0) step={step};\n            int next=min({{n-1,rightmost+step,limit}});')]
    recipes.append((f'r8_smooth_rising{step}',edits,f'Use stride {step} only on significant low-noise unbracketed rising branch; retain8 in rough/multipeak branches',dict(smooth_rising_step=step)))
records=[]
for name,edits,purpose,params in recipes:
    item=derive(name,parent,edits,purpose,params);item['offline']=d.validate(item);records.append(item);d.save(D/'grid_screening.json',records)
    print(json.dumps(dict(name=name,**item['offline'])),flush=True)
