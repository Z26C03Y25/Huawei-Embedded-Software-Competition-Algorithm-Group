"""Local raw concavity closure: a heuristic with explicit evidence gates."""
from pathlib import Path
import json,sys,importlib.util
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
state=json.loads((D/'session.json').read_text(encoding='utf-8'));b=max(state['results'],key=lambda r:r['score']);parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
records=[]
for span in (3,4):
    method='''    bool rawConcavityClosed() {
        if (best<SPAN || best+SPAN>rightmost || bestValue==VMAX) return false;
        for (int x=best-SPAN;x<=best+SPAN;++x) if (value[x]<0) return false;
        long long lo=VMAX*4, hi=0;
        for (int x=best-SPAN+1;x<best+SPAN;++x) {
            const long long bend=2*value[x]-value[x-1]-value[x+1];
            if (bend<=0) return false;
            lo=min(lo,bend);hi=max(hi,bend);
        }
        if (hi>3*lo) return false;
        Features evidence=features();
        if (evidence.flat || evidence.plateau || evidence.noisy || !evidence.significant) return false;
        for (int x:evidence.peaks)
            if (abs(x-best)>32 && value[x]>bestValue-0.25*evidence.contrast) return false;
        return true; // Local model evidence, not a global maximum certificate.
    }
'''.replace('SPAN',str(span))
    edits=[('    void refine() {',method+'    void refine() {'),('                progress=true;\n                if (certificate()) return;','                progress=true;\n                if (certificate() || rawConcavityClosed()) return;')]
    item=derive(f'raw_concavity{span}',parent,edits,f'After real fine samples stop only with complete raw +/-{span} strict concavity, comparable curvature, low noise and no observed competitor; heuristic global risk remains',dict(raw_concavity_span=span,raw_concavity_ratio=3))
    item['offline']=d.validate(item);records.append(item);d.save(D/'concavity_screening.json',records);print(json.dumps(dict(name=item['name'],**item['offline'])),flush=True)
