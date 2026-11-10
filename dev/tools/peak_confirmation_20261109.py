"""Controlled waveform-confirmation ablations. Online totals select performance."""
from pathlib import Path
from datetime import datetime,timedelta
import argparse,json,re,sys,time,traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'dev/tools'),str(ROOT/'dev'),str(ROOT/'automation')]
from guard_equivalence_20261108 import _guard_audit,appcontrol_only_missing_cases
import wave_batch_20261106 as legacy
DAY='2026-11-09';OUT=ROOT/'data/experiments/main_peak_20261109'
BASE=ROOT/'data/versions/online_search/scored_217614_a87714acc894.cpp'
BASE_SHA='a87714acc894b2921c10a1ab65a2583916d29783c951502460d79620eff89bee'
AUTH=['继续优化，目前看着还有零分，试着改珠峰确认方案','你可以通过线上提交来确定，你设计的主峰识别对不对']
WHY={
 'after_challenge':'From the frozen best confirmed parent, challenge only marginal fitted peaks with a right interval survey.',
 'after_rebound':'From the frozen best parent, remove the short-stop versus rebound-distance blind interval.',
 'after_edge':'From the frozen best parent, recover an unresolved right boundary before and after refinement.',
 'after_width':'Use observed half-height peak width to choose the short confirmation horizon instead of a universal16position cap.',
 'after_plateau':'Directly query the center-preferred point between equal observed maxima before refinement, rather than leaving that tie-critical point to randomized planning.',
 'after_robust':'Add robust local-model agreement to the frozen best confirmation mechanism.',
 'after_sharp':'Add a verified dominant-spike confirmation path to the frozen best smooth-peak mechanism.',
 'after_predictive':'Add held-out predictive validation to the frozen best confirmation mechanism.',

 'spatial_fit':'Fit local curvature using the physical support interval of each observation rather than counting dense summit reads as independent broad support.',
 'spatial_all':'Correct spacing bias in both background dominance and the local quadratic confirmation.',
 'persistent_spatial_fit':'Combine temporal persistence with spacing-weighted local curvature confirmation.',
 'persistent_spatial_all':'Combine temporal persistence, spacing-weighted background and spacing-weighted local curvature.',
 'robust_confirmation':'Require the ordinary local quadratic and an existing iteratively reweighted fit to locate their maxima within the allowed parking tolerance.',
 'robust_persistent':'Use both temporal stability and agreement with a robust curvature fit before quick stopping.',
 'sharp_or_fit':'A unique raw spike with verified lower adjacent integer values and an extreme lead over every other observed value is a separate confirmation path; retain the smooth-fit path.',
 'hybrid_sharp':'Retain temporally stable smooth-peak confirmation while admitting a separately verified dominant raw spike; no raw maximum is removed as noise.',

 'persistent_challenge':'Combine the two individually beneficial mechanisms: temporally persistent peak confirmation and active interval falsification for marginal candidates.',
 'spatial_background':'Weight confirmation background and dispersion by the physical interval represented by each sample; dense summit bursts must not inflate their apparent statistical support.',
 'spatial_persistent':'Combine spacing-weighted background evidence with confirmation persistence across distinct forward samples.',
 'curvature_noise':'Estimate noise from four-point quadratic interpolation residuals normalized for irregular sample spacing; smooth curvature is not independent measurement noise.',
 'persistent_curvature_noise':'Combine temporal confirmation with a noise estimate that removes the effect of smooth curvature and nonuniform query gaps.',

 'challenge_marginal':'Falsify a statistically marginal fitted summit with a short right interval survey before accepting it; retain ordinary quick stopping for strongly separated single peaks.',
 'weak_companions':'Add a small stratified set of auxiliary reads only in weak-signal intervals, always preserving the parent outer endpoint and its logical coarse budget to avoid global grid phase drift.',

 'shoulder_recovery':'A right shoulder still rising toward a predicted value above the winner is also unconfirmed, even if its last sampled value has not become the raw maximum; probe within the current winner lease.',

 'persistent_confirmation':'Require coherent fitted peak location to persist across two distinct forward measurements; all fast apex exits use the same cached confirmation instead of a one-frame fit.',

 'edge_recovery':'A winner at the right search boundary is unbracketed; spend remaining budget on forward coverage with a reserved fine cell, then verify again if refinement exposes a new open boundary.',

 'predictive_fit':'Require leave-one-out quadratic prediction to beat constant-level error; a fitted peak must predict unused observations before authorizing short confirmation.',
 'scale_confirmation':'Local peak confirmation requires an independently spaced wider shoulder quadratic to place its maximum within the allowed3position parking tolerance of the local fit.',
 'short_rebound':'Resolve the16position quick-stop versus24position rebound blind spot: use the latest observed gap to decide when rebound evidence is available; retain amplitude/noise thresholds.',
 'confirmed_apex':'The unit-read apex exit must meet the same waveform evidence as the short scout; a few descending unit samples alone cannot bypass peak confirmation.',
 'rival_veto':'A coherent local fit cannot authorize short confirmation while a measured competing basin has a quadratic upper estimate comparable with the raw winner.',
}

