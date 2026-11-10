"""Freeze lower-cost variants of the500..550 target-prior corridor."""
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/peak_prior_20261103'; OUT.mkdir(parents=True,exist_ok=True)
PARENT=ROOT/'data/versions/main_online_216258.cpp'
SKETCH=ROOT/'data/experiments/blackbox_20261102/forward_peak_sketch.cpp'
mode=sys.argv[1]
if mode not in {'late_stride4','late_half_midpoints','late_half_midpoints_odd','early_stride4'}: raise ValueError(mode)
text=PARENT.read_text(encoding='utf-8-sig'); sketch=SKETCH.read_text(encoding='utf-8-sig')
a=text.index('    Features features() {'); b=text.index('    bool coarseRivalEvidence(',a)
sa=sketch.index('    Features features() {'); sb=sketch.index('    bool coarseRivalEvidence(',sa)
text=text[:a]+sketch[sa:sb]+text[b:]
text=text.replace('    vector<long long> value;','    vector<long long> value;\n    vector<unsigned char> fineAux;',1)
text=text.replace(': wire(transport),n(length),value(length,-1),trace(diagnostics)',
                  ': wire(transport),n(length),value(length,-1),fineAux(length,0),trace(diagnostics)',1)
a=text.index('    void explore() {'); b=text.index('    optional<double> vertex',a); chunk=text[a:b]
chunk=chunk.replace('        int flatRuns=0, adjacentReads=0;',
                    '        int flatRuns=0, adjacentReads=0,priorReads=0;',1)
for old,new in [('q<128','q<128+priorReads'),('q+3<=128','q+3<=128+priorReads'),
                ('q+2<=128','q+2<=128+priorReads'),('remaining=128-q','remaining=128+priorReads-q')]:
    chunk=chunk.replace(old,new)
if mode=='late_stride4':
    condition='inserted>=500 && inserted<=550'; phase='true'; offset=4; cap=16
elif mode=='late_half_midpoints':
    condition='inserted>=500 && inserted<=550'; phase='((cellLeft/8)&1)==0'; offset=4; cap=8
elif mode=='late_half_midpoints_odd':
    condition='inserted>=500 && inserted<=550'; phase='((cellLeft/8)&1)==1'; offset=4; cap=8
else:
    condition='inserted>=50 && inserted<=100'; phase='true'; offset=4; cap=16
anchor='''            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;'''
replacement=f'''            const long long previousBest=bestValue;
            const int cellLeft=rightmost;
            const int inserted=cellLeft+{offset};
            if (priorReads<{cap} && inserted<next && ({condition}) && ({phase})) {{
                fineAux[inserted]=1;
                if (!sample(inserted)) {{ coarseFrontier=rightmost; return; }}
                ++priorReads;
                if (certificate()) {{ coarseFrontier=rightmost; return; }}
            }}
            if (next<=rightmost || !sample(next)) break;'''
if chunk.count(anchor)!=1: raise RuntimeError('coarse read interface changed')
chunk=chunk.replace(anchor,replacement,1); text=text[:a]+chunk+text[b:]
name='prior_corridor_'+mode; path=OUT/(name+'.cpp'); raw=text.encode('utf-8')
if path.exists() and path.read_bytes()!=raw: raise RuntimeError('frozen candidate differs')
path.write_bytes(raw)
meta=dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
          source=str(path),sha256=hashlib.sha256(raw).hexdigest(),mode=mode,
          description=f'Preserve216258 structural8-grid. Insert one midpoint in selected prior cells ({mode}); exclude insertions from structural trend/noise, retain raw winner; cap{cap} extra reads.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
