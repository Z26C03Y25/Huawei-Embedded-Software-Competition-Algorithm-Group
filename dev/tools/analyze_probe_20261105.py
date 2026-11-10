"""Decode fixed-zero N code, preserving ambiguity rather than fitting one answer."""
import json,sys
from pathlib import Path
p=int(sys.argv[1]);score=int(sys.argv[2]);count=int(sys.argv[3]) if len(sys.argv)>3 else 1
assert 66<=p<=395 and count in {1,2}
exclude={401,454,797,829,978}
def code(n):
 z=n-400;c,r=divmod(z,193)
 return c*(2*p+62)+r
loss=count*(2999-p)-score
lookup={code(n):n for n in range(400,1001) if n not in exclude}
if count==1:
 ns=[lookup[loss]] if loss in lookup else []
 result=dict(point=p,score=score,count=count,loss=loss,possible_lengths=ns)
else:
 pairs=[]
 for d,n in lookup.items():
  m=lookup.get(loss-d)
  if m is not None and n<=m:pairs.append([n,m])
 sums=sorted(set(a+b for a,b in pairs))
 result=dict(point=p,score=score,count=count,loss=loss,pair_count=len(pairs),possible_sums=sums,partition_threshold=sums[0]//2 if len(sums)==1 else None,pairs=pairs)
path=Path(__file__).resolve().parents[2]/f'data/experiments/blackbox_20261105/decode_{p}_{score}_{count}.json'
path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='pairs'}))
