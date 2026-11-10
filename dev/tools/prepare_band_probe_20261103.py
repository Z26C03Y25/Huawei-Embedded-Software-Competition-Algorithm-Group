"""Freeze full-band scan or single-point probes; aggregate scores are experimental evidence."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/peak_prior_20261103'
lo,hi=map(int,sys.argv[1:3])
if not 0<=lo<=hi<1000 or hi-lo>190: raise ValueError('band out of bounds')
text=r'''#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    if(n<=HIGH){
        cout<<0<<endl;long long z;if(!(cin>>z))return 0;
        cout<<0<<endl;if(!(cin>>z))return 0;
        cout<<"DONE"<<endl;return 0;
    }
    int lo=min(LOW,n-1),hi=min(HIGH,n-1),winner=-1;
    long long top=-1;
    for(int x=lo;x<=hi;++x){
        cout<<x<<endl;
        long long v;if(!(cin>>v))return 0;
        if(v>top||(v==top&&(winner<0||abs(2*x-(n-1))<abs(2*winner-(n-1))||
            (abs(2*x-(n-1))==abs(2*winner-(n-1))&&x<winner)))){
            top=v;winner=x;
        }
    }
    if(winner!=hi){cout<<winner<<endl;long long v;if(!(cin>>v))return 0;}
    cout<<"DONE"<<endl;
}
'''.replace('LOW',str(lo)).replace('HIGH',str(hi))
name=f'band_probe_{lo}_{hi}';p=OUT/(name+'.cpp');raw=text.encode()
if p.exists() and p.read_bytes()!=raw:raise RuntimeError('immutable source')
p.write_bytes(raw)
parent=ROOT/'data/versions/main_online_216258.cpp'
meta=dict(parent=str(parent),source=str(p),sha256=hashlib.sha256(raw).hexdigest(),description=f'Scan every point{lo}..{hi}, park at tie-correct raw maximum. Diagnostic aggregate probe, intentionally zeros outside band; no claim of universal peak identification.')
p.with_suffix('.metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
print(json.dumps(meta))
