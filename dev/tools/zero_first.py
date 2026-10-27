"""Per-case zero ledger and lexicographic research ranking.

All measured zeros are retained, including information-limited arrays. A higher
mean cannot compensate for a newly introduced zero. Transform siblings veto
regressions but never inflate the count of independently repaired mother curves.
This evaluates finite observed curves; it is not a hidden-array guarantee.
"""
from __future__ import annotations
from collections import Counter, defaultdict

VERSION=2

def analyze(rows, baseline, metadata, curve_ids=None):
    if len(rows)!=len(baseline) or len(rows)!=len(metadata):
        raise ValueError('Unpaired case counts')
    names=[r['name'] for r in rows]
    if len(set(names))!=len(names) or names!=[r['name'] for r in baseline]:
        raise ValueError('Unpaired or duplicate case identities')
    if curve_ids is not None and len(curve_ids)!=len(rows):raise ValueError('Unpaired curve fingerprints')
    independent=[];hard=[];new=[];ledger=[];repairs=[];groups=defaultdict(list)
    seen_curves={};duplicate_bases=[]
    seen_clusters=set()
    for index,(r,b,m) in enumerate(zip(rows,baseline,metadata)):
        if r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or not r.get('parked_observed_winner'):
            hard.append(r['name'])
        introduced=r['score']==0 and b['score']>0
        resolved=r['score']>0 and b['score']==0
        if introduced:new.append(r['name'])
        if resolved:repairs.append(r['name'])
        if r['score']==0:
            ledger.append(dict(name=r['name'],split=m['split'],family=m['family'],cluster=m['cluster'],
                transform=m['transform'],difficulty=r['difficulty'],introduced=introduced,
                reasons=r.get('zero_reasons') or ['score floor or protocol failure'],queries=r['queries'],
                oscillations=r['oscillations'],redundancy=r['redundancy'],distance=r['distance'],
                final_position=r['final_position'],target=r.get('target'),baseline_score=b['score']))
        if m['transform']=='base':
            if m['cluster'] in seen_clusters:raise ValueError('Duplicate mother identity')
            seen_clusters.add(m['cluster'])
            curve=curve_ids[index] if curve_ids is not None else m['cluster']
            if curve in seen_curves:
                duplicate_bases.append(dict(name=r['name'],same_as=seen_curves[curve]));continue
            seen_curves[curve]=r['name'];independent.append((r,b,m))
            groups[(m['split'],m['family'],r['difficulty'])].append((r,b,m))
    families={};structured_rates=[];means=[];reasons=Counter()
    for key,items in sorted(groups.items()):
        zeros=sum(r['score']==0 for r,b,m in items)
        baseline_zeros=sum(b['score']==0 for r,b,m in items)
        fam=dict(cases=len(items),zero_cases=zeros,baseline_zero_cases=baseline_zeros,
            repaired_cases=sum(r['score']>0 and b['score']==0 for r,b,m in items),
            new_zero_cases=sum(r['score']==0 and b['score']>0 for r,b,m in items),
            zero_rate=zeros/len(items),mean_score=sum(r['score'] for r,b,m in items)/len(items))
        families['/'.join(key)]=fam;means.append(fam['mean_score'])
        if key[2]!='information_limited':structured_rates.append(fam['zero_rate'])
    positive=sorted(r['score'] for r,b,m in independent if r['score']>0)
    low=positive[int((len(positive)-1)*.1)] if positive else 0
    zero_count=sum(r['score']==0 for r,b,m in independent)
    worst=max(structured_rates,default=0);macro=sum(means)/max(1,len(means))
    for r,b,m in independent:
        if r['score']==0:reasons.update(r.get('zero_reasons') or ['score floor or protocol failure'])
    return dict(version=VERSION,objective='zero_first',
        observed_cases=len(rows),independent_mothers=len(independent),unique_base_curves=len(independent),
        exact_duplicate_base_entries=duplicate_bases,
        structured_unique_zero_cases=sum(r['score']==0 and r['difficulty']!='information_limited' for r,b,m in independent),
        information_limited_unique_zero_cases=sum(r['score']==0 and r['difficulty']=='information_limited' for r,b,m in independent),
        hard_failures=hard,introduced_zeros_all_cases=new,independent_zero_cases=zero_count,
        independent_baseline_zero_cases=sum(b['score']==0 for r,b,m in independent),
        independent_repairs=sum(r['score']>0 and b['score']==0 for r,b,m in independent),
        repair_entries_including_siblings=len(repairs),worst_structured_group_zero_rate=worst,
        positive_p10_score=low,macro_mean_score=macro,
        rank_key=[len(hard),len(new),zero_count,worst,-low,-macro],
        all_observed_cases_nonzero=not ledger and not hard,
        zero_reason_counts=dict(reasons),zero_reasons_may_overlap=True,
        groups=families,zero_ledger=ledger,
        note='Lower rank_key is better. New zeros are vetoes in research promotion; existing zeros remain unresolved until actually measured positive. Exact repeated base arrays are deduplicated when curve fingerprints are supplied. No universal claim.')


def redundancy_conflict(first, second, redundancy_limit=199, distance_tolerance=3):
    """Prove incompatible positive-score requirements from identical histories.

    The first curve forbids queries beyond its target+redundancy_limit. If all
    legal-prefix replies match a second curve whose acceptable final interval
    lies strictly further right, a policy cannot distinguish them in time.
    This is an exact finite-pair certificate, independent of a candidate solver.
    """
    if type(redundancy_limit) is not int or type(distance_tolerance) is not int or redundancy_limit<0 or distance_tolerance<0:
        raise ValueError('Bounds must be nonnegative integers')
    if len(first.values)!=len(second.values):
        return None
    bound=min(len(first.values)-1,first.target+redundancy_limit)
    if first.values[:bound+1]!=second.values[:bound+1]:
        return None
    other_low=max(0,second.target-distance_tolerance)
    if other_low<=bound:
        return None
    return dict(type='identical_safe_prefix_redundancy_conflict',
        first=first.name,second=second.name,length=len(first.values),
        first_target=first.target,second_target=second.target,
        first_maximum_safe_query=bound,identical_prefix_replies=bound+1,
        second_acceptable_final_interval=[other_low,min(len(second.values)-1,second.target+distance_tolerance)],
        redundancy_limit=redundancy_limit,distance_tolerance=distance_tolerance,
        unavoidable_zeros_at_least=1,all_cases_nonzero_guarantee_possible=False,
        proof='On the first curve every positive run stays at or left of the safe bound. The second curve gives identical replies there and has the same length, so the same policy follows the same history. A successful final query for the second must cross the bound and would already make the first zero. Holds also for every fixed random seed.')
