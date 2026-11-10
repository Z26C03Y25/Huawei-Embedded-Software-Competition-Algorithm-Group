"""Compare finished local executables on independent classic and mixed waves."""
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/experiments/blackbox_20261106'
sys.path.insert(0, str(ROOT / 'dev'))
from tools.local_judge import make_suite, run_case
from tools.mixed_scenarios import make_scenarios

def online_cost_proxy(row):
    return max(0, row['score']-29*row['oscillations'])

def stats(scores):
    ordered = sorted(scores)
    return {'mean': round(statistics.mean(scores),2),
            'zero': sum(s==0 for s in scores),
            'count':len(scores),
            'cvar25':round(statistics.mean(ordered[:max(1,len(ordered)//4)]),2)}

def evaluate(entry, suites):
    path=Path(entry['snapshot_path']).parent / 'candidate.exe'
    output={'name':entry['name'],'source_sha256':entry['sha256']}
    for suite,cases in suites.items():
        rows=[run_case([str(path)],case) for case in cases]
        families=defaultdict(list)
        for row in rows:
            families[row['family']].append(online_cost_proxy(row))
        output[suite]=dict(stats([online_cost_proxy(row) for row in rows]),
                           families={family:stats(scores) for family,scores in families.items()},
                           failures=[{key:r[key] for key in ('name','status','score','queries','oscillations','final_position','target')} for r in rows if r['score']==0 or r['status']!='ok'])
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('names',nargs='*')
    args=parser.parse_args()
    state=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
    entries=[r for r in state['rounds'] if r.get('preflight',{}).get('passed') and
             (not args.names or r['name'] in args.names)]
    suites={'classic': make_suite('extended',2026110619),
            'mixed': [c for c,m in make_scenarios(per_family=2,splits=['blind_shift'],
                        seed_tag=2026110624,novel=True) if m['transform']=='base']}
    with ThreadPoolExecutor(max_workers=4) as pool:
        reports=list(pool.map(lambda r:evaluate(r,suites),entries))
    p=OUT/'local_wave_comparison.json'
    p.write_text(json.dumps(dict(official=False,score_proxy='paper score minus 29 per reversal when feasible',
                                 classic_seed=2026110619,mixed_seed=2026110624,
                                 reports=reports),ensure_ascii=False,indent=2),encoding='utf-8')
    for row in sorted(reports,key=lambda r:r['classic']['mean']+r['mixed']['mean'],reverse=True):
        print(row['name'],*(f"{s}:{row[s]['mean']}/{row[s]['zero']} zeros/{row[s]['cvar25']} low" for s in suites))
if __name__=='__main__':
    main()
