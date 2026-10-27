"""Freeze and screen fixed solver operators with real interactive pipes.

Example: python dev/tools/screen_operators.py --out data/experiments/my-study
 --program formal=main.cpp --program candidate=data/experiments/candidate.cpp
No networking. Reuse the same output directory to resume unchanged inputs only.
Raw cases and paths are ignored under dev/build/research; the public summary
records hashes, grouped evidence and retained counterexamples.
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, shutil, subprocess, sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'dev'),str(ROOT/'automation')]
from tools.scenario_factory import make_scenarios, FAMILIES, SEEDS, VERSION
from tools.zero_first import analyze as zero_analysis
from tools.robust_score import analyze as score_analysis
from tools.local_judge import Case, make_suite, run_case
from online_judge.jobs import SubmissionLock


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def encode(data):return json.dumps(data,sort_keys=True,separators=(',',':')).encode()


def paired(rows,baseline,metadata,curve_ids=None):
    pairs=list(zip(rows,baseline,metadata))
    groups={}
    for split in [*SEEDS,'regression']:
        members=[(r,b,m) for r,b,m in pairs if m['split']==split]
        if not members:continue
        fam={}
        for family in sorted({m['family'] for r,b,m in members}):
            group=[(r,b,m) for r,b,m in members if m['family']==family]
            base=[(r,b,m) for r,b,m in group if m['transform']=='base']
            deltas=[r['score']-b['score'] for r,b,m in base]
            fam[family]=dict(cases=len(group),base_cases=len(base),delta=sum(deltas),
              mean_delta=sum(deltas)/max(1,len(deltas)),
              zeros=sum(r['score']==0 for r,b,m in group),
              new_zero=sum(r['score']==0 and b['score']>0 for r,b,m in group),
              resolved_zero=sum(r['score']>0 and b['score']==0 for r,b,m in group),
              path_changed=sum(r['query_positions']!=b['query_positions'] for r,b,m in group))
        structured=[(r,b,m) for r,b,m in members if r['difficulty']!='information_limited' and m['transform']=='base']
        by_family=defaultdict(list)
        for r,b,m in structured:by_family[m['family']].append(r['score']-b['score'])
        means=[sum(ds)/len(ds) for ds in by_family.values()]
        boot=[];rng=random.Random(20261026)
        if means:
            for _ in range(1000):
                boot.append(sum(sum(rng.choice(ds) for j in ds)/len(ds) for ds in by_family.values())/len(by_family))
            boot.sort()
        groups[split]=dict(families=fam,base_structured_cases=len(structured),
          macro_mean_delta=sum(means)/max(1,len(means)),
          stratified_base_bootstrap_95=[boot[24],boot[974]] if boot else [0,0],
          worst_family_mean_delta=min(means,default=0),
          structured_new_zero=sum(r['score']==0 and b['score']>0 for r,b,m in members if r['difficulty']!='information_limited'),
          structured_resolved_zero=sum(r['score']>0 and b['score']==0 for r,b,m in members if r['difficulty']!='information_limited'))
    hard=[]
    for r,b,m in pairs:
        if r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or not r.get('parked_observed_winner'):
            hard.append(r['name'])
    zero_first=zero_analysis(rows,baseline,metadata,curve_ids)
    reasons=[]
    if zero_first['introduced_zeros_all_cases']:reasons.append('new zero in measured cases, including information-limited or transformed cases')
    independent=sum(m['transform']=='base' and m['split']!='regression' for m in metadata)
    if independent<1000:reasons.append('fewer than1000 independent base cases')
    if hard:reasons.append('protocol/budget/parking failure')
    for split in SEEDS:
        if split not in groups:
            reasons.append(split+': missing split');continue
        g=groups[split]
        if g['structured_new_zero']:reasons.append(split+': newly introduced structured zeros')
        if g['macro_mean_delta']<=0:reasons.append(split+': nonpositive family-balanced gain')
        if g['worst_family_mean_delta'] < -25:reasons.append(split+': family degradation exceeds25 mean points')
        if split!='development' and g['stratified_base_bootstrap_95'][0]<=0:
            reasons.append(split+': bootstrap lower bound does not exceed0')
    if groups.get('regression',{}).get('structured_new_zero'):reasons.append('retained regression newly fails')
    repairs=sum(groups.get(s,{}).get('structured_resolved_zero',0) for s in SEEDS)
    if not repairs and min(groups.get(s,{}).get('macro_mean_delta',0) for s in SEEDS)<5:
        reasons.append('gain too small without a repeated zero repair')
    return dict(zero_first=zero_first,groups=groups,independent_base_cases=independent,cases=len(rows),
      hard_failures=hard,max_queries=max(r['queries'] for r in rows),max_turns=max(r['oscillations'] for r in rows),
      max_redundancy=max(r['redundancy'] for r in rows),
      total_synthetic_score=sum(r['score'] for r in rows),
      qualification=dict(eligible=not reasons,reasons=reasons,
       note='Local gate only; bootstrap uses independent base curves within families, siblings excluded. No prediction of official gain.'))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True)
    ap.add_argument('--suite',choices=('classic','mixed'),default='classic');ap.add_argument('--mixed-seed',type=int,default=20261026401);ap.add_argument('--novel-families',action='store_true');ap.add_argument('--splits',nargs='+',choices=tuple(SEEDS));ap.add_argument('--trace-solvers',action='store_true')
    ap.add_argument('--generator-version',type=int,choices=(1,2,3),default=3);ap.add_argument('--per-family',type=int,default=18);ap.add_argument('--case-offset',type=int,default=0);ap.add_argument('--extra-cases');ap.add_argument('--program',action='append',required=True)
    args=ap.parse_args();out=(ROOT/args.out).resolve();out.relative_to(ROOT)
    build=ROOT/'dev/build/research'/out.name;build.mkdir(parents=True,exist_ok=True)
    solvers=[]
    for arg in args.program:
        name,path=arg.split('=',1)
        if not name.replace('_','').isalnum():raise ValueError('unsafe program name')
        source=(ROOT/path).resolve();solvers.append(dict(name=name,source=source.relative_to(ROOT).as_posix(),sha256=sha(source)))
    if len({s['name'] for s in solvers})!=len(solvers):raise ValueError('duplicate solver name')
    policy_path=ROOT/'automation/research_policy.json'
    policy=json.loads(policy_path.read_text(encoding='utf-8'));policy_hash=sha(policy_path)
    main_hash=sha(ROOT/'main.cpp')
    with SubmissionLock(ROOT/'automation/online_judge/runs/.offline-research.lock'):
        generator_path=ROOT/'dev/tools/scenario_factory.py'
        generator=make_scenarios
        version=VERSION;gen_families=FAMILIES;gen_seeds=SEEDS
        if args.suite=='mixed':
            from tools import mixed_scenarios as mixed
            generator_path=ROOT/'dev/tools/mixed_scenarios.py';version=mixed.VERSION
            gen_families=mixed.FAMILIES+(mixed.NOVEL if args.novel_families else ());gen_seeds=mixed.SEEDS
            generator=lambda count:mixed.make_scenarios(count,args.splits,args.mixed_seed,args.novel_families)
        if args.suite=='classic' and args.generator_version in (1,2):
            import importlib.util
            generator_path=ROOT/('data/experiments/local_screen_20261026/scenario_factory_v1.py' if args.generator_version==1 else 'data/experiments/local_widevalley_20261026/scenario_factory_v2_incomplete.py')
            spec=importlib.util.spec_from_file_location('tools.frozen_factory_v1',generator_path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            generator=module.make_scenarios;version=module.VERSION
        if args.case_offset<0:raise ValueError('negative case offset')
        data=generator(args.per_family+args.case_offset)
        if args.splits and args.suite=='classic':data=[(c,m) for c,m in data if m['split'] in args.splits]
        if args.case_offset:
            data=[(c,m) for c,m in data if int(m['cluster'].rsplit('/',1)[1])>=args.case_offset]
            siblings=[]
            for c,m in data:
                if int(m['cluster'].rsplit('/',1)[1])==args.case_offset:
                    for tag,vs in [('mirror',c.values[::-1]),('offset',tuple(v+12345 for v in c.values)),('scale',tuple(v*2 for v in c.values))]:
                        siblings.append((Case(c.name+'/'+tag,vs,c.family,c.difficulty),dict(m,transform=tag)))
            data+=siblings
        for c in make_suite('smoke'):
            data.append((c,dict(split='regression',family=c.family,cluster='smoke/'+c.name,transform='base')))
        frozen=[ROOT/'data/experiments/2026-10-26-B/counterexamples/rippled_early_finish.json']
        old=ROOT/'data/experiments/2026-10-26/counterexamples/fit16_holdout_failures.json'
        if old.exists():
            content=json.loads(old.read_text(encoding='utf-8'))
            items=content['cases'] if isinstance(content,dict) and 'cases' in content else content
            if isinstance(items,list):
                for item in items:
                    c=Case('frozen/'+item['name'],tuple(item['values']),'retained_failure','structured')
                    data.append((c,dict(split='regression',family=c.family,cluster=c.name,transform='base')))
        for p in frozen:
            if p.exists():
                item=json.loads(p.read_text(encoding='utf-8'));c=Case('frozen/'+item['name'],tuple(item['values']),'retained_failure','structured')
                data.append((c,dict(split='regression',family=c.family,cluster=c.name,transform='base')))
        if args.extra_cases:
            extra_path=(ROOT/args.extra_cases).resolve();extra_path.relative_to(ROOT)
            for item in json.loads(extra_path.read_text(encoding='utf-8')):
                c=Case(item['name'],tuple(item['values']),item.get('family','acceptance'),item.get('difficulty','structured'))
                meta=item.get('metadata',dict(split='regression',family=c.family,cluster=c.name,transform='base'))
                if meta['split']!='regression':raise ValueError('Extra observed cases must be tagged regression')
                data.append((c,meta))
        cases=[dict(name=c.name,values=c.values,family=c.family,difficulty=c.difficulty,metadata=m) for c,m in data]
        identity=hashlib.sha256(encode(cases)).hexdigest()
        manifest=dict(generator_version=version,generator_sha256=sha(generator_path),
          seeds=gen_seeds,per_family=args.per_family,families=gen_families,cases=len(cases),dataset_sha256=identity,
          solvers=solvers,fixed_before_scoring=True,official=False,
          method='Independent stratified base cases; siblings share cluster; held-out parameter shifts. Candidates fixed before evaluation.',
          research_policy_sha256=policy_hash,research_objective=policy['research_objective'],
          score_analysis_sha256=sha(ROOT/'dev/tools/robust_score.py'))
        if args.suite=='mixed':manifest.update(suite='mixed',mixed_seed=args.mixed_seed,novel_families=args.novel_families)
        if args.splits:manifest['splits']=args.splits
        if args.trace_solvers:manifest['trace_solvers']=True
        if args.extra_cases:manifest['extra_cases']=dict(path=extra_path.relative_to(ROOT).as_posix(),sha256=sha(extra_path))
        if args.case_offset:manifest['case_offset']=args.case_offset
        mp=out/'manifest.json'
        if mp.exists():
            if json.loads(mp.read_text(encoding='utf-8'))!=json.loads(json.dumps(manifest)):
                raise RuntimeError('Frozen input/source manifest changed; use a new study directory')
        else:save(mp,manifest)
        save(build/'cases.json',cases)
        metadata=[m for c,m in data];curve_ids=[hashlib.sha256(encode(c.values)).hexdigest() for c,m in data];summaries={};base_rows=None
        for solver in solvers:
            if sha(ROOT/solver['source'])!=solver['sha256']:raise RuntimeError('source changed')
            exe=build/(solver['name']+('.exe' if os.name=='nt' else ''))
            p=subprocess.run([shutil.which('g++') or 'g++','-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(ROOT/solver['source']),'-o',str(exe)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            if p.returncode or p.stderr:raise RuntimeError(p.stderr)
            rp=build/(solver['name']+'.json');report=dict(dataset_sha256=identity,source_sha256=solver['sha256'],rows=[])
            if rp.exists():
                report=json.loads(rp.read_text(encoding='utf-8'))
                if report['dataset_sha256']!=identity or report['source_sha256']!=solver['sha256']:raise RuntimeError('resume hash mismatch')
            rows=report['rows']
            for i,(c,m) in enumerate(data):
                if i<len(rows):
                    if rows[i]['name']!=c.name:raise RuntimeError('resume order mismatch')
                    continue
                result=run_case([str(exe)]+(['--trace'] if args.trace_solvers else []),c)
                seen=result['query_positions']
                winner=min(set(seen),key=lambda x:(-c.values[x],abs(2*x-(len(c.values)-1)),x)) if seen else None
                result['parked_observed_winner']=bool(seen) and result['final_position']==winner
                rows.append(result)
                if (i+1)%32==0:save(rp,report)
                if (i+1)%200==0:print(json.dumps(dict(solver=solver['name'],completed=i+1,total=len(data))),flush=True)
            save(rp,report)
            if base_rows is None:base_rows=rows
            summaries[solver['name']]=paired(rows,base_rows,metadata,curve_ids)
            if policy['research_objective']=='robust_total_score':
                score=score_analysis(rows,base_rows,metadata,curve_ids,policy['min_independent_base_cases'],policy['min_structured_families'])
                summaries[solver['name']]['robust_score']=score
                summaries[solver['name']]['legacy_qualification']=summaries[solver['name']]['qualification']
                summaries[solver['name']]['qualification']=score['qualification']
                save(out/'scorecards'/(solver['name']+'.json'),score)
                rankings={n:v['robust_score'] for n,v in summaries.items()}
                save(out/'score_ranking.json',dict(objective='robust_total_score',ranking=sorted(rankings,key=lambda n:rankings[n]['rank_key']),
                  solvers={n:{k:v for k,v in result.items() if k!='groups'} for n,result in rankings.items()}))
            save(out/'summary.json',dict(manifest_sha256=sha(mp),official=False,solvers=summaries))
            # Freeze new zeros with the actual hidden oracle only in the local report.
            failures=[]
            for (c,m),r,b in zip(data,rows,base_rows):
                if r['score']==0 and b['score']>0:
                    failures.append(dict(name=c.name,family=c.family,difficulty=c.difficulty,metadata=m,values=c.values,
                      target=c.target,baseline=b,candidate=r))
            save(out/'counterexamples'/(solver['name']+'.json'),failures)
            priorities={name:{k:v for k,v in item['zero_first'].items() if k not in ('zero_ledger','groups')} for name,item in summaries.items()}
            save(out/'zero_priority.json',dict(objective='zero_first',ranking=sorted(priorities,key=lambda name:priorities[name]['rank_key']),solvers=priorities))
            save(out/'zero_ledger'/ (solver['name']+'.json'),summaries[solver['name']]['zero_first']['zero_ledger'])
            print(json.dumps(dict(solver=solver['name'],qualification=summaries[solver['name']]['qualification'],
              splits={k:{a:v for a,v in g.items() if a!='families'} for k,g in summaries[solver['name']]['groups'].items()})),flush=True)
        if sha(policy_path)!=policy_hash:raise RuntimeError('Research policy changed during the frozen study')
        if sha(ROOT/'main.cpp')!=main_hash:raise RuntimeError('formal main was modified during screening')
        save(out/'completion.json',dict(complete=True,cases=len(data),solvers=len(solvers),
          interactive_runs=len(data)*len(solvers),main_preserved=True,online_submissions=0,ranking_requests=0))

if __name__=='__main__':main()
