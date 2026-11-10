"""Freeze cost-neutral phase shifts inside the dominant500..550 corridor."""
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/peak_prior_20261103'; OUT.mkdir(parents=True,exist_ok=True)
PARENT=ROOT/'data/versions/main_online_216258.cpp'
delta=int(sys.argv[1])
if delta not in {2,4,6}: raise ValueError(delta)
text=PARENT.read_text(encoding='utf-8-sig')
a=text.index('    void explore() {'); b=text.index('    optional<double> vertex',a); chunk=text[a:b]
chunk=chunk.replace('        int flatRuns=0, adjacentReads=0;',
                    '        int flatRuns=0, adjacentReads=0;\n        bool priorPhase=false;',1)
anchor='''            int next=min({n-1,rightmost+step,limit});
            const int center=(n-1)/2;'''
replacement=f'''            int next=min({{n-1,rightmost+step,limit}});
            // Shift the regular grid once on entry to the dominant corridor,
            // retain its8-cell spacing, then restore the original phase with
            // one short final gap. No extra point or travel is introduced.
            if (!priorPhase && rightmost<500 && next>=500 && next<=550 && next+{delta}<=limit) {{
                next+= {delta}; priorPhase=true;
            }} else if (priorPhase && next>550) {{
                next=min({{n-1,limit,rightmost+{8-delta}}}); priorPhase=false;
            }}
            const int center=(n-1)/2;'''
if chunk.count(anchor)!=1: raise RuntimeError('next-point interface changed')
chunk=chunk.replace(anchor,replacement,1); text=text[:a]+chunk+text[b:]
name=f'corridor500_phase_plus{delta}'; path=OUT/(name+'.cpp'); raw=text.encode('utf-8')
if path.exists() and path.read_bytes()!=raw: raise RuntimeError('frozen candidate differs')
path.write_bytes(raw)
meta=dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
          source=str(path),sha256=hashlib.sha256(raw).hexdigest(),delta=delta,
          description=f'Cost-neutral target-prior placement: shift the original8-grid by+{delta} only while traversing500..550, then restore phase with one short gap. Preserve query count, travel budget, stops and refinement; tests modulo aliasing for32/102 targets.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
