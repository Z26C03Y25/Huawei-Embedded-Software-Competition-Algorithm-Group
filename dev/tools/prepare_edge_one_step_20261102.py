"""Freeze a one-position pre-reversal edge extension."""
from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'data/versions/main_online_216258.cpp'
OUT=ROOT/'data/experiments/blackbox_20261102'
text=PARENT.read_text(encoding='utf-8-sig')
anchor='''            vector<int> plan=selectPlan(candidates,budget,descending,f);
            if (plan.empty() || !routeSafe(plan)) break;'''
replacement='''            vector<int> plan=selectPlan(candidates,budget,descending,f);
            // One-cell slow charge at the left edge before the first reverse:
            // extend an already descending high-cell route by exactly one
            // adjacent unknown position, never by a new global sweep.
            if (round==0 && !plan.empty()) {
                const int leftmost=*min_element(plan.begin(),plan.end());
                auto it=lower_bound(f.x.begin(),f.x.end(),leftmost);
                if (it!=f.x.begin()) {
                    const int anchor=*prev(it),extra=leftmost-1;
                    const double threshold=bestValue-max({1.0,3*f.noise+0.02*f.contrast,
                                                          0.04*f.contrast});
                    if (leftmost-anchor>=2 && leftmost-anchor<=8 && value[anchor]>=threshold &&
                        extra>anchor && value[extra]<0 &&
                        static_cast<int>(plan.size())<available) {
                        vector<int> extended=plan;
                        extended.push_back(extra);
                        extended=canonical(move(extended),true);
                        if (routeSafe(extended)) plan=move(extended);
                    }
                }
            }
            if (plan.empty() || !routeSafe(plan)) break;'''
if text.count(anchor)!=1: raise RuntimeError('refinement interface changed')
text=text.replace(anchor,replacement,1)
name='pre_reversal_one_step'
path=OUT/(name+'.cpp'); raw=text.encode('utf-8')
if path.exists() and path.read_bytes()!=raw: raise RuntimeError('frozen candidate differs')
path.write_bytes(raw)
meta=dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
          source=str(path),sha256=hashlib.sha256(raw).hexdigest(),
          description='Preserve216258 trajectory. Before the first descending refinement reverses, extend by exactly one unknown adjacent position left of the selected frontier when it remains in a high cell of width<=8. At most one reply, monotone path and spare budget only; tests narrow-peak rescue without changing coarse geometry.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
