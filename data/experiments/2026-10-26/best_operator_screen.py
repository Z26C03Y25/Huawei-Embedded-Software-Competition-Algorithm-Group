"""Structural refinement operators on the formally scored risk-repaired parent."""
from pathlib import Path
import json,sys,importlib.util
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
s=json.loads((D/'session.json').read_text(encoding='utf-8'));b=max(s['results'],key=lambda x:x['score'])
parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
old=(D/'raw_concavity3.cpp').read_text(encoding='utf-8');start=old.index('    bool rawConcavityClosed() {');end=old.index('    void refine() {',start);method=old[start:end]
recipes=[('bops_concavity3',[('    void refine() {',method+'    void refine() {'),('                progress=true;\n                if (certificate()) return;','                progress=true;\n                if (certificate() || rawConcavityClosed()) return;')],'On latest formally scored parent add complete7-point raw concavity closure with curvature ratio3, low noise, no observed competitor; retain known model counterexample',dict(raw_concavity_span=3,raw_concavity_ratio=3))]
old=(D/'edge_scenarios1.cpp').read_text(encoding='utf-8');start=old.index('        if (bestValue<VMAX && f.significant && !f.noisy &&');end=old.index('        return result;\n    }\n    bool routeSafe',start);extra=old[start:end]
marker='''            result.push_back(move(c));
        }
        return result;
    }
    bool routeSafe'''
replacement='''            result.push_back(move(c));
        }
'''+extra+'''        return result;
    }
    bool routeSafe'''
recipes.append(('bops_edge_scenario1',[(marker,replacement)],'On latest formally scored parent include one left competitive-edge hidden-peak scenario in broad/plateau/multipeak low-noise planning; preserve observations',dict(edge_scenarios=1)))
block='''            if (!f.noisy && f.significant && !f.plateau) {
                bool neighborsKnown=true,uniquePeak=true;
                for (int x=max(0,best-3);x<=min(rightmost,best+3);++x)
                    if (value[x]<0) neighborsKnown=false;
                for (int x:f.peaks) if (abs(x-best)>32 && value[x]>bestValue-0.25*f.contrast) uniquePeak=false;
                if (neighborsKnown && uniquePeak) {
                    const auto imagined=scenarios(f);
                    const auto oriented=orient(all,descending);
                    if (planScore(oriented,imagined,candidates)<=planScore({},imagined,candidates)) {
                        use(Op::K07);return {};
                    }
                }
            }
'''
recipes.append(('bops_fullfit_dominance',[('            return orient(move(all),descending);',block+'            return orient(move(all),descending);')],'Check existing finite-model empty-plan dominance before eager all-candidate execution, only with measured neighbors, low noise and unique observed peak; no global certificate',dict(fullfit_dominance=True)))
recipes += [('bops_first75',[('available-min(48,available/3)','available-min(48,available/4)')],'On latest formally scored parent allocate75 percent to first fine batch instead of two thirds, retain shared hard query cap',dict(first_reserve_divisor=4))]
rows=[]
for n,edits,purpose,cfg in recipes:
    n=n+"_"+parent["sha256"][:8]
    item=derive(n,parent,edits,purpose,cfg);item['offline']=d.validate(item);rows.append(item);d.save(D/'best_operator_screening.json',rows);print(json.dumps(dict(name=n,**item['offline'])),flush=True)