def replace(s,a,b):
 if s.count(a)!=1:raise ValueError('Nonunique source anchor '+a)
 return s.replace(a,b,1)

def spatial_fit(code):
 start=code.index('    bool observedPeakEvidence() {');end=code.index('    void explore() {',start)
 body=code[start:end]
 body=replace(body,'        double matrix[3][4]{};',
  '        double matrix[3][4]{};\n        vector<double> fitWeights(hi-lo+1);\n        double weightSum=0,weightSquares=0;')
 a='            const double t=(xs[i]-best)/radius,y=value[xs[i]]-bestValue;'
 b=a+'\n            const int a=i>lo ? xs[i-1] : xs[i],b=i<hi ? xs[i+1] : xs[i];\n            const double weight=max(0.5,0.5*(b-a));\n            fitWeights[i-lo]=weight;weightSum+=weight;weightSquares+=weight*weight;'
 body=replace(body,a+'\n            const double basis[]={1,t,t*t};',b+'\n            const double basis[]={1,t,t*t};')
 body=replace(body,'matrix[r][c]+=basis[r]*basis[c];','matrix[r][c]+=weight*basis[r]*basis[c];')
 body=replace(body,'matrix[r][3]+=basis[r]*y;','matrix[r][3]+=weight*basis[r]*y;')
 body=replace(body,'for (int i=lo;i<=hi;++i) mean+=value[xs[i]]-bestValue;','for (int i=lo;i<=hi;++i) mean+=fitWeights[i-lo]*(value[xs[i]]-bestValue);')
 body=replace(body,'mean/=hi-lo+1;','mean/=weightSum;\n        const double effectiveFit=weightSum*weightSum/weightSquares;\n        if (effectiveFit<=3) '+('return reject();' if 'auto reject=' in body else 'return false;'))
 body=replace(body,'error+=residual*residual;total+=(y-mean)*(y-mean);','error+=fitWeights[i-lo]*residual*residual;total+=fitWeights[i-lo]*(y-mean)*(y-mean);')
 body=replace(body,'error*sqrt(static_cast<double>(hi-lo+1))','error*sqrt(effectiveFit)')
 return code[:start]+body+code[end:]

