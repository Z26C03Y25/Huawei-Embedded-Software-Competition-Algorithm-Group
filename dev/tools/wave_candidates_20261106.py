"""Build the wave-only reference from an immutable historical source."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/experiments/blackbox_20261106'
PARENT = ROOT / 'data/versions/main_online_224148.cpp'

def replace(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError(f'Expected one anchor: {old}')
    return source.replace(old, new, 1)

def freeze(name, source):
    path = OUT / (name + '.cpp')
    raw = source.encode('utf-8')
    if path.exists():
        if path.read_bytes() != raw:
            raise RuntimeError(f'Already frozen: {path}')
        return path
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path

def baseline():
    code = PARENT.read_text(encoding='utf-8-sig')
    code = re.sub(r'    if \(n==(?:454|401|829|978|797)\) \{\n.*?\n    \}\n', '', code, flags=re.S)
    code = replace(code, '    vector<pair<int,long long>> deferred;\n    bool fingerprintStop=false;\n', '')
    code = code.replace('q-static_cast<int>(deferred.size())', 'q')
    start = code.index('    bool fingerprintEnabled(')
    end = code.index('        use(Op::B01);', start)
    code = code[:start] + '    void explore() {\n' + code[end:]
    code = code.replace('cq()', 'q')
    start = code.index('            const int from=rightmost;')
    end = code.index('            // Read a forward contiguous', start)
    code = code[:start] + '            if (next<=rightmost || !sample(next)) break;\n' + code[end:]
    code = replace(code, '((n>=539 && n<=613)) && ', '')
    code = replace(code, 'int scout=n<=500 ? clamp(static_cast<int>(f.halfLeft*0.3),16,32) : (n<=650 ? clamp(static_cast<int>(f.halfLeft*1.05),80,112) : clamp(static_cast<int>(f.halfLeft*1.2),96,144));',
                   '                int scout=clamp(static_cast<int>(0.85*f.halfLeft+0.18*f.halfRight),20,132);')
    code = replace(code, 'if (alive && !fingerprintStop) refine();', 'if (alive) refine();')
    if re.search(r'fingerprint|deferred|n\s*==\s*\d+|\b(?:586|662|774)\b', code):
        raise RuntimeError('Potential old table remains')
    return code


# Each candidate changes query placement, stopping, or route selection.
STEPS = {
    'adaptive': r'''
            if (!f.flat && f.x.size()>=5) {
                const int span=max(1,n-1-rightmost);
                const int cover=max(3,(span+125-q)/max(1,126-q));
                const double last=f.slopes.back();
                const double previous=f.slopes[f.slopes.size()-2];
                if (best==rightmost && last>0 && previous>last && !f.noisy) {
                    const int gap=f.x.back()-f.x[f.x.size()-2];
                    const double remaining=gap*last/(previous-last);
                    step=clamp(static_cast<int>(ceil(remaining/2)),2,cover+6);
                } else if (f.noisy || f.rebound) {
                    step=clamp(cover,3,8);
                } else {
                    step=clamp(cover+3,6,15);
                }
            }
''',
    'phase': r'''
            if (!f.flat && f.x.size()>=5) {
                const int stride=max(5,(n-1-rightmost+125-q)/max(1,126-q));
                const int spread=f.rises>0 && f.falls>0 ? 1 : 3;
                step=min(17,stride+static_cast<int>(random64()%static_cast<uint64_t>(2*spread+1)));
            }
''',
    'paired': r'''
            if (!f.flat && f.x.size()>=5) {
                // Alternate short and long gaps to expose narrow shoulders.
                const int cover=max(3,(n-1-rightmost+125-q)/max(1,126-q));
                step=q%2==0 ? min(16,2*cover+1) : max(1,cover/3);
                if (f.rebound || best>=rightmost-3) step=min(step,6);
            }
''',
    'asymmetry': r'''
            if (!f.flat && f.x.size()>=5) {
                const bool rawCrest=rightmost-best<12;
                const double uncertainty=max(1.0,f.noise);
                const int recentSpan=f.x.back()-f.x[f.x.size()-4];
                const double swing=abs(static_cast<double>(value[rightmost]-value[f.x[f.x.size()-4]]));
                if (rawCrest && swing<=4*uncertainty) step=3;
                else if (f.falls>0 && f.rises==0) step=13;
                else if (swing<=8*uncertainty && recentSpan>=12) step=14;
                else if (f.rises>=3 && !f.noisy) step=6;
            }
''',
    'scale': r'''
            if (!f.flat && f.x.size()>=5 && f.rises>=2 && best==rightmost) {
                const int width=f.halfLeft;
                const double slope=f.slopes.back();
                const int local=width>0 ? max(3,width/7) : 12;
                step=clamp(local,3,15);
                if (slope>0 && f.curvature<0 && !f.noisy) {
                    const int gap=f.x.back()-f.x[f.x.size()-2];
                    const double distance=slope*gap/(-f.curvature);
                    if (distance<=2.0*step) step=max(1,static_cast<int>(ceil(distance*0.6)));
                }
            }
''',
}

AUDITS = {
    'sentinel': r'''
        if (!alive || best<0 || q>=142 || rightmost>=n-1) return;
        const Features f=features();
        if (f.flat || f.plateau || bestValue==VMAX || !f.significant) return;
        const int cap=min(n-1,best+192);
        const int width=max(16,f.halfLeft+f.halfRight);
        const int first=min(cap,rightmost+clamp(width/2,11,38));
        if (first<=rightmost) return;
        const long long original=bestValue, previous=value[rightmost];
        if (!sample(first) || certificate()) return;
        const double threshold=max(2*f.noise,0.04*f.contrast);
        if (value[first]>previous+threshold) {
            const int end=min(n-1,min(best+192,first+clamp(width,32,112)));
            for (int x=first+5;x<=end && q<150;x+=5)
                if (!sample(x) || certificate()) return;
        } else if (value[first]>original-0.35*f.contrast) {
            for (int x=first+1;x<=min(cap,first+3);++x)
                if (!sample(x) || certificate()) return;
        }
''',
    'ladder': r'''
        if (!alive || best<0 || q>=142 || rightmost>=n-1 || bestValue==VMAX) return;
        Features f=features();
        if (f.x.size()<6 || f.plateau) return;
        const int cap=min(n-1,best+193);
        const int initial=rightmost;
        const long long originValue=value[initial];
        const double threshold=max(2*f.noise,0.02*f.contrast);
        bool signal=false;
        for (int offset:{8,21,43}) {
            const int x=min(cap,initial+offset);
            if (x<=rightmost || !sample(x)) break;
            if (value[x]>originValue+threshold) { signal=true; break; }
            if (x==cap || certificate()) return;
        }
        if (!signal) return;
        for (int x=rightmost+4;x<=min(n-1,best+193) && q<153;x+=4) {
            if (!sample(x) || certificate()) return;
            if (rightmost-best>=35 && bestValue-value[x]>max(3*f.noise,0.14*f.contrast)) break;
        }
''',
    'blank': r'''
        if (!alive || best<0 || q>=145 || rightmost>=n-1 || bestValue==VMAX) return;
        const Features f=features();
        // An almost level history leaves a large unobserved right region plausible.
        if (!f.flat && (f.significant || f.plateau || f.rises>1 || f.falls>1)) return;
        const int center=(n-1)/2;
        const int cap=min(n-1,max(best,center)+192);
        const int prior=rightmost;
        const int stride=max(3,(cap-prior+23)/24);
        for (int x=min(cap,prior+stride);x>rightmost && q<155;x=min(cap,x+stride)) {
            const long long old=bestValue;
            if (!sample(x) || certificate()) return;
            if (value[x]>old+max(1.0,2*f.noise)) {
                for (int y=x+1;y<=min(cap,x+5) && q<155;++y)
                    if (!sample(y) || certificate()) return;
            }
        }
''',
    'shoulder': r'''
        if (!alive || best<0 || q>=144 || rightmost>=n-1 || bestValue==VMAX) return;
        const Features f=features();
        if (f.x.size()<7 || f.flat || f.plateau) return;
        const int cap=min(n-1,best+190);
        array<double,3> blocks{};
        for (size_t b=0;b<blocks.size();++b) {
            vector<double> v;
            for (size_t j=0;j<2;++j) v.push_back(value[f.x[f.x.size()-6+2*b+j]]);
            blocks[b]=median(v);
        }
        const bool slowing=blocks[1]-blocks[2]<0.50*(blocks[0]-blocks[1]);
        if (!slowing && !f.rebound) return;
        const int start=rightmost;
        const int limit=min(cap,start+clamp(2*f.halfRight,25,92));
        const int stride=f.noisy ? 4 : 7;
        for (int x=min(limit,start+stride);x>rightmost && q<151;x=min(limit,x+stride)) {
            const auto previous=value[rightmost];
            if (!sample(x) || certificate()) return;
            if (value[x]<previous-max(3*f.noise,0.12*f.contrast) && x>best+24) return;
        }
''',
}

REFINE = {
    'exact': r'''
        if (!alive || best<0 || q>=188 || bestValue==VMAX) return false;
        const Features f=features();
        const auto it=lower_bound(f.x.begin(),f.x.end(),best);
        if (it==f.x.begin() || next(it)==f.x.end() || !f.significant || f.noisy || f.plateau)
            return false;
        const int left=*prev(it), right=*next(it);
        if (right-left>28 || value[left]>=bestValue || value[right]>=bestValue) return false;
        for (int p:f.peaks)
            if (abs(p-best)>right-left && value[p]>bestValue-0.22*f.contrast) return false;
        vector<int> plan;
        for (int x=right-1;x>left;--x) if (value[x]<0) plan.push_back(x);
        if (!routeSafe(plan)) return false;
        for (int x:plan) if (!sample(x)) return false;
        return true;
''',
    'envelope': r'''
        if (!alive || best<0 || q>=180 || bestValue==VMAX) return false;
        const Features f=features();
        if (f.flat || f.x.size()<4) return false;
        struct Gap { double rank; int a,b; };
        vector<Gap> gaps;
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1], b=f.x[i], width=b-a;
            if (width<=1) continue;
            const double high=max(value[a],value[b]);
            const double low=min(value[a],value[b]);
            const double localSlope=abs(f.slopes[i-1]);
            const double uncertainty=min(0.38*f.contrast, 0.5*width*localSlope+2*f.noise);
            const double rank=(high+0.22*(low-high)+uncertainty-bestValue)/max(1.0,f.contrast);
            if (rank>=-0.18 || a==best || b==best) gaps.push_back({rank,a,b});
        }
        sort(gaps.begin(),gaps.end(),[](const Gap& a,const Gap& b) {
            return a.rank!=b.rank ? a.rank>b.rank : a.b-a.a>b.b-b.a;
        });
        vector<int> plan;
        const int budget=min(42,QMAX-1-q);
        for (const auto& g:gaps) {
            const int free=budget-static_cast<int>(plan.size());
            if (g.b-g.a-1>free) continue;
            for (int x=g.a+1;x<g.b;++x) plan.push_back(x);
        }
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return false;
        for (int x:plan) if (!sample(x) || certificate()) break;
        return false;
''',
    'triad': r'''
        if (!alive || best<0 || q>=176 || bestValue==VMAX) return false;
        const Features f=features();
        if (!f.noisy && !f.rebound && f.peaks.size()<3) return false;
        vector<int> peaks=f.peaks;
        if (find(peaks.begin(),peaks.end(),best)==peaks.end()) peaks.push_back(best);
        sort(peaks.begin(),peaks.end(),[&](int a,int b){return better(a,value[a],b,value[b]);});
        vector<int> plan;
        const int budget=min(28,QMAX-1-q);
        for (int p:peaks) {
            if (value[p]<bestValue-max(5*f.noise,0.16*f.contrast)) break;
            for (int x=max(0,p-4);x<=min(rightmost,p+4) && static_cast<int>(plan.size())<budget;++x)
                if (value[x]<0 && find(plan.begin(),plan.end(),x)==plan.end()) plan.push_back(x);
        }
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return false;
        for (int x:plan) if (!sample(x) || certificate()) break;
        return false;
''',
    'modelgate': r'''
        if (!alive || best<0 || q>=178 || bestValue==VMAX) return false;
        const Features f=features();
        if (f.x.size()<6 || !f.significant || f.noisy || f.plateau || f.rebound) return false;
        auto model=multiModelVertex(f);
        if (!model || *model<0 || *model>rightmost) return false;
        const int center=static_cast<int>(llround(*model));
        const int left=max(0,center-4), right=min(rightmost,center+4);
        for (int p:f.peaks)
            if (abs(p-center)>20 && value[p]>=bestValue-0.18*f.contrast) return false;
        vector<int> plan;
        for (int x=right;x>=left;--x) if (value[x]<0) plan.push_back(x);
        if (!routeSafe(plan)) return false;
        for (int x:plan) if (!sample(x)) return false;
        if (best<=left || best>=right) return false;
        return value[best-1]<bestValue && value[best+1]<bestValue &&
               value[left]<bestValue && value[right]<bestValue;
''',
    'midcell': r'''
        if (!alive || best<0 || q>=183 || bestValue==VMAX) return false;
        const Features f=features();
        if (f.flat || f.x.size()<4) return false;
        vector<pair<double,int>> centers;
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1],b=f.x[i],gap=b-a;
            if (gap<=3) continue;
            const double high=max(value[a],value[b]);
            const double floorWeight=max(1.0,f.contrast);
            const double valueScore=(high-bestValue)/floorWeight;
            const double flatBonus=gap>=12 ? 0.05 : 0.0;
            centers.emplace_back(valueScore+flatBonus+0.015*log(gap),a+gap/2);
        }
        sort(centers.begin(),centers.end(),greater<pair<double,int>>());
        vector<int> plan;
        const int budget=min(17,QMAX-1-q);
        for (auto [priority,center]:centers) {
            if (priority<-0.24 || static_cast<int>(plan.size())>=budget) break;
            plan.push_back(center);
        }
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return false;
        for (int x:plan) if (!sample(x) || certificate()) break;
        return false;
''',
}

VARIANTS = {
    'wave_adaptive': ('adaptive','',''),
    'wave_exact': ('','','exact'),
    'wave_sentinel': ('','sentinel',''),
    'wave_ladder': ('','ladder',''),
    'wave_paired': ('paired','',''),
    'wave_blank': ('','blank',''),
    'wave_envelope': ('','','envelope'),
    'wave_phase': ('phase','',''),
    'wave_triad': ('','','triad'),
    'wave_asymmetry': ('asymmetry','',''),
    'wave_shoulder': ('','shoulder',''),
    'wave_modelgate': ('','','modelgate'),
    'wave_scale': ('scale','',''),
    'wave_midcell': ('','','midcell'),
    'wave_adapt_exact': ('adaptive','','exact'),
    'wave_adapt_ladder': ('adaptive','ladder',''),
    'wave_scale_sentinel': ('scale','sentinel',''),
    'wave_scale_exact': ('scale','','exact'),
    'wave_asym_envelope': ('asymmetry','','envelope'),
    'wave_asym_shoulder': ('asymmetry','shoulder',''),
    'wave_phase_blank': ('phase','blank',''),
    'wave_phase_triad': ('phase','','triad'),
    'wave_pair_midcell': ('paired','','midcell'),
    'wave_pair_ladder': ('paired','ladder',''),
    'wave_sentinel_exact': ('','sentinel','exact'),
    'wave_ladder_model': ('','ladder','modelgate'),
    'wave_blank_envelope': ('','blank','envelope'),
    'wave_shoulder_triad': ('','shoulder','triad'),
    'wave_adapt_ladder_envelope': ('adaptive','ladder','envelope'),
    'wave_scale_sentinel_exact': ('scale','sentinel','exact'),
    'wave_asym_shoulder_triad': ('asymmetry','shoulder','triad'),
    'wave_phase_blank_midcell': ('phase','blank','midcell'),
}

def variant(name):
    step, audit, refine = VARIANTS[name]
    code = baseline()
    if step:
        anchor = '            // Estimate where a positive slope will reach zero'
        code = replace(code, anchor, STEPS[step] + '\n' + anchor)
    if audit:
        anchor = '    void refine() {'
        code = replace(code, anchor, '    void auditFrontier() {' + AUDITS[audit] +
                       '    }\n' + anchor)
        code = replace(code, 'else { explore(); if (alive) refine(); }',
                       'else { explore(); if (alive) auditFrontier(); if (alive) refine(); }')
    if refine:
        anchor = '    void refine() {'
        code = replace(code, anchor, '    bool refineObservedCells() {' + REFINE[refine] +
                       '    }\n' + anchor + '\n        if (refineObservedCells() || certificate()) return;')
    return code


ALTERNATE = r'''
    void alternateExplore() {
        for (int x:{0,3,9,18}) {
            if (x>=n || !sample(x) || certificate()) return;
        }
        const int center=(n-1)/2;
        int stale=0;
        while (rightmost<n-1 && q<151 && seconds()<7.0) {
            const Features f=features();
            const size_t k=f.x.size();
            const int width=max(8,f.halfLeft+f.halfRight);
            const int rightAge=rightmost-best;
            const int lastGap=f.x[k-1]-f.x[k-2];
            const double last=f.slopes.back();
            const double prior=f.slopes[f.slopes.size()-2];
            const int cruise=max(4,(n-1-rightmost+148-q)/max(1,149-q));
            const double quiet=max(1.0,2.5*f.noise);
            const bool crest=f.significant && !f.noisy && best==rightmost &&
                last>0 && last<prior && lastGap*last<=11.0*(prior-last);
            const bool rival=rightAge>=20 && f.rebound;
            const bool resolved=f.significant && rightAge>=max(6,width/5) &&
                f.falls>=2 && value[rightmost]<bestValue-max(quiet,0.045*f.contrast);
            int stride=cruise;
            int cap=n-1;
            if (f.flat) {
                cap=min(n-1,center+166);
                stride=clamp(cruise+2,5,12);
            } else if (f.significant) {
                cap=min(n-1,best+191);
                if (crest) stride=1;
                else if (rival) stride=clamp(cruise/2,3,7);
                else if (f.noisy) stride=clamp(cruise,3,8);
                else stride=clamp(cruise+2,6,13);
                if (resolved && !rival) {
                    if (rightAge>=max(18,width/2) || stale>=1) break;
                    stride=clamp(width/4,8,31);
                    ++stale;
                } else stale=0;
            } else {
                stride=clamp(cruise+(q%3),4,12);
            }
            int x=min(cap,rightmost+stride);
            if (f.flat && rightmost<center && x>center) x=center;
            if (x<=rightmost || !sample(x) || certificate()) break;
        }
        coarseFrontier=rightmost;
    }
'''

STRATEGIC = {
    'wave_two_scale': ('alternate', ''),
    'wave_two_scale_exact': ('alternate','exact'),
    'wave_two_scale_envelope': ('alternate','envelope'),
    'wave_two_scale_triad': ('alternate','triad'),
    'wave_turn_pricing': ('priced',''),
    'wave_priced_midcell': ('priced','midcell'),
    'wave_priced_exact': ('priced','exact'),
    'wave_plateau_walk': ('plateau',''),
    'wave_plateau_model': ('plateau','modelgate'),
    'wave_crest_run': ('creep',''),
    'wave_crest_envelope': ('creep','envelope'),
    'wave_crest_triad': ('creep','triad'),
    'wave_persistence': ('persistence',''),
    'wave_persist_triad': ('persistence','triad'),
    'wave_persist_model': ('persistence','modelgate'),
    'wave_quantile_gap': ('quantile',''),
}

def strategic(name):
    kind, finish = STRATEGIC[name]
    code = baseline()
    if kind=='alternate':
        anchor = '    void explore() {'
        code = replace(code, anchor, ALTERNATE + '\n' + anchor)
        code = replace(code,'else { explore(); if (alive) refine(); }',
                       'else { alternateExplore(); if (alive) refine(); }')
    elif kind=='priced':
        code = replace(code,'return m-travel+o-turns;','return m-travel+30*(o-turns);')
        code = replace(code,'-parking-m-o-redundancy','-parking-m-30*o-redundancy')
        code = replace(code,'plan=canonical(move(plan),descending);','plan=orient(move(plan),descending);')
        code = replace(code,'proposal=canonical(move(proposal),descending);',
                       'proposal=orient(move(proposal),descending);')
    elif kind=='plateau':
        anchor='            // Estimate where a positive slope will reach zero'
        code=replace(code,anchor,r'''
            if (bestValue==VMAX) {
                int x=(n-1)/2;
                if (x<=rightmost) break;
                x=min(x,limit);
                if (x<=rightmost || !sample(x) || certificate()) return;
                continue;
            }
            if (f.plateau && rightmost<(n-1)/2 && value[rightmost]==bestValue)
                step=clamp(((n-1)/2-rightmost)/4,1,11);
''' + anchor)
    elif kind=='creep':
        code=replace(code,'if (nearApex) apexActive=true;',
                     'if (nearApex || (f.significant && !f.noisy && f.rises>=2 && best==rightmost && f.curvature<0)) apexActive=true;')
        code=replace(code,'if (apexActive && apexReads<18 && rightmost-best<=3 && !f.rebound) {\n                step=1;++apexReads;',
                     'if (apexActive && apexReads<28 && rightmost-best<=4 && !f.rebound) {\n                step=nearApex ? 1 : 2; ++apexReads;')
    elif kind=='persistence':
        anchor='                    use(Op::K07); break;'
        code=replace(code,anchor,r'''
                    const int near=rightmost-best;
                    const double spread=max(1.0,f.contrast);
                    const double drop=(bestValue-value[rightmost])/spread;
                    const int last=f.x.back()-f.x[f.x.size()-2];
                    const bool unresolved=drop<0.42 || (last>=8 && f.noisy);
                    const int ceiling=min(n-1,best+190);
                    if (unresolved && near<max(37,2*f.halfRight) && rightmost<ceiling) {
                        if (!sample(min(ceiling,rightmost+max(3,last/2)))) break;
                        if (certificate()) return;
                        continue;
                    }
''' + anchor)
    elif kind=='quantile':
        code=replace(code,'            const double uncertainty=max(f.noise,0.015*f.contrast);',
                     '            const double uncertainty=max(f.noise,0.025*f.contrast)*sqrt(max(1.0,(b-a)/6.0));')
        code=replace(code,'(s%2 ? 2*u-0.5 : 1.5*u);',
                     '(s%2 ? (x==(a+b)/2 ? 3*u : 0.8*u) : 1.4*u-0.35);')
        code=replace(code,'return 0.9*total/cases.size()+0.1*worst+','return 0.72*total/cases.size()+0.28*worst+')
    if finish:
        anchor='    void refine() {'
        code=replace(code,anchor,'    bool refineObservedCells() {'+REFINE[finish]+
                     '    }\n'+anchor+'\n        if (refineObservedCells() || certificate()) return;')
    return code

REVISIONS = {
    name + '_v2': name for name, parts in VARIANTS.items()
    if parts[1] in {'sentinel','shoulder'}
}
REVISIONS.update({
    name + '_v2': name for name, parts in STRATEGIC.items()
    if parts[0] in {'alternate','persistence'}
})


REOPEN = r'''
    void reopenAfterRefine() {
        if (!alive || best<0 || q>=184 || rightmost>=n-1 || certificate()) return;
        const Features f=features();
        if (f.x.size()<7 || f.plateau) return;
        const int from=rightmost;
        const int oldBest=best;
        const int cap=min(n-1,oldBest+191);
        const int lowGap=from-oldBest;
        const bool uncertain=f.flat || f.rebound ||
            (!f.significant && f.noise<4 && lowGap<170) ||
            (f.noisy && value[from]>=bestValue-0.15*f.contrast && lowGap<60);
        if (!uncertain || cap<=from || (pos<from-75 && !f.rebound)) return;
        const double threshold=max(1.0,max(2*f.noise,0.04*f.contrast));
        const int stride=f.flat ? 5 : 8;
        int limit=min(cap,from+24);
        for (int x=min(limit,from+stride);x>rightmost && q<191;x=min(limit,x+stride)) {
            if (!sample(x) || certificate()) return;
            if (best>oldBest && bestValue-value[from]>threshold) {
                limit=min(cap,x+14);
                for (int y=x+1;y<=limit && q<196;++y)
                    if (!sample(y) || certificate()) return;
                break;
            }
        }
    }
'''

ROBUST_FRONTIER = r'''
            // Compare several derivatives without smoothing the raw parking winner.
            if (f.x.size()>=7 && !f.flat) {
                const size_t k=f.x.size();
                const int p=f.x[k-1], l=f.x[k-3], ll=f.x[k-5], lll=f.x[k-7];
                const double a=static_cast<double>(value[p]-value[l])/(p-l);
                const double b=static_cast<double>(value[l]-value[ll])/(l-ll);
                const double c=static_cast<double>(value[ll]-value[lll])/(ll-lll);
                const int cover=max(3,(n-1-rightmost+124-q)/max(1,125-q));
                if (a>0 && b>0 && c>0 && a<b && b<c && rightmost-best<=4) {
                    const double deceleration=(b-a)/max(1.0,(p-ll)*0.5);
                    const double predicted=a/deceleration;
                    step=clamp(static_cast<int>(ceil(predicted/3)),1,13);
                } else if (max({a,b,c})>0 && min({a,b,c})<0) {
                    step=clamp(cover-1,3,7);
                } else if (a>=b && b>=c && c>=0) {
                    step=clamp(cover+3,6,14);
                }
            }
'''

EXPERIMENTS = {
    'wave_reopen': ('reopen','',''),
    'wave_adaptive_reopen': ('reopen','adaptive',''),
    'wave_reopen_envelope': ('reopen','','envelope'),
    'wave_robust_slope': ('slope','',''),
    'wave_robust_slope_exact': ('slope','','exact'),
    'wave_robust_slope_envelope': ('slope','','envelope'),
}

def experiment(name):
    kind, step, refiner=EXPERIMENTS[name]
    code=baseline()
    if step or kind=='slope':
        anchor='            // Estimate where a positive slope will reach zero'
        code=replace(code,anchor,(ROBUST_FRONTIER if kind=='slope' else STEPS[step]) + anchor)
    if kind=='reopen':
        anchor='    void refine() {'
        code=replace(code,anchor,REOPEN+'\n'+anchor)
        code=replace(code,'const int available=QMAX-1-q;',
                     'const int available=max(0,QMAX-1-q-(rightmost<n-1 ? 12 : 0));')
        code=replace(code,'else { explore(); if (alive) refine(); }',
                     'else { explore(); if (alive) refine(); if (alive) reopenAfterRefine(); }')
    if refiner:
        anchor='    void refine() {'
        code=replace(code,anchor,'    bool refineObservedCells() {'+REFINE[refiner]+
                     '    }\n'+anchor+'\n        if (refineObservedCells() || certificate()) return;')
    return code

REVISIONS.update({name+'_v2':name for name,parts in VARIANTS.items() if parts[0]=='adaptive'})
REVISIONS.update({name+'_v2':name for name,parts in EXPERIMENTS.items() if parts[0]=='slope' or parts[1]=='adaptive'})

def candidate(name):
    if name=='wave_baseline':
        return baseline()
    key=REVISIONS.get(name,name)
    code=experiment(key) if key in EXPERIMENTS else strategic(key) if key in STRATEGIC else variant(key)
    if name in REVISIONS:
        for old,new in (
            ('max(16,f.halfLeft+f.halfRight)','max(16,static_cast<int>(f.halfLeft+f.halfRight))'),
            ('clamp(2*f.halfRight,25,92)','clamp(static_cast<int>(2*f.halfRight),25,92)'),
            ('max(8,f.halfLeft+f.halfRight)','max(8,static_cast<int>(f.halfLeft+f.halfRight))'),
            ('max(37,2*f.halfRight)','max(37,static_cast<int>(2*f.halfRight))'),
            ('clamp(static_cast<int>(ceil(remaining/2)),2,cover+6)',
             'static_cast<int>(clamp(ceil(remaining/2),2.0,static_cast<double>(cover+6)))'),
            ('clamp(static_cast<int>(ceil(predicted/3)),1,13)',
             'static_cast<int>(clamp(ceil(predicted/3),1.0,13.0))'),
        ):
            code=code.replace(old,new)
    return code

if __name__ == '__main__':
    import sys
    names = sys.argv[1:] or ['wave_baseline']
    if names == ['--all']:
        names = list(VARIANTS) + list(STRATEGIC) + list(REVISIONS) + list(EXPERIMENTS)
    for name in names:
        print(freeze(name, candidate(name)))
