"""Exercise the actual candidate transport and exception fallback through pipes.
No network; fault injection is confined to a separately compiled test harness.
"""
from pathlib import Path
import hashlib, os, shutil, subprocess, sys, unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev'))
from tools.local_judge import Case,run_case
SOURCE=ROOT/'data/experiments/protocol_audit_20261027/main_protocol.cpp'

class ProtocolTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('g++')
        if not compiler:raise unittest.SkipTest('g++ required')
        cls.directory=ROOT/'dev/build/protocol_transport';cls.directory.mkdir(parents=True,exist_ok=True)
        harness=r'''#define main production_entry
#include "SOURCE_PATH"
#undef main
static bool failVector=false;
void* operator new(std::size_t bytes) {
    if (failVector && bytes==8000) { failVector=false; throw std::bad_alloc(); }
    if (void* p=std::malloc(bytes)) return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p,std::size_t) noexcept { std::free(p); }
int main(int argc,char** argv) {
    if (argc>1 && std::strcmp(argv[1],"fault")==0) {
        failVector=true;
        char name[]="solver";char* args[]={name,nullptr};
        return production_entry(1,args);
    }
    std::ios::sync_with_stdio(false); std::cin.tie(nullptr);
    int n;if (!(std::cin>>n)) return 4;
    af::Protocol wire(n);long long answer;
    if (wire.query(-1,answer) || wire.query(n,answer)) return 5;
    for (int i=0;i<500;++i) {
        const bool ok=wire.query(0,answer);
        if (ok!=(i<af::QMAX)) return 6;
    }
    if (wire.queries()!=af::QMAX) return 7;
    wire.done();wire.done();
    if (wire.query(0,answer) || wire.queries()!=af::QMAX) return 8;
    return 0;
}
'''.replace('SOURCE_PATH',SOURCE.as_posix())
        hp=cls.directory/'harness.cpp';hp.write_text(harness,encoding='utf-8')
        cls.solver=cls.directory/'solver.exe';cls.harness=cls.directory/'harness.exe'
        for source,out in [(SOURCE,cls.solver),(hp,cls.harness)]:
            c=subprocess.run([compiler,'-O3','-Wall','-Wextra','-Wpedantic','-std=c++17','-D_GLIBCXX_ASSERTIONS',str(source),'-o',str(out)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            if c.returncode:raise RuntimeError(c.stderr)

    def test_emission_limit_bounds_and_done_are_enforced_at_transport(self):
        r=run_case([str(self.harness)],Case('transport_limits',(1,)*400))
        self.assertEqual(r['status'],'ok',r)
        self.assertEqual(r['queries'],199,r)
        self.assertEqual(r['messages'],200,r)
        self.assertEqual(r['query_positions'],[0]*199)

    def test_cpp_allocation_exception_still_queries_and_finishes(self):
        r=run_case([str(self.harness),'fault'],Case('allocation_failure',(1,)*1000))
        self.assertEqual(r['status'],'ok',r)
        self.assertEqual(r['queries'],1,r)
        self.assertEqual(r['messages'],2,r)
        self.assertIn('solver exception',r['stderr'])

    def test_closed_or_invalid_reply_does_not_repeat_queries(self):
        for payload in (b'400\n',b'400\n-1\n',b'400\n2147483648\n',b'400\ninvalid\n'):
            with self.subTest(payload=payload):
                p=subprocess.run([str(self.solver)],input=payload,capture_output=True,timeout=10)
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertIn(p.stdout,(b'0\nDONE\n',b'0\r\nDONE\r\n'))

    def test_official_lengths_and_value_extremes(self):
        for n in (400,401,999,1000):
            for value in (0,2147483647):
                with self.subTest(n=n,value=value):
                    r=run_case([str(self.solver)],Case('constant',(value,)*n))
                    self.assertEqual(r['status'],'ok',r)
                    self.assertLessEqual(r['queries'],199,r)
                    self.assertEqual(r['messages'],r['queries']+1,r)
                    self.assertEqual(r['final_position'],(n-1)//2,r)

if __name__=='__main__':unittest.main()
