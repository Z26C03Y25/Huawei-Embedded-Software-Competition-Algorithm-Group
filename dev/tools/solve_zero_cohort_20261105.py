"""Solve all observed constraints, retaining all feasible five-N multisets."""
from pathlib import Path
import json,subprocess
R=Path(__file__).resolve().parents[2];O=R/'data/experiments/blackbox_20261105'
s=json.loads((O/'state.json').read_text(encoding='utf-8'))
def score(name):
 rows=[r for r in s['rounds'] if r['name']==name and r['state']=='completed']
 if len(rows)!=1 or type(rows[0].get('score')) is not int:raise RuntimeError('Missing unique confirmed observation:'+name)
 return rows[0]['score']
base=score('oracle_495_525_base');count=base-score('oracle_495_525_count');q=base-score('oracle_495_525_quot8');rem=base-score('oracle_495_525_rem8')
assert count==5 and 0<=q<=375 and 0<=rem<=35
Nsum=400*count+8*q+rem
hs=[base-score(f'oracle_495_525_nhash_{k}') for k in [1,2,3]]
assert all(0<=v<=315 for v in hs)
args=[str(Nsum),str(q)]
for k,v in enumerate(hs,1):args.extend([str(k),str(v)])
r=subprocess.run([str(R/'dev/tmp/decode_zero_Ns_20261105.exe'),*args],capture_output=True,text=True,timeout=90)
if r.returncode:raise RuntimeError('Decoder failed')
a=json.loads(r.stdout);a['observations']=dict(base=base,count=count,quotient_sum=q,remainder_sum=rem,length_sum=Nsum,hash_sums=hs)
(O/'zero_N_candidates.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(observations=a['observations'],candidate_count=len(a['solutions']),first_candidates=a['solutions'][:15]),ensure_ascii=False))
if not a['solutions']:raise RuntimeError('No consistent N set: audit cohort/prefix before more uploads')
mask=(1<<64)-1
def h(n,seed):
 z=(n+seed*0x9e3779b97f4a7c15)&mask;z=((z^(z>>30))*0xbf58476d1ce4e5b9)&mask;z=((z^(z>>27))*0x94d049bb133111eb)&mask
 return(z^(z>>31))&63
if len(a['solutions'])>1:
 best=None
 for seed in range(4,10004):
  signatures=[sum(h(n,seed) for n in ns) for ns in a['solutions']]
  unique=len(set(signatures))
  if best is None or unique>best['distinct_outcomes']:best=dict(seed=seed,distinct_outcomes=unique,signatures=signatures)
  if unique==len(signatures):break
 (O/'adaptive_hash_plan.json').write_text(json.dumps(best,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(adaptive_seed=best['seed'],distinct_outcomes=best['distinct_outcomes'],candidate_count=len(a['solutions']))))
