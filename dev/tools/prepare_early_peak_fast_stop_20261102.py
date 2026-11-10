"""Freeze a more decisive resolved early-peak stopping policy."""
from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'data/versions/main_online_216258.cpp'
OUT=ROOT/'data/experiments/blackbox_20261102'
text=PARENT.read_text(encoding='utf-8-sig')
old='''                if (f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound) {
                    const int observedTailBudget=max(16,static_cast<int>(ceil(1.5*f.halfRight)));
                    scout=min(max(16,scout/2),observedTailBudget);
                }'''
new='''                if (best<(n-1)/2 && f.halfLeft>0 && f.halfRight>0 &&
                    f.falls>=3 && f.rises==0 && !f.rebound) {
                    const int observedTailBudget=max(12,static_cast<int>(ceil(1.1*f.halfRight)));
                    scout=min(max(12,scout/3),observedTailBudget);
                } else if (f.halfLeft>0 && f.halfRight>0 && f.falls>=3 &&
                           f.rises==0 && !f.rebound) {
                    const int observedTailBudget=max(16,static_cast<int>(ceil(1.5*f.halfRight)));
                    scout=min(max(16,scout/2),observedTailBudget);
                }'''
if text.count(old)!=1: raise RuntimeError('resolved descent interface changed')
text=text.replace(old,new,1)
name='early_peak_fast_stop'
path=OUT/(name+'.cpp'); raw=text.encode('utf-8')
if path.exists() and path.read_bytes()!=raw: raise RuntimeError('frozen candidate differs')
path.write_bytes(raw)
meta=dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
          source=str(path),sha256=hashlib.sha256(raw).hexdigest(),
          description='More decisive parking only for resolved early peaks: when best is left of center, both half-height sides are observed, at least3 recent falls and no rise/rebound, reduce postpeak scout to one-third with12 minimum and1.1x observed right-half-width cap. All unresolved, competing, middle/right peaks retain frozen216258 policy.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
