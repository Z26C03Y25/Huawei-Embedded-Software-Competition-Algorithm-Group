"""Reproducibility, difficulty coverage and independent mixed-curve generation."""
from pathlib import Path
import sys,unittest
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.mixed_scenarios import make_scenarios,FAMILIES,NOVEL,MODELS,INFO

class MixedScenarioTests(unittest.TestCase):
    def test_per_case_prefix_reproducibility_and_distinct_seed_tags(self):
        small={c.name:(c,m) for c,m in make_scenarios(1,['development'],seed_tag=7)}
        large={c.name:(c,m) for c,m in make_scenarios(2,['development'],seed_tag=7)}
        self.assertTrue(all(large[k]==v for k,v in small.items()))
        other=make_scenarios(1,['development'],seed_tag=8)
        self.assertNotEqual(next(iter(small.values()))[0].values,other[0][0].values)
    def test_stratified_difficulty_no_hidden_easy_constant_family(self):
        data=make_scenarios(4,['development'],seed_tag=9)
        base=[(c,m) for c,m in data if m['transform']=='base']
        self.assertEqual(Counter(c.family for c,m in base),{f:4 for f in FAMILIES})
        self.assertEqual(Counter(m['tier'] for c,m in base),dict(medium=24,hard=48,extreme=24))
        self.assertFalse({'flat','constant','unimodal'}&set(FAMILIES))
        for c,m in data:
            self.assertTrue(400<=len(c.values)<=1000)
            self.assertTrue(all(0<=v<=2**31-1 for v in c.values))
            self.assertEqual(c.difficulty=='information_limited',c.family in INFO)
            self.assertTrue(m['composite'])
    def test_split_template_separation_and_novel_family_registry(self):
        sets=[set(v) for v in MODELS.values()]
        self.assertTrue(all(not a&b for i,a in enumerate(sets) for b in sets[i+1:]))
        self.assertFalse(set(NOVEL)&set(FAMILIES));self.assertEqual(len(NOVEL),4)
    def test_transforms_share_mother_and_preserve_values(self):
        data=make_scenarios(1,['development'],seed_tag=10)
        mothers={m['cluster']:c for c,m in data if m['transform']=='base'}
        for c,m in data:
            a=mothers[m['cluster']]
            if m['transform']=='mirror':self.assertEqual(c.values,a.values[::-1])
            elif m['transform']=='scale':self.assertEqual(c.values,tuple(2*v for v in a.values))
            elif m['transform']=='offset':self.assertEqual(c.values,tuple(v+12345 for v in a.values))
        with self.assertRaises(ValueError):make_scenarios(0)
        with self.assertRaises(ValueError):make_scenarios(1,['unknown'])

if __name__=='__main__':unittest.main()
