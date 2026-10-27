"""Offline-first gate for automatic research controllers, not the manual CLI.

Apply only before a NEW upload. Already delivered/uncertain jobs must always be
resumed first, even after the local cap or official quota is reached.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib, json
from pathlib import Path
TZ=timezone(timedelta(hours=8))
class ResearchPause(RuntimeError):pass

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inside(root,path):
    result=(root/path).resolve()
    try:result.relative_to(root.resolve())
    except ValueError:raise ResearchPause('Evidence/source must stay inside repository')
    return result

def cached_day_stop(root,now=None):
    now=now or datetime.now(TZ);today=now.astimezone(TZ).date().isoformat()
    p=root/'data/experiments/research_state.json'
    if not p.exists():return None
    state=read(p)
    if state.get('confirmed_platform_quota_date')==today and state.get('confirmed_remaining_submissions')==0:
        return 'official_quota_exhausted_today'
    return None

def check_local_evidence(info,root):
    policy=read(root/'automation/research_policy.json')
    if policy.get('mode')!='offline_first':raise ResearchPause('Unsupported research policy')
    source=inside(root,info.get('source') or info['path'])
    digest=sha(source)
    if digest!=info['sha256']:raise ResearchPause('Candidate source changed')
    records=read(root/'data/versions/online_search/results.json')
    parent=max(records,key=lambda r:r['score'])['sha256']
    entries=read(inside(root,policy['qualified_candidates']))['candidates']
    entry=next((x for x in entries if x.get('sha256')==digest and x.get('status')=='qualified'),None)
    if not entry:raise ResearchPause('Candidate has no broad local qualification; continue offline')
    if entry.get('parent_sha256')!=parent:raise ResearchPause('Evidence parent is no longer the official best')
    condition=entry.get('execution_condition')
    if condition:
        if condition.get('kind')!='primary_not_improved':raise ResearchPause('Unknown trial execution condition')
        dated=[]
        for r in records:
            if r.get('sha256')!=condition['primary_sha256']:continue
            try:day=datetime.fromisoformat(str(r.get('submitted_at',''))[:10]).date().isoformat()
            except ValueError:continue
            if day>=condition['not_before_date']:dated.append(r)
        if not dated:raise ResearchPause('Primary trial needs a recorded official result before this backup')
        primary=max(dated,key=lambda r:r['submitted_at'])
        if primary['score']>condition['baseline_score']:
            raise ResearchPause('Primary improved; do not consume quota on the conservative backup')

    evidence=inside(root,entry['evidence'])
    if sha(evidence)!=entry['evidence_sha256']:raise ResearchPause('Evidence report changed')
    report=read(evidence);manifest=inside(root,entry['manifest'])
    if sha(manifest)!=report.get('manifest_sha256'):raise ResearchPause('Frozen manifest changed')
    manifest_data=read(manifest)
    if manifest_data.get('generator_version',0)<policy['minimum_generator_version']:
        raise ResearchPause('Generator evidence predates the corrected family taxonomy')
    if not manifest_data.get('fixed_before_scoring'):raise ResearchPause('Inputs were not frozen before scoring')
    solvers=manifest_data['solvers']
    if solvers[0]['sha256']!=parent:raise ResearchPause('Comparison baseline is not the official best')
    candidate=next((s for s in solvers if s['sha256']==digest),None)
    if not candidate:raise ResearchPause('Candidate absent from frozen manifest')
    result=report['solvers'][candidate['name']]
    if report.get('official') is not False or not result.get('qualification',{}).get('eligible'):
        raise ResearchPause('Local evidence does not qualify')
    zero=result.get('zero_first',{})
    if policy['research_objective']=='robust_total_score':
        if manifest_data.get('research_policy_sha256')!=sha(root/'automation/research_policy.json'):
            raise ResearchPause('Score evidence uses a different objective policy')
        if manifest_data.get('score_analysis_sha256')!=sha(root/'dev/tools/robust_score.py'):
            raise ResearchPause('Score evaluator changed since the frozen study')
        score=result.get('robust_score',{})
        if score.get('objective')!='robust_total_score' or score.get('version',0)<policy['minimum_robust_analysis_version']:
            raise ResearchPause('Missing robust total-score audit')
        if result['hard_failures'] or score.get('hard_failures') or result['max_queries']>199 or result['max_turns']>6:
            raise ResearchPause('Protocol/query/turn/parking failure')
        if score.get('independent_fresh_cases',0)<policy['min_independent_base_cases']:
            raise ResearchPause('Insufficient fresh score samples')
        for split in ('selection','blind_shift'):
            g=score['groups'][split]
            if g['structured_family_count']<policy['min_structured_families']:
                raise ResearchPause('Insufficient family coverage')
            if g['macro_delta']<=0 or g['zero_rate_delta']>1e-12 or g['cvar25_delta'] < -1e-9:
                raise ResearchPause('Held-out total score or aggregate robustness failed')
        if score['heldout_macro_delta_ci95'][0]<=0:
            raise ResearchPause('Uncertain pooled held-out score gain')
        if entry.get('claims_all_measured_nonzero') and not zero.get('all_observed_cases_nonzero'):
            raise ResearchPause('Claimed all-nonzero contract is not met')
        return entry
    if zero.get('objective')!=policy['research_objective'] or zero.get('version',0)<policy['minimum_zero_analysis_version']:
        raise ResearchPause('Evidence lacks the current zero-first audit')
    if zero.get('hard_failures') or zero.get('introduced_zeros_all_cases'):
        raise ResearchPause('Zero-first audit found a new zero or hard failure')
    if entry.get('claims_all_measured_nonzero') and not zero.get('all_observed_cases_nonzero'):
        raise ResearchPause('Claimed all-nonzero contract is not met')
    if result['independent_base_cases']<policy['min_independent_base_cases'] or result['hard_failures']:
        raise ResearchPause('Insufficient samples or a hard failure')
    if result['max_queries']>199 or result['max_turns']>6:raise ResearchPause('Query/oscillation budget failed')
    for split in ('development','selection','blind_shift'):
        g=result['groups'][split]
        families=[f for f in g['families'] if f not in ('random_unstructured','single_spike')]
        if len(families)<policy['min_structured_families']:raise ResearchPause('Insufficient structured diversity')
        if g['structured_new_zero'] or g['macro_mean_delta']<=0:raise ResearchPause('Unstable local gain or new zeros')
        if g['worst_family_mean_delta'] < -policy['max_family_mean_regression']:raise ResearchPause('Family regression')
        if split!='development' and g['stratified_base_bootstrap_95'][0]<=0:raise ResearchPause('Uncertain held-out gain')
    return entry

def authorize_new_upload(info,quota,root,now=None):
    now=now or datetime.now(TZ);today=now.astimezone(TZ).date().isoformat()
    if cached_day_stop(root,now):raise ResearchPause('Official quota already confirmed0 today; no new request/upload')
    policy=read(root/'automation/research_policy.json')
    used=quota.get('used');limit=quota.get('limit');remaining=quota.get('remaining')
    if type(used) is not int or type(limit) is not int or type(remaining) is not int or not 0<=used<=limit<=30 or remaining!=limit-used:
        raise ResearchPause('Invalid official team quota')
    if quota.get('date')!=today:raise ResearchPause('Stale quota date')
    try:checked=datetime.fromisoformat(quota['checked_at'])
    except (ValueError,KeyError):raise ResearchPause('Quota timestamp unavailable')
    if checked.tzinfo is None or not 0<=(now-checked).total_seconds()<=policy['quota_fresh_seconds']:
        raise ResearchPause('Quota needs a fresh official read before upload')
    if not remaining:raise ResearchPause('Official daily quota exhausted')
    if used>=policy['auto_daily_team_cap']:raise ResearchPause('Local automatic team cap reached; continue offline')
    return check_local_evidence(info,root)


if __name__=='__main__':
    import argparse,sys
    parser=argparse.ArgumentParser(description='Read-only local evidence/condition check; does not check live quota or upload.')
    parser.add_argument('source');parser.add_argument('--sha256')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    try:
        path=inside(root,args.source)
        info=dict(source=args.source,sha256=args.sha256 or sha(path))
        entry=check_local_evidence(info,root)
        print(json.dumps(dict(local_evidence_eligible=True,name=entry['name'],sha256=entry['sha256'],live_quota_still_required=True)))
    except ResearchPause as exc:
        print(json.dumps(dict(local_evidence_eligible=False,reason=str(exc))))
        sys.exit(2)
