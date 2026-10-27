"""Aggregate score includes zeros; robustness is evaluated on fresh groups."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.robust_score import analyze,cvar25
from test_zero_first import row

def fixture():
    rows=[];base=[];metadata=[]
    for split in ('development','selection','blind_shift'):
        for family in ('smooth','noisy'):
            for i in range(4):
                name=f'{split}/{family}/{i}'
                base.append(row(name,1000));rows.append(row(name,1010))
                metadata.append(dict(split=split,family=family,cluster=name,transform='base'))
    return rows,base,metadata

def score(rows,base,metadata,ids=None):return analyze(rows,base,metadata,ids,min_cases=1,min_families=1,bootstrap=100)

class RobustScoreTests(unittest.TestCase):
    def test_stable_gain_qualifies_and_zero_scores_count_in_the_mean(self):
        r,b,m=fixture();result=score(r,b,m)
        self.assertTrue(result['qualification']['eligible'])
        self.assertEqual(result['overall']['macro_delta'],10)
        self.assertEqual(result['heldout_macro_delta_ci95'],[10,10])
        r[0]['score']=0
        self.assertEqual(score(r,b,m)['groups']['development']['families']['smooth']['mean'],757.5)
    def test_individual_zero_does_not_automatically_veto_a_net_gain(self):
        r,b,m=fixture()
        for i in range(len(r)):
            if i%4==0:b[i]['score']=0;r[i]['score']=1000
            elif i%4==1:r[i]['score']=0
        result=score(r,b,m)
        self.assertEqual(result['groups']['selection']['zero_rate_delta'],0)
        self.assertTrue(result['new_zero_entries_all_measured'])
        self.assertFalse(any('new zero' in x for x in result['qualification']['reasons']))
    def test_increased_zero_rate_and_lower_tail_can_fail_despite_high_mean(self):
        r,b,m=fixture()
        for i in range(len(r)):r[i]['score']=2000
        r[8]['score']=0
        self.assertFalse(score(r,b,m)['qualification']['eligible'])
        r[8]['score']=1;r[9]['score']=1
        self.assertTrue(any('lower-quarter' in s for s in score(r,b,m)['qualification']['reasons']))
    def test_regression_rows_do_not_inflate_the_primary_fresh_score(self):
        r,b,m=fixture();r.append(row('old',100000));b.append(row('old',0))
        m.append(dict(split='regression',family='old',cluster='old',transform='base'))
        result=score(r,b,m)
        self.assertEqual(result['overall']['macro_delta'],10)
        self.assertEqual(result['independent_fresh_cases'],24)
    def test_siblings_and_exact_duplicates_are_not_independent_weight(self):
        r,b,m=fixture();ids=[str(i) for i in range(len(r))]
        r.append(row('copy',100000));b.append(row('copy',0));ids.append(ids[0]);m.append(dict(m[0],cluster='alias'))
        r.append(row('mirror',100000));b.append(row('mirror',0));ids.append('mirror');m.append(dict(m[0],transform='mirror'))
        self.assertEqual(score(r,b,m,ids)['independent_fresh_cases'],24)
        self.assertEqual(score(r,b,m,ids)['overall']['macro_delta'],10)
        r[-1]['queries']=200
        self.assertFalse(score(r,b,m,ids)['qualification']['eligible'])
    def test_pairing_validation_and_fractional_lower_tail(self):
        r,b,m=fixture()
        with self.assertRaises(ValueError):score(r,b[:-1],m)
        b[0]['name']='wrong'
        with self.assertRaises(ValueError):score(r,b,m)
        self.assertEqual(cvar25([0,100,200,300,400,500]),100/3)
        self.assertEqual(cvar25([8]),8)

if __name__=='__main__':unittest.main()