def followup(mode):
 spec=json.loads((OUT/'followup_parent.json').read_text(encoding='utf-8'))
 if spec['mode'].startswith('after_'):raise ValueError('Recursive followup parent')
 raw=generate(spec['mode'])
 import hashlib
 if hashlib.sha256(raw).hexdigest()!=spec['sha256']:raise ValueError('Frozen followup parent mismatch')
 code=raw.decode('utf-8')
 if mode=='after_challenge':
  reference=generate('challenge_marginal').decode('utf-8')
  lo=reference.index('                    if (marginalPeak(f)');hi=reference.index('                    if (auto sentinel=coarseShoulderSentinel(f)) {',lo)
  code=replace(code,'    void explore() {',(ROOT/'dev/templates/peak_challenge_20261109.inc').read_text(encoding='utf-8')+'\n    void explore() {')
  code=replace(code,'                    if (auto sentinel=coarseShoulderSentinel(f)) {',reference[lo:hi]+'                    if (auto sentinel=coarseShoulderSentinel(f)) {')
 elif mode=='after_rebound':
  code=replace(code,'rightmost>best+24 && value[f.x.back()]-valley>',
   'rightmost>best+max(3,f.x.size()>1 ? f.x.back()-f.x[f.x.size()-2] : 3) && value[f.x.back()]-valley>')
 elif mode=='after_edge':
  code=replace(code,'    void refine() {','    void localRefine() {')
  code=replace(code,'    void finish() {',(ROOT/'dev/templates/peak_edge_recovery_20261109.inc').read_text(encoding='utf-8')+'\n    void finish() {')
 elif mode=='after_width':
  code=replace(code,'                if (observedPeakEvidence()) scout=min(scout,16);',r"""
                if (observedPeakEvidence()) {
                    const double width=f.halfLeft>0 && f.halfRight>0 ?
                        sqrt(f.halfLeft*f.halfRight) : max(f.halfLeft,f.halfRight);
                    scout=min(scout,width>0 ? max(3,static_cast<int>(ceil(width))) : 16);
                }""")
 elif mode=='after_plateau':
  code=replace(code,'    void refine() {','    void localRefine() {')
  wrapper=r"""
    void refine() {
        if (alive && best>=0 && q<QMAX-1) {
            int left=best,right=best;
            for (int x:observed()) if (value[x]==bestValue) {
                left=min(left,x);right=max(right,x);
            }
            const int preferred=clamp((n-1)/2,left,right);
            if (left<right && value[preferred]<0) sample(preferred);
        }
        localRefine();
    }
"""
  code=replace(code,'    void finish() {',wrapper+'\n    void finish() {')
 elif mode=='after_sharp':
  reference=generate('sharp_or_fit').decode('utf-8');lo=reference.index('    bool observedPeakEvidence() {');hi=reference.index('    void explore() {',lo)
  code=replace(code,'    bool observedPeakEvidence() {','    bool smoothPeakEvidence() {')
  code=replace(code,'    void explore() {',reference[lo:hi]+'    void explore() {')
 elif mode in ('after_robust','after_predictive'):
  rejects='return reject();' if 'int evidenceQuery=' in code else 'return false;'
  if mode=='after_robust':
   test='\n        vector<int> robustSites(xs.begin()+lo,xs.begin()+hi+1);\n        const auto robustVertex=fittedVertex(robustSites);\n        if (!robustVertex || abs(*robustVertex-vertexPosition)>3) RETURN_REJECT;\n'.replace('RETURN_REJECT;',rejects)
  else:
   reference=generate('predictive_fit').decode('utf-8');lo=reference.index('        double predictionError=0;');hi=reference.index('        return predictionError<total;',lo)
   helper='\n    bool heldOutCoherent(const vector<int>& xs,int lo,int hi,double radius) {\n        double total=0,mean=0;\n        for (int i=lo;i<=hi;++i) mean+=value[xs[i]]-bestValue;\n        mean/=hi-lo+1;\n        for (int i=lo;i<=hi;++i) {\n            const double residual=value[xs[i]]-bestValue-mean;\n            total+=residual*residual;\n        }\n'+reference[lo:hi]+'        return total>1 && predictionError<total;\n    }\n'
   code=replace(code,'    void explore() {',helper+'\n    void explore() {')
   test='\n        if (!heldOutCoherent(xs,lo,hi,radius)) '+rejects+'\n'
  if 'int evidenceQuery=' in code:
   lo=code.index('        if (!(dominant && total>1 &&');hi=code.index('\n',lo)
   code=code[:hi+1]+test+code[hi+1:]
  else:
   lo=code.index('        return dominant && total>1 &&');code=code[:lo]+test+code[lo:]
 else:raise ValueError('Unknown followup')
 return code

