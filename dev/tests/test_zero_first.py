"""Zero preservation, independent repair counts and exact infeasibility proof."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.zero_first import analyze,redundancy_conflict
from tools.local_judge import Case

def row(name,score,**kw):
    return dict(name=name,score=score,status='ok',queries=50,oscillations=2,
        parked_observed_winner=True,difficulty='structured',zero_reasons=[] if score else ['distance > 3'],
        redundancy=100,distance=0 if score else 20,final_position=100,target=100,**kw)
def meta(name,transform='base',difficulty='structured'):
    return dict(split='development',family='smooth',cluster=name,transform=transform)

class ZeroFirstTests(unittest.TestCase):
    def test_higher_average_cannot_compensate_for_a_new_zero(self):
        b=[row('a',100),row('b',100)];a=[row('a',0),row('b',10000)];m=[meta('a'),meta('b')]
        self.assertGreater(analyze(a,b,m)['rank_key'],analyze(b,b,m)['rank_key'])
    def test_repair_outranks_mean_score_when_no_old_positive_is_lost(self):
        b=[row('a',0),row('b',2500)];a=[row('a',1),row('b',1)];m=[meta('a'),meta('b')]
        self.assertLess(analyze(a,b,m)['rank_key'],analyze(b,b,m)['rank_key'])
    def test_transform_repairs_do_not_inflate_independent_count(self):
        b=[row('a',0),row('a/mirror',0)];a=[row('a',1),row('a/mirror',1)]
        r=analyze(a,b,[meta('a'),meta('a','mirror')])
        self.assertEqual(r['independent_repairs'],1);self.assertEqual(r['repair_entries_including_siblings'],2)
        a[1]['score']=0;b[1]['score']=1
        self.assertEqual(analyze(a,b,[meta('a'),meta('a','mirror')])['introduced_zeros_all_cases'],['a/mirror'])
    def test_exact_repeated_base_arrays_are_not_multiple_repairs(self):
        b=[row('a',0),row('alias',0)];a=[row('a',1),row('alias',1)]
        r=analyze(a,b,[meta('a'),meta('alias')],['same_array','same_array'])
        self.assertEqual(r['independent_repairs'],1)
        self.assertEqual(r['unique_base_curves'],1)
        self.assertEqual(len(r['exact_duplicate_base_entries']),1)
        with self.assertRaises(ValueError):analyze(a,b,[meta('a'),meta('alias')],[])
    def test_zero_ledger_and_all_case_status_are_explicit(self):
        b=[row('a',0),row('b',10)];r=analyze(b,b,[meta('a'),meta('b')])
        self.assertFalse(r['all_observed_cases_nonzero']);self.assertEqual(r['zero_ledger'][0]['name'],'a')
        b[0]['score']=1;b[0]['zero_reasons']=[]
        self.assertTrue(analyze(b,b,[meta('a'),meta('b')])['all_observed_cases_nonzero'])
        b[0]['queries']=200
        self.assertFalse(analyze(b,b,[meta('a'),meta('b')])['all_observed_cases_nonzero'])
    def test_unpaired_or_duplicate_input_is_rejected(self):
        b=[row('a',1)]
        with self.assertRaises(ValueError):analyze(b,[],[meta('a')])
        with self.assertRaises(ValueError):analyze(b,[row('b',1)],[meta('a')])
        with self.assertRaises(ValueError):analyze(b*2,b*2,[meta('a'),meta('a')])
    def test_exact_constant_and_late_peak_incompatibility(self):
        a=Case('constant',(0,)*1000)
        b=Case('late',tuple(max(0,1800-100*abs(i-900)) for i in range(1000)))
        proof=redundancy_conflict(a,b)
        self.assertEqual(proof['first_target'],499)
        self.assertEqual(proof['first_maximum_safe_query'],698)
        self.assertEqual(proof['second_acceptable_final_interval'],[897,903])
        self.assertEqual(proof['unavoidable_zeros_at_least'],1)
    def test_difference_inside_safe_prefix_invalidates_certificate(self):
        a=Case('constant',(0,)*1000);vs=[0]*1000;vs[600]=10;vs[900]=100
        self.assertIsNone(redundancy_conflict(a,Case('visible_signal',tuple(vs))))
        self.assertIsNone(redundancy_conflict(a,Case('same',a.values)))
        self.assertIsNone(redundancy_conflict(a,Case('length',(0,)*400)))
        with self.assertRaises(ValueError):redundancy_conflict(a,a,-1)
        with self.assertRaises(ValueError):redundancy_conflict(a,a,199,-1)

if __name__=='__main__':unittest.main()
