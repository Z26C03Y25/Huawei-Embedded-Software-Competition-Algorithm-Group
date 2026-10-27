"""Decompose observed synthetic score loss; no hidden-data performance claim."""
from pathlib import Path
import argparse,collections,hashlib,json
ROOT=Path(__file__).resolve().parents[2]

def explain(result):
    upper=2999-result['target']
    if result['score']==0:
        return dict(omniscient_upper=upper,loss=upper,zero_cliff=upper)
    components=dict(query=result['queries']-1,extra_travel=result['travel']-result['target'],
        turns=result['oscillations'],redundancy=result['redundancy'],distance=200*result['distance'])
    loss=upper-result['score']
    if sum(components.values())!=loss:raise ValueError('Score decomposition does not match checker')
    return dict(omniscient_upper=upper,loss=loss,positive_components=components)

def analyze(study,solver):
    study=Path(study);raw=ROOT/'dev/build/research'/study.name
    cases=json.loads((raw/'cases.json').read_text(encoding='utf-8'))
    report=json.loads((raw/(solver+'.json')).read_text(encoding='utf-8'));rows=report['rows']
    if len(cases)!=len(rows):raise ValueError('Unpaired rows')
    seen=set();components=collections.Counter();reasons=collections.Counter();families=collections.defaultdict(lambda:collections.Counter())
    total=collections.Counter();distances=collections.Counter()
    for c,r in zip(cases,rows):
        m=c['metadata']
        if m['transform']!='base' or m['split']=='regression':continue
        if c['name']!=r['name']:raise ValueError('Unpaired identity')
        key=hashlib.sha256(json.dumps(c['values'],separators=(',',':')).encode()).hexdigest()
        if key in seen:continue
        seen.add(key);e=explain(r);total['cases']+=1;total['actual_score']+=r['score'];total['omniscient_upper']+=e['omniscient_upper']
        family=families[c['family']];family['cases']+=1;family['score']+=r['score']
        if r['score']==0:
            total['zeros']+=1;total['zero_cliff_loss']+=e['zero_cliff'];family['zero_cliff_loss']+=e['zero_cliff'];family['zeros']+=1
            reasons.update(r['zero_reasons'] or ['score_floor_or_protocol'])
        else:
            total['positive']+=1;total['positive_loss']+=e['loss'];components.update(e['positive_components']);distances[r['distance']]+=1
    gap=total['omniscient_upper']-total['actual_score'];assert gap==total['zero_cliff_loss']+total['positive_loss']
    return dict(official=False,study=study.as_posix(),solver=solver,source_sha256=report['source_sha256'],totals=dict(total),
        positive_loss_components=dict(components),positive_distance_histogram=dict(distances),zero_reason_counts=dict(reasons),zero_reasons_overlap=True,
        failure_share_of_observed_oracle_gap=total['zero_cliff_loss']/max(1,gap),
        positive_component_shares={k:v/max(1,total['positive_loss']) for k,v in components.items()},families=dict(families),
        warning='2999-target is an omniscient one-query upper bound, not a feasible score promise. extra_travel may be slightly negative when final position is left of target. All measured zeros retain their full loss; components are not conditioned away from the main total.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',required=True);p.add_argument('--solver',default='champion');p.add_argument('--out',required=True);a=p.parse_args()
    result=analyze(a.study,a.solver);out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('families','warning')}))
if __name__=='__main__':main()