"""Diagnose cached coarse coverage failures. Oracle uses are offline-only labels.
No solver, network, upload or new performance-confirmation run is started.
"""
from pathlib import Path
import argparse,bisect,collections,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev'))
from tools.local_judge import score_path,target_index

def classify(values,row):
    n=len(values);target=target_index(values)
    if row['status']!='ok':return dict(category='protocol_or_runtime_failure',target=target)
    if row['score']>0:return dict(category='positive',target=target)
    match=re.search(r'TRACE (\{[^\r\n]*\})',row.get('stderr',''))
    if not match:return dict(category='no_coarse_trace',target=target)
    trace=json.loads(match.group(1));frontier=trace['coarse_frontier'];path=row['query_positions']
    if frontier not in path:return dict(category='unresolved_coarse_prefix',target=target)
    prefix=path[:path.index(frontier)+1]
    if any(a>b for a,b in zip(prefix,prefix[1:])):return dict(category='nonmonotone_coarse_prefix',target=target)
    result=dict(target=target,coarse_frontier=frontier,coarse_queries=len(prefix),remaining_with_one_parking=199-len(prefix)-1,actual_queries=row['queries'],unused_final_query_budget=199-row['queries'])
    if frontier-target>=200:return result|dict(category='irreversible_coarse_redundancy')
    if target>frontier+3:return result|dict(category='uncovered_right_target')
    if row['distance']<=3:return result|dict(category='zero_despite_close_parking')
    if target>frontier:return result|dict(category='right_edge_near_miss')
    xs=sorted(set(prefix))
    if target in xs:return result|dict(category='observed_target_not_parked')
    at=bisect.bisect_left(xs,target)
    if not 0<at<len(xs):return result|dict(category='outside_coarse_bracket')
    left,right=xs[at-1],xs[at]
    best=min(xs,key=lambda x:(-values[x],abs(2*x-(n-1)),x))
    gaps=[(a,b) for a,b in zip(xs,xs[1:]) if b-a>1]
    # Observable endpoint ranking; target is only used below to label its rank.
    gaps.sort(key=lambda ab:(-max(values[ab[0]],values[ab[1]]),-(values[ab[0]]+values[ab[1]]),abs(ab[0]+ab[1]-2*best),ab[0]))
    rank=gaps.index((left,right))+1
    fill=list(range(right-1,left,-1));counterfactual=prefix+fill
    winner=min(set(counterfactual),key=lambda x:(-values[x],abs(2*x-(n-1)),x))
    if counterfactual[-1]!=winner:counterfactual.append(winner)
    m=score_path(values,counterfactual)
    legal=m['queries']<=199 and m['oscillations']<=6
    return result|dict(category='covered_unread_target',target_gap=[left,right],endpoint_gap_rank=rank,gap_unread_points=len(fill),coarse_observed_winner=best,oracle_gap_fill_legal=legal,oracle_gap_fill_score=m['score'] if legal else 0,oracle_gap_fill_queries=m['queries'],oracle_gap_fill_turns=m['oscillations'])

def analyze(study,solver='formal203239'):
    raw=ROOT/'dev/build/research'/Path(study).name
    cases=json.loads((raw/'cases.json').read_text(encoding='utf-8'))
    report=json.loads((raw/(solver+'.json')).read_text(encoding='utf-8'))
    if len(cases)!=len(report['rows']):raise ValueError('unpaired cases/results')
    seen=set();details=[];categories=collections.Counter();families=collections.defaultdict(collections.Counter);ranks=collections.Counter();budget=collections.defaultdict(list);total=0
    for c,row in zip(cases,report['rows']):
        if c['name']!=row['name']:raise ValueError('case identity mismatch')
        meta=c['metadata']
        if meta['transform']!='base' or meta['split']=='regression':continue
        key=hashlib.sha256(json.dumps(c['values'],separators=(',',':')).encode()).hexdigest()
        if key in seen:continue
        seen.add(key);total+=1;entry=classify(c['values'],row);cat=entry['category'];categories[cat]+=1;families[c['family']][cat]+=1
        if cat!='positive':
            entry.update(name=c['name'],family=c['family'],split=meta['split'],array_sha256=key);details.append(entry)
            if 'unused_final_query_budget' in entry:budget[cat].append(entry['unused_final_query_budget'])
        if cat=='covered_unread_target':ranks[entry['endpoint_gap_rank']]+=1
    gapcases=[d for d in details if d['category']=='covered_unread_target'];zeros=total-categories['positive']
    return dict(study=Path(study).as_posix(),solver=solver,source_sha256=report['source_sha256'],dataset_sha256=report['dataset_sha256'],analysis_only=True,new_validation_cases=0,independent_cached_base_cases=total,zeros=zeros,categories=dict(categories),category_share_of_zeros={k:v/max(1,zeros) for k,v in categories.items() if k!='positive'},covered_gap_rank_histogram=dict(sorted(ranks.items())),covered_gap_top_k={str(k):sum(d['endpoint_gap_rank']<=k for d in gapcases) for k in [1,2,3,5,10]},covered_gap_feasible_oracle_rescues=sum(d['oracle_gap_fill_legal'] and d['oracle_gap_fill_score']>0 for d in gapcases),covered_gap_oracle_score_upper=sum(d['oracle_gap_fill_score'] for d in gapcases),unused_query_budget_by_category={k:dict(mean=sum(v)/len(v),min=min(v),max=max(v)) for k,v in budget.items()},families={k:dict(v) for k,v in families.items()},details=details,warning='Target labels and chosen-gap sweeps use the synthetic oracle for diagnosis only. Ranking is observable, selecting the true gap is not. Rescue counts/scores are not achievable algorithm claims or official per-case results. Cached data is consumed development evidence, not new blind confirmation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--study',required=True);ap.add_argument('--solver',default='formal203239');ap.add_argument('--out',required=True);a=ap.parse_args();d=analyze(a.study,a.solver);p=ROOT/a.out;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in d.items() if k not in ['details','families','warning']}))
if __name__=='__main__':main()
