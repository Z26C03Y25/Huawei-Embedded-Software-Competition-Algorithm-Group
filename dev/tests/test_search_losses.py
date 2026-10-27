"""Loss accounting matches the true checker, including score floor and motion."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.local_judge import score_path
from tools.analyze_search_losses import explain

class SearchLossTests(unittest.TestCase):
    def test_positive_components_sum_to_exact_gap(self):
        values=[0]*10;values[4]=100
        for path in ([0,6,4],[0,6,3],[3]):
            result=score_path(values,path)|dict(target=4)
            loss=explain(result)
            self.assertEqual(sum(loss['positive_components'].values()),loss['loss'])
            self.assertEqual(loss['omniscient_upper'],2995)
    def test_zero_floor_stays_a_zero_even_with_valid_action_budgets(self):
        values=[0]*1000;values[850]=100
        result=score_path(values,[0,999,0,999,850])|dict(target=850)
        self.assertEqual(result['score'],0)
        self.assertFalse(result['zero_reasons'])
        self.assertEqual(explain(result)['zero_cliff'],2149)
    def test_inconsistent_positive_score_is_not_silently_accounted(self):
        values=[0]*10;values[4]=100
        result=score_path(values,[4])|dict(target=4);result['score']-=1
        with self.assertRaises(ValueError):explain(result)

if __name__=='__main__':unittest.main()