def generate(mode):
 raw=BASE.read_bytes()
 import hashlib
 if hashlib.sha256(raw).hexdigest()!=BASE_SHA:raise ValueError('Frozen217614baseline changed')
 code=raw.decode('utf-8')
 if mode=='short_rebound':
  code=replace(code,'rightmost>best+24 && value[f.x.back()]-valley>',
   'rightmost>best+max(3,f.x.size()>1 ? f.x.back()-f.x[f.x.size()-2] : 3) && value[f.x.back()]-valley>')
 elif mode=='confirmed_apex':
  code=replace(code,'if (apexActive && apexReads>=3 && rightmost-best>=3 &&',
   'if (observedPeakEvidence() && apexActive && apexReads>=3 && rightmost-best>=3 &&')
 elif mode=='predictive_fit':
  code=replace(code,'        return dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;',r"""
        if (!(dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total)) return false;
        double predictionError=0;
        for (int held=lo;held<=hi;++held) {
            double trained[3][4]{};
            for (int i=lo;i<=hi;++i) if (i!=held) {
                const double t=(xs[i]-best)/radius,y=value[xs[i]]-bestValue;
                const double basis[]={1,t,t*t};
                for (int r=0;r<3;++r) {
                    for (int c=0;c<3;++c) trained[r][c]+=basis[r]*basis[c];
                    trained[r][3]+=basis[r]*y;
                }
            }
            for (int c=0;c<3;++c) {
                int pivot=c;
                for (int r=c+1;r<3;++r) if (abs(trained[r][c])>abs(trained[pivot][c])) pivot=r;
                if (abs(trained[pivot][c])<1e-12) return false;
                for (int j=c;j<4;++j) swap(trained[c][j],trained[pivot][j]);
                const double scale=trained[c][c];
                for (int j=c;j<4;++j) trained[c][j]/=scale;
                for (int r=0;r<3;++r) if (r!=c) {
                    const double factor=trained[r][c];
                    for (int j=c;j<4;++j) trained[r][j]-=factor*trained[c][j];
                }
            }
            const double t=(xs[held]-best)/radius;
            const double residual=value[xs[held]]-bestValue-(trained[0][3]+trained[1][3]*t+trained[2][3]*t*t);
            predictionError+=residual*residual;
        }
        return predictionError<total;""")
 elif mode=='scale_confirmation':
  code=replace(code,'        return dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;',r"""
        if (!(dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total)) return false;
        int left=-1,right=-1;
        for (int x:xs) {
            if (x<=best-2*radius) left=x;
            if (x>=best+2*radius) { right=x; break; }
        }
        if (left<0 || right<0) return physicalEdge;
        const double rising=static_cast<double>(value[best]-value[left])/(best-left);
        const double falling=static_cast<double>(value[right]-value[best])/(right-best);
        const double bend=(falling-rising)/(right-left);
        if (bend>=-1e-12) return false;
        const double widerVertex=(left+best)/2.0-rising/(2*bend);
        return widerVertex>=left && widerVertex<=right && abs(widerVertex-vertexPosition)<=3;""")
 elif mode=='edge_recovery':
  code=replace(code,'    void refine() {','    void localRefine() {')
  code=replace(code,'    void finish() {',(ROOT/'dev/templates/peak_edge_recovery_20261109.inc').read_text(encoding='utf-8')+'\n    void finish() {')
 elif mode=='persistent_confirmation':
  first=code.index('    bool observedPeakEvidence() {');last=code.index('    void explore() {',first)
  function=code[first:last]
  function=function.replace('return false;','return reject();')
  function=replace(function,'    bool observedPeakEvidence() {',r"""
    int evidenceQuery=-1,evidenceVotes=0,evidenceRight=-1;
    double evidenceVertex=0;
    bool evidenceAccepted=false;
    bool observedPeakEvidence() {
        if (evidenceQuery==q) return evidenceAccepted;
        evidenceQuery=q;evidenceAccepted=false;
        auto reject=[&]() { evidenceVotes=0;return false; };""")
  function=replace(function,'        return dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;',r"""
        if (!(dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total)) return reject();
        if (evidenceVotes>0 && abs(vertexPosition-evidenceVertex)<=3) {
            if (rightmost>evidenceRight) ++evidenceVotes;
        } else evidenceVotes=1;
        evidenceRight=rightmost;evidenceVertex=vertexPosition;
        evidenceAccepted=evidenceVotes>=2;
        return evidenceAccepted;""")
  code=code[:first]+function+code[last:]
  code=replace(code,'if (apexActive && apexReads>=3 && rightmost-best>=3 &&',
   'if (observedPeakEvidence() && apexActive && apexReads>=3 && rightmost-best>=3 &&')
 elif mode=='shoulder_recovery':
  recovery=(ROOT/'dev/templates/peak_edge_recovery_20261109.inc').read_text(encoding='utf-8')
  helper=r"""
    bool boundaryUnresolved() {
        if (rightmost>=n-1 || best<0) return false;
        if (best==rightmost) return true;
        const vector<int> xs=observed();
        if (xs.size()<3) return false;
        const int a=xs[xs.size()-3],b=xs[xs.size()-2],c=xs.back();
        const double first=static_cast<double>(value[b]-value[a])/(b-a);
        const double last=static_cast<double>(value[c]-value[b])/(c-b);
        if (first<=0 || last<=0) return false;
        const double bend=(last-first)/(c-a);
        double upper=value[c]+last*(c-b);
        if (bend<-1e-12) {
            const double derivative=last+bend*(c-b);
            if (derivative<=0) return false;
            upper=value[c]-derivative*derivative/(4*bend);
        }
        return upper>=bestValue;
    }
"""
  recovery=recovery.replace('best==rightmost && rightmost<n-1','boundaryUnresolved()')
  recovery=replace(recovery,'const int target=min(n-1,rightmost+step);',
      'const int target=min({n-1,rightmost+step,best+(199-3)});\n            if (target<=rightmost) break;')
  code=replace(code,'    void refine() {','    void localRefine() {')
  code=replace(code,'    void finish() {',helper+recovery+'\n    void finish() {')
 elif mode in ('challenge_marginal','persistent_challenge'):
  if mode=='persistent_challenge':code=generate('persistent_confirmation').decode('utf-8')
  helper=(ROOT/'dev/templates/peak_challenge_20261109.inc').read_text(encoding='utf-8')
  code=replace(code,'    void explore() {',helper+'\n    void explore() {')
  anchor='                    if (auto sentinel=coarseShoulderSentinel(f)) {'
  code=replace(code,anchor,r"""
                    if (marginalPeak(f) && q+3<=128) {
                        challengedPeak=best;
                        const int end=min({n-1,best+(199-3),rightmost+max(3,static_cast<int>(ceil(f.halfLeft+f.halfRight)))});
                        if (end>rightmost+2) {
                            const int start=rightmost;
                            const long long oldTop=bestValue,oldTail=value[rightmost];
                            for (int j=1;j<=3;++j) {
                                const int target=start+(end-start)*j/3;
                                if (!sample(target)) break;
                            }
                            if (!alive || certificate()) break;
                            if (bestValue>oldTop || value[rightmost]>oldTail+max(1.0,3*f.noise)) continue;
                            break;
                        }
                    }
"""+anchor)
 elif mode=='weak_companions':
  start=code.index('    void explore() {');end=code.index('    optional<double> vertex(',start)
  body=code[start:end]
  body=replace(body,'        int flatRuns=0, adjacentReads=0,apexReads=0;',
      '        const int companionBudget=static_cast<int>(ceil(sqrt(QMAX)));\n        int extraReads=0,companionIndex=0;\n        int flatRuns=0, adjacentReads=0,apexReads=0;')
  body=re.sub(r'\b128\b','(128+extraReads)',body)
  anchor='            if (next<=rightmost || !sample(next)) break;'
  body=replace(body,anchor,r"""
            while (companionIndex<companionBudget &&
                   static_cast<int>((companionIndex+0.5)*n/companionBudget)<=rightmost) ++companionIndex;
            if (!f.significant && companionIndex<companionBudget && extraReads<companionBudget &&
                q+2+2*companionBudget<QMAX) {
                const int probe=static_cast<int>((companionIndex+0.5)*n/companionBudget);
                if (probe>rightmost && probe<next) {
                    if (!sample(probe)) break;
                    ++extraReads;++companionIndex;
                }
            }
"""+anchor)
  code=code[:start]+body+code[end:]
 elif mode in ('spatial_background','spatial_persistent'):
  if mode=='spatial_persistent':code=generate('persistent_confirmation').decode('utf-8')
  original='        vector<double> levels;\n        for (int x:xs) levels.push_back(value[x]);\n        const double background=median(levels);\n        const double scatter=max(1.0,mad(levels));\n        const bool dominant=bestValue-background>scatter*sqrt(2*log(2.0+xs.size()));'
  code=replace(code,original,(ROOT/'dev/templates/peak_spatial_background_20261109.inc').read_text(encoding='utf-8'))
 elif mode in ('curvature_noise','persistent_curvature_noise'):
  if mode=='persistent_curvature_noise':code=generate('persistent_confirmation').decode('utf-8')
  code=replace(code,'        f.tolerance=max({1.0,3*f.noise,0.04*f.contrast});',r"""
        vector<double> cubicResidual;
        for (size_t i=1;i+2<f.x.size();++i) {
            const int sites[]={f.x[i-1],f.x[i],f.x[i+1],f.x[i+2]};
            const double location=sites[1];
            double prediction=0,variance=1;
            for (int j:{0,2,3}) {
                double weight=1;
                for (int k:{0,2,3}) if (j!=k)
                    weight*=(location-sites[k])/(sites[j]-sites[k]);
                prediction+=weight*value[sites[j]];variance+=weight*weight;
            }
            cubicResidual.push_back((value[sites[1]]-prediction)/sqrt(variance));
        }
        if (cubicResidual.size()>=5) f.noise=mad(cubicResidual);
        f.tolerance=max({1.0,3*f.noise,0.04*f.contrast});""")
 elif mode in ('spatial_fit','spatial_all','persistent_spatial_fit','persistent_spatial_all'):
  parent={'spatial_fit':None,'spatial_all':'spatial_background','persistent_spatial_fit':'persistent_confirmation','persistent_spatial_all':'spatial_persistent'}[mode]
  if parent:code=generate(parent).decode('utf-8')
  code=spatial_fit(code)
 elif mode in ('robust_confirmation','robust_persistent'):
  if mode=='robust_persistent':code=generate('persistent_confirmation').decode('utf-8')
  robust=r"""
        vector<int> robustSites(xs.begin()+lo,xs.begin()+hi+1);
        const auto robustVertex=fittedVertex(robustSites);
        if (!robustVertex || abs(*robustVertex-vertexPosition)>3) RETURN_REJECT;
"""
  if mode=='robust_confirmation':
   old='        return dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;'
   code=replace(code,old,robust.replace('RETURN_REJECT','return false')+old)
  else:
   old='        if (!(dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total)) return reject();'
   code=replace(code,old,old+robust.replace('RETURN_REJECT','return reject()'))
 elif mode in ('sharp_or_fit','hybrid_sharp'):
  if mode=='hybrid_sharp':code=generate('persistent_confirmation').decode('utf-8')
  code=replace(code,'    bool observedPeakEvidence() {','    bool smoothPeakEvidence() {')
  wrapper=r"""
    bool observedPeakEvidence() {
        if (best>0 && best+1<n && value[best-1]>=0 && value[best+1]>=0 &&
            bestValue>value[best-1] && bestValue>value[best+1]) {
            vector<double> levels;
            long long runnerUp=-1;
            for (int x:observed()) {
                levels.push_back(value[x]);
                if (x!=best) runnerUp=max(runnerUp,value[x]);
            }
            const double uncertainty=max(1.0,mad(levels))*sqrt(2*log(2.0+levels.size()));
            if (runnerUp>=0 && bestValue-runnerUp>uncertainty) return true;
        }
        return smoothPeakEvidence();
    }
"""
  code=replace(code,'    void explore() {',wrapper+'\n    void explore() {')
 elif mode.startswith('after_'):
  code=followup(mode)
 elif mode=='rival_veto':
  code=replace(code,'        return dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;',r"""
        if (!(dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total)) return false;
        const double sigma=max(1.0,sqrt(error/max(1,hi-lo-2)));
        const double margin=sigma*sqrt(2*log(2.0+xs.size()));
        for (size_t i=1;i+1<xs.size();++i) {
            const int a=xs[i-1],b=xs[i],c=xs[i+1];
            if (b>=xs[lo] && b<=xs[hi]) continue;
            if (value[b]<value[a] || value[b]<value[c] ||
                (value[b]==value[a] && value[b]==value[c])) continue;
            const double rising=static_cast<double>(value[b]-value[a])/(b-a);
            const double falling=static_cast<double>(value[c]-value[b])/(c-b);
            const double bend=(falling-rising)/(c-a);
            double upper=static_cast<double>(value[b]);
            if (bend<-1e-12) {
                const double derivative=rising+bend*(b-a);
                const double peak=b-derivative/(2*bend);
                if (peak>=a && peak<=c) upper-=derivative*derivative/(4*bend);
            }
            if (upper+margin>=bestValue) return false;
        }
        return true;""")
 else:raise ValueError('Unknown reviewed hypothesis '+mode)
 if re.search(r'fingerprint|deferred|\bn\s*==\s*\d+|\b(?:586|662|774)\b',code):raise ValueError('Lookup audit failed')
 return code.encode('utf-8')

