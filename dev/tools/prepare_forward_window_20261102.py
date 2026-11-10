"""Predict a near-forward peak, then read a bounded contiguous raw window."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
parent=ROOT/'data/versions/main_online_216258.cpp'
text=parent.read_text(encoding='utf-8-sig')
helper=r'''    optional<int> forwardPeakWindow(const Features& f) const {
        if (!f.significant || f.plateau || best!=rightmost ||
            f.noise>0.03*f.contrast) return nullopt;
        vector<int> knots;
        for (auto it=f.x.rbegin();it!=f.x.rend() && knots.size()<3;++it)
            if (knots.empty() || knots.back()-*it>=4) knots.push_back(*it);
        if (knots.size()!=3) return nullopt;
        const int a=knots[2],b=knots[1],c=knots[0];
        const double sl=static_cast<double>(value[b]-value[a])/(b-a);
        const double sr=static_cast<double>(value[c]-value[b])/(c-b);
        if (sr<=0 || sl<=sr) return nullopt;
        const double bend=(sr-sl)/(c-a);
        const double predicted=(a+b)/2.0-sl/(2*bend);
        if (!isfinite(predicted) || predicted<rightmost || predicted>rightmost+12)
            return nullopt;
        return min(n-1,max(rightmost+4,static_cast<int>(ceil(predicted))+3));
    }
'''
anchor='    void explore() {'
assert text.count(anchor)==1
text=text.replace(anchor,helper+anchor,1)
start=text.index(anchor); end=text.index('    optional<double> vertex',start)
chunk=text[start:end]
anchor='        int flatRuns=0, adjacentReads=0;'
assert chunk.count(anchor)==1
chunk=chunk.replace(anchor,anchor+'\n        int fineUntil=-1,fineReads=0,fineFalls=0,lastFineStart=-64;',1)
for a,b in [('q<128','q<128+fineReads'),('q+3<=128','q+3<=128+fineReads'),
            ('q+2<=128','q+2<=128+fineReads'),('remaining=128-q','remaining=128+fineReads-q')]:
    chunk=chunk.replace(a,b)
anchor='            int next=min({n-1,rightmost+step,limit});'
insert=r'''            if (fineReads<24 && fineUntil<=rightmost && rightmost-lastFineStart>=32) {
                if (auto predicted=forwardPeakWindow(f)) {
                    fineUntil=min(limit,*predicted);
                    lastFineStart=rightmost; fineFalls=0;
                }
            }
            const bool denseNow=fineReads<24 && rightmost<fineUntil;
            if (denseNow) step=1;
'''
assert chunk.count(anchor)==1
chunk=chunk.replace(anchor,insert+anchor,1)
anchor='''            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;'''
assert chunk.count(anchor)==1
chunk=chunk.replace(anchor,r'''            const long long previousBest=bestValue;
            const long long previousRaw=value[rightmost];
            if (next<=rightmost || !sample(next)) break;
            if (denseNow) {
                ++fineReads;
                fineFalls=value[next]<previousRaw ? fineFalls+1 : 0;
                if (fineFalls>=3) fineUntil=rightmost;
                else if (rightmost>=fineUntil && value[next]>previousRaw && fineReads<24)
                    fineUntil=min(limit,rightmost+4);
            }''',1)
anchor='if (((n>=539 && n<=613)) &&'
assert chunk.count(anchor)==1
chunk=chunk.replace(anchor,'if (!denseNow && ((n>=539 && n<=613)) &&',1)
text=text[:start]+chunk+text[end:]
p=ROOT/'data/experiments/blackbox_20261102/forward_peak_window.cpp'; raw=text.encode('utf-8')
if p.exists() and p.read_bytes()!=raw: raise RuntimeError('Frozen source differs')
p.write_bytes(raw)
info=dict(parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),description='User forward-fine idea: rising deceleration predicts a peak within12 cells, enter step1 window through predicted+3; stop dense mode after3 raw declines, extend4 when still rising, total24 dense reads maximum. Charge dense reads separately against128 anchor budget, retain fine/parking reserve and original right boundary.')
p.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
