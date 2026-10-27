"""Protocol audit on fresh diverse curves, retaining failures and exact trajectories.
Not a candidate-selection benchmark and not an official-score prediction.
"""
from pathlib import Path
import concurrent.futures, hashlib, json, math, random, sys, time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev'));sys.path.insert(0,str(ROOT/'automation'))
from tools.local_judge import Case,run_case,make_suite
from tools.mixed_scenarios import make_scenarios
from online_judge.jobs import SubmissionLock
OUT=ROOT/'dev/build/protocol_audit_20261027'
PUBLIC=ROOT/'data/experiments/protocol_audit_20261027'
SEED=20261026405

def save(p,v):
    t=p.with_suffix('.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(p)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    original=ROOT/'dev/build/protocol_original_checked.exe'
    hardened=ROOT/'dev/build/protocol_hardened_checked.exe'
    assert original.exists() and hardened.exists()
    cases=make_scenarios(per_family=14,seed_tag=SEED,novel=True)
    cases.extend((c,dict(transform='control',cluster=c.name)) for c in make_suite('extended'))
    rng=random.Random(20261027001)
    for j in range(140):
        n=(400,401,999,1000)[j%4];mode=j%7
        if mode==0:values=[rng.choice((0,1,2147483646,2147483647)) for _ in range(n)]
        elif mode==1:values=[2147483647-rng.randrange(4) for _ in range(n)]
        elif mode==2:values=[rng.randrange(4) for _ in range(n)]
        elif mode==3:values=[max(0,2147483647-1000*abs(i-rng.randrange(n))) for i in range(n)]
        elif mode==4:values=[(i%2)*2147483647 for i in range(n)]
        elif mode==5:values=[min(2147483647,1000000000+(i//9)*10000+rng.randrange(3)) for i in range(n)]
        else:
            center=rng.randrange(n);values=[max(0,2147483647-1000000*(i-center)**2) for i in range(n)]
        c=Case(f'extreme_{j:03d}',tuple(values),'protocol_extreme')
        cases.append((c,dict(transform='control',cluster=c.name)))
    unique=[];seen=set()
    for c,m in cases:
        digest=hashlib.sha256(json.dumps(c.values,separators=(',',':')).encode()).hexdigest()
        if digest not in seen:unique.append((c,m,digest));seen.add(digest)
    rows=[];started=time.monotonic()
    def run(item):
        c,m,digest=item
        old=run_case([str(original)],c);new=run_case([str(hardened)],c)
        return dict(name=c.name,family=c.family,metadata=m,values=list(c.values),array_sha256=digest,original=old,hardened=new)
    with SubmissionLock(ROOT/'automation/online_judge/runs/.offline-research.lock'):
        statepath=ROOT/'data/experiments/research_state.json';state=json.loads(statepath.read_text(encoding='utf-8-sig'))
        state.update(phase='2026_10_27_protocol_audit_running',active_offline_pipeline='dev/tools/audit_protocol.py',next_action='Finish fresh protocol audit; do not upload until audited candidate and genuine failure analysis are recorded.');save(statepath,state)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            for row in pool.map(run,unique):
                rows.append(row)
                if len(rows)%100==0:
                    save(OUT/'checkpoint.json',dict(seed=SEED,done=len(rows),planned=len(unique),failures=[r['name'] for r in rows if r['original']['status']!='ok' or r['hardened']['status']!='ok']))
                    print(json.dumps(dict(done=len(rows),planned=len(unique),elapsed=round(time.monotonic()-started,1))),flush=True)
        failures=[];changed=[]
        for row in rows:
            for name in ['original','hardened']:
                r=row[name]
                if r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or r['messages']!=r['queries']+1:
                    failures.append(dict(name=row['name'],solver=name,status=r['status'],error=r['error']))
            if row['original']['query_positions']!=row['hardened']['query_positions'] or row['original']['score']!=row['hardened']['score']:
                changed.append(row['name'])
        summary=dict(seed=SEED,unique_arrays=len(rows),fresh_base_cases=sum(r['metadata'].get('transform')=='base' for r in rows),interactive_runs=len(rows)*2,original_protocol_failures=sum(r['original']['status']!='ok' for r in rows),hardened_protocol_failures=sum(r['hardened']['status']!='ok' for r in rows),failures=failures,changed_trajectories_or_scores=changed,max_queries=max(r['hardened']['queries'] for r in rows),max_messages=max(r['hardened']['messages'] for r in rows),max_oscillations=max(r['hardened']['oscillations'] for r in rows),max_elapsed_seconds=max(r['hardened']['elapsed_seconds'] for r in rows),original_internal_error_reproduced=any(r['original']['status']!='ok' for r in rows),root_cause='not established unless a saved real failing trace is found',online_qualified=False)
        save(OUT/'report.json',dict(summary=summary,rows=rows));save(PUBLIC/'audit_summary.json',summary)
        state=json.loads(statepath.read_text(encoding='utf-8-sig'));state.pop('active_offline_pipeline',None);state.update(phase='2026_10_27_protocol_audit_complete',protocol_audit='data/experiments/protocol_audit_20261027/audit_summary.json',next_action='Read protocol audit and exception tests; retain original failure. No duplicate A or backup B. Protocol hardening alone does not establish the original root cause.');state['latest_consumed_mixed_seed']=SEED;state['next_unused_mixed_seed']=SEED+1;save(statepath,state)
        print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