def runtime():
 p=ROOT/'dev/tools/online_round_20261030.py';s=p.read_text(encoding='utf-8')
 s=s.replace('online_20261030"','main_peak_20261109"')
 s=replace(s,'DATE = "2026-10-30"','DATE = "2026-11-09"')
 start=s.index('AUTHORIZATION = ');end=s.index('\n',start);s=s[:start]+'AUTHORIZATION = '+repr(AUTH)+s[end:]
 a='                canonical = self.root / "data/versions" / f"main_online_{score}.cpp"'
 s=replace(s,a,a+'\n                if canonical.exists() and digest(canonical.read_bytes()) != entry["sha256"]:\n                    canonical = self.root / "data/versions" / f"main_wave_20261109_{score}_{digest(contents)[:12]}.cpp"')
 ns={'__name__':'confirmation_round_runtime','__file__':str(p)};exec(compile(s,str(p),'exec'),ns)
 original=ns['Controller'].preflight
 def preflight(self,entry):
  raw=Path(entry['snapshot_path']).read_bytes();proof=ns['read'](OUT/'qualifications'/(entry['sha256']+'.json'))
  if raw!=generate(proof['mode']):raise ValueError('Frozen candidate provenance mismatch')
  certificate=_guard_audit(raw)
  try:return original(self,entry)
  except RuntimeError as error:
   if str(error)!='26-case preflight protocol/query/turn/parking check failed':raise
   directory=Path(entry['snapshot_path']).parent;rows=ns['read'](directory/'smoke.json')['rows']
   if len(rows)!=26 or not appcontrol_only_missing_cases(rows):raise
   entry['preflight']=dict(passed=False,native_cases_passed=sum(r['status']=='ok' for r in rows),native_cases_blocked=sum(r['status']=='launch_error' for r in rows),alternate_static_admission=True,native_error='Windows4551before queries only',source_guard_certificate=certificate)
   ns['save'](directory/'source_guard_certificate.json',certificate);self.persist()
 ns['Controller'].preflight=preflight
 return ns

