"""November8 user-authorized direct online trials. Wait never uploads."""
from datetime import datetime,timedelta,timezone
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/main_peak_20261108'
DAY='2026-11-08';TZ=timezone(timedelta(hours=8))
sys.path[:0]=[str(ROOT/'dev'),str(ROOT/'automation')]
from tools.online_round_20261030 import candidate_review,parse_quota
from tools.local_judge import make_suite,run_case
from online_judge.browser import connect,load_config
from online_judge.jobs import JobStore,SubmissionLock

def digest(raw):return hashlib.sha256(raw).hexdigest()
def admission():
    if sys.argv[3]!='submit':return
    if datetime.now(TZ).date().isoformat()!=DAY:raise RuntimeError('Beijing day changed; no new upload')
    if '--repeat' in sys.argv:raise RuntimeError('Repeat uploads prohibited')
    auth=json.loads((OUT/'authorization.json').read_text(encoding='utf-8'))
    if auth['date']!=DAY or auth['authorization']!='优化30次，全部根据线上数据，你打表的数据可以参考总结规律，但是不能写死参数':raise RuntimeError('Authorization mismatch')
    sha=sys.argv[2];proof=json.loads((OUT/'qualifications'/(sha+'.json')).read_text(encoding='utf-8'))
    source=Path(sys.argv[sys.argv.index('--file')+1]).resolve();raw=source.read_bytes();code=raw.decode('utf-8-sig')
    if source!=OUT/(proof['candidate']+'.cpp') or digest(raw)!=sha or proof['sha256']!=sha:raise RuntimeError('Frozen source mismatch')
    if proof.get('claimed_local_winner') or not proof.get('rationale'):raise RuntimeError('Online trial hypothesis missing')
    candidate_review(raw)
    if re.search(r'fingerprint|deferred|\bn\s*==\s*\d+|\b(?:586|662|774)\b',code):raise RuntimeError('Fixed-case lookup or fingerprint audit failed')
    rows=[]
    for case in make_suite('smoke',2026):
        r=run_case([str(source.with_suffix('.exe'))],case);path=r['query_positions']
        winner=min(set(path),key=lambda x:(-case.values[x],abs(2*x-(len(case.values)-1)),x)) if path else None
        r['parked_observed_winner']=bool(path) and r['final_position']==winner;rows.append(r)
    native_passed=len(rows)==26 and not any(r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or not r['parked_observed_winner'] for r in rows)
    static_certificate=None
    if not native_passed:
        from guard_equivalence_20261108 import appcontrol_only_missing_cases,audit
        if len(rows)!=26 or not appcontrol_only_missing_cases(rows):raise RuntimeError('Protocol/query/turn/parking failure')
        static_certificate=audit(raw,proof['flags'])
    config=load_config();store=JobStore(Path(config['runs_directory']));jobs=[store.load(p.parent.name) for p in store.root.glob('*/job.json')]
    if any(j['sha256']==sha and j['state']!='snapshot_ready' for j in jobs):raise RuntimeError('Already attempted source; resume only')
    today=[j for j in jobs if j.get('submission_attempt_at','').startswith(DAY)]
    with connect(config) as page:
        page.records(refresh=True);quota=parse_quota(page.page.locator('body').inner_text())
    if len(today)>=30 or quota['used']>=30 or quota['beijing_date']!=DAY:raise RuntimeError('Daily quota exhausted')
    (OUT/(proof['candidate']+'_admission.json')).write_text(json.dumps(dict(date=DAY,quota=quota,sha256=sha,proof=proof,rows=rows,native_passed=native_passed,static_certificate=static_certificate),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
    if len(sys.argv)<4 or sys.argv[1]!='--judge':raise SystemExit('Use --judge SHA submit|wait')
    with SubmissionLock(OUT/'.online-round.lock'):
        admission();p=ROOT/'dev/tools/wave_round_20261106.py';s=p.read_text(encoding='utf-8').replace("'2026-11-06'","'2026-11-08'")
        ns={'__name__':'day8_judge','__file__':str(p)};exec(compile(s,str(p),'exec'),ns);raise SystemExit(ns['judge']())
