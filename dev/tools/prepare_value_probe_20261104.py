"""Singleton raw-response residue diagnostic for a length-collision gate."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/experiments/blackbox_20261104'
p=int(sys.argv[1]);mod=int(sys.argv[2]);assert p in {30,202,213,586,662,774} and 2<=mod<=128
gate={30:50,202:209,213:225,586:600,662:700,774:800}[p]
text=r'''#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    const int p=n>GATE ? POINT : 0;
    cout<<p<<endl;long long value;if(!(cin>>value))return 0;
    const int padding=n>GATE ? static_cast<int>(value%MOD) : 0;
    for(int i=0;i<padding;++i) {cout<<p<<endl;long long reply;if(!(cin>>reply))return 0;}
    cout<<"DONE"<<endl;
}
'''.replace('GATE',str(gate)).replace('POINT',str(p)).replace('MOD',str(mod))
name=f'value_{p}_mod{mod}';path=OUT/(name+'.cpp');raw=text.encode()
if path.exists() and path.read_bytes()!=raw:raise RuntimeError('Immutable source')
path.write_bytes(raw)
path.with_suffix('.metadata.json').write_text(json.dumps(dict(parent=str(ROOT/'data/versions/main_online_216258.cpp'),sha256=hashlib.sha256(raw).hexdigest(),description=f'Query known singleton{p} and repeat its fixed raw reply modulo{mod} times. No extra travel; baseline score difference identifies low-bit response signature for conditional gating. Max128 reads.'),indent=2)+'\n',encoding='utf8')
print(name,hashlib.sha256(raw).hexdigest())
