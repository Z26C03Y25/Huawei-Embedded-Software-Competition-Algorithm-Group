"""Explicit November8,30 unique official trials. Online scores choose parents."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import argparse,hashlib,itertools,json,math,random,re,subprocess,sys,time,traceback
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/main_peak_20261108'
sys.path[:0]=[str(ROOT/'dev/tools'),str(ROOT/'dev'),str(ROOT/'automation')]
from peak_round_20261108 import runtime
from main_peak_20261107 import generate,evaluate
from tools.local_judge import make_suite,Case
from tools.mixed_scenarios import make_scenarios
TZ=timezone(timedelta(hours=8));DAY='2026-11-08'
OPS=['zerosalvage','fitstop','nocentercap','widthcap','staggerweak','burstsupport','tailvalley','staggered','sweepcover','multiguard','curvaturenoise','maincoherent','basinunion','winnerfrontier','mainall','flatreach','tailprobe','intervalfine','evidencescout','cellbudget','shapescout','modeltight','modelguard','startdense','paired','wideaudit','nocreststop','midscout','ladder','quant','noisehalf','noiselocal','nomodel','priced','scalestep','gapfill','widescout','phase','asymmetry','adaptive','blank','interior','five','six','contour','narrow','relativetolerance','statisticalsignal','quantilefloor','maincover','mainverify']
GROUPS=[{'nocentercap','widthcap','fitstop'},{'staggered','staggerweak'},{'narrow','burstsupport'},{'maincover','mainverify','maincoherent','mainall','zerosalvage'},{'quant','statisticalsignal'},{'contour','wideaudit'},{'tailprobe','ladder','blank'},{'shapescout','midscout','widescout'},{'modeltight','modelguard','interior','nomodel'},{'paired','scalestep','phase','asymmetry','adaptive','five','six'}]
WHY={
 'zerosalvage':'If the current winner lies left of rightmost minus the allowed199redundancy and3parking error, returning there is provably zero. Redirect refinement into unresolved feasible cells, reserving queries to refine any new higher winner.',

 'fitstop':'Permit short right confirmation only when the sampled maximum dominates the background and has coherent concave fit support; replace the array-center shortcut with waveform evidence.',

 'nocentercap':'Remove the assumption that a measured crest past the array center needs only16positions of right confirmation; later competing main peaks must be decided from waveform scouting.',
 'widthcap':'Derive the close-crest scouting cap from observed half-widths rather than whether the current winner lies past the array center.',

 'staggerweak':'Apply low-discrepancy coarse phase shifts only while measurements cannot distinguish signal from background dispersion; preserve established peak trajectories.',
 'burstsupport':'A statistically meaningful local rise triggers adjacent forward reads even before it becomes the global winner; old noise spikes cannot suppress all competitor shoulder checks.',

 'tailvalley':'Fit the robust descending tail curvature to locate a possible coming valley; choose the right sentinel from that geometry within the observed-winner redundancy lease.',
 'staggered':'Dither ordinary coarse gaps using a deterministic low-discrepancy phase so periodic narrow peaks cannot repeatedly align between a fixed lattice; retain unit apex reads.',

 'sweepcover':'Derive the finest domain-covering stride from the query budget while reserving a complete two-sided fine cell; preserve waveform stopping and use the corresponding coarse budget.',
 'multiguard':'A locally concave crest cannot trigger early apex stopping while measured competing maxima remain; preserve ordinary shoulder scouting for multimodal waveforms.',
 'curvaturenoise':'Estimate measurement dispersion from normalized four-point quadratic interpolation residuals so variable sample gaps do not count smooth quadratic curvature as noise.',

 'maincoherent':'Peak confirmation requires both background dominance and coherent local curvature; an isolated raw high cannot bypass unresolved-gap coverage.',
 'basinunion':'Rank every measured gap by a local-curvature interpolation envelope, then exhaust competitive integer cells before the prior refiner.',
 'winnerfrontier':'Test whether a high-value band anchored too far left prematurely truncates the right search; anchor the redundancy lease at the observed raw winner instead.',
 'mainall':'Diagnostic structural probe: audit unresolved midpoint gaps regardless of apparent peak confidence, retaining exact cell verification and physical parking.',

 'maincover':'An unconfirmed observed maximum triggers a complete midpoint sweep of unresolved coarse gaps, then exact winner-cell refinement and right-boundary recovery. Strong established curves retain the prior refinement.',
 'mainverify':'Replace model agreement as peak confirmation with observed background dominance or coherent peak support; audit unresolved gaps and verify the full winning cell before permitting the old refiner to finish.',
 'relativetolerance':'Derive the high-value uncertainty band from sample count, current noise and contrast instead of a fixed contrast fraction.',
 'statisticalsignal':'Scale signal confidence with the number of measurements and measured noise rather than a fixed noise multiplier.',
 'quantilefloor':'Estimate background from a low empirical order statistic to reduce isolated low-outlier distortion.',
 'cellbudget':'Allocate refinement reserve from currently unresolved high-value sample cells; use the remaining budget for coarse coverage instead of a fixed reserve.',
 'intervalfine':'Replace fitted-vertex stopping and randomized refinement with measured interval uncertainty and exact promising-cell completion.',
 'evidencescout':'Replace coarse length tiers with observed-width, slope, noise and remaining-budget scouting.',
 'flatreach':'A flat prefix cannot prove no late peak; continue measured flat coverage using remaining query budget.',
 'tailprobe':'After a local summit, probe a geometry-derived right shoulder and continue only on measured recovery.',
 'shapescout':'Use observed half-width to determine scouting extent instead of coarse length tiers.',
 'modeltight':'Require closer agreement of independent fitted vertices before stopping.',
 'modelguard':'Require a verified interior summit before model-based early termination.',
 'startdense':'Use a geometric initial grid to reduce early narrow-peak aliasing.',
 'paired':'Alternate coarse gaps on measured signal to expose narrow shoulders.',
 'wideaudit':'Confirm more competing basins using current noise and contrast.',
 'nocreststop':'A locally bracketed crest may precede a higher peak; retain ordinary right scouting.',
 'midscout':'Use continuous observed-width scouting in place of length tiers.',
 'ladder':'Use increasing right probes to detect a higher basin after local descent.',
 'quant':'Small quantized variation should not establish peak identity prematurely.',
 'noisehalf':'Test sensitivity to curvature entering the noise estimate.',
 'noiselocal':'Compare global and recent residual dispersion for noisy peak recognition.',
 'nomodel':'Test whether model consensus causes premature termination on nonquadratic peaks.',
 'priced':'Value real direction changes in refinement route planning.',
 'scalestep':'Set rising-curve resolution from measured width and curvature.',
 'gapfill':'Complete a larger neighborhood around noisy competing peaks.',
 'widescout':'Test broader measured-width scouting for hidden later main peaks.',
 'phase':'Dither sampling gaps to avoid regular-grid peak aliasing.',
 'asymmetry':'Adapt gap size to local rise/fall asymmetry and uncertainty.',
 'adaptive':'Choose gap from slope deceleration and remaining coverage budget.',
 'blank':'Add budgeted coverage when weak measurements do not establish a peak.',
 'interior':'Reserve a margin around the model peak before accepting completion.',
 'five':'Measure whether denser coarse coverage recovers peaks missed by ordinary spacing.',
 'six':'Compare denser coarse spacing with the ordinary coverage/stop interaction.',
 'contour':'Confirm additional competitive cells before accepting the sampled winner.',
 'narrow':'Trigger adjacent shoulder reads by measured peak width rather than an input identity.'}
def now():return datetime.now(TZ).isoformat(timespec='seconds')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(p,default=None):return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(p)
def freeze(p,raw):
 if p.exists():
  if p.read_bytes()!=raw:raise RuntimeError('Refuse source overwrite '+str(p))
 else:p.write_bytes(raw)
def best_flags(c):
 sha=c.state['best_sha256'];p=OUT/'strategies'/(sha+'.json')
 if p.exists():return read(p)['flags']
 p=OUT/'qualifications'/(sha+'.json')
 if p.exists() and read(p).get('flags'):return read(p)['flags']
 old=read(ROOT/'data/experiments/main_peak_20261107/state.json')
 for row in reversed(old['rounds']):
  if row['sha256']==sha:
   stem=Path(row['source_path']).stem
   if stem.startswith('peak_core'):return stem.split('_')[1:]
 raise RuntimeError('Cannot infer parent strategy provenance')
def mutated(flags,ops):
 f=set(flags)
 if 'cellbudget' in ops:f.add('evidencescout')
 for op in ops:
  for group in GROUPS:
   if op in group:f-=group
  f.add(op)
 # Remove operators whose implementation is wholly replaced by a new framework.
 # This rejects identical strategies by construction, not by synthetic scores.
 if 'evidencescout' in f:
  f-={'frontier','flatreach','narrow','nocreststop','startdense','shapescout','midscout','widescout','paired','scalestep','phase','asymmetry','adaptive','five','six'}
 if 'intervalfine' in f:
  f-={'selective','efficient','contour','wideaudit','gapfill','nomodel','modeltight','modelguard','interior'}
 if f & {'contour','wideaudit','gapfill','efficient'}:f.add('selective')
 return sorted(f)
def diagnostic_cases():
 cases=make_suite('smoke',2026)
 cases += [c for c,m in make_scenarios(1,['development','selection'],20261108801,novel=True) if m['transform']=='base']
 rng=random.Random(20261108803)
 for j in range(12):
  n=rng.randint(300,1000);p=rng.randrange(n);w=rng.randint(3,70);amp=rng.choice([3,8,16,32])
  vals=tuple(7+round(amp*math.exp(-min(700,((x-p)/w)**2/2))) for x in range(n))
  cases.append(Case('quantized_mechanism_'+str(j),vals,'quantized_mechanism'))
 return cases
def behavior(rows):return digest(json.dumps([(r['name'],r['query_positions']) for r in rows],separators=(',',':')).encode())
def report(c):
 sha=c.state['best_sha256'];score=c.state['best_score'];raw=(ROOT/'main.cpp').read_bytes()
 if digest(raw)!=sha:raise RuntimeError('Main/best digest mismatch')
 rows=c.state['rounds'];best=next((r for r in reversed(rows) if r['sha256']==sha and r.get('score')==score),None)
 selection=dict(selected=best['name'] if best else 'initial_wave_parent',sha256=sha,official_score=score,official_state='completed',online_job_id=best.get('job_id') if best else None,historical_benchmark=224148,above_historical_best=score>224148,basis='Highest confirmed table-free source. New strategy decisions use official totals only.',updated_at=now())
 save(OUT/'selection.json',selection)
 table=['| 方案 | 正式分数 | 相对提交前最佳 | 状态 |','| --- | ---: | ---: | --- |']
 for r in rows:table.append('| '+r['name']+' | '+str(r.get('score','—'))+' | '+str(r.get('delta','—'))+' | '+r['state']+' |')
 text='# 2026-11-08 纯波形线上优化\n\n[返回实验目录](../README.md) · [当前源码](../../../main.cpp) · [逐次记录](state.json) · [授权](authorization.json)\n\n'
 text+='用户授权30次，方案只根据线上正式总分选择。历史峰位可用于形成假设，提交代码不包含已知坐标、特定N到峰位分派或回复指纹。通用步长、窗口与容错规则仍属于待验证的启发式参数。\n\n'
 text+=f'当前采用正式 **{score}** 分，SHA256 `{sha}`。历史含样例适配的224148仅作突破目标。\n\n'+'\n'.join(table)+'\n\n'
 text+='本地只检查编译、交互、Q≤199、O≤6和实际停在已查询原始最大值。合成曲线仅验证分支确实改变查询，零分与失败完整保留；不以其分数筛选线上方案。聚合线上分数不能指出具体哪个隐藏样例为零，也不能证明任意数组均找对主峰。\n\n'
 text+='部分本机启动被Windows应用控制4551阻止：仅当所有实际运行项通过原协议断言、未运行项均为查询前启动拒绝时，另行核对源码来源与查询/振荡/停车内核。未运行项不冒充26项通过；逐项结果和源码审计证书保留在rounds目录。\n\n'
 text+='未知或待判任务只恢复原任务；不会重传。所有正式源码按原字节归档。日志和策略沿袭见本目录JSON文件。\n'
 (OUT/'README.md').write_text(text,encoding='utf-8')
 p=ROOT/'README.md';text=p.read_text(encoding='utf-8');text=re.sub(r'当前 main\.cpp 采用.*?历史最高分与当前源码分开记录。',f'当前 main.cpp 采用[纯波形线上优化版](data/experiments/main_peak_20261108/README.md)，当前正式分 **{score}**。历史最高分与当前源码分开记录。',text,count=1);p.write_text(text,encoding='utf-8')
 p=ROOT/'data/experiments/README.md';text=p.read_text(encoding='utf-8')
 if 'main_peak_20261108/README.md' not in text:text+='\n[2026-11-08纯波形线上优化](main_peak_20261108/README.md)\n';p.write_text(text,encoding='utf-8')
 p=ROOT/'data/versions/README.md';text=p.read_text(encoding='utf-8').replace('正式成绩待判',f'当前正式{score}').replace('../experiments/main_peak_20261107/README.md','../experiments/main_peak_20261108/README.md');text=re.sub(r'当前正式\d+',f'当前正式{score}',text);p.write_text(text,encoding='utf-8')
def prepare(c,seq,ops,state,cases):
 fixed=state.get('fixed_construction',{}).get('_'.join(ops))
 construction=fixed['flags'] if fixed else best_flags(c)
 flags=mutated(construction,ops);code=generate('peak_'+'_'.join(flags));raw=code.encode('utf-8');sha=digest(raw)
 if any(j['sha256']==sha and j['state']!='snapshot_ready' for j in c.jobs()):return None,'already_attempted_source'
 if re.search(r'fingerprint|deferred|\bn\s*==\s*\d+|\b(?:586|662|774)\b',code):raise RuntimeError('Fixed case audit failed')
 name=f'wave{seq:02d}_'+('_'.join(ops))[:54];source=OUT/(name+'.cpp');freeze(source,raw)
 strategy=dict(name=name,flags=flags,operators=ops,sha256=sha,parent_sha256=c.state['best_sha256'],parent_score=c.state['best_score'],rationale='; '.join(WHY[op] for op in ops),source=str(source),created_at=now());save(OUT/'strategies'/(sha+'.json'),strategy)
 if fixed:
  strategy['construction_parent']=fixed
  save(OUT/'strategies'/(sha+'.json'),strategy)
 exe=source.with_suffix('.exe');cmd=[str(ROOT/'dev/toolchains/w64devkit/bin/g++.exe'),'-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(source),'-o',str(exe)]
 r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90);(OUT/(name+'.compile.txt')).write_text(r.stdout+r.stderr,encoding='utf-8')
 if r.returncode or r.stderr.strip():return None,'compile_error_or_warning'
 rows=evaluate(exe,cases[:1])
 if rows[0]['status']=='launch_error':
  save(OUT/(name+'.launch_failure.json'),dict(official=False,sha256=sha,rows=rows,classification='host_execution_failure_not_algorithm_zero'))
  if '4551' not in str(rows[0].get('error')):return None,'host_execution_unavailable: '+str(rows[0].get('error'))
  from guard_equivalence_20261108 import audit
  certificate=audit(raw,flags)
  strategy['native_execution_available']=False;strategy['source_guard_certificate']=certificate
  save(OUT/(name+'.source_guard.json'),certificate);save(OUT/'strategies'/(sha+'.json'),strategy)
  proof=dict(candidate=name,sha256=sha,kind='direct_online_blackbox',claimed_local_winner=False,rationale=strategy['rationale'],flags=flags,
   native_execution_available=False,source_guard_certificate=certificate,baseline_note=f"Official parent{c.state['best_score']}; host runtime unavailable, matching protected guards verified; only official scores select performance.")
  save(OUT/'qualifications'/(sha+'.json'),proof)
  return strategy,None
 rows+=evaluate(exe,cases[1:]);sig=behavior(rows);save(OUT/(name+'.diagnostic.json'),dict(official=False,performance_not_used_for_selection=True,sha256=sha,behavior=sig,rows=rows))
 if any(r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or not r['parked_observed_winner'] for r in rows):return None,'protocol_or_parking_failure'
 strategy['same_diagnostic_trajectories_as']=state['behaviors'].get(sig)
 state['behaviors'][sig]=sha
 save(OUT/'strategies'/(sha+'.json'),strategy)
 proof=dict(candidate=name,sha256=sha,kind='direct_online_blackbox',claimed_local_winner=False,rationale=strategy['rationale'],flags=flags,baseline_note=f"Current confirmed table-free parent{c.state['best_score']}. Official score alone decides adoption.")
 save(OUT/'qualifications'/(sha+'.json'),proof);return strategy,None

@contextmanager
def await_round_lock(ns):
 lock=ns['SubmissionLock'](OUT/'.round.lock')
 while True:
  try:
   lock.__enter__();break
  except RuntimeError as error:
   if 'Another submission process holds the lock' not in str(error):raise
   time.sleep(2)
 try:yield
 finally:lock.__exit__(None,None,None)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--report-only',action='store_true');args=parser.parse_args();ns=runtime();ns['AUTHORIZATION']=['优化30次，全部根据线上数据，你打表的数据可以参考总结规律，但是不能写死参数']
 with ns['SubmissionLock'](OUT/'.adaptive.lock'):
  state=read(OUT/'adaptive_state.json',dict(date=DAY,plan_index=0,preparations=0,experiments=[],behaviors={},status='running',created_at=now()))
  plan=[(op,) for op in OPS]+list(itertools.combinations(OPS[:16],2))
  cases=diagnostic_cases();save(OUT/'branch_diagnostic_cases.json',[dict(name=c.name,family=c.family,values=c.values) for c in cases])
  while True:
   with await_round_lock(ns):
    c=ns['Controller']();report(c)
    if args.report_only:return 0
    open_rows=[r for r in c.state['rounds'] if r['state'] not in {'completed','failed'}]
    if open_rows:
     for r in open_rows:
      if not r.get('job_id'):raise RuntimeError('Unresolved upload with no identity; stop without retrial')
      result=c.resume(r['job_id']);report(c)
      if result:return result
    failed=[r for r in c.state['rounds'] if r['state']=='failed']
    if failed:
     state['status']='official_failure_requires_review';save(OUT/'adaptive_state.json',state);report(c);return 3
    if datetime.now(TZ).date().isoformat()!=DAY:state['status']='date_changed';save(OUT/'adaptive_state.json',state);return 0
    with ns['connect'](c.config) as page:
     page.records(refresh=True);quota=ns['parse_quota'](page.page.locator('body').inner_text())
    if quota['remaining']==0:
     c.state['last_quota']=quota;c.persist();state['status']='quota_exhausted';save(OUT/'adaptive_state.json',state);report(c);return 0
    quota=c.quota_check()
    if (OUT/'STOP_NEW_UPLOADS').exists():state['status']='stop_requested';save(OUT/'adaptive_state.json',state);return 0
    if state['plan_index']>=len(plan):raise RuntimeError('No distinct untried waveform strategy remains')
    ops=plan[state['plan_index']];state['plan_index']+=1;state['preparations']+=1;save(OUT/'adaptive_state.json',state)
    try:strategy,rejection=prepare(c,state['preparations'],ops,state,cases)
    except Exception as e:
     strategy=None;rejection=repr(e);(OUT/f"local_rejection_{state['preparations']:03d}.txt").write_text(traceback.format_exc(),encoding='utf-8')
    entry=dict(operators=ops,preparation=state['preparations'],parent_score=c.state['best_score'],rejection=rejection,time=now());state['experiments'].append(entry);save(OUT/'adaptive_state.json',state)
    if rejection:print('LOCAL_SKIP '+json.dumps(entry),flush=True);continue
    entry['sha256']=strategy['sha256'];entry['name']=strategy['name'];save(OUT/'adaptive_state.json',state)
    print('NEXT '+json.dumps(strategy,ensure_ascii=False),flush=True)
    result=c.start(strategy['name'],Path(strategy['source']),strategy['rationale']+'; explicit direct-online authorization; no fixed-case lookups.')
    report(c);entry['result']=result;entry['official_best']=c.state['best_score'];save(OUT/'adaptive_state.json',state)
    if result:state['status']='judge_or_identity_error';save(OUT/'adaptive_state.json',state);return result
if __name__=='__main__':
 try:raise SystemExit(main())
 except KeyboardInterrupt:print('Interrupted; resume saved jobs only.',flush=True);raise
 except Exception:traceback.print_exc();raise SystemExit(5)
