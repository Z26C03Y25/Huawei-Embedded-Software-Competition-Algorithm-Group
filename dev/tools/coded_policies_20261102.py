"""Orthogonal aggregate-score experiments with pure N-based policy routing."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261102'
SOURCES={'cv':'cross_validated_models.cpp','tour':'beam_interval_tour.cpp',
         'batch':'batched_validated_cells.cpp','paired':'paired_lattice_long.cpp'}

def generate(family,mask):
    if family not in SOURCES or not 0<mask<15:
        raise ValueError('Only distinct mixed policies; never resubmit all-A or all-B')
    parent=ROOT/'data/versions/main_online_216258.cpp'
    component=OUT/SOURCES[family]
    a=parent.read_text(encoding='utf-8-sig'); b=component.read_text(encoding='utf-8-sig')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    index=json.loads((ROOT/'data/versions/online_search/results.json').read_text(encoding='utf-8'))
    bindings=[r for r in index if r.get('sha256')==sha(component) and type(r.get('score')) is int]
    if not bindings: raise RuntimeError('Component has no confirmed official total')
    if b.count('namespace af {')!=1: raise RuntimeError('Unsupported component namespace')
    a=a[:a.rindex('int main(')]
    b=b[:b.rindex('int main(')].replace('namespace af {','namespace coded_alternative {',1)
    entry=r'''
int main(int argc,char** argv) {
    ios::sync_with_stdio(false); cin.tie(nullptr);
    bool trace=false,strict=false,late=false;
    for (int i=1;i<argc;++i) {
        const string arg=argv[i];
        if (arg=="--trace") trace=true;
        else if (arg=="--strict-redundancy") strict=true;
        else if (arg=="--late-flat") late=true;
    }
    int n;
    if (!(cin>>n) || n<=0 || n>1000) return 0;
    const int group=n<=500 ? 0 : (n<=650 ? 1 : (n<=800 ? 2 : 3));
    constexpr unsigned mask=MASK_VALUE;
    if ((mask & (1u<<group))!=0) {
        coded_alternative::Protocol wire(n);
        coded_alternative::Solver(n,trace,strict,late,wire).run();
    } else {
        af::Protocol wire(n);
        af::Solver(n,trace,strict,late,wire).run();
    }
}
'''.replace('MASK_VALUE',str(mask))
    text=a+'\n'+b+'\n'+entry
    name=f'coded_{family}_{mask}'
    p=OUT/(name+'.cpp'); raw=text.encode('utf-8')
    if p.exists() and p.read_bytes()!=raw: raise RuntimeError('Frozen mixture differs')
    p.write_bytes(raw)
    info=dict(name=name,parent=str(parent),parent_sha256=sha(parent),sha256=sha(p),
              component=str(component),component_sha256=sha(component),component_score=bindings[-1]['score'],
              mask=mask,groups=['N<=500','501..650','651..800','801..1000'],
              description='New deterministic mixed policy: only mask-selected N groups run frozen component B; others run frozen216258 A. Single N read and direct solver dispatch preserve each expert trajectory/RNG. Masks5,3,9 plus existing all-B total identify4 group contributions by Hadamard inversion.')
    p.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(info,ensure_ascii=False))

def fit(family):
    rows=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
    data={}
    for mask in [5,3,9]:
        matching=[r for r in rows if r['name']==f'coded_{family}_{mask}' and r['state']=='completed']
        if not matching: raise RuntimeError('Missing confirmed code mask '+str(mask))
        data[mask]=matching[-1]['score']-216258
    meta=json.loads((OUT/f'coded_{family}_5.metadata.json').read_text(encoding='utf-8'))
    total=meta['component_score']-216258
    z=[total,2*data[5]-total,2*data[3]-total,2*data[9]-total]
    hadamard=[[1,1,1,1],[1,-1,1,-1],[1,1,-1,-1],[1,-1,-1,1]]
    numerators=[sum(z[r]*hadamard[r][i] for r in range(4)) for i in range(4)]
    if any(x%4 for x in numerators): raise RuntimeError('Nonintegral inversion: audit attribution/determinism')
    gains=[x//4 for x in numerators]
    positiveMask=sum(1<<i for i,g in enumerate(gains) if g>0)
    result=dict(family=family,total_delta=total,group_deltas=gains,positive_mask=positiveMask,
                predicted_score=216258+sum(max(0,g) for g in gains),
                note='Group contributions inferred from aggregate official totals; a new positive mixture needs direct official grading unless already scored.')
    (OUT/f'coded_{family}_fit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1]=='fit': fit(sys.argv[2])
    else: generate(sys.argv[1],int(sys.argv[2]))