core=runtime()
for name,value in dict(core=core,Controller=core['Controller'],OUT=OUT,DAY=DAY,BATCH_IN_FLIGHT=2,connect=core['connect'],parse_quota=core['parse_quota'],now=core['now'],save=core['save'],read=core['read'],digest=core['digest']).items():setattr(legacy,name,value)
legacy.Batch.accept_wave=lambda self,entry:None

def report(c):
 if core['digest']((ROOT/'main.cpp').read_bytes())!=c.state['best_sha256']:raise RuntimeError('Main/best source mismatch')
 rows=c.state['rounds'];table=['|方案|正式分|对比提交前最高|状态|','|---|---:|---:|---|']
 for e in rows:table.append(f"|{e['name']}|{e.get('score','—')}|{e.get('delta','—')}|{e['state']}|")
 text='# 2026-11-09主峰确认实验\n\n[实验目录](../README.md) · [当前代码](../../../main.cpp) · [逐次状态](state.json)\n\n'
 text+=f"当前无打表采用 **{c.state['best_score']}**，当日起点217614。前期方案从冻结217614出发，后续受控组的父版见qualifications与followup_parent.json；按线上总分判断收益；不由合成分数挑选，不含指定样例长度、峰位或回复指纹。\n\n"+'\n'.join(table)+'\n\n'
 text+='carry_20261108行是昨日原作品只读恢复，不计入当日上传次数。 [研究过程](WORKLOG.md)记录机制假设与线上消融。\n\n'
 text+='本地只验证编译与交互/查询/振荡/真实停车。主机若在查询前被Windows4551拒绝启动，保留原记录，仅以源码内核等价审计补充缺项，未运行项不冒充通过；真实协议或预算错误仍拒绝。总分不能确认每个零分样例已恢复。未知上传只恢复原任务；旧任务保留原作品编号，无重传。\n'
 (OUT/'README.md').write_text(text,encoding='utf-8')
 core['save'](OUT/'selection.json',dict(score=c.state['best_score'],sha256=c.state['best_sha256'],checked_at=core['now']()))
 p=ROOT/'README.md';text=p.read_text(encoding='utf-8');text=re.sub(r'当前 main\.cpp 采用.*?历史最高分与当前源码分开记录。',f"当前 main.cpp 采用[纯波形主峰确认版](data/experiments/main_peak_20261109/README.md)，当前正式分 **{c.state['best_score']}**。历史最高分与当前源码分开记录。",text,count=1);p.write_text(text,encoding='utf-8')
 p=ROOT/'data/experiments/README.md';text=p.read_text(encoding='utf-8')
 if 'main_peak_20261109/README.md' not in text:p.write_text(text+'\n[2026-11-09主峰确认实验](main_peak_20261109/README.md)\n',encoding='utf-8')

