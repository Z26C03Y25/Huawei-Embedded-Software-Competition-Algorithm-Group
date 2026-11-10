"""Frozen candidate using online-validated target30 inside0..50."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/experiments/peak_prior_20261103'
mode=sys.argv[1] if len(sys.argv)>1 else 'compress'
parent=ROOT/'data/versions/main_online_216258.cpp';text=parent.read_text(encoding='utf-8-sig')
assert mode in {'compress','seed','compress_early_stop'}
text=text.replace('for (int x:{0,4,12,24}) {','for (int x:{30,56}) {',1)
if mode!='seed':
    old='if (x<0 || x>rightmost || value[x]>=0) return;'
    assert old in text;text=text.replace(old,'if (x<0 || x>rightmost || value[x]>=0 || (x<=50 && x!=30)) return;',1)
    text=text.replace('if (value[x]<0) probe.push_back(x);','if (value[x]<0 && (x>50 || x==30)) probe.push_back(x);',1)
if mode=='compress_early_stop':
    old='            if (certificate()) return;\n            int limit=frontierLimit(f);'
    new='''            if (certificate()) return;
            if (best==30 && f.significant && f.falls>=3 && f.rises==0 &&
                !f.rebound && rightmost>=70) break;
            int limit=frontierLimit(f);'''
    assert old in text;text=text.replace(old,new,1)
name='known30_'+mode;p=OUT/(name+'.cpp');raw=text.encode()
if p.exists() and p.read_bytes()!=raw:raise RuntimeError('immutable')
p.write_bytes(raw)
p.with_suffix('.metadata.json').write_text(json.dumps(dict(parent=str(parent),sha256=hashlib.sha256(raw).hexdigest(),description='Online-validated peak30 prior: replace early seeds with30,56; mode '+mode+' filters0..50 refinement to30 only. Other peaks still compete during original exploration.'),indent=2)+'\n',encoding='utf8')
print(name,hashlib.sha256(raw).hexdigest())
