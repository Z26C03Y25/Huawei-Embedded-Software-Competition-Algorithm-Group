"""Mean score INCLUDING zeros is the objective; tail risk is a validation check.

Fixed before evaluation: equal family/split weight on fresh base curves, exact
array deduplication, siblings reported without independent weight. Individual new
zeros are audited but do not veto net gains. No official-distribution inference.
"""
from __future__ import annotations
from collections import defaultdict
import math,random
VERSION=1
FRESH=('development','selection','blind_shift')

def mean(values):return sum(values)/len(values) if values else 0.0

def cvar25(values):
    if not values:return 0.0
    values=sorted(values);mass=len(values)*.25;whole=int(mass);fraction=mass-whole
    return (sum(values[:whole])+(fraction*values[whole] if fraction else 0))/mass

def lower10(values):
    return sorted(values)[int(.1*(len(values)-1))] if values else 0

def _stats(items):
    groups=defaultdict(list)
    for r,b,m in items:groups[m['family']].append((r,b,m))
    families={}
    for family,group in sorted(groups.items()):
        scores=[r['score'] for r,b,m in group];before=[b['score'] for r,b,m in group]
        families[family]=dict(cases=len(group),mean=mean(scores),baseline_mean=mean(before),
            delta=mean(scores)-mean(before),zeros=sum(x==0 for x in scores),
            baseline_zeros=sum(x==0 for x in before),
            difficulty=group[0][0]['difficulty'])
    scores=[r['score'] for r,b,m in items];before=[b['score'] for r,b,m in items]
    n=max(1,len(items))
    return dict(cases=len(items),families=families,
        structured_family_count=sum(f['difficulty']!='information_limited' for f in families.values()),
        macro_mean=mean([f['mean'] for f in families.values()]),
        baseline_macro_mean=mean([f['baseline_mean'] for f in families.values()]),
        macro_delta=mean([f['delta'] for f in families.values()]),
        mean=mean(scores),baseline_mean=mean(before),
        zeros=sum(x==0 for x in scores),baseline_zeros=sum(x==0 for x in before),
        zero_rate_delta=(sum(x==0 for x in scores)-sum(x==0 for x in before))/n,
        cvar25=cvar25(scores),baseline_cvar25=cvar25(before),cvar25_delta=cvar25(scores)-cvar25(before),
        p10=lower10(scores),baseline_p10=lower10(before),
        new_zeros=sum(r['score']==0 and b['score']>0 for r,b,m in items),
        resolved_zeros=sum(r['score']>0 and b['score']==0 for r,b,m in items))

def analyze(rows,baseline,metadata,curve_ids=None,min_cases=1000,min_families=12,bootstrap=1000):
    if len(rows)!=len(baseline) or len(rows)!=len(metadata):raise ValueError('unpaired lengths')
    if curve_ids is not None and len(curve_ids)!=len(rows):raise ValueError('unpaired curve identities')
    names=[r['name'] for r in rows]
    if names!=[b['name'] for b in baseline] or len(set(names))!=len(names):raise ValueError('unpaired case identity')
    if bootstrap<100:raise ValueError('too few bootstrap replicates')
    seen=set();selected=[];hard=[];new=[]
    for i,(r,b,m) in enumerate(zip(rows,baseline,metadata)):
        if r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or not r.get('parked_observed_winner'):
            hard.append(r['name'])
        if r['score']==0 and b['score']>0:new.append(r['name'])
        if m['transform']!='base':continue
        key=curve_ids[i] if curve_ids is not None else m['cluster']
        if key in seen:continue
        seen.add(key);selected.append((r,b,m))
    groups={s:_stats([i for i in selected if i[2]['split']==s]) for s in (*FRESH,'regression')}
    fresh=[i for i in selected if i[2]['split'] in FRESH]
    overall=_stats(fresh)
    # Equal weight to each fresh split and each family, regardless of duplicates.
    overall['macro_mean']=mean([groups[s]['macro_mean'] for s in FRESH])
    overall['baseline_macro_mean']=mean([groups[s]['baseline_macro_mean'] for s in FRESH])
    overall['macro_delta']=mean([groups[s]['macro_delta'] for s in FRESH])
    strata=defaultdict(list)
    for r,b,m in fresh:
        if m['split']!='development':strata[(m['split'],m['family'])].append(r['score']-b['score'])
    rng=random.Random(2026102603);boot=[]
    if strata:
        for _ in range(bootstrap):boot.append(mean([mean([rng.choice(ds) for j in ds]) for ds in strata.values()]))
        boot.sort();ci=[boot[int(.025*(bootstrap-1))],boot[int(.975*(bootstrap-1))]]
    else:ci=[0,0]
    reasons=[]
    if hard:reasons.append('protocol/query/turn/parking failure')
    if len(fresh)<min_cases:reasons.append('insufficient fresh base cases')
    for split in ('selection','blind_shift'):
        g=groups[split]
        if g['structured_family_count']<min_families:reasons.append(split+': insufficient family coverage')
        if g['macro_delta']<=0:reasons.append(split+': no positive total-score gain')
        if g['zero_rate_delta']>1e-12:reasons.append(split+': aggregate zero rate increased')
        if g['cvar25_delta'] < -1e-9:reasons.append(split+': lower-quarter score deteriorated')
    if ci[0]<=0:reasons.append('pooled held-out score gain remains uncertain')
    return dict(version=VERSION,objective='robust_total_score',groups=groups,overall=overall,
        independent_fresh_cases=len(fresh),hard_failures=hard,new_zero_entries_all_measured=new,
        heldout_macro_delta_ci95=ci,
        rank_key=[len(hard),-overall['macro_mean'],overall['zeros']/max(1,len(fresh)),-overall['cvar25']],
        qualification=dict(eligible=not reasons,reasons=reasons,
          note='For limited online validation only. Total score includes zeros; individual losses allowed. Held-out mean, aggregate zero rate and CVaR25 checked. Synthetic cohorts do not identify official performance.'))
