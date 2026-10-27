"""Automatic quota/evidence gate and recovery do not depend on browser/network."""
import ast, copy, hashlib, json, sys, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev'))
from tools.research_policy import ResearchPause,authorize_new_upload,cached_day_stop,check_local_evidence
from tools.scenario_factory import make_scenarios,FAMILIES,INFO

class ScenarioTests(unittest.TestCase):
    def test_reproducible_balanced_disjoint_and_valid(self):
        data=make_scenarios(2)
        self.assertEqual(data,make_scenarios(2))
        base=[(c,m) for c,m in data if m['transform']=='base']
        self.assertEqual(len(base),3*len(FAMILIES)*2)
        self.assertEqual(len({m['cluster'] for c,m in base}),len(base))
        self.assertEqual(len({m['seed'] for c,m in base}),len(base))
        for c,m in data:
            self.assertTrue(400<=len(c.values)<=1000)
            self.assertTrue(all(0<=v<=2**31-1 for v in c.values))
            self.assertEqual(c.difficulty=='information_limited',c.family in INFO)
    def test_shoulders_are_broad_components_and_hump_bumps_are_narrow(self):
        base=[(c,m) for c,m in make_scenarios(3,['development']) if m['transform']=='base']
        for c,m in base:
            if c.family=='shoulder':
                self.assertAlmostEqual(m['parameters']['component_width']/m['parameters']['width'],.85)
            elif c.family=='bump_on_hump':
                self.assertLess(m['parameters']['component_width']/m['parameters']['width'],.1)
    def test_siblings_share_cluster_and_targets_are_recomputed(self):
        data=make_scenarios(1,['development'])
        mothers={m['cluster']:c for c,m in data if m['transform']=='base'}
        for c,m in data:
            base=mothers[m['cluster']]
            if m['transform']=='mirror':self.assertEqual(c.values,base.values[::-1])
            elif m['transform']=='scale':self.assertEqual(c.values,tuple(2*v for v in base.values))
            elif m['transform']=='offset':self.assertEqual(c.values,tuple(v+12345 for v in base.values))
            best=min(range(len(c.values)),key=lambda x:(-c.values[x],abs(2*x-len(c.values)+1),x))
            self.assertEqual(c.target,best)
        with self.assertRaises(ValueError):make_scenarios(0)

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.now=datetime(2026,10,27,8,tzinfo=timezone(timedelta(hours=8)))
        legacy_policy=json.loads((ROOT/'automation/research_policy.json').read_text(encoding='utf-8'))
        legacy_policy['research_objective']='zero_first'  # Retain historical gate coverage.
        self.save('automation/research_policy.json',legacy_policy)
        self.save('data/versions/online_search/results.json',[dict(score=203239,sha256='parent')])
        p=self.root/'candidate.cpp';p.write_text('int main(){}');self.digest=hashlib.sha256(p.read_bytes()).hexdigest()
        self.info=dict(path='candidate.cpp',sha256=self.digest)
        families={f:{} for f in FAMILIES if f not in INFO}
        group=dict(families=families,structured_new_zero=0,macro_mean_delta=10,
            worst_family_mean_delta=-1,stratified_base_bootstrap_95=[2,20])
        result=dict(qualification=dict(eligible=True),zero_first=dict(version=2,objective='zero_first',hard_failures=[],introduced_zeros_all_cases=[],all_observed_cases_nonzero=True),independent_base_cases=1188,hard_failures=[],
            max_queries=199,max_turns=6,groups={s:copy.deepcopy(group) for s in ('development','selection','blind_shift')})
        self.save('manifest.json',dict(generator_version=3,fixed_before_scoring=True,solvers=[dict(name='base',sha256='parent'),dict(name='new',sha256=self.digest)]))
        self.report=dict(official=False,manifest_sha256=self.hash('manifest.json'),solvers=dict(new=result))
        self.save('summary.json',self.report)
        self.entry=dict(sha256=self.digest,status='qualified',parent_sha256='parent',manifest='manifest.json',
            evidence='summary.json',evidence_sha256=self.hash('summary.json'))
        self.entries()
        self.quota=dict(date='2026-10-27',limit=30,used=2,remaining=28,checked_at=self.now.isoformat())
    def save(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data),encoding='utf-8')
    def hash(self,path):return hashlib.sha256((self.root/path).read_bytes()).hexdigest()
    def entries(self):self.save('data/experiments/qualified_candidates.json',dict(candidates=[self.entry]))
    def test_qualified_candidate_and_fresh_team_quota(self):
        self.assertEqual(authorize_new_upload(self.info,self.quota,self.root,self.now),self.entry)
    def test_cap_is_separate_from_official_remaining(self):
        q=self.quota|dict(used=3,remaining=27)
        with self.assertRaisesRegex(ResearchPause,'cap'):authorize_new_upload(self.info,q,self.root,self.now)
    def test_cached_zero_resets_at_beijing_midnight(self):
        self.save('data/experiments/research_state.json',dict(confirmed_platform_quota_date='2026-10-27',confirmed_remaining_submissions=0))
        self.assertIsNotNone(cached_day_stop(self.root,self.now))
        self.assertIsNone(cached_day_stop(self.root,self.now+timedelta(days=1)))
        with self.assertRaisesRegex(ResearchPause,'confirmed0'):authorize_new_upload(self.info,self.quota,self.root,self.now)
    def test_stale_or_inconsistent_quota_rejected(self):
        for delta in (dict(date='2026-10-26'),dict(checked_at=(self.now-timedelta(seconds=121)).isoformat()),dict(remaining=29),dict(used=True)):
            with self.subTest(delta=delta),self.assertRaises(ResearchPause):authorize_new_upload(self.info,self.quota|delta,self.root,self.now)
    def test_source_report_and_parent_must_match_frozen_evidence(self):
        for mutate in ('source','report','parent','unqualified'):
            with self.subTest(mutate=mutate):
                if mutate=='source':self.info['sha256']='wrong'
                elif mutate=='report':self.entry['evidence_sha256']='wrong';self.entries()
                elif mutate=='parent':self.entry['parent_sha256']='wrong';self.entries()
                else:self.entry['status']='offline_only';self.entries()
                with self.assertRaises(ResearchPause):check_local_evidence(self.info,self.root)
                self.info['sha256']=self.digest;self.entry.update(status='qualified',evidence_sha256=self.hash('summary.json'),parent_sha256='parent');self.entries()
    def test_new_information_limited_zero_and_false_guarantee_are_rejected(self):
        for mode in ('new_zero','false_guarantee'):
            r=self.report['solvers']['new']['zero_first']
            r['introduced_zeros_all_cases']=['random_spike'] if mode=='new_zero' else []
            r['all_observed_cases_nonzero']=False
            self.entry['claims_all_measured_nonzero']=mode=='false_guarantee'
            self.save('summary.json',self.report)
            self.entry['evidence_sha256']=self.hash('summary.json');self.entries()
            with self.subTest(mode=mode),self.assertRaises(ResearchPause):check_local_evidence(self.info,self.root)
    def test_old_generator_cannot_be_qualified_by_relabeling_families(self):
        self.save('manifest.json',dict(generator_version=1,fixed_before_scoring=True,solvers=[dict(name='base',sha256='parent'),dict(name='new',sha256=self.digest)]))
        self.report['manifest_sha256']=self.hash('manifest.json')
        self.save('summary.json',self.report)
        self.entry['evidence_sha256']=self.hash('summary.json');self.entries()
        with self.assertRaisesRegex(ResearchPause,'taxonomy'):check_local_evidence(self.info,self.root)
    def test_new_zero_or_insufficient_samples_cannot_be_overridden_by_eligible_flag(self):
        saved=copy.deepcopy(self.report)
        for mutate in ('zeros','count','budget'):
            self.report=copy.deepcopy(saved)
            r=self.report['solvers']['new']
            if mutate=='zeros':r['groups']['blind_shift']['structured_new_zero']=1
            elif mutate=='count':r['independent_base_cases']=999
            else:r['max_queries']=200
            self.save('summary.json',self.report);self.entry['evidence_sha256']=self.hash('summary.json');self.entries()
            with self.subTest(mutate=mutate),self.assertRaises(ResearchPause):check_local_evidence(self.info,self.root)
    def test_already_delivered_job_recovers_before_any_new_upload_gate(self):
        tree=ast.parse((ROOT/'dev/tools/online_search_loop.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='evaluate_online')
        def forbidden(*args,**kwargs):raise AssertionError('new-upload check must not block recovery')
        complete=dict(state='completed',job_id='original')
        env=dict(jobs_for=lambda _: [complete],quota=forbidden,check_local_evidence=forbidden)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'evaluate_online','exec'),env)
        self.assertEqual(env['evaluate_online'](self.info),complete)
        pending=dict(state='score_wait',job_id='original');jobs=[pending]
        def resume(args):
            self.assertEqual(args[:2],['wait','original']);jobs[0]=complete
            return None
        env.update(jobs_for=lambda _:jobs,invoke=resume)
        self.assertEqual(env['evaluate_online'](self.info),complete)

