from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/experiments/peak_prior_20261103'
point=int(sys.argv[1]);assert 0<point<400
text=r'''#include <bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    cout<<0<<endl;long long a;if(!(cin>>a))return 0;
    const int p=min(POINT,n-1);
    cout<<p<<endl;long long b;if(!(cin>>b))return 0;
    const bool win=b>a||(b==a&&abs(2*p-(n-1))<abs(n-1));
    if(!win){cout<<0<<endl;long long c;if(!(cin>>c))return 0;}
    cout<<"DONE"<<endl;
}
'''.replace('POINT',str(point))
name=f'point_compare_0_{point}';p=OUT/(name+'.cpp');raw=text.encode()
if p.exists() and p.read_bytes()!=raw:raise RuntimeError('immutable')
p.write_bytes(raw);parent=ROOT/'data/versions/main_online_216258.cpp'
p.with_suffix('.metadata.json').write_text(json.dumps(dict(parent=str(parent),sha256=hashlib.sha256(raw).hexdigest(),description=f'Read0 and{point}; park higher with correct tie. User-directed test of single-query zero hypothesis.'),indent=2)+'\n',encoding='utf8')
print(name,hashlib.sha256(raw).hexdigest())
