"""Sequential, resumable online policy optimization explicitly requested by user.

Only judge.py uploads. Every score is bound to its immutable snapshot. Stops on
200000, the displayed daily quota, or an unresolved delivery/authentication error.
The queue can be edited between trials; completed names are never repeated.
"""
from pathlib import Path
import json
import importlib
import os
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
sys.path.insert(0, str(ROOT / "automation"))
from tools.policy_search import generate,record,OUT
import tools.policy_search as policies
from tools.local_judge import make_suite,run_case
from online_judge.browser import connect,load_config

PY=ROOT/"automation/online_judge/.venv/Scripts/python.exe"
JUDGE=ROOT/"automation/online_judge/judge.py"
QUEUE=OUT/"queue.json"
STATE=OUT/"controller.json"


def emit(**data):
    print(json.dumps(data,ensure_ascii=False),flush=True)


def save(state):
    p=STATE.with_suffix('.tmp')
    p.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    p.replace(STATE)


def quota():
    cfg=load_config()
    with connect(cfg) as adapter:
        text=adapter.page.locator('body').inner_text()
        found=re.search(r'每日可上传\s*(\d+)\s*次.*?已经上传\s*(\d+)\s*次',text,re.S)
        if not found:
            raise RuntimeError('Cannot read a displayed upload quota; no upload attempted')
        limit,used=map(int,found.groups())
        return {'limit':limit,'used':used,'remaining':max(0,limit-used)}


def jobs_for(digest):
    result=[]
    for p in (ROOT/'automation/online_judge/runs').glob('*/job.json'):
        j=json.loads(p.read_text(encoding='utf-8'))
        if j['sha256']==digest: result.append(j)
    return sorted(result,key=lambda j:j['created_at'])


def invoke(arguments):
    p=subprocess.run([str(PY),str(JUDGE),*arguments],cwd=ROOT,capture_output=True,text=True,
                     encoding='utf-8',errors='replace',env=os.environ|{'PYTHONIOENCODING':'utf-8'},timeout=230)
    # Judge logs only sanitized score/identity information, never credentials.
    if p.stderr.strip(): emit(judge_progress=p.stderr.strip()[-1800:])
    return p


def evaluate_online(info):
    jobs=jobs_for(info['sha256'])
    completed=[j for j in jobs if j['state']=='completed']
    if completed: return completed[-1]
    if not jobs:
        p=invoke(['submit','--file',info['path'],'--no-wait'])
        jobs=jobs_for(info['sha256'])
        if not jobs: raise RuntimeError('Upload not established: '+p.stdout[-1600:])
    job=jobs[-1]
    for attempt in range(6):
        if job['state'] in {'completed','failed','ambiguous'}: return job
        p=invoke(['wait',job['job_id'],'--timeout','120','--interval','5'])
        job=jobs_for(info['sha256'])[-1]
        if job['state']=='completed': return job
        if '登录' in (job.get('last_error') or '') and '失效' in job['last_error']:
            raise RuntimeError('Browser login expired; waiting job preserved')
        # Refresh/read only; never retry an uncertain upload.
        invoke(['latest'])
        emit(recovering=job['job_id'],attempt=attempt+1,state=job['state'])
    raise RuntimeError('Unresolved job '+job['job_id']+'; no further uploads allowed')


def validate(info):
    exe=ROOT/'dev/build'/('online_'+info['sha256'][:12]+'.exe')
    p=subprocess.run(['g++','-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',info['path'],'-o',str(exe)],
                     cwd=ROOT,capture_output=True,text=True,timeout=90)
    if p.returncode or p.stderr: raise RuntimeError('Compilation failed/warned: '+p.stderr)
    for case in make_suite('smoke'):
        r=run_case([str(exe)],case)
        if r['status']!='ok' or r['queries']>199 or r['oscillations']>6:
            raise RuntimeError('Protocol/budget regression: '+json.dumps(r,ensure_ascii=False))
        expected=min(set(r['query_positions']),key=lambda x:(-case.values[x],abs(2*x-(len(case.values)-1)),x))
        if r['final_position']!=expected: raise RuntimeError('Motor did not park at observed winner')


def incumbent():
    p=OUT/'results.json'
    rows=json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    rows=[r for r in rows if r['score']>159487]
    if not rows: return 159487,{}
    best=max(rows,key=lambda x:x['score'])
    return best['score'],best.get('config',{})


def main():
    OUT.mkdir(exist_ok=True)
    state=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'done':[]}
    while True:
        best,base=incumbent()
        if best>=200000:
            state['stop']='target_reached';save(state);emit(stop=state['stop'],best=best);return
        q=quota();state['quota']=q;save(state);emit(quota=q,best=best)
        if q['remaining']==0:
            state['stop']='daily_quota_exhausted';save(state);emit(stop=state['stop'],best=best);return
        queue=json.loads(QUEUE.read_text(encoding='utf-8'))
        remaining=[x for x in queue if x['name'] not in state['done']]
        if not remaining:
            state['stop']='queue_empty';save(state);emit(stop=state['stop'],best=best);return
        item=remaining[0]
        config=(base if item.get('parent')=='best' else {}) | item['config']
        importlib.reload(policies)
        try:
            info=policies.generate(item['name'],config)
        except ValueError as e:
            if 'Unchanged baseline' not in str(e): raise
            state['done'].append(item['name']);save(state);continue
        state['active']=info;state.pop('stop',None);save(state)
        emit(candidate=info['name'],config=info['config'],sha256=info['sha256'])
        validate(info)
        job=evaluate_online(info)
        if job['state']!='completed': raise RuntimeError('Judge needs attention: '+job['state'])
        result=policies.record(job['job_id'],item['name'])
        state['done'].append(item['name']);state['last']=result;state.pop('active',None);save(state)
        emit(result=result)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except Exception as e:
        emit(error=type(e).__name__+': '+str(e));sys.exit(1)
