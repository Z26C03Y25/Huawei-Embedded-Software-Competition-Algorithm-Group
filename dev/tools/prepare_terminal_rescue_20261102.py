"""Freeze a terminal-only rescue, retaining the confirmed search prefix."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
parent=ROOT/'data/versions/main_online_216258.cpp'
text=parent.read_text(encoding='utf-8-sig')
anchor='''        if (alive && best>=0 && pos!=best) readReal(best,true);'''
assert text.count(anchor)==1
new=r'''        int parking=best;
        // Activate only when the old implementation really would park at b.
        // If b<r-202, every t either violates R<=199 or has |b-t|>3.
        if (alive && best>=0 && best<rightmost-202 &&
            (pos==best || canRead(best,true))) {
            const int lo=max(0,rightmost-202);
            const vector<int> xs=observed();
            vector<pair<double,int>> ranked;
            for (int x=lo;x<=rightmost;++x) if (value[x]<0) {
                auto it=lower_bound(xs.begin(),xs.end(),x);
                if (it==xs.begin() || it==xs.end()) continue;
                const int a=*prev(it),b=*it;
                const double t=static_cast<double>(x-a)/(b-a);
                const double prediction=value[a]+t*(value[b]-value[a]);
                ranked.push_back({prediction,x});
            }
            sort(ranked.begin(),ranked.end(),[](const auto& a,const auto& b) {
                return a.first!=b.first ? a.first>b.first : a.second>b.second;
            });
            vector<int> probes;
            const int budget=max(0,QMAX-1-q);
            for (int i=0;i<min(budget,static_cast<int>(ranked.size()));++i)
                probes.push_back(ranked[i].second);
            sort(probes.rbegin(),probes.rend());
            if (routeSafe(probes)) for (int x:probes) if (!sample(x)) break;
            parking=-1;
            for (int x=lo;x<=rightmost;++x) {
                if (value[x]<0 || !canRead(x,true)) continue;
                if (parking<0 || better(x,value[x],parking,value[parking])) parking=x;
            }
            // A real final query keeps the rescue proof trace-auditable.
            if (parking>=0) readReal(parking,true);
        } else if (alive && best>=0 && pos!=best) readReal(best,true);'''
text=text.replace(anchor,new,1)
out=ROOT/'data/experiments/blackbox_20261102'
out.mkdir(parents=True,exist_ok=True)
p=out/'terminal_viable_window.cpp'
raw=text.encode('utf-8')
if p.exists() and p.read_bytes()!=raw: raise RuntimeError('Frozen candidate differs')
p.write_bytes(raw)
info=dict(name='terminal_viable_window',parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),source=str(p),sha256=hashlib.sha256(raw).hexdigest(),description='Keep216258 search prefix. Only when original final parking is legal and provably zero for every true target, use spare reads inside the existing viable window and park at a legal observed candidate. Never extend rightmost; Q/O/time/parking guards retained.')
p.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
