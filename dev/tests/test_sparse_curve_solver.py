"""True-pipe tests for sparse fitting, raw-spike preservation and protocol bounds."""
from pathlib import Path
import json,math,os,re,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev'))
from tools.local_judge import Case,run_case
SOURCE=ROOT/'data/experiments/sparse_curve_20261027/sparse_relative_support.cpp'
class SparseCurveSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('g++')
        if not compiler:raise unittest.SkipTest('g++ required')
        cls.exe=ROOT/'dev/build/test_sparse_curve.exe'
        r=subprocess.run([compiler,'-O3','-Wall','-Wextra','-Wpedantic','-std=c++17','-D_GLIBCXX_ASSERTIONS',str(SOURCE),'-o',str(cls.exe)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        if r.returncode or r.stderr:raise RuntimeError(r.stderr)
    def solve(self,values,name):
        case=Case(name,tuple(values));r=run_case([str(self.exe),'--trace'],case)
        self.assertEqual(r['status'],'ok',r)
        self.assertLessEqual(r['queries'],199,r);self.assertLessEqual(r['oscillations'],6,r)
        self.assertEqual(r['messages'],r['queries']+1,r)
        observed=min(set(r['query_positions']),key=lambda x:(-case.values[x],abs(2*x-(len(values)-1)),x))
        self.assertEqual(r['final_position'],observed,r)
        return r
    def test_clean_curve_uses_sparse_early_fit(self):
        v=[100+round(1000000*math.exp(-.5*((i-280)/24)**2)) for i in range(700)]
        r=self.solve(v,'gaussian_clean')
        self.assertEqual(r['final_position'],280,r)
        trace=json.loads(re.search(r'SPARSE (\{.*\})',r['stderr']).group(1))
        self.assertGreater(trace['early_stops'],0,r)
    def test_observed_raw_spike_is_preserved_as_target(self):
        v=[100+round(1000000*math.exp(-.5*((i-280)/24)**2)) for i in range(700)]
        v[262]=max(v)+200000
        r=self.solve(v,'observed_spike')
        self.assertIn(262,r['query_positions'],r)
        self.assertEqual(r['final_position'],262,r)
    def test_flat_integer_limits_and_boundary(self):
        for v in ([0]*400,[2147483647]*1000,list(range(1000)),list(range(1000,0,-1))):
            with self.subTest(n=len(v),first=v[0]):self.solve(v,'protocol_edge')
if __name__=='__main__':unittest.main()
