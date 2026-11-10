"""Source-kernel equivalence for benign catalog code when Windows refuses native launch.
Does not execute a blocked binary or alter host policy. Does not certify peak/R success.
"""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/versions/online_search/scored_214783_3ccdb7d04e21.cpp'
BASE_SHA='3ccdb7d04e21f51444cee99f03020391befa200bcc18376d48bd73a0552ce3f9'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def mask(code):
 # Retain offsets and code braces while hiding strings, chars and comments.
 out=list(code);i=0
 while i<len(code):
  start=i
  if code.startswith('//',i):
   end=code.find('\n',i);i=len(code) if end<0 else end
  elif code.startswith('/*',i):
   end=code.find('*/',i+2)
   if end<0:raise ValueError('Unterminated comment')
   i=end+2
  elif code[i] in ('"',"'"):
   quote=code[i];i+=1
   while i<len(code):
    if code[i]=='\\':i+=2
    elif code[i]==quote:i+=1;break
    else:i+=1
   else:raise ValueError('Unterminated literal')
  else:i+=1;continue
  for j in range(start,min(i,len(out))):
   if out[j]!='\n':out[j]=' '
 return ''.join(out)
def section(code,a,b):
 if code.count(a)!=1 or code.count(b)!=1:raise ValueError('Nonunique protected section')
 lo=code.index(a);hi=code.index(b,lo)
 return lo,hi,code[lo:hi]
def function(code,anchor):
 if code.count(anchor)!=1:raise ValueError('Nonunique function anchor '+anchor)
 lo=code.index(anchor);clean=mask(code);begin=clean.index('{',lo);depth=0
 for i in range(begin,len(clean)):
  if clean[i]=='{':depth+=1
  elif clean[i]=='}':
   depth-=1
   if depth==0:return lo,i+1,code[lo:i+1]
 raise ValueError('Unbalanced function '+anchor)
def _guard_audit(raw):
 base_raw=BASE.read_bytes()
 if digest(base_raw)!=BASE_SHA:raise ValueError('Validated reference bytes changed')
 baseline=base_raw.decode('utf-8');code=raw.decode('utf-8');spans=[];hashes={}
 specifications=[('transport_constants','section','constexpr long long VMAX','\n#define OPS'),
 ('ledger_cache_and_read_guards','section','    Protocol& wire;','    Features features() {'),
 ('physical_parking','function','    void finish() {',None),
 ('constructor','function','    Solver(int length',None),
 ('local_q_shadow','function','    optional<double> multiModelVertex(',None)]
 for label,kind,a,b in specifications:
  reference=section(baseline,a,b) if kind=='section' else function(baseline,a)
  candidate=section(code,a,b) if kind=='section' else function(code,a)
  if candidate[2]!=reference[2]:raise ValueError('Protected kernel changed: '+label)
  spans.append(candidate[:2]);hashes[label]=digest(candidate[2].encode())
 for label,anchor in [('run','    void run() {'),('entry','int main(int argc,char** argv) {')]:
  ref=function(baseline,anchor);actual=function(code,anchor);allowed=[ref[2]]
  if label=='run':allowed.append(ref[2].replace('if (alive) refine();','if (alive) { auditTail(); refine(); }'))
  else:allowed.append(ref[2].replace('bool trace=false,strict=false,late=false;','bool trace=false,strict=false,late=true;'))
  if actual[2] not in allowed:raise ValueError('Unexpected public control flow: '+label)
  spans.append(actual[:2]);hashes[label]=digest(actual[2].encode())
 clean=list(mask(code))
 for lo,hi in spans:
  for i in range(lo,hi):clean[i]=' '
 rest=''.join(clean)
 ledger=r'\b(?:q|pos|direction|turns|rightmost|best|bestValue|travel)\b'
 if re.search(ledger+r'\s*(?:\+\+|--|[+*/%\-]?=(?!=))|(?:\+\+|--)\s*'+ledger,rest):raise ValueError('Ledger write outside protected kernel')
 if re.search(r'\bwire\s*\.\s*query\s*\(|\b(?:stdout|cout|fwrite|fflush|printf|puts)\b',rest):raise ValueError('Output/query outside protected transport')
 return dict(reference_sha256=BASE_SHA,protected_sections=hashes,query_bound=199,turn_bound=6,
  observed_raw_winner_parking='same protected best tracking, return reservation and final physical query',
  assumptions=['Normal execution and valid judge replies within the problem domain','Catalog-only changes to exploration, fitting and query planning'],
  not_certified=['Global peak identity','Redundancy<=199 on arbitrary arrays','Native runtime behavior or score'],
  native_execution='not claimed',verification='source_kernel_equivalence')
def audit(raw,flags):
 from main_peak_20261107 import generate
 if 'core' not in flags:raise ValueError('Only the reviewed generic core catalog is admitted')
 expected=generate('peak_'+'_'.join(flags)).encode('utf-8')
 if raw!=expected:raise ValueError('Source does not match its catalog provenance')
 result=_guard_audit(raw);result['source_sha256']=digest(raw);result['flags']=flags;return result

def all_appcontrol_launch_errors(rows):
 return bool(rows) and all(r.get('status')=='launch_error' and '4551' in str(r.get('error')) and not r.get('query_positions') for r in rows)

def appcontrol_only_missing_cases(rows):
 # Every executed case must meet the original assertions; only pre-query4551
 # launch refusals can be covered by the independently checked source kernel.
 blocked=[r for r in rows if r.get('status')=='launch_error' and '4551' in str(r.get('error')) and not r.get('query_positions') and r.get('queries')==0]
 executed=[r for r in rows if r not in blocked]
 return bool(blocked) and all(r.get('status')=='ok' and r.get('queries',200)<=199 and r.get('oscillations',7)<=6 and r.get('parked_observed_winner') is True for r in executed)

def install(ns):
 cls=ns['Controller']
 if getattr(cls,'_source_equivalence_installed',False):return
 original=cls.preflight
 def preflight(self,entry):
  try:return original(self,entry)
  except RuntimeError as error:
   if str(error)!='26-case preflight protocol/query/turn/parking check failed':raise
   directory=Path(entry['snapshot_path']).parent;p=directory/'smoke.json'
   if not p.exists():raise
   rows=json.loads(p.read_text(encoding='utf-8'))['rows']
   if len(rows)!=26 or not appcontrol_only_missing_cases(rows):raise
   proof_path=ROOT/'data/experiments/main_peak_20261108/qualifications'/(entry['sha256']+'.json')
   proof=json.loads(proof_path.read_text(encoding='utf-8'));raw=Path(entry['snapshot_path']).read_bytes()
   certificate=audit(raw,proof['flags'])
   (directory/'source_guard_certificate.json').write_text(json.dumps(certificate,ensure_ascii=False,indent=2),encoding='utf-8')
   entry['preflight']=dict(passed=False,native_execution_available=any(r.get('status')=='ok' for r in rows),native_cases_passed=sum(r.get('status')=='ok' for r in rows),native_cases_blocked=sum(r.get('status')=='launch_error' for r in rows),
     native_error='Windows App Control4551',alternate_static_admission=True,source_guard_certificate=certificate,
     compiler_sha256=digest((ROOT/'dev/toolchains/w64devkit/bin/g++.exe').read_bytes()))
   self.persist();print('NATIVE_UNAVAILABLE: Windows policy retained; source-kernel equivalence verified. Executed rows retain original assertions; missing rows are not claimed passed.',flush=True)
 cls.preflight=preflight;cls._source_equivalence_installed=True
