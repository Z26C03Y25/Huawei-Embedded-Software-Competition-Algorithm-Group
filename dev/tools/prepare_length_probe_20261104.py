"""Freeze a singleton length-encoding probe; only repeated stationary reads vary."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261104'
p=int(sys.argv[1]);mode=sys.argv[2]
threshold={30:50,202:209,213:225,586:600,662:700,774:800}[p]
if mode not in {'quarter','rem4'}:raise ValueError(mode)
expression='(n-400)/4' if mode=='quarter' else '(n-400)%4'
text=r'''#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    const int point=n>THRESHOLD ? POINT : 0;
    const int padding=n>THRESHOLD ? max(0,EXPRESSION) : 0;
    for(int k=0;k<=padding;++k) {
        cout<<point<<endl;
        long long value;if(!(cin>>value))return 0;
    }
    cout<<"DONE"<<endl;
}
'''.replace('THRESHOLD',str(threshold)).replace('POINT',str(p)).replace('EXPRESSION',expression)
name=f'length_{p}_{mode}';path=OUT/(name+'.cpp');raw=text.encode()
if path.exists() and path.read_bytes()!=raw:raise RuntimeError('Immutable source')
path.write_bytes(raw)
meta=dict(parent=str(ROOT/'data/versions/main_online_216258.cpp'),source=str(path),sha256=hashlib.sha256(raw).hexdigest(),
          description=f'Singleton length probe at{p}, matching original N>{threshold} eligibility. Repeat stationary point floor((N-400)/4) or residue%4 extra times. Max151 queries, no travel/turn/redundancy change; sole scoring case total difference decodes length component. Compare measured singleton baseline before any assumption.')
path.with_suffix('.metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
print(json.dumps(meta))
