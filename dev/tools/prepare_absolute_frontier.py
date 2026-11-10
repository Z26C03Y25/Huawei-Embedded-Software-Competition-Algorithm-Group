"""Freeze absolute right-frontier policies from the revealed target histogram."""
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/peak_prior_20261103'; OUT.mkdir(parents=True,exist_ok=True)
PARENT=ROOT/'data/versions/main_online_216258.cpp'
cap=int(sys.argv[1])
if cap not in {560,600,700,800}: raise ValueError(cap)
text=PARENT.read_text(encoding='utf-8-sig')
a=text.index('    void explore() {'); b=text.index('    optional<double> vertex',a)
chunk=text[a:b]
anchor='''            if (rightmost>=limit) break;
            int step=12;'''
replacement=f'''            // Position-prior frontier: official histogram has no
            // target in600..650,700..750 or beyond800. Keep every original
            // evidence-based earlier limit, but never explore past this cap.
            limit=min(limit,min(n-1,{cap}));
            if (rightmost>=limit) break;
            int step=12;'''
if chunk.count(anchor)!=1: raise RuntimeError('frontier interface changed')
chunk=chunk.replace(anchor,replacement,1); text=text[:a]+chunk+text[b:]
name=f'absolute_frontier_{cap}'; path=OUT/(name+'.cpp'); raw=text.encode('utf-8')
if path.exists() and path.read_bytes()!=raw: raise RuntimeError('frozen candidate differs')
path.write_bytes(raw)
meta=dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
          source=str(path),sha256=hashlib.sha256(raw).hexdigest(),cap=cap,
          description=f'Preserve216258 sampling, features, refinement and evidence-based early stops; clamp only coarse right frontier to absolute index{cap} using revealed102-target histogram. No extra reads; knowingly trades far-tail outliers for Q/M/R savings.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