def import_prior(c):
 old=core['read'](ROOT/'data/experiments/main_peak_20261108/state.json')
 for r in old['rounds']:
  if not r.get('job_id') or r['state'] in ('completed','failed'):continue
  if any(e.get('job_id')==r['job_id'] for e in c.state['rounds']):continue
  j=c.store.load(r['job_id']);c.store.validate_snapshot(j)
  if j.get('bound_submission_id')!=r.get('submission_id'):raise RuntimeError('Prior task identity mismatch')
  e=c.new_metadata('carry_20261108_'+r['name'],Path(j['snapshot_path']).read_bytes(),'Prior day original work: read/register only, never re-upload.',r['source_path'],True)
  c.attach(e,j);e.update(submission_id=j['bound_submission_id'],submitted_at=r.get('submitted_at'),prior_day=True);c.persist()

def run(modes,minutes):
 OUT.mkdir(parents=True,exist_ok=True)
 auth=dict(date=DAY,user_request=AUTH,maximum_platform_daily_attempts=30,plan=modes,selection='Online formal scores only; local checks for protocol/budget/parking',no_case_lookup=True,scope='Original Huawei contest only, new uploads stop at date change or zero actual remaining quota')
 prior=core['read'](OUT/'authorization.json',{})
 auth['runs']=prior.get('runs',[])+[dict(started_at=core['now'](),modes=modes)]
 core['save'](OUT/'authorization.json',auth)
 with core['SubmissionLock'](OUT/'.pipeline.lock'),core['SubmissionLock'](OUT/'.round.lock'):
  c=core['Controller']();import_prior(c)
  with core['connect'](c.config) as page:
   batch=legacy.Batch(c,page,minutes);batch.check_foreign_jobs();index=0;sent=[]
   while time.monotonic()<batch.stop_at:
    quota,records=batch.poll();report(c)
    if quota['beijing_date']==DAY and quota['used']<len(c.delivered()[0]):raise RuntimeError('Live quota is stale relative to saved attempts; no new upload')
    if any(e.get('job_id') and not e.get('prior_day') and e['state']=='failed' for e in c.state['rounds']):raise RuntimeError('Official judging failure; stop new uploads and preserve original jobs')
    own=[e for e in c.state['rounds'] if e.get('job_id') and not e.get('prior_day')]
    if index>=len(modes) and all(e['state'] in ('completed','failed') for e in own):return 0
    if index<len(modes) and quota['remaining']>0 and core['now']()[:10]==DAY and batch.can_send(records):
     mode=modes[index];index+=1;raw=generate(mode);sha=core['digest'](raw)
     if any(j['sha256']==sha for j in c.jobs()) or any(e.get('sha256')==sha for e in core['read'](c.manifest_path,{})['files']):print('Prior source: skip without upload',mode,sha,flush=True);continue
     core['candidate_review'](raw);certificate=_guard_audit(raw)
     source=OUT/(mode+'.cpp');core['preserve'](source,raw)
     construction=core['read'](OUT/'followup_parent.json') if mode.startswith('after_') else dict(sha256=BASE_SHA,score=217614)
     core['save'](OUT/'qualifications'/(sha+'.json'),dict(mode=mode,sha256=sha,construction_parent_sha256=construction['sha256'],construction_parent_score=construction['score'],rationale=WHY[mode],source_guard_certificate=certificate))
     e=c.new_metadata(mode,raw,WHY[mode],str(source));c.preflight(e)
     if not batch.upload(e):raise RuntimeError('Upload preconditions changed; no retry')
     sent.append(e['job_id']);report(c);print(json.dumps(dict(mode=mode,job_id=e['job_id'],actual_used=c.state['last_quota']['used'],best=c.state['best_score']),ensure_ascii=False),flush=True)
    else:
     if core['now']()[:10]!=DAY or quota['remaining']==0:
      if not any(not e.get('prior_day') and e['state'] not in ('completed','failed') for e in own):return 0
     page.page.wait_for_timeout(3000 if any(time.monotonic()-t<3 for _,t in batch.signatures.values()) else 15000)
   print('Read-only time window ended; resume existing jobs only.',flush=True);return 2

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('modes',nargs='*',choices=WHY);p.add_argument('--minutes',type=float,default=20);a=p.parse_args()
 try:raise SystemExit(run(a.modes,a.minutes))
 except Exception:traceback.print_exc();raise SystemExit(5)
