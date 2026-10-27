"""Resumable daily experiments; only the existing judge performs uploads."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib,json,os,re,subprocess,sys,time
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path[:0]=[str(ROOT/'dev'),str(ROOT/'automation')]
os.environ['PYTHONIOENCODING']='utf-8'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['PATH']=r'D:\application\mingw64\app\mingw64\bin'+os.pathsep+os.environ.get('PATH','')
from online_judge.browser import load_config,connect
from online_judge.jobs import SubmissionLock
from tools.online_search_loop import evaluate_online,jobs_for
from tools.research_policy import ResearchPause,cached_day_stop,check_local_evidence
from tools.policy_search import record
from tools.local_judge import make_suite,run_case,Case
from tools.compare_solvers import make_benchmark
DIR=Path(__file__).resolve().parent
STATE=DIR/'session.json'
QUEUE=DIR/'queue.json'
TZ=timezone(timedelta(hours=8))

def save(p,obj):
    tmp=p.with_name(p.name+'.'+uuid4().hex+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    for attempt in range(8):
        try:
            tmp.replace(p);return
        except PermissionError:
            if attempt==7:raise
            time.sleep(min(0.5,0.05*2**attempt))
def stamp():return datetime.now(TZ).isoformat(timespec='seconds')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quota():
    if cached_day_stop(ROOT):raise ResearchPause('Official quota already confirmed0 today; continue offline')
    with connect(load_config()) as adapter:
        rows=adapter.records(refresh=True)
        text=adapter.page.locator('body').inner_text()
        match=re.search(r'每日可上传\s*(\d+)\s*次.*?已经上传\s*(\d+)\s*次',text,re.S)
        if not match:raise RuntimeError('Official daily quota unavailable; no upload')
        limit,used=map(int,match.groups())
        if limit!=30 or not 0<=used<=limit:raise RuntimeError('Unexpected official quota')
        if any(r.status=='pending' for r in rows):raise RuntimeError('Platform has pending work; inspect before uploading')
        return dict(date=datetime.now(TZ).date().isoformat(),limit=limit,used=used,remaining=limit-used,checked_at=stamp())
def validate(info):
    source=ROOT/info['source'];actual=digest(source)
    if actual!=info['sha256']:raise RuntimeError('Candidate hash changed')
    cached=ROOT/'dev/build/research'/('day26_'+info['name']+'.json')
    if cached.exists():
        prior=json.loads(cached.read_text(encoding='utf-8'))
        if prior.get('source_sha256')==actual and prior.get('cases')==56 and len(prior.get('results',[]))==56:
            return {k:v for k,v in prior.items() if k not in ('results','source')}
    exe=ROOT/'dev/build/research'/('day26_'+actual[:12]+'.exe');exe.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run(['g++','-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(source),'-o',str(exe)],capture_output=True,text=True,timeout=90)
    if p.returncode or p.stderr:raise RuntimeError('Compilation failed/warned: '+p.stderr)
    cases=make_suite('smoke')+[i.case for i in make_benchmark(261026,28)]
    a=[0]*1000;a[200:401]=[10000]*201;a[336]=10090
    cases.append(Case('wide_control',tuple(a)));a[201]=10100;cases.append(Case('wide_hidden',tuple(a)))
    results=[]
    for c in cases:
        r=run_case([str(exe)],c)
        if r['status']!='ok' or r['queries']>199 or r['oscillations']>6:raise RuntimeError('Protocol/budget regression '+c.name)
        winner=min(set(r['query_positions']),key=lambda x:(-c.values[x],abs(2*x-(len(c.values)-1)),x))
        if r['final_position']!=winner:raise RuntimeError('Observed winner parking regression '+c.name)
        results.append(r)
    report=dict(source=info,source_sha256=actual,official=False,cases=len(cases),total_score=sum(r['score'] for r in results),zeros=sum(r['score']==0 for r in results),max_queries=max(r['queries'] for r in results),max_turns=max(r['oscillations'] for r in results),results=results)
    save(ROOT/'dev/build/research'/('day26_'+info['name']+'.json'),report)
    return {k:v for k,v in report.items() if k not in ('results','source')}
def progress(state):
    prior=json.loads((ROOT/'data/experiments/research_state.json').read_text(encoding='utf-8'))
    rows=json.loads((ROOT/'data/versions/online_search/results.json').read_text(encoding='utf-8'))
    best=max(rows,key=lambda x:x['score'])
    prior.update(date='2026-10-26',phase=state.get('phase','online'),last_known_official_best=best['score'],best_sha256=best['sha256'],confirmed_platform_quota_date=state.get('quota',{}).get('date'),confirmed_remaining_submissions=state.get('quota',{}).get('remaining'),quota_source='Fresh official submission-page quota',unresolved_jobs=len([j for p in (ROOT/'automation/online_judge/runs').glob('*/job.json') if (j:=json.loads(p.read_text(encoding='utf-8')))['state'] not in ('completed','failed')]),research_note='docs/daily_research/2026-10-26.md',next_day_queue='data/experiments/2026-10-26/queue.json',session='data/experiments/2026-10-26/session.json')
    today_jobs=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'automation/online_judge/runs').glob('*/job.json')]
    prior['online_submissions_this_batch']=sum(j.get('submission_attempt_at','').startswith('2026-10-26') for j in today_jobs)
    ranking_reads=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'automation/online_judge/runs/rankings').glob('*_*.json')]
    prior['network_ranking_reads_this_batch']=sum(r.get('captured_at','').startswith('2026-10-26') for r in ranking_reads)
    prior['next_action']='Resume the active work ID first if any; otherwise assess the next candidate in the dated queue after a fresh official quota check. After quota0 continue offline research.'
    prior['batch_summary']='data/experiments/2026-10-26/session.json'
    save(ROOT/'data/experiments/research_state.json',prior)
    lines=['# 2026-10-26 持续线上优化','',f"最高正式总分：{best['score']}。未评分候选不替换最高版。",'', '| 实验 | 正式分数 | 父版本 | 目的 |','| --- | ---: | --- | --- |']
    for row in state.get('results',[]):lines.append(f"| {row['name']} | {row['score']} | {row['parent_sha256'][:12]} | {row['purpose']} |")
    lines+=['', '状态：'+state.get('phase','online'),'','官方次数证据：'+json.dumps(state.get('quota',{}),ensure_ascii=False),'','每份候选先编译并执行56条真实管道交互，含26条烟测、28条固定种子配对曲线及宽平台有/无隐藏尖点。Q≤199、O≤6及最佳已观测点停车硬检查；真实冗余仍为模型风险，保留合成零分。','', '详细源码、哈希、参数、作品ID及离线报告见 '+str(STATE.relative_to(ROOT))+'.']
    (ROOT/'docs/daily_research/2026-10-26.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def finish_job(state,item,job,check):
    if job['state']!='completed':raise RuntimeError('Unresolved work '+job['job_id']+' '+job['state'])
    result=record(job['job_id'],item['name'])
    row=result['recorded']|dict(parent_sha256=item['parent_sha256'],purpose=item['purpose'],parameters=item['config'],config=item['config'],validation=check)
    records_path=ROOT/'data/versions/online_search/results.json'
    records=json.loads(records_path.read_text(encoding='utf-8'))
    for saved in records:
        if saved['job_id']==job['job_id']:saved.update(parent_sha256=item['parent_sha256'],purpose=item['purpose'],config=item['config'])
    save(records_path,records)

    if not any(r['job_id']==row['job_id'] for r in state['results']):state['results'].append(row)
    state.pop('active',None);state['phase']='result_recorded';save(STATE,state);progress(state)
    print(json.dumps(dict(name=row['name'],score=row['score'],job_id=row['job_id'],sha256=row['sha256'],best_score=result['best_score']),ensure_ascii=True),flush=True)

def main():
    with SubmissionLock(ROOT/'automation/online_judge/runs/.optimization.lock'):
        state=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else dict(date='2026-10-26',results=[])
        queue=json.loads(QUEUE.read_text(encoding='utf-8'))
        done={r['name'] for r in state['results']}
        rejected=DIR/'submission_rejections.json'
        if rejected.exists():done.update(json.loads(rejected.read_text(encoding='utf-8')))
        active=state.get('active')
        item=active or next((x for x in queue if x['name'] not in done),None)
        existing=jobs_for(item['sha256']) if item else []
        if active and existing and existing[-1]['state']!='snapshot_ready':
            job=evaluate_online(dict(name=item['name'],path=str(ROOT/item['source']),sha256=item['sha256']))
            finish_job(state,item,job,state.get('validation') or validate(item))
            return  # Record a submitted work even when the day's quota is already0.
        if item:check_local_evidence(item,ROOT)
        state['quota']=quota();state['phase']='online_ready';save(STATE,state);progress(state)
        if not state['quota']['remaining']:
            state['phase']='daily_quota_exhausted';save(STATE,state);progress(state);print(json.dumps(state['quota']),flush=True);return
        if not item:print('queue_empty',flush=True);return
        state['active']=item;state['phase']='validating';save(STATE,state)
        check=validate(item)
        candidate_report=json.loads((ROOT/'dev/build/research'/('day26_'+item['name']+'.json')).read_text(encoding='utf-8'))
        for report_path in (ROOT/'dev/build/research').glob('day26_*.json'):
            parent_report=json.loads(report_path.read_text(encoding='utf-8'))
            if parent_report.get('source_sha256')!=item['parent_sha256'] or parent_report.get('cases')!=56:continue
            current_rows=candidate_report['results'];parent_rows=parent_report['results']
            check['paired_parent_delta']=sum(a['score']-b['score'] for a,b in zip(current_rows,parent_rows))
            check['paired_new_zero']=sum(a['score']==0 and b['score']>0 for a,b in zip(current_rows,parent_rows))
            check['paired_resolved_zero']=sum(a['score']>0 and b['score']==0 for a,b in zip(current_rows,parent_rows))
            if check['paired_new_zero'] and check['paired_parent_delta']<=0:
                rejection=DIR/'submission_rejections.json';rejections=json.loads(rejection.read_text(encoding='utf-8')) if rejection.exists() else {}
                rejections[item['name']]='Offline dominated: lower/equal total with newly introduced zeros; not uploaded'
                save(rejection,rejections);state.pop('active',None);state['phase']='offline_candidate_rejected';state['validation']=check;save(STATE,state);progress(state)
                print(json.dumps(dict(rejected=item['name'],validation=check)),flush=True);return
            break
        state['validation']=check;save(STATE,state)
        # Refresh quota immediately before using the judge upload path.
        state['quota']=quota();state['phase']='awaiting_official_score';save(STATE,state);progress(state)
        if not state['quota']['remaining']:return
        print(json.dumps(dict(candidate=item['name'],parameters=item['config'],sha256=item['sha256'],validation=check,quota=state['quota']),ensure_ascii=True),flush=True)
        job=evaluate_online(dict(name=item['name'],path=str(ROOT/item['source']),sha256=item['sha256']))
        finish_job(state,item,job,check)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:main()
    except Exception as exc:print(type(exc).__name__+': '+str(exc),flush=True);raise
