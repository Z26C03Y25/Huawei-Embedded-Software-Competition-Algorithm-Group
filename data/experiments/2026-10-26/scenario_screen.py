"""Add explicit edge-hidden-peak scenarios, preserving all observed raw values."""
from pathlib import Path
import json,sys,importlib.util
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
s=json.loads((D/'session.json').read_text(encoding='utf-8'));b=max(s['results'],key=lambda r:r['score']);parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
marker='''            result.push_back(move(c));
        }
        return result;
    }
    bool routeSafe'''
block='''            result.push_back(move(c));
        }
        if (bestValue<VMAX && f.significant && !f.noisy &&
            (f.plateau || f.shape==Shape::Broad || f.shape==Shape::Multi)) {
            vector<int> hidden;
            const double gate=bestValue-max(6*f.noise,0.1*f.contrast);
            for (size_t i=1;i<f.x.size();++i) {
                const int a=f.x[i-1], b=f.x[i];
                if (b-a<2 || b-a>12 || max(value[a],value[b])<gate) continue;
                const int x=(a+b)/2;
                if (x>=rightmost-199) hidden.push_back(x);
            }
            if (!hidden.empty()) {
                vector<int> chosen={hidden.front()};
                if (BOTH && hidden.back()!=hidden.front()) chosen.push_back(hidden.back());
                for (int x:chosen) {
                    Scenario imagined=result.front();
                    imagined.value[x]=min(VMAX,bestValue+max(1LL,static_cast<long long>(ceil(0.02*f.contrast))));
                    imagined.target=x;
                    result.push_back(move(imagined));
                }
            }
        }
        return result;
    }
    bool routeSafe'''
rows=[]
for both in (False,True):
    name='edge_scenarios'+('2' if both else '1')
    item=derive(name,parent,[(marker,block.replace('BOTH','true' if both else 'false'))],f'Counterfactual edge-hidden peak scenarios on broad/plateau/multipeak low-noise branch, count {2 if both else 1}; raw observations preserved, probability heuristic only',dict(edge_scenarios=2 if both else 1))
    item['offline']=d.validate(item);rows.append(item);d.save(D/'scenario_screening.json',rows);print(json.dumps(dict(name=name,**item['offline'])),flush=True)
