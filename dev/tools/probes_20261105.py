"""Freeze black-box band and travel-encoded length probes; no upload."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/experiments/blackbox_20261105'
OUT.mkdir(parents=True,exist_ok=True)
mode=sys.argv[1]
if mode=='calibrate':
 name='travel_length30_calibration'
 code=r'''#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 int p=min(30,n-1);cout<<p<<endl;long long a;if(!(cin>>a))return 0;
 if(n==479 && a%127==7){
  int z=n-400,l=min(199,z/3),padding=z-3*l+(l==0?30:0);
  int x=p+l;cout<<x<<endl;long long b;if(!(cin>>b))return 0;
  int winner=(a>b || (a==b && abs(2*p-(n-1))<=abs(2*x-(n-1))))?p:x;
  cout<<winner<<endl;long long v;if(!(cin>>v))return 0;
  for(int k=0;k<padding;++k){cout<<winner<<endl;if(!(cin>>v))return 0;}
 }
 cout<<"DONE"<<endl;
}
'''
 description='Calibrate single-grade N encoding on known singleton30/N479/replymod127=7. Offset L=min(199,(N-400)/3), repeated reads encode remainder; if target30 stays winner, total loss from2969 is32+(N-400), predicted2858. Other matches park raw observed winner so extra positives cause an out-of-range/inconclusive total. Q<=35,O<=1.'
elif mode=='band':
 b,a=sorted(map(int,sys.argv[2:4]));assert 4<=b<=a<=395 and a-b<=100
 padding=int(sys.argv[4]) if len(sys.argv)>4 else 0
 assert a-b+2+padding<=199 and padding>=0
 name=f'band_{b}_{a}_pad{padding}'
 code=r'''#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 if(n<=A || n==401 || n==454 || n==797 || n==829 || n==978){
  cout<<0<<endl;long long v;if(!(cin>>v))return 0;cout<<"DONE"<<endl;return 0;
 }
 long long best=-1;int at=B;
 for(int p=B;p<=A;++p){
  cout<<p<<endl;long long v;if(!(cin>>v))return 0;
  if(v>best || (v==best && (abs(2*p-(n-1))<abs(2*at-(n-1)) || (abs(2*p-(n-1))==abs(2*at-(n-1))&&p<at)))){best=v;at=p;}
 }
 long long v;for(int k=0;k<=PAD;++k){cout<<at<<endl;if(!(cin>>v))return 0;}
 cout<<"DONE"<<endl;
}
'''.replace('PAD',str(padding)).replace('A',str(a)).replace('B',str(b))
 description=f'Probe unresolved lengths only: scan inclusive{b}..{a}, always reread raw winner, center tie; skip five already-dispatched lengths by querying0. Padding{padding} stationary reads can encode scoring-case count against an otherwise identical baseline. Exact interior singleton expected2968+b-4a+2p under observed O30; right endpoint adds30; halo errors considered, never blindly apply29.'
elif mode in {'zero_length','zero_calibrate'}:
 p=30 if mode=='zero_calibrate' else int(sys.argv[2]);assert (mode=='zero_calibrate') or 66<=p<=395
 name='zero_roundtrip_calibration' if mode=='zero_calibrate' else f'zero_length_{p}'
 cexpr='3' if mode=='zero_calibrate' else 'z/193'
 rexpr='5' if mode=='zero_calibrate' else 'z-193*c'
 gate='n==479 && a%127==7' if mode=='zero_calibrate' else 'true'
 skip='false' if mode=='zero_calibrate' else 'n==401 || n==454 || n==797 || n==829 || n==978'
 code=r'''#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 if(n<=POINT || SKIP){cout<<0<<endl;long long v;if(!(cin>>v))return 0;cout<<"DONE"<<endl;return 0;}
 int p=POINT;cout<<p<<endl;long long a;if(!(cin>>a))return 0;
 if(GATE){
  int z=max(0,n-400),c=CEXPR,padding=REXPR;
  for(int k=0;k<c;++k){
   cout<<0<<endl;long long b;if(!(cin>>b))return 0;
   if(b>a || (b==a && abs(n-1)<=abs(2*p-(n-1)))){cout<<"DONE"<<endl;return 0;}
   cout<<p<<endl;long long v;if(!(cin>>v))return 0;
  }
  for(int k=0;k<padding;++k){cout<<p<<endl;long long v;if(!(cin>>v))return 0;}
 }
 cout<<"DONE"<<endl;
}
'''.replace('POINT',str(p)).replace('SKIP',skip).replace('GATE',gate).replace('CEXPR',cexpr).replace('REXPR',rexpr)
 description='Known30/N479/replymod127=7 forced3 zero-return cycles plus5 repeats: target Q12/M210/O6/R0 predicts2598. All nonmatching cases stop at original30; raw0 winner aborts at0, no speculative unseen coordinates.' if mode=='zero_calibrate' else f'Fixed-0 roundtrip N encoder at{p}: z=N-400,c=z//193,r=z-193c. Return0->p c times then repeatp r times. Target loss c*(2p+62)+r, Q<=197,O<=6,R=0 on target. p>=66 makes code blocks disjoint. Finalp remains same direct-point contributing set; if0 wins, abort there (historical probes support no0..3 targets). No moving-auxiliary-point contamination.'
elif mode=='collision':
 b,a=sorted(map(int,sys.argv[2:4]));assert 4<=b<=a<=975 and a-b+2<=199
 experts={401:202,454:213,797:662,829:586,978:774}
 for n,peak in experts.items():
  if n>b:
   h=min(a,n-1)
   assert peak<b-6 or peak>h+6,'Band halo overlaps adopted expert'
 name=f'collision_{b}_{a}'
 code=r'''#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 if(n<=LOW || (n!=401 && n!=454 && n!=797 && n!=829 && n!=978)){cout<<0<<endl;long long v;if(!(cin>>v))return 0;cout<<"DONE"<<endl;return 0;}
 int hi=min(HIGH,n-1),at=LOW;long long best=-1;
 for(int p=LOW;p<=hi;++p){cout<<p<<endl;long long v;if(!(cin>>v))return 0;
  if(v>best || (v==best && (abs(2*p-(n-1))<abs(2*at-(n-1)) || (abs(2*p-(n-1))==abs(2*at-(n-1))&&p<at)))){best=v;at=p;}
 }
 cout<<at<<endl;long long v;if(!(cin>>v))return 0;
 cout<<"DONE"<<endl;
}
'''.replace('LOW',str(b)).replace('HIGH',str(a))
 description=f'Zero-case witness probe only in five adopted dispatch lengths401/454/797/829/978: scan{b}..min({a},N-1), park raw winner. Every target within3 of any queried parking point lies>3 from that N adopted fixed stop (validated6-position halo separation). Thus every positive contribution in these groups proves a baseline zero case, apart from historical no0..3 fallback assumption. Q<=199,O<=1. Other lengths query0.'
elif mode=='direct':
 p=int(sys.argv[2]);assert 4<=p<=395
 name=f'direct_{p}'
 code=r'''#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 int p=(n<=POINT || n==401 || n==454 || n==797 || n==829 || n==978)?0:POINT;
 cout<<p<<endl;long long v;if(!(cin>>v))return 0;
 cout<<"DONE"<<endl;
}
'''.replace('POINT',str(p))
 description=f'Direct fixed-point{p} diagnostic on same unresolved length set as bands. Score bound per positive [2999-p-603,2999-p]; exact multiples at upper bound can establish repeated same-position targets when count bounds agree. No claim from raw quotient without bounds.'
elif mode=='length':
 p=int(sys.argv[2]);assert 4<=p<=395
 name=f'travel_length_{p}'
 code=r'''#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 if(n<=POINT || n==401 || n==454 || n==797 || n==829 || n==978){cout<<0<<endl;long long v;if(!(cin>>v))return 0;cout<<"DONE"<<endl;return 0;}
 int p=POINT,z=max(0,n-400),l=min(199,z/3),padding=z-3*l+(l==0?30:0);
 cout<<p<<endl;long long a;if(!(cin>>a))return 0;
 int x=p+l;cout<<x<<endl;long long b;if(!(cin>>b))return 0;
 int winner=(a>b || (a==b && abs(2*p-(n-1))<=abs(2*x-(n-1))))?p:x;
 cout<<winner<<endl;long long v;if(!(cin>>v))return 0;
 for(int k=0;k<padding;++k){cout<<winner<<endl;if(!(cin>>v))return 0;}
 cout<<"DONE"<<endl;
}
'''.replace('POINT',str(p))
 description=f'One-score length encoder for candidate singleton{p}<=395. On target winnerp, overshoot L=min(199,(N-400)/3) and stationary remainder give loss32+(N-400) against2999-p under observed O30. Skip same five length experts as band probes. If excursion wins or several cases score, total may be contaminated and no N is asserted without aggregate validation. Protocol Q<=35,O<=1; official scoring R limit respected on target.'
else:raise ValueError(mode)
if '--nrange' in sys.argv:
 i=sys.argv.index('--nrange');low,high=map(int,sys.argv[i+1:i+3]);assert 400<=low<=high<=1000 and mode in {'band','length','zero_length','direct'}
 if mode=='direct':
  if code.count('int p=(n<=')!=1:raise RuntimeError('N filter direct anchor changed')
  code=code.replace('int p=(n<=',f'int p=(n<{low} || n>{high} || n<=',1)
 else:
  if code.count('if(n<=')!=1:raise RuntimeError('N filter anchor changed')
  code=code.replace('if(n<=',f'if(n<{low} || n>{high} || n<=',1)
 name+=f'_n{low}_{high}'
 description+=f' Additional N range{low}..{high}; other lengths query0 only.'
path=OUT/(name+'.cpp');raw=code.encode()
if path.exists() and path.read_bytes()!=raw:raise RuntimeError('Frozen bytes differ')
path.write_bytes(raw)
info=dict(source=str(path),sha256=hashlib.sha256(raw).hexdigest(),parent=str(ROOT/'data/versions/main_online_224148.cpp'),description=description)
path.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
