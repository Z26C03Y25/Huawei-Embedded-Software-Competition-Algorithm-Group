"""Behavioral checks for frozen coarse-coverage and competing-gap candidates.
The source snapshots stay unchanged. The isolated helper harness changes only
Solver access visibility in an ignored build copy; it never uploads anything.
Difficult raw-spike controls intentionally have no all-nonzero assertion.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev'))
from tools.local_judge import Case,PDF_SAMPLE,run_case

BASE=ROOT/'data/experiments/coarse_compete_20261027'
SOURCES={
    'coarse':BASE/'coarse/coarse_rival_release.cpp',
    'gap':BASE/'gap/competing_gap_midpoints.cpp',
    'combined':BASE/'combined_coarse_gap.cpp',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(result,key):
    match=re.search(r'^'+re.escape(key)+r' (\{[^\r\n]*\})',result['stderr'],re.M)
    if match is None:
        raise AssertionError('Missing '+key+' trace: '+result['stderr'])
    return json.loads(match.group(1))


class CoarseCompeteSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('g++')
        if compiler is None:
            raise unittest.SkipTest('C++ interaction checks require g++')
        cls.build=ROOT/'dev/build/coarse_compete_tests'
        cls.build.mkdir(parents=True,exist_ok=True)
        cls.executables={}
        cls.source_hashes={}
        for name,source in SOURCES.items():
            metadata=json.loads(source.with_suffix('.json').read_text(encoding='utf-8-sig'))
            before=digest(source)
            if before!=metadata['sha256']:
                raise AssertionError('Frozen candidate changed: '+source.name)
            cls.source_hashes[name]=before
            executable=cls.build/(name+'.exe')
            cls.compile(compiler,source,executable)
            cls.executables[name]=executable

        # Unit access is confined to a copy. Production paths and hashes remain intact.
        production=SOURCES['combined'].read_text(encoding='utf-8-sig')
        if production.count('class Solver {')!=1 or production.count('int main(int argc,char** argv)')!=1:
            raise AssertionError('Unexpected frozen combined source structure')
        helper=production.replace('class Solver {','struct Solver {',1).replace(
            'int main(int argc,char** argv)','int production_entry(int argc,char** argv)',1)
        helper+=r'''
int main() {
    af::Protocol wire(80);
    af::Solver solver(80,false,false,false,wire);
    solver.best=24;solver.bestValue=10000;
    const int xs[]={0,8,16,24,32,40,48};
    const long long ys[]={0,8500,9800,10000,9850,9950,9000};
    for (int i=0;i<7;++i) solver.value[xs[i]]=ys[i];
    af::Features f;f.x.assign(xs,xs+7);f.peaks={24};
    f.noisy=false;f.noise=50;f.contrast=10000;
    if (!solver.competingGapAudit(f,21,27).empty()) return 10;
    f.peaks.push_back(40);
    const auto rival=solver.competingGapAudit(f,21,27);
    if (rival.size()!=2) return 11;
    for (const auto& gap:rival) {
        if (gap.mid>=21 && gap.mid<=27) return 12;
        if (std::abs(gap.mid-solver.best)>48 || solver.value[gap.mid]>=0) return 13;
    }
    f.peaks={24};f.noisy=true;
    const auto noisy=solver.competingGapAudit(f,21,27);
    if (noisy.size()!=2) return 14;
    std::cerr<<"GATE_CHECKS {\"near_rival\":2,\"noisy\":2,\"quiet_single_peak\":0}\n";
    return 0;
}
'''
        helper_source=cls.build/'helper_access.cpp'
        helper_source.write_text(helper,encoding='utf-8')
        cls.helper=cls.build/'helper_access.exe'
        cls.compile(compiler,helper_source,cls.helper)
        for name,source in SOURCES.items():
            if digest(source)!=cls.source_hashes[name]:
                raise AssertionError('Test harness altered production source')

        controls=json.loads((BASE/'structural_controls.json').read_text(encoding='utf-8-sig'))
        cls.controls={item['name']:item for item in controls}
        smoke=json.loads((BASE/'coarse/smoke.json').read_text(encoding='utf-8-sig'))
        if not smoke.get('development_controls_only'):
            raise AssertionError('Expected explicit development fixture')
        cls.shoulder=next(item['values'] for item in smoke['rows']
                          if item['name']=='designed_decelerating_shoulder')

    @classmethod
    def compile(cls,compiler,source,out):
        result=subprocess.run([compiler,'-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',
            '-D_GLIBCXX_ASSERTIONS',str(source),'-o',str(out)],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        if result.returncode or result.stderr:
            raise RuntimeError(source.name+' compilation failed/warned:\n'+result.stderr)

    def solve(self,version,values,name):
        case=Case(name,tuple(values))
        result=run_case([str(self.executables[version]),'--trace'],case)
        self.assertEqual(result['status'],'ok',result)
        self.assertIsNone(result['error'],result)
        self.assertGreater(result['queries'],0,result)
        self.assertLessEqual(result['queries'],199,result)
        self.assertLessEqual(result['oscillations'],6,result)
        self.assertEqual(result['messages'],result['queries']+1,result)
        observed=min(set(result['query_positions']),key=lambda x:(
            -case.values[x],abs(2*x-(len(case.values)-1)),x))
        self.assertEqual(result['final_position'],observed,result)
        return result

    def test_protocol_example_and_integer_extremes(self):
        for version in SOURCES:
            for name,values in [('pdf',PDF_SAMPLE),('zero400',[0]*400),
                                ('max1000',[2147483647]*1000)]:
                with self.subTest(version=version,case=name):
                    self.solve(version,values,name)

    def test_one_sentinel_resolves_the_development_shoulder(self):
        for version in ['coarse','combined']:
            with self.subTest(version=version):
                result=self.solve(version,self.shoulder,'development_shoulder')
                coarse=trace(result,'COARSE_RIVAL')
                self.assertEqual(coarse['sentinels'],1,result)
                self.assertIn(320,result['query_positions'],result)
                self.assertLessEqual(coarse['max_beyond_best'],191,result)

    def test_midpoints_form_one_budgeted_model_audit(self):
        values=[max(0,round(100+1000000*math.exp(-.5*((i-280)/65)**2)
                            +15000*math.sin(i*.45))) for i in range(700)]
        for version in ['gap','combined']:
            with self.subTest(version=version):
                result=self.solve(version,values,'development_ripple15000')
                audit=trace(result,'GAP_AUDIT')
                self.assertEqual(audit['batches'],1,result)
                self.assertGreater(audit['reads'],0,result)
                self.assertLessEqual(audit['reads'],2,result)
                self.assertLessEqual(audit['challenges'],audit['batches'],result)

    def test_near_rival_and_noise_have_independent_helper_triggers(self):
        result=subprocess.run([str(self.helper)],capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('GATE_CHECKS',result.stderr)
        self.assertIn('"quiet_single_peak":0',result.stderr)
        for name,source in SOURCES.items():
            self.assertEqual(digest(source),self.source_hashes[name])

    def test_observed_raw_impulse_keeps_priority(self):
        values=self.controls['raw_impulse_262']['values']
        self.assertEqual(max(range(len(values)),key=values.__getitem__),262)
        for version in SOURCES:
            with self.subTest(version=version):
                result=self.solve(version,values,'observed_raw_impulse262')
                self.assertIn(262,result['query_positions'],result)
                self.assertEqual(result['final_position'],262,result)

    def test_known_unobserved_impulses_are_retained_without_nonzero_claim(self):
        for index in [264,268]:
            item=self.controls['raw_impulse_'+str(index)]
            values=item['values']
            self.assertEqual(max(range(len(values)),key=values.__getitem__),index)
            for version in SOURCES:
                with self.subTest(version=version,index=index):
                    # Protocol and raw-observation parking are the contract here.
                    # Zero on this retained narrow-peak case is not concealed.
                    self.solve(version,values,item['name'])

if __name__=='__main__':
    unittest.main()