class RobustPolicyTests(unittest.TestCase):
    save=PolicyTests.save
    hash=PolicyTests.hash
    entries=PolicyTests.entries
    def setUp(self):
        PolicyTests.setUp(self)
        policy=json.loads((self.root/'automation/research_policy.json').read_text(encoding='utf-8'))
        policy['research_objective']='robust_total_score'
        self.save('automation/research_policy.json',policy)
        p=self.root/'dev/tools/robust_score.py';p.parent.mkdir(parents=True);p.write_text('score evaluator v1')
        self.save('manifest.json',dict(generator_version=3,fixed_before_scoring=True,
            research_policy_sha256=self.hash('automation/research_policy.json'),
            score_analysis_sha256=self.hash('dev/tools/robust_score.py'),
            solvers=[dict(name='base',sha256='parent'),dict(name='new',sha256=self.digest)]))
        self.report['manifest_sha256']=self.hash('manifest.json')
        group=dict(structured_family_count=20,macro_delta=25,zero_rate_delta=-.01,cvar25_delta=10)
        self.report['solvers']['new']['robust_score']=dict(version=1,objective='robust_total_score',
            hard_failures=[],independent_fresh_cases=2376,
            groups={s:copy.deepcopy(group) for s in ('selection','blind_shift')},heldout_macro_delta_ci95=[2,40])
        # An individual loss is allowed when net score and aggregate risk improve.
        self.report['solvers']['new']['zero_first'].update(introduced_zeros_all_cases=['individual_loss'],all_observed_cases_nonzero=False)
        self.refresh()
    def refresh(self):
        self.save('summary.json',self.report);self.entry['evidence_sha256']=self.hash('summary.json');self.entries()
    def test_accepts_net_score_gain_despite_an_individual_new_zero(self):
        self.assertEqual(check_local_evidence(self.info,self.root),self.entry)
    def test_rejects_aggregate_zero_tail_and_uncertain_score_regressions(self):
        saved=copy.deepcopy(self.report)
        for change in ('zeros','tail','mean','uncertain','hard'):
            self.report=copy.deepcopy(saved);score=self.report['solvers']['new']['robust_score']
            if change=='zeros':score['groups']['selection']['zero_rate_delta']=.001
            elif change=='tail':score['groups']['blind_shift']['cvar25_delta']=-1
            elif change=='mean':score['groups']['blind_shift']['macro_delta']=0
            elif change=='uncertain':score['heldout_macro_delta_ci95'][0]=0
            else:score['hard_failures']=['bad_query']
            self.refresh()
            with self.subTest(change=change),self.assertRaises(ResearchPause):check_local_evidence(self.info,self.root)
    def test_policy_and_evaluator_must_match_frozen_evidence(self):
        p=self.root/'dev/tools/robust_score.py';p.write_text('different evaluator')
        with self.assertRaisesRegex(ResearchPause,'evaluator'):check_local_evidence(self.info,self.root)
        p.write_text('score evaluator v1')
        policy=json.loads((self.root/'automation/research_policy.json').read_text(encoding='utf-8'));policy['auto_daily_team_cap']=2
        self.save('automation/research_policy.json',policy)
        with self.assertRaisesRegex(ResearchPause,'objective policy'):check_local_evidence(self.info,self.root)

