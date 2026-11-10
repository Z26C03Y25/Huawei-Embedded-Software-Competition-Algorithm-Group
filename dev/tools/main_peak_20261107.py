"""Wave-only main-peak recovery with frozen local ablations."""
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import hashlib
import json
import re
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/main_peak_20261107'
sys.path.insert(0,str(ROOT/'dev'))
from tools.local_judge import make_suite, run_case
from tools.mixed_scenarios import make_scenarios

PARENT=ROOT/'data/experiments/blackbox_20261106/wave_two_scale_v2.cpp'
COMPILER=ROOT/'dev/toolchains/w64devkit/bin/g++.exe'

def replace(code, old, new):
    if code.count(old)!=1:
        raise RuntimeError('Expected exactly one source anchor '+old)
    return code.replace(old,new,1)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def frozen(path,raw):
    if path.exists() and path.read_bytes()!=raw:
        raise RuntimeError('Refusing frozen overwrite '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        path.write_bytes(raw)

DENSE = r'''
    void completeCompetitors() {
        if (!alive || best<0 || q>=181 || certificate()) return;
        const Features f=features();
        if (f.flat || f.x.size()<4) return;
        vector<int> ranked=f.peaks;
        if (find(ranked.begin(),ranked.end(),best)==ranked.end()) ranked.push_back(best);
        sort(ranked.begin(),ranked.end(),[&](int a,int b) { return better(a,value[a],b,value[b]); });
        const double allowance=max(5*f.noise,0.12*f.contrast);
        vector<int> plan, selected;
        const int budget=min(44,QMAX-1-q);
        for (int peak:ranked) {
            if (value[peak]<bestValue-allowance) break;
            bool overlaps=false;
            for (int prior:selected) if (abs(peak-prior)<=12) overlaps=true;
            if (overlaps) continue;
            const auto it=lower_bound(f.x.begin(),f.x.end(),peak);
            const int left=it==f.x.begin() ? max(0,peak-5) : *prev(it);
            const int right=next(it)==f.x.end() ? min(rightmost,peak+5) : *next(it);
            const int radius=f.noisy ? 10 : 5;
            const int lo=max(0,min(left,peak-radius)),hi=min(rightmost,max(right,peak+radius));
            vector<int> cell;
            for (int x=lo;x<=hi;++x) if (value[x]<0) cell.push_back(x);
            if (cell.size()+plan.size()>static_cast<size_t>(budget)) continue;
            selected.push_back(peak);
            plan.insert(plan.end(),cell.begin(),cell.end());
            if (selected.size()>=3) break;
        }
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return;
        for (int x:plan) if (!sample(x) || certificate()) return;
    }
'''

LEASE = r'''
            bool coherentRise=false;
            if (k>=7 && rightAge>=24) {
                array<double,3> levels{};
                for (size_t b=0;b<3;++b) {
                    vector<double> block;
                    for (size_t j=0;j<2;++j) block.push_back(value[f.x[k-6+2*b+j]]);
                    levels[b]=median(block);
                }
                const double increment=max(1.0,0.008*f.contrast);
                const double first=levels[1]-levels[0],second=levels[2]-levels[1];
                coherentRise=first>increment && second>increment &&
                    second>0.6*first && levels[2]>=f.floor+0.08*f.contrast;
            }
'''

RESOLVED = r'''
    bool observedTopResolved() {
        if (best<0 || bestValue==VMAX) return certificate();
        const Features f=features();
        if (f.flat || f.plateau || f.x.size()<5) return false;
        for (int x=max(0,best-3);x<=min(rightmost,best+3);++x)
            if (value[x]<0) return false;
        const double allowance=max(4*f.noise,0.025*f.contrast);
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1], b=f.x[i];
            if (b-a>1 && max(value[a],value[b])>=bestValue-allowance) return false;
        }
        return true;
    }
'''

def generate(name):
    flags=name.split('_')
    if 'core' in flags:
        from wave_candidates_20261106 import baseline
        code=baseline()
        code=replace(code,'int scout=clamp(static_cast<int>(0.85*f.halfLeft+0.18*f.halfRight),20,132);',
                     'int scout=n<=500 ? clamp(static_cast<int>(f.halfLeft*0.3),16,32) : (n<=650 ? clamp(static_cast<int>(f.halfLeft*1.05),80,112) : clamp(static_cast<int>(f.halfLeft*1.2),96,144));')
    else:
        code=PARENT.read_text(encoding='utf-8-sig')
    if ('frontier' in flags or 'joint' in flags) and 'core' not in flags:
        code=replace(code,'cap=min(n-1,center+166);','cap=min(n-1,center+199);')
        code=replace(code,'stride=clamp(cruise+2,5,12);',
                     'stride=clamp(cruise+2,5,12);\n                if (cap-rightmost<=44) stride=min(stride,3);')
    if 'core' in flags and 'frontier' in flags:
        code=replace(code,'return lateFlat ? n-1 : min(n-1,(n-1)/2+144);','return lateFlat ? n-1 : min(n-1,(n-1)/2+199);')
        code=replace(code,'step=flatRuns>=8 ? 8 : 12;', 'step=flatRuns>=8 ? 8 : 12;\n                if (limit-rightmost<=44) step=min(step,3);')
    if 'lease' in flags or 'joint' in flags:
        code=replace(code,'            const bool rival=rightAge>=20 && f.rebound;',
                     LEASE+'\n            const bool rival=rightAge>=20 && (f.rebound || coherentRise);')
        code=replace(code,'cap=min(n-1,best+191);',
                     'cap=min(n-1,best+191);\n                if (coherentRise) cap=min(n-1,max(cap,rightmost+32));')
        code=replace(code,'if (rightAge>=max(18,width/2) || stale>=1) break;',
                     'if (rightAge>=max(30,3*width/4) || stale>=2) break;')
    if 'window' in flags or 'basin' in flags:
        code=replace(code,'            const bool rival=rightAge>=20 && f.rebound;',
                     LEASE+'\n            const bool rival=rightAge>=20 && (f.rebound || coherentRise);')
        code=replace(code,'cap=min(n-1,best+191);',
                     'cap=min(n-1,best+198);\n                if (coherentRise) cap=min(n-1,max(cap,rightmost+32));')
        if 'window' in flags:
            code=replace(code,'if (rightAge>=max(18,width/2) || stale>=1) break;',
                         'if (rightAge>=198) break;')
        else:
            code=replace(code,'if (rightAge>=max(18,width/2) || stale>=1) break;',
                         'if (rightAge>=clamp(2*width,88,180)) break;')
        code=replace(code,'stride=clamp(width/4,8,31);','stride=clamp(width/4,9,15);')
        code=replace(code,'        int stale=0;','')
        code=replace(code,'                    ++stale;','')
        code=replace(code,'                } else stale=0;','                }')
    if 'shelf' in flags:
        code=replace(code,'                if (coherentRise) cap=min(n-1,max(cap,rightmost+32));',
                     r'''
                bool shelf=false;
                if (k>=7 && rightAge>=60) {
                    const int begin=f.x[k-6];
                    long long low=value[begin],high=low;
                    for (size_t i=k-6;i<k;++i) {
                        low=min(low,value[f.x[i]]); high=max(high,value[f.x[i]]);
                    }
                    shelf=rightmost-begin>=24 && low>=bestValue-0.22*f.contrast &&
                        high-low<=max(3*f.noise,0.045*f.contrast);
                }
                if (coherentRise || shelf) cap=min(n-1,max(cap,rightmost+32));
''')
    if 'guarded' in flags:
        code=replace(code,'            const bool rival=rightAge>=20 && f.rebound;',
                     LEASE.replace('max(1.0,0.008*f.contrast)','max(2.5*f.noise,0.012*f.contrast)')+
                     '\n            const bool rival=rightAge>=20 && (f.rebound || coherentRise);')
        code=replace(code,'cap=min(n-1,best+191);',r'''
                const auto peakIt=lower_bound(f.x.begin(),f.x.end(),best);
                const int plausibleLeft=peakIt==f.x.begin() ? best : *prev(peakIt);
                cap=min(n-1,plausibleLeft+194);
                if (coherentRise) cap=min(n-1,max(cap,rightmost+24));
''')
        code=replace(code,'if (rightAge>=max(18,width/2) || stale>=1) break;',
                     'if (rightAge>=clamp(width,38,96) || stale>=2) break;')
    if 'selective' in flags:
        code=replace(code,'    void refine() {',DENSE.replace('        if (f.flat || f.x.size()<4) return;', '        if (f.flat || f.x.size()<4 || (!f.noisy && f.peaks.size()<=1 && !f.rebound)) return;')+'\n    void refine() {\n        completeCompetitors();')
    if 'dense' in flags or 'joint' in flags:
        code=replace(code,'    void refine() {',DENSE+'\n    void refine() {\n        completeCompetitors();')
    if 'contour' in flags:
        if 'selective' not in flags: raise RuntimeError('contour requires competitor scan')
        code=replace(code,'max(5*f.noise,0.12*f.contrast)','max(5*f.noise,0.25*f.contrast)')
        code=replace(code,'const int budget=min(44,QMAX-1-q);','const int budget=min(60,QMAX-1-q);')
        code=replace(code,'if (selected.size()>=3) break;','if (selected.size()>=5) break;')
    if 'interior' in flags:
        code=replace(code,'best>modelLo && best<modelHi','best>=modelLo+3 && best<=modelHi-3')
    if 'efficient' in flags:
        code=replace(code,'    void refine() {',RESOLVED+'\n    void refine() {')
        code=replace(code,'        completeCompetitors();','        completeCompetitors();\n        if (observedTopResolved()) return;')
    if 'flatreach' in flags:
        code=replace(code,'bool trace=false,strict=false,late=false;', 'bool trace=false,strict=false,late=true;')
        code=replace(code,'step=flatRuns>=8 ? 8 : 12;', 'step=max(5,(n-1-rightmost+127-q)/max(1,128-q));')
        code=replace(code,'int flatRuns=0, adjacentReads=0,apexReads=0;', 'int adjacentReads=0,apexReads=0;')
        code=replace(code,'++flatRuns; use(Op::B02);','use(Op::B02);')
        code=replace(code,'                flatRuns=0;','')
    if 'six' in flags or 'five' in flags:
        stride=6 if 'six' in flags else 5
        start=code.index('                if (f.rises>=2 && f.falls==0) {')
        end=code.index('                if (f.leftEdge',start)
        code=code[:start]+'                step='+str(stride)+';\n'+code[end:]
        code=replace(code,'if (f.rebound) { use(Op::K05); step=8; }', 'if (f.rebound) { use(Op::K05); step='+str(stride)+'; }')
    if 'nocreststop' in flags:
        code=replace(code,'if (apexActive && apexReads>=3 && rightmost-best>=3 &&', 'if (false && apexActive && apexReads>=3 && rightmost-best>=3 &&')
    if 'flatcover' in flags:
        code=replace(code,'bool trace=false,strict=false,late=false;', 'bool trace=false,strict=false,late=true;')
        code=replace(code,'step=flatRuns>=8 ? 8 : 12;',
                     'step=max(5,(n-1-rightmost+127-q)/max(1,128-q));')
    if 'narrow' in flags:
        code=replace(code,'if (f.significant && f.curvature<0 &&',
                     'if (f.significant && f.curvature<0 && f.halfLeft>0 && f.halfLeft<=2*f.maxGap &&')
    if 'priced' in flags:
        code=replace(code,'return m-travel+o-turns;','return m-travel+30*(o-turns);')
        code=replace(code,'-parking-m-o-redundancy','-parking-m-30*o-redundancy')

    from wave_candidates_20261106 import STEPS, AUDITS
    for flag,op in [('scalestep','scale'),('phase','phase'),('paired','paired'),('adaptive','adaptive'),('asymmetry','asymmetry')]:
        if flag in flags:
            code=replace(code,'            // Estimate where a positive slope will reach zero using local curvature.',
                         STEPS[op]+'\n            // Estimate where a positive slope will reach zero using local curvature.')
    for flag,op in [('tailprobe','sentinel'),('ladder','ladder'),('blank','blank')]:
        if flag in flags:
            code=replace(code,'    void refine() {','    void auditTail() {\n'+AUDITS[op].replace('max(16,f.halfLeft+f.halfRight)','max(16,static_cast<int>(ceil(f.halfLeft+f.halfRight)))')+'\n    }\n\n    void refine() {')
            code=replace(code,'else { explore(); if (alive) refine(); }','else { explore(); if (alive) { auditTail(); refine(); } }')
    if 'wideaudit' in flags:
        code=replace(code,'if (selected.size()>=3) break;','if (selected.size()>=5) break;')
        code=replace(code,'max(5*f.noise,0.12*f.contrast)','max(6*f.noise,0.35*f.contrast)')
        code=replace(code,'const int budget=min(44,QMAX-1-q);','const int budget=min(64,QMAX-1-q);')
    if 'nomodel' in flags:
        code=replace(code,'if (bestValue<VMAX && q<188) {','if (false && bestValue<VMAX && q<188) {')
    if 'modelguard' in flags:
        code=replace(code,'best>modelLo && best<modelHi','best>=modelLo+3 && best<=modelHi-3 && !f.noisy')
    if any(flag in flags for flag in ('widescout','shapescout','midscout')):
        old='int scout=n<=500 ? clamp(static_cast<int>(f.halfLeft*0.3),16,32) : (n<=650 ? clamp(static_cast<int>(f.halfLeft*1.05),80,112) : clamp(static_cast<int>(f.halfLeft*1.2),96,144));'
        if 'widescout' in flags: new='int scout=clamp(static_cast<int>(1.4*f.halfLeft+0.4*f.halfRight),96,160);'
        elif 'midscout' in flags: new='int scout=clamp(static_cast<int>(1.1*f.halfLeft+0.3*f.halfRight),48,144);'
        else:new='int scout=clamp(static_cast<int>(1.6*max(f.halfLeft,f.halfRight)),32,176);'
        code=replace(code,old,new)
    if 'quant' in flags:
        code=replace(code,'f.significant=f.contrast>max(4.0,25*f.noise);',r'''
        long long resolution=0;
        for (size_t i=1;i<f.x.size();++i)
            resolution=gcd(resolution,llabs(value[f.x[i]]-value[f.x[i-1]]));
        const double quantizationConfidence=max(1LL,resolution)*sqrt(f.x.size()*log(2.0+f.x.size()));
        f.significant=f.contrast>max(quantizationConfidence,f.tolerance*sqrt(log(2.0+f.x.size())));''')
    if 'noisehalf' in flags:
        code=replace(code,'})/1.2247448714;','})/2.4494897428;')
    if 'noiselocal' in flags:
        code=replace(code,'max({mad(residual),mad(local),0*median(absoluteResidual)})','min(mad(residual),mad(local))')
    if 'modeltight' in flags:
        code=replace(code,'abs(*v1-*v2)<10.0','abs(*v1-*v2)<3.0')
    if 'gapfill' in flags:
        code=replace(code,'const int radius=f.noisy ? 10 : 5;','const int radius=f.noisy ? 18 : 8;')
    if 'startdense' in flags:
        code=replace(code,'for (int x:{0,4,12,24}) {','for (int x=0;x<=max(12,static_cast<int>(sqrt(n)));x+=3) {')

    if 'intervalfine' in flags:
        start=code.index('    void refine() {');end=code.index('    void finish() {',start)
        body=r'''
    void refine() {
        for (int round=0;round<3 && q<QMAX-1 && alive && seconds()<7.5;++round) {
            if (certificate()) return;
            const Features f=features();
            if (f.x.size()<2) return;
            vector<double> absSlope;
            for (double slope:f.slopes) absSlope.push_back(abs(slope));
            const double slopeScale=max(1.0,median(absSlope));
            const double uncertainty=max(1.0,f.noise)*sqrt(log(2.0+q));
            vector<pair<double,pair<int,int>>> cells;
            for (size_t i=1;i<f.x.size();++i) {
                const int a=f.x[i-1],b=f.x[i];
                if (b-a<=1) continue;
                const double upper=max(value[a],value[b])+uncertainty+slopeScale*(b-a)/2;
                if (upper>=bestValue-f.tolerance)
                    cells.push_back({upper-bestValue+uncertainty,{a,b}});
            }
            sort(cells.begin(),cells.end(),[](const auto& a,const auto& b){return a.first>b.first;});
            const int remaining=QMAX-1-q;
            const int budget=round==0 ? max(1,remaining/2) : remaining;
            vector<int> plan;
            for (int x=max(0,best-3);x<=min(rightmost,best+3);++x)
                if (value[x]<0 && static_cast<int>(plan.size())<budget) plan.push_back(x);
            for (const auto& cell:cells) {
                const int lo=cell.second.first+1,hi=cell.second.second-1;
                const int room=budget-static_cast<int>(plan.size());
                if (room<=0) break;
                if (hi-lo+1<=room) {
                    for (int x=lo;x<=hi;++x) plan.push_back(x);
                } else {
                    const int mid=lo+(hi-lo)/2;
                    for (int radius=0;static_cast<int>(plan.size())<budget && radius<=hi-lo;++radius)
                        for (int x:{mid-radius,mid+radius}) if (x>=lo && x<=hi &&
                            find(plan.begin(),plan.end(),x)==plan.end() && static_cast<int>(plan.size())<budget)
                            plan.push_back(x);
                }
            }
            sort(plan.begin(),plan.end());plan.erase(unique(plan.begin(),plan.end()),plan.end());
            plan=orient(move(plan),round%2==0);
            if (plan.empty() || !routeSafe(plan)) return;
            for (int x:plan) if (!sample(x) || certificate()) return;
        }
    }
'''
        code=code[:start]+body+code[end:]
    if 'evidencescout' in flags:
        start=code.index('    void explore() {');end=code.index('    optional<double> vertex(',start)
        body=r'''
    void explore() {
        if (!sample(0)) return;
        const int reserve=max(3,static_cast<int>(ceil(2*sqrt(n))));
        const int coarseBudget=max(1,QMAX-1-reserve);
        while (q<coarseBudget && rightmost<n-1 && seconds()<7.0) {
            const Features f=features();
            if (certificate()) return;
            int cap=n-1;
            if (f.significant) cap=min(n-1,f.left+199);
            if (rightmost>=cap) break;
            const int remaining=max(1,coarseBudget-q);
            const int coverage=max(1,(cap-rightmost+remaining-1)/remaining);
            const double width=max(static_cast<double>(max(1,f.maxGap)),f.halfLeft+f.halfRight);
            int step=max(coverage,static_cast<int>(ceil(sqrt(width))));
            if (!f.slopes.empty() && best==rightmost && f.slopes.back()>0) {
                const double change=max(1.0,abs(f.curvature));
                const double vertexDistance=f.slopes.back()*max(1,f.maxGap)/change;
                step=max(1,min(step,static_cast<int>(ceil(sqrt(max(1.0,vertexDistance))))));
            }
            if (f.noisy) step=min(step,max(1,static_cast<int>(ceil(sqrt(max(1.0,width/2))))));
            const double tail=width*sqrt(log(2.0+f.x.size()))+max(1,f.maxGap);
            if (f.significant && !f.rebound && f.halfRight>0 && rightmost-best>=tail &&
                bestValue-value[rightmost]>max(f.tolerance,2*f.noise)) break;
            if (q+max(1,(n-1-rightmost+step-1)/step)>coarseBudget &&
                (f.flat || best==rightmost)) step=max(step,coverage);
            int next=min(cap,rightmost+step);
            const int center=(n-1)/2;
            if (f.flat && rightmost<center && next>center) next=center;
            if (next<=rightmost || !sample(next)) break;
        }
        coarseFrontier=rightmost;
    }
'''
        code=code[:start]+body+code[end:]

    if 'cellbudget' in flags:
        if 'evidencescout' not in flags: raise RuntimeError('Cell budget requires evidence scout')
        code=replace(code,'        const int reserve=max(3,static_cast<int>(ceil(2*sqrt(n))));\n        const int coarseBudget=max(1,QMAX-1-reserve);\n        while (q<coarseBudget && rightmost<n-1 && seconds()<7.0) {',
                     '        const int minimumReserve=max(3,static_cast<int>(ceil(log2(n+1.0))));\n        while (q<QMAX-1-minimumReserve && rightmost<n-1 && seconds()<7.0) {')
        start=code.index('    void explore() {');end=code.index('    optional<double> vertex(',start)
        body=code[start:end]
        body=replace(body,'            if (certificate()) return;\n            int cap=n-1;',r'''
            if (certificate()) return;
            int unresolved=0;
            if (f.significant) for (size_t i=1;i<f.x.size();++i) {
                const int a=f.x[i-1],b=f.x[i];
                if (max(value[a],value[b])>=bestValue-f.tolerance) unresolved+=max(0,b-a-1);
            }
            const int reserve=max(minimumReserve,min(QMAX-1,unresolved));
            const int coarseBudget=QMAX-1-reserve;
            if (q>=coarseBudget) break;
            int cap=n-1;''')
        code=code[:start]+body+code[end:]

    if 'relativetolerance' in flags:
        code=replace(code,'f.tolerance=max({1.0,3*f.noise,0.04*f.contrast});',
                     'f.tolerance=max({1.0,f.noise*sqrt(2*log(2.0+f.x.size())),f.contrast/max(1.0,sqrt(static_cast<double>(f.x.size())))});')
    if 'statisticalsignal' in flags:
        code=replace(code,'f.significant=f.contrast>max(4.0,25*f.noise);',
                     'f.significant=f.contrast>max(4.0,sqrt(f.x.size()*log(2.0+f.x.size()))*f.noise);')
    if 'quantilefloor' in flags:
        code=replace(code,'        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;',r'''
        vector<double> floorLevels;
        for (int x:f.x) floorLevels.push_back(value[x]);
        sort(floorLevels.begin(),floorLevels.end());
        const size_t lowCount=max(size_t{1},static_cast<size_t>(sqrt(floorLevels.size())));
        f.floor=floorLevels[(lowCount-1)/2];
        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;''')
    if 'sweepcover' in flags:
        method="""
    int coverageStride() const {
        int stride=1;
        // Cover the domain plus a two-sided fine cell and initial/adjacent reads.
        while ((n-1+stride-1)/stride+2*stride+16>QMAX-1 && stride<n) ++stride;
        return stride;
    }
"""
        code=replace(code,'    void explore() {',method+'\n    void explore() {')
        start=code.index('    void explore() {');end=code.index('    optional<double> vertex(',start)
        body=code[start:end]
        body=re.sub(r'\b128\b','(QMAX-2-2*coverageStride())',body)
        body=replace(body,'step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;','step=coverageStride();')
        body=replace(body,'if (f.noisy) step=8;','if (f.noisy) step=coverageStride();')
        body=replace(body,'else step=f.noisy || state==Shape::Rough ? 8 : 8;','else step=coverageStride();')
        body=replace(body,'if (f.rebound) { use(Op::K05); step=8; }','if (f.rebound) { use(Op::K05); step=coverageStride(); }')
        code=code[:start]+body+code[end:]
    if 'multiguard' in flags:
        code=replace(code,'if (apexActive && apexReads>=3 && rightmost-best>=3 &&',
            'if (f.peaks.size()<=1 && apexActive && apexReads>=3 && rightmost-best>=3 &&')
    if 'curvaturenoise' in flags:
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
                prediction+=weight*value[sites[j]];
                variance+=weight*weight;
            }
            cubicResidual.push_back((value[sites[1]]-prediction)/sqrt(variance));
        }
        if (cubicResidual.size()>=5) f.noise=mad(cubicResidual);
        f.tolerance=max({1.0,3*f.noise,0.04*f.contrast});""")
    if 'tailvalley' in flags:
        start=code.index('    optional<int> coarseShoulderSentinel(')
        end=code.index('    int frontierLimit(',start)
        code=code[:start]+(ROOT/'dev/templates/peak_tail_valley_20261108.inc').read_text(encoding='utf-8')+'\n'+code[end:]
    if 'staggered' in flags or 'staggerweak' in flags:
        code=replace(code,'            int next=min({n-1,rightmost+step,limit});',r"""
            if (step>3 && !f.flat) {
                const double phase=fmod(q*0.6180339887498948482,1.0);
                step=max(4,step+static_cast<int>(llround((phase-0.5)*step/2)));
            }
            int next=min({n-1,rightmost+step,limit});""")
        if 'staggerweak' in flags:
            code=replace(code,'if (step>3 && !f.flat) {',
                'if (step>3 && !f.flat && !f.significant && f.contrast<=max(1.0,f.noise)*sqrt(2*log(2.0+f.x.size()))) {')
    if 'burstsupport' in flags:
        code=replace(code,'            const long long previousBest=bestValue;',
            '            const int previousPosition=rightmost;\n            const long long previousBest=bestValue;')
        code=replace(code,'if (f.significant && f.curvature<0 &&\n                value[next]>previousBest && adjacentReads+2<=12 &&',
            'if ((value[next]>previousBest || !f.significant || f.rebound) &&\n                value[next]>value[previousPosition]+max(1.0,f.noise)*sqrt(2*log(2.0+q)) && adjacentReads+2<=12 &&')
    if 'fitstop' in flags:
        helper=(ROOT/'dev/templates/main_peak_verification_20261108.inc').read_text(encoding='utf-8').split('    void verifyWinningCell() {')[0]
        helper=replace(helper,'        if (bestValue-background>scatter*sqrt(2*log(2.0+xs.size()))) return true;',
            '        const bool dominant=bestValue-background>scatter*sqrt(2*log(2.0+xs.size()));')
        helper=replace(helper,'return total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;',
            'return dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;')
        code=replace(code,'    void explore() {',helper+'\n    void explore() {')
        code=replace(code,'                if (best>=(n-1)/2) scout=min(scout,16);',
            '                if (observedPeakEvidence()) scout=min(scout,16);')
    if 'nocentercap' in flags:
        code=replace(code,'                if (best>=(n-1)/2) scout=min(scout,16);','')
    if 'widthcap' in flags:
        code=replace(code,'                if (best>=(n-1)/2) scout=min(scout,16);',
            '                scout=min(scout,max(16,static_cast<int>(ceil(f.halfLeft+f.halfRight))));')
    if 'winnerfrontier' in flags:
        code=replace(code,'return min(n-1,f.left+199);','return min(n-1,best+199);')
    if 'basinunion' in flags:
        code=replace(code,'    void completeCompetitors() {','    void legacyCompetitors() {')
        code=replace(code,'    void refine() {',(ROOT/'dev/templates/peak_basin_union_20261108.inc').read_text(encoding='utf-8')+'\n    void refine() {')
    if any(op in flags for op in ('maincover','mainverify','maincoherent','mainall')):
        code=replace(code,'    void refine() {','    void legacyRefine() {')
        verification=(ROOT/'dev/templates/main_peak_verification_20261108.inc').read_text(encoding='utf-8')
        verification=verification.replace('__VERIFY_STRONG__','true' if 'mainverify' in flags else 'false')
        verification=verification.replace('__EXHAUST_AUDIT__','true' if 'mainverify' in flags else 'false')
        if 'maincoherent' in flags:
            verification=replace(verification,'        if (bestValue-background>scatter*sqrt(2*log(2.0+xs.size()))) return true;',
                '        const bool dominant=bestValue-background>scatter*sqrt(2*log(2.0+xs.size()));')
            verification=replace(verification,'return total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;',
                'return dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;')
        if 'mainall' in flags:
            verification=replace(verification,'const bool evidence=observedPeakEvidence();','const bool evidence=false;')
        code=replace(code,'    void finish() {',verification+'\n    void finish() {')
    if 'zerosalvage' in flags:
        code=replace(code,'    void refine() {','    void legacyRefine() {')
        code=replace(code,'    void finish() {',(ROOT/'dev/templates/peak_zero_salvage_20261108.inc').read_text(encoding='utf-8')+'\n    void finish() {')
    return code

def compile_source(name):
    source=OUT/(name+'.cpp')
    code=generate(name)
    if any(token in code for token in ('fingerprint','deferred','n==479','n==797','n==829','n==978')):
        raise RuntimeError('Table audit failed')
    frozen(source,code.encode('utf-8'))
    executable=OUT/(name+'.exe')
    result=subprocess.run([str(COMPILER),'-O3','-Wall','-Wextra','-Wpedantic','-std=c++17',str(source),'-o',str(executable)],
                          capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/(name+'.compile.txt')).write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode or result.stderr.strip():
        raise RuntimeError('Compiler rejected '+name)
    return source,executable

def score(row):
    return max(0,row['score']-29*row['oscillations'])

def stats(rows):
    scores=sorted(score(r) for r in rows)
    return dict(cases=len(rows),mean=round(statistics.mean(scores),3),zeros=scores.count(0),
                cvar25=round(statistics.mean(scores[:max(1,len(scores)//4)]),3),
                wrong_peak=sum(r['distance']>3 for r in rows),
                redundancy_fail=sum(r['redundancy']>199 for r in rows),
                errors=sum(r['status']!='ok' or r['queries']>199 or r['oscillations']>6 or not r['parked_observed_winner'] for r in rows))

def evaluate(executable,cases):
    rows=[]
    for case in cases:
        row=run_case([str(executable)],case)
        path=row['query_positions']
        winner=min(set(path),key=lambda x:(-case.values[x],abs(2*x-(len(case.values)-1)),x)) if path else None
        row['parked_observed_winner']=bool(path) and row['final_position']==winner
        rows.append(row)
    return rows

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=['development','confirmation','core_confirmation','final_confirmation'],default='development')
    parser.add_argument('names',nargs='+')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.phase=='development':
        mixed=[c for c,m in make_scenarios(8,['development'],20261107103,novel=True) if m['transform']=='base']
        classic=make_suite('extended',20261107041)
    elif args.phase=='final_confirmation':
        mixed=[c for c,m in make_scenarios(18,['selection','blind_shift'],20261107719,novel=True) if m['transform']=='base']
        classic=make_suite('extended',20261107723)
    elif args.phase=='core_confirmation':
        mixed=[c for c,m in make_scenarios(18,['selection','blind_shift'],20261107503,novel=True) if m['transform']=='base']
        classic=make_suite('extended',20261107511)
    else:
        mixed=[c for c,m in make_scenarios(18,['selection','blind_shift'],20261107317,novel=True) if m['transform']=='base']
        classic=make_suite('extended',20261107089)
    cases=classic+mixed
    manifest=[dict(name=c.name,family=c.family,array_sha256=sha(json.dumps(c.values).encode())) for c in cases]
    frozen(OUT/(args.phase+'_manifest.json'),json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
    sources={}
    for name in args.names:
        sources[name]=compile_source(name)
    def run(item):
        name,(source,executable)=item
        rows=evaluate(executable,cases)
        groups=defaultdict(list)
        for row in rows: groups[row['family']].append(row)
        summary=dict(name=name,sha256=sha(source.read_bytes()),official=False,
                     classic=stats(rows[:len(classic)]),mixed=stats(rows[len(classic):]),
                     families={k:stats(v) for k,v in groups.items()})
        save(OUT/(args.phase+'_'+name+'.json'),dict(summary=summary,rows=rows))
        print(json.dumps({k:v for k,v in summary.items() if k!='families'},ensure_ascii=False),flush=True)
        return summary
    with ThreadPoolExecutor(max_workers=4) as pool:
        summaries=list(pool.map(run,sources.items()))
    save(OUT/(args.phase+'_summary.json'),summaries)

if __name__=='__main__':
    main()
