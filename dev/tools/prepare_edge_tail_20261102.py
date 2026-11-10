"""Freeze a minimal pre-reversal edge-cell completion candidate."""
from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'data/versions/main_online_216258.cpp'
OUT=ROOT/'data/experiments/blackbox_20261102'
text=PARENT.read_text(encoding='utf-8-sig')
anchor='''            vector<int> plan=selectPlan(candidates,budget,descending,f);
            if (plan.empty() || !routeSafe(plan)) break;'''
replacement='''            vector<int> plan=selectPlan(candidates,budget,descending,f);
            // Before the first descending refinement reverses direction, do
            // not strand the last one-to-three unknown positions in the same
            // high edge cell. Completion is monotone and uses only otherwise
            // spare replies; it does not alter the coarse feature history.
            if (round==0 && !plan.empty()) {
                const int leftmost=*min_element(plan.begin(),plan.end());
                auto it=lower_bound(f.x.begin(),f.x.end(),leftmost);
                if (it!=f.x.begin()) {
                    const int anchor=*prev(it);
                    const double threshold=bestValue-max({1.0,3*f.noise+0.02*f.contrast,
                                                          0.04*f.contrast});
                    vector<int> completion;
                    if (leftmost-anchor>=2 && leftmost-anchor<=4 && value[anchor]>=threshold)
                        for (int x=leftmost-1;x>anchor;--x)
                            if (value[x]<0) completion.push_back(x);
                    if (!completion.empty() &&
                        static_cast<int>(plan.size()+completion.size())<=available) {
                        vector<int> extended=plan;
                        extended.insert(extended.end(),completion.begin(),completion.end());
                        extended=canonical(move(extended),true);
                        if (routeSafe(extended)) plan=move(extended);
                    }
                }
            }
            if (plan.empty() || !routeSafe(plan)) break;'''
if text.count(anchor)!=1: raise RuntimeError('refinement interface changed')
text=text.replace(anchor,replacement,1)
name='pre_reversal_edge_tail'
path=OUT/(name+'.cpp'); raw=text.encode('utf-8')
if path.exists() and path.read_bytes()!=raw: raise RuntimeError('frozen candidate differs')
path.write_bytes(raw)
meta=dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
          source=str(path),sha256=hashlib.sha256(raw).hexdigest(),
          description='Before first descending refinement reverses, complete at most3 unknown positions between its leftmost selected point and a nearby high observed anchor (cell width<=4). Monotone path, spare budget only; coarse scan/features unchanged. Targets one-to-three-cell narrow peaks stranded at a high-region edge.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
