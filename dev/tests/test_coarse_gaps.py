"""Separate irreversible coverage failures from locally refinable gaps."""
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'dev'))
from tools.analyze_coarse_gaps import classify
from tools.local_judge import score_path

def row(values,path,frontier):
    m=score_path(values,path)
    return dict(m,status='ok',query_positions=path,stderr='TRACE '+json.dumps(dict(coarse_frontier=frontier)))
class CoarseGapTests(unittest.TestCase):
    def test_uncovered_later_target(self):
        v=[0]*400;v[350]=100
        self.assertEqual(classify(v,row(v,[0,8,16],16))['category'],'uncovered_right_target')
    def test_coarse_redundancy_cannot_be_repaired_by_refining(self):
        v=[0]*400;v[0]=100
        self.assertEqual(classify(v,row(v,[0,100,200,0],200))['category'],'irreversible_coarse_redundancy')
    def test_covered_gap_can_be_filled_with_legal_oracle_path(self):
        v=[0]*400;v[4]=100;v[8]=90
        x=classify(v,row(v,[0,8,16,8],16))
        self.assertEqual(x['category'],'covered_unread_target')
        self.assertEqual(x['target_gap'],[0,8]);self.assertEqual(x['endpoint_gap_rank'],1)
        self.assertTrue(x['oracle_gap_fill_legal']);self.assertGreater(x['oracle_gap_fill_score'],0)
        self.assertLessEqual(x['oracle_gap_fill_queries'],199);self.assertLessEqual(x['oracle_gap_fill_turns'],6)
    def test_positive_is_not_counted_as_a_zero_opportunity(self):
        v=[0]*400;v[4]=100
        self.assertEqual(classify(v,row(v,[0,8,4],8))['category'],'positive')
if __name__=='__main__':unittest.main()
