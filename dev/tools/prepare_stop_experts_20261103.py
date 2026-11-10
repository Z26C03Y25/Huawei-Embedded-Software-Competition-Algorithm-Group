from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/peak_prior_20261103'
parent=ROOT/'data/versions/main_online_216258.cpp'
text=parent.read_text(encoding='utf-8-sig')
mode=sys.argv[1]
anchor='                if (f.significant && rightmost-best>=scout && !f.rebound && !rival &&'
if mode.startswith('early'):
    distance=int(mode[5:])
    new=f'''                if (best>=50 && best<=150 && f.significant &&
                    f.falls>=3 && f.rises==0 && !f.rebound && !rival)
                    scout=min(scout,{distance});
'''+anchor
    text=text.replace(anchor,new,1)
elif mode.startswith('central'):
    distance=int(mode[7:])
    new=f'''                if (best>=450 && best<=550 && f.significant &&
                    f.falls>=3 && f.rises==0 && !f.rebound && !rival)
                    scout=min(scout,{distance});
'''+anchor
    text=text.replace(anchor,new,1)
elif mode=='no_sentinel':
    text=text.replace('if (auto sentinel=coarseShoulderSentinel(f)) {','if (auto sentinel=optional<int>{}) {',1)
elif mode=='model_bracket':
    old='if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;'
    new='''if (certificate()) return;
                        if (bestValue<VMAX && best>modelLo && best<modelHi) {
                            const int winner=best;
                            int lo=winner,hi=winner;
                            while (lo>0 && value[lo-1]>=0) --lo;
                            while (hi<rightmost && value[hi+1]>=0) ++hi;
                            vector<int> edge;
                            if (lo>0 && winner-lo<=4) edge.push_back(lo-1);
                            if (hi<rightmost && hi-winner<=4) edge.push_back(hi+1);
                            edge=canonical(move(edge),false);
                            if (routeSafe(edge)) for (int x:edge) if (!sample(x)) return;
                            return;
                        }'''
    assert old in text; text=text.replace(old,new,1)
elif mode=='no_model_return':
    text=text.replace('if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;',
                      'if (certificate()) return;',1)
else: raise ValueError(mode)
name='stop_expert_'+mode
p=OUT/(name+'.cpp'); raw=text.encode()
if p.exists() and p.read_bytes()!=raw: raise RuntimeError('immutable source')
p.write_bytes(raw)
meta=dict(parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),source=str(p),sha256=hashlib.sha256(raw).hexdigest(),description='Position-conditioned stopping/refinement expert '+mode)
p.with_suffix('.metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
print(json.dumps(meta))
