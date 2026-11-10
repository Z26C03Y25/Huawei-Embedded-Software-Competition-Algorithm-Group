"""Freeze a corridor sampler using the revealed 102-target position histogram."""
from pathlib import Path
import hashlib, json, sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/peak_prior_20261102'
OUT.mkdir(parents=True,exist_ok=True)
PARENT=ROOT/'data/versions/main_online_216258.cpp'
SKETCH=ROOT/'data/experiments/blackbox_20261102/forward_peak_sketch.cpp'

mode=sys.argv[1] if len(sys.argv)>1 else 'both'
if mode not in {'both','early','late'}: raise ValueError(mode)
corridor_expr={
    'both':'(x>=50 && x<=100) || (x>=500 && x<=550)',
    'early':'x>=50 && x<=100',
    'late':'x>=500 && x<=550',
}[mode]
name={'both':'prior_corridor_stride2','early':'prior_corridor_early_stride2',
      'late':'prior_corridor_late_stride2'}[mode]

text=PARENT.read_text(encoding='utf-8-sig')
sketch=SKETCH.read_text(encoding='utf-8-sig')

# Keep inserted corridor samples out of the structural residual/slope sketch,
# while retaining them as raw maximum and refinement candidates.
a=text.index('    Features features() {')
b=text.index('    bool coarseRivalEvidence(',a)
sa=sketch.index('    Features features() {')
sb=sketch.index('    bool coarseRivalEvidence(',sa)
text=text[:a]+sketch[sa:sb]+text[b:]
text=text.replace('    vector<long long> value;',
                  '    vector<long long> value;\n    vector<unsigned char> fineAux;',1)
text=text.replace(': wire(transport),n(length),value(length,-1),trace(diagnostics)',
                  ': wire(transport),n(length),value(length,-1),fineAux(length,0),trace(diagnostics)',1)

a=text.index('    void explore() {')
b=text.index('    optional<double> vertex',a)
chunk=text[a:b]
chunk=chunk.replace('        int flatRuns=0, adjacentReads=0;',
                    '        int flatRuns=0, adjacentReads=0,priorReads=0;',1)
for old,new in [('q<128','q<128+priorReads'),
                ('q+3<=128','q+3<=128+priorReads'),
                ('q+2<=128','q+2<=128+priorReads'),
                ('remaining=128-q','remaining=128+priorReads-q')]:
    chunk=chunk.replace(old,new)

anchor='''            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;'''
replacement='''            const long long previousBest=bestValue;
            const int cellLeft=rightmost;
            // Preserve the original8-position anchor trajectory. In the two
            // high-mass target corridors, fill only the even phase positions
            // before reading the same anchor. Insertions are monotone, add no
            // travel, and are excluded from structural noise/trend estimates.
            auto inPriorCorridor=[](int x) {
                return CORRIDOR_EXPR;
            };
            for (int x=cellLeft+2;x<next && priorReads<40;++x) {
                if (!inPriorCorridor(x) || ((x-cellLeft)&1)) continue;
                fineAux[x]=1;
                if (!sample(x)) { coarseFrontier=rightmost; return; }
                ++priorReads;
                if (certificate()) { coarseFrontier=rightmost; return; }
            }
            if (next<=rightmost || !sample(next)) break;'''
if chunk.count(anchor)!=1: raise RuntimeError('coarse read interface changed')
chunk=chunk.replace(anchor,replacement,1)
chunk=chunk.replace('CORRIDOR_EXPR',corridor_expr)
text=text[:a]+chunk+text[b:]

path=OUT/(name+'.cpp'); raw=text.encode('utf-8')
if path.exists() and path.read_bytes()!=raw: raise RuntimeError('frozen candidate differs')
path.write_bytes(raw)
meta=dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
          source=str(path),sha256=hashlib.sha256(raw).hexdigest(),
          histogram={'50_100':29,'500_550':32,'total':102},mode=mode,
          description='Preserve216258 step8 structural anchors and all stop/refine logic. Monotonically insert stride2 raw samples only inside target-position prior corridor mode '+mode+'. Tag inserts out of structural noise/trend sketch; raw maxima and refinement still see them. At most40 extra reads, charged outside128 anchor budget, leaving parking reserve.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
