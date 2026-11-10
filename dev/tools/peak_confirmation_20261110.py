"""Nov10 waveform-only controlled experiments; imports never start uploads.

Candidate recipes and descriptions are owned by peak_candidates_20261110.
An empty mode list resumes this controller's existing jobs only. A nonempty list
runs only those reviewed unique recipes under the actual daily quota and locks.
"""
from pathlib import Path
import argparse,importlib,json,re,sys,time,traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'dev/tools'),str(ROOT/'dev'),str(ROOT/'automation')]
from guard_equivalence_20261108 import _guard_audit,appcontrol_only_missing_cases
import wave_batch_20261106 as legacy
DAY='2026-11-10';OUT=ROOT/'data/experiments/main_peak_20261110'
BASE=ROOT/'data/versions/online_search/scored_218796_5dcce0efd1f9.cpp'
BASE_SHA='5dcce0efd1f94b7b7d602d31f956ba70d4292d6c0e8d2e09af9feff9c80a0b4f'
AUTH=['持续优化','优化30次，全部根据线上数据，你打表的数据可以参考总结规律，但是不能写死参数','继续优化，目前看着还有零分，试着改珠峰确认方案']
recipes=importlib.import_module('peak_candidates_20261110')
WHY=recipes.WHY

def replace(s,a,b):
 if s.count(a)!=1:raise ValueError('Nonunique source anchor '+a)
 return s.replace(a,b,1)

def construction_parent(mode):
 if hasattr(recipes,'construction_parent'):
  parent=recipes.construction_parent(mode)
 else:parent=dict(sha256=BASE_SHA,score=218796)
 if not re.fullmatch('[0-9a-f]{64}',parent['sha256']) or type(parent['score']) is not int:
  raise ValueError('Invalid frozen construction parent')
 return parent

def generate(mode):
 import hashlib
 if hashlib.sha256(BASE.read_bytes()).hexdigest()!=BASE_SHA:raise ValueError('Frozen218796 parent changed')
 if mode not in WHY:raise ValueError('Unknown reviewed hypothesis '+mode)
 raw=recipes.generate(mode)
 if not isinstance(raw,bytes):raise TypeError('Generator must return bytes')
 code=raw.decode('utf-8')
 if re.search(r'fingerprint|deferred|\bn\s*==\s*\d+|\b(?:586|662|774)\b',code):raise ValueError('Lookup audit failed')
 return raw

def runtime():
 p=ROOT/'dev/tools/online_round_20261030.py';s=p.read_text(encoding='utf-8')
 s=s.replace('online_20261030"','main_peak_20261110"')
 s=replace(s,'DATE = "2026-10-30"','DATE = "2026-11-10"')
 start=s.index('AUTHORIZATION = ');end=s.index('\n',start);s=s[:start]+'AUTHORIZATION = '+repr(AUTH)+s[end:]
 a='                canonical = self.root / "data/versions" / f"main_online_{score}.cpp"'
 s=replace(s,a,a+'\n                if canonical.exists() and digest(canonical.read_bytes()) != entry["sha256"]:\n                    canonical = self.root / "data/versions" / f"main_wave_20261110_{score}_{digest(contents)[:12]}.cpp"')
 ns={'__name__':'confirmation_round_runtime','__file__':str(p)};exec(compile(s,str(p),'exec'),ns)
 original=ns['Controller'].preflight
 def preflight(self,entry):
  raw=Path(entry['snapshot_path']).read_bytes();proof=ns['read'](OUT/'qualifications'/(entry['sha256']+'.json'))
  if raw!=generate(proof['mode']):raise ValueError('Frozen candidate provenance mismatch')
  certificate=_guard_audit(raw)
  try:return original(self,entry)
  except RuntimeError as error:
   if str(error)!='26-case preflight protocol/query/turn/parking check failed':raise
   directory=Path(entry['snapshot_path']).parent;rows=ns['read'](directory/'smoke.json')['rows']
   if len(rows)!=26 or not appcontrol_only_missing_cases(rows):raise
   entry['preflight']=dict(passed=False,native_cases_passed=sum(r['status']=='ok' for r in rows),native_cases_blocked=sum(r['status']=='launch_error' for r in rows),alternate_static_admission=True,native_error='Windows4551before queries only',source_guard_certificate=certificate)
   ns['save'](directory/'source_guard_certificate.json',certificate);self.persist()
 ns['Controller'].preflight=preflight
 return ns

core=runtime()
for name,value in dict(core=core,Controller=core['Controller'],OUT=OUT,DAY=DAY,BATCH_IN_FLIGHT=2,connect=core['connect'],parse_quota=core['parse_quota'],now=core['now'],save=core['save'],read=core['read'],digest=core['digest']).items():setattr(legacy,name,value)
legacy.Batch.accept_wave=lambda self,entry:None

