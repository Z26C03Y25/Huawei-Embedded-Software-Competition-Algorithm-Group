"""Single qualified wave-only trial on November7; wait mode never uploads."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/main_peak_20261107'
DAY='2026-11-07'
TZ=timezone(timedelta(hours=8))
sys.path[:0]=[str(ROOT/'dev'),str(ROOT/'automation')]
from tools.online_round_20261030 import candidate_review, parse_quota
from tools.local_judge import make_suite, run_case
from online_judge.browser import load_config, connect
from online_judge.jobs import JobStore, SubmissionLock

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def admission():
    if sys.argv[3]!='submit':
        return
    if datetime.now(TZ).date().isoformat()!=DAY:
        raise RuntimeError('New trial is restricted to November7')
    if '--repeat' in sys.argv:
        raise RuntimeError('Repeat uploads are not admitted')
    source=Path(sys.argv[sys.argv.index('--file')+1]).resolve()
    qualification=OUT/'qualification.json'
    if (OUT/'online_control_plan.json').exists():
        control=json.loads((OUT/'online_control_plan.json').read_text(encoding='utf-8'))
        if control['sha256']==sys.argv[2]:
            qualification=OUT/'online_control_plan.json'
    specific=OUT/'qualifications'/(sys.argv[2]+'.json')
    if specific.exists(): qualification=specific
    proof=json.loads(qualification.read_text(encoding='utf-8'))
    if proof.get('kind')=='direct_online_blackbox':
        auth=json.loads((OUT/'authorization_30.json').read_text(encoding='utf-8'))
        if auth.get('authorization')!='持续优化30次' or auth.get('selection_authorization')!='本地数据不一定够好，直接测线上':
            raise RuntimeError('Missing explicit direct online selection authorization')
        if proof.get('claimed_local_winner') or not proof.get('rationale'):
            raise RuntimeError('Black-box experiment needs a concrete waveform hypothesis')
    elif proof.get('kind')=='online_calibration':
        if proof.get('scope')=='wave_blackbox30':
            auth=json.loads((OUT/'authorization_30.json').read_text(encoding='utf-8'))
            if auth.get('authorization')!='持续优化30次' or proof.get('claimed_local_winner'):
                raise RuntimeError('Current black-box authorization mismatch')
            diagnostic=json.loads((OUT/proof['evidence']).read_text(encoding='utf-8'))
            if proof['independent_base_cases']<1000 or diagnostic['summary']['mixed']['errors'] or diagnostic['summary']['classic']['errors']:
                raise RuntimeError('Diverse protocol/parking regression admission failed')
            if diagnostic['summary']['sha256']!=proof['sha256']:
                raise RuntimeError('Regression evidence source mismatch')
        else:
            prior=JobStore(Path(load_config()['runs_directory'])).load('20261107T065919885800Z_279afde295ba')
            if proof['candidate']!='peak_core' or prior['state']!='completed' or prior['score']!=177469:
                raise RuntimeError('Calibration authorization context changed')
            if proof.get('authorization_verbatim')!='本地数据测试可能不准，你根据线上成绩拟合，只能黑盒测试，你只会拿到总分，去拟合':
                raise RuntimeError('Missing user black-box calibration authorization')
            if proof['independent_base_cases']<1000 or proof.get('claimed_local_winner'):
                raise RuntimeError('Calibration must preserve the full local regression evidence')
    elif not proof['eligible'] or proof['independent_base_cases']<1000:
        raise RuntimeError('Independent evidence did not qualify')
    if source!=OUT/(proof['candidate']+'.cpp') or digest(source.read_bytes())!=proof['sha256'] or sys.argv[2]!=proof['sha256']:
        raise RuntimeError('Qualified frozen source does not match')
    candidate_review(source.read_bytes())
    exe=source.with_suffix('.exe')
    rows=[]
    for case in make_suite('smoke',2026):
        row=run_case([str(exe)],case)
        path=row['query_positions']
        winner=min(set(path),key=lambda x:(-case.values[x],abs(2*x-(len(case.values)-1)),x)) if path else None
        row['parked_observed_winner']=bool(path) and row['final_position']==winner
        rows.append(row)
    if len(rows)!=26 or any(r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or not r['parked_observed_winner'] for r in rows):
        raise RuntimeError('Smoke protocol/query/turn/parking admission failed')
    config=load_config()
    store=JobStore(Path(config['runs_directory']))
    attempts=[store.load(p.parent.name) for p in store.root.glob('*/job.json')]
    today=[j for j in attempts if j.get('submission_attempt_at','').startswith(DAY)]
    auth=json.loads((OUT/'authorization_30.json').read_text(encoding='utf-8'))
    if auth.get('authorization')!='持续优化30次' or auth.get('date')!=DAY: raise RuntimeError('Missing current explicit30 authorization')
    if len(today)>=30:
        raise RuntimeError('Explicit daily authorization exhausted')
    if any(j['sha256']==proof['sha256'] and j['state']!='snapshot_ready' for j in attempts):
        raise RuntimeError('This source already has an upload attempt. Resume its job.')
    with connect(config) as page:
        page.records(refresh=True)
        quota=parse_quota(page.page.locator('body').inner_text())
    if quota['beijing_date']!=DAY or quota['used']>=30 or not quota['remaining']:
        raise RuntimeError('Fresh official quota does not admit another research trial')
    report=dict(date=DAY,quota=quota,source_sha256=proof['sha256'],executable_sha256=digest(exe.read_bytes()),
                cases=rows,authorization='保证不打表，但是突破目前的分数，只要不找错主峰',local_baseline=proof['baseline_note'])
    (OUT/(proof['candidate']+'_online_admission.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if not (OUT/'online_admission.json').exists():
        (OUT/'online_admission.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    if len(sys.argv)<4 or sys.argv[1]!='--judge':
        raise SystemExit('Use --judge SHA submit|wait with original judging arguments')
    with SubmissionLock(OUT/'.online-round.lock'):
        admission()
        wrapper=ROOT/'dev/tools/wave_round_20261106.py'
        source=wrapper.read_text(encoding='utf-8').replace("'2026-11-06'","'2026-11-07'")
        runtime={'__name__':'qualified_peak_judge','__file__':str(wrapper)}
        exec(compile(source,str(wrapper),'exec'),runtime)
        raise SystemExit(runtime['judge']())