class ConditionalBackupTests(unittest.TestCase):
    save=PolicyTests.save
    hash=PolicyTests.hash
    entries=PolicyTests.entries
    def setUp(self):
        PolicyTests.setUp(self)
        self.entry['execution_condition']=dict(kind='primary_not_improved',primary_sha256='primary',baseline_score=203239,not_before_date='2026-10-27')
        self.entries()
    def set_primary(self,score,date='2026-10-27 08:00:00'):
        self.save('data/versions/online_search/results.json',[dict(score=203239,sha256='parent'),dict(score=score,sha256='primary',submitted_at=date)])
    def test_backup_waits_for_recorded_official_primary(self):
        with self.assertRaisesRegex(ResearchPause,'recorded official'):check_local_evidence(self.info,self.root)
        self.set_primary(203100)
        self.assertEqual(check_local_evidence(self.info,self.root),self.entry)
    def test_tied_primary_allows_backup_but_improvement_blocks_it(self):
        self.set_primary(203239)
        self.assertEqual(check_local_evidence(self.info,self.root),self.entry)
        self.set_primary(203240)
        with self.assertRaises(ResearchPause):check_local_evidence(self.info,self.root)
    def test_old_or_undated_result_does_not_trigger_tomorrows_backup(self):
        for date in ('2026-10-26 23:00:00','not_a_date'):
            self.set_primary(200000,date)
            with self.subTest(date=date),self.assertRaises(ResearchPause):check_local_evidence(self.info,self.root)
    def test_unknown_condition_is_rejected(self):
        self.entry['execution_condition']['kind']='always_submit';self.entries()
        with self.assertRaisesRegex(ResearchPause,'Unknown'):check_local_evidence(self.info,self.root)

if __name__=='__main__':unittest.main()