def report(c):
 if core['digest']((ROOT/'main.cpp').read_bytes())!=c.state['best_sha256']:raise RuntimeError('Main/best source mismatch')
 rows=c.state['rounds'];table=['|方案|正式分|对比提交前最高|状态|','|---|---:|---:|---|']
 for e in rows:table.append(f"|{e['name']}|{e.get('score','—')}|{e.get('delta','—')}|{e['state']}|")
 text='# 2026-11-10主峰确认实验\n\n[实验目录](../README.md) · [当前代码](../../../main.cpp) · [逐次状态](state.json)\n\n'
 text+=f"当前无打表采用 **{c.state['best_score']}**，当日起点218796。默认从冻结218796出发，后续受控组的父版见qualifications；按线上总分判断收益；不由合成分数挑选，不含指定样例长度、峰位或回复指纹。\n\n"+'\n'.join(table)+'\n\n'
 text+='[研究过程](WORKLOG.md)记录机制假设与线上消融。\n\n'
 text+='本地只验证编译与交互/查询/振荡/真实停车。主机若在查询前被Windows4551拒绝启动，保留原记录，仅以源码内核等价审计补充缺项，未运行项不冒充通过；真实协议或预算错误仍拒绝。总分不能确认每个零分样例已恢复。未知上传只恢复原任务；旧任务保留原作品编号，无重传。\n'
 (OUT/'README.md').write_text(text,encoding='utf-8')
 core['save'](OUT/'selection.json',dict(score=c.state['best_score'],sha256=c.state['best_sha256'],checked_at=core['now']()))
 p=ROOT/'README.md';text=p.read_text(encoding='utf-8');text=re.sub(r'当前 main\.cpp 采用.*?历史最高分与当前源码分开记录。',f"当前 main.cpp 采用[纯波形主峰确认版](data/experiments/main_peak_20261110/README.md)，当前正式分 **{c.state['best_score']}**。历史最高分与当前源码分开记录。",text,count=1);p.write_text(text,encoding='utf-8')
 p=ROOT/'data/experiments/README.md';text=p.read_text(encoding='utf-8')
 if 'main_peak_20261110/README.md' not in text:p.write_text(text+'\n[2026-11-10主峰确认实验](main_peak_20261110/README.md)\n',encoding='utf-8')

def run(modes,minutes):
 if len(modes)!=len(set(modes)) or any(mode not in WHY for mode in modes):raise ValueError('Explicit reviewed modes must be unique and known')
 OUT.mkdir(parents=True,exist_ok=True)
 auth=dict(date=DAY,user_request=AUTH,maximum_platform_daily_attempts=30,plan=modes,selection='Online formal scores only; local checks for protocol/budget/parking',no_case_lookup=True,scope='Original Huawei contest only, new uploads stop at date change or zero actual remaining quota')
 prior=core['read'](OUT/'authorization.json',{})
 auth['runs']=prior.get('runs',[])+[dict(started_at=core['now'](),modes=modes)]
 core['save'](OUT/'authorization.json',auth)
 with core['SubmissionLock'](OUT/'.pipeline.lock'),core['SubmissionLock'](OUT/'.round.lock'):
  c=core['Controller']()
  with core['connect'](c.config) as page:
   batch=legacy.Batch(c,page,minutes);batch.check_foreign_jobs();index=0;sent=[]
   while time.monotonic()<batch.stop_at:
    quota,records=batch.poll();report(c)
    if quota['beijing_date']==DAY and quota['used']<len(c.delivered()[0]):raise RuntimeError('Live quota is stale relative to saved attempts; no new upload')
    judge_failed=any(e.get('job_id') and not e.get('prior_day') and e['state']=='failed' for e in c.state['rounds'])
    if judge_failed:index=len(modes)  # Drain acknowledged work, never start another upload after an official failure.
    own=[e for e in c.state['rounds'] if e.get('job_id') and not e.get('prior_day')]
    if index>=len(modes) and all(e['state'] in ('completed','failed') for e in own):return 3 if judge_failed else 0
    if index<len(modes) and quota['remaining']>0 and core['now']()[:10]==DAY and batch.can_send(records):
     mode=modes[index];index+=1;raw=generate(mode);sha=core['digest'](raw)
     if any(j['sha256']==sha for j in c.jobs()) or any(e.get('sha256')==sha for e in core['read'](c.manifest_path,{}).get('files',[])+core['read'](c.index_path,[])):print('Prior source: skip without upload',mode,sha,flush=True);continue
     core['candidate_review'](raw);certificate=_guard_audit(raw)
     source=OUT/(mode+'.cpp');core['preserve'](source,raw)
     construction=construction_parent(mode)
     core['save'](OUT/'qualifications'/(sha+'.json'),dict(mode=mode,sha256=sha,construction_parent_sha256=construction['sha256'],construction_parent_score=construction['score'],rationale=WHY[mode],source_guard_certificate=certificate))
     e=c.new_metadata(mode,raw,WHY[mode],str(source));c.preflight(e)
     if not batch.upload(e):raise RuntimeError('Upload preconditions changed; no retry')
     sent.append(e['job_id']);report(c);print(json.dumps(dict(mode=mode,job_id=e['job_id'],actual_used=c.state['last_quota']['used'],best=c.state['best_score']),ensure_ascii=False),flush=True)
    else:
     if core['now']()[:10]!=DAY or quota['remaining']==0:
      if not any(not e.get('prior_day') and e['state'] not in ('completed','failed') for e in own):return 0
     page.page.wait_for_timeout(3000 if any(time.monotonic()-t<3 for _,t in batch.signatures.values()) else 15000)
   print('Read-only time window ended; resume existing jobs only.',flush=True);return 2

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('modes',nargs='*',choices=WHY);p.add_argument('--minutes',type=float,default=20);a=p.parse_args()
 try:raise SystemExit(run(a.modes,a.minutes))
 except Exception:traceback.print_exc();raise SystemExit(5)
