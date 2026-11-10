"""Generate named structural experiments from a frozen, officially scored parent.

Generation is offline; this file never uploads or selects by synthetic scores.
"""
from pathlib import Path
import argparse, hashlib, json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261031'

def replace_once(text,old,new):
    if text.count(old)!=1:
        raise ValueError('Unexpected source anchor: '+old)
    return text.replace(old,new,1)

def generate(name, parent):
    parent=parent.resolve()
    text=parent.read_text(encoding='utf-8-sig')
    condition={'continue_all':'true','continue_short':'n<=500',
               'continue_mid':'n>500 && n<=650','continue_long':'n>650'}.get(name)
    if condition:
        text=replace_once(text,
            'if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;',
            'if (certificate() || (!('+condition+') && bestValue<VMAX && best>modelLo && best<modelHi)) return;')
        description='Keep model verification reads, but continue candidate search instead of model early exit when '+condition
    elif name in ['interval_sweep_retry','interval_early_handoff'] or name.startswith('interval_sweep_retry_v2'):
        helper=r'''
    void intervalSweepRetry() {
        for (int attempt=0;attempt<2 && alive && seconds()<7.5;++attempt) {
            Features f=features();
            double center=best;
            if (!attempt) if (auto v=multiModelVertex(f)) center=*v;
            const int radius=attempt ? 16 : 8;
            const int L=max(0,min(best-radius,static_cast<int>(floor(center))-3));
            const int U=min(rightmost,max(best+radius,static_cast<int>(ceil(center))+3));
            vector<int> scan;
            for (int x=U;x>=L;--x) if (value[x]<0) scan.push_back(x);
            // First verification reserves a retry corridor, a second complete
            // interval and final parking. Never label a partial scan complete.
            const int reserve=attempt ? 1 : 41;
            int p=pos,d=direction,o=turns; long long m=travel;
            for (int x:scan) moveTo(x,p,d,o,m);
            if (q+static_cast<int>(scan.size())+reserve>QMAX ||
                o+(attempt?1:3)>OMAX || !routeSafe(scan)) {
                if (!attempt) refine();
                return;
            }
            for (int x:scan) if (!sample(x) || certificate()) return;
            const bool rightOpen=best>=U-2 && U<n-1;
            const bool leftOpen=best<=L+2 && L>0;
            if (attempt || (!rightOpen && !leftOpen)) return;
            if (leftOpen && !rightOpen) continue;
            const long long previousBest=bestValue;
            // Continue right only after unresolved right-boundary evidence.
            // Candidate-relative R control is heuristic, not a true-target proof.
            for (int k=0;k<16 && q+26<=QMAX && seconds()<7.0;++k) {
                Features g=features();
                const int limit=min(frontierLimit(g),min(n-1,best+196));
                const int next=min(limit,rightmost+8);
                if (next<=rightmost || !sample(next)) break;
                if (certificate()) return;
                if (bestValue>previousBest && rightmost-best>=16 && value[rightmost]<bestValue) break;
            }
            if (bestValue<=previousBest) return; // Cached previous winner remains available.
        }
    }
'''
        if name.startswith('interval_sweep_retry_v2') or name=='interval_early_handoff':
            helper=helper.replace('attempt ? 1 : 41','attempt ? 1 : 49').replace('q+26<=QMAX','q+34<=QMAX')
        if name=='interval_early_handoff':
            helper=helper.replace('if (attempt || (!rightOpen && !leftOpen)) return;',
                                  'if (attempt) return;')
            helper=helper.replace('const bool rightOpen=best>=U-2 && U<n-1;',
                                  'const bool rightOpen=best>=U-2 && U<n-1;')
            text=replace_once(text,'            int limit=frontierLimit(f);',
                '            if (f.significant && f.falls>=2 && rightmost-best>=16) break;\n            int limit=frontierLimit(f);')
        text=replace_once(text,'    void refine() {',helper+'    void refine() {')
        group=name.removeprefix('interval_sweep_retry_v2').lstrip('_') if name.startswith('interval_sweep_retry_v2') else ''
        gate={'':'true','short':'n<=500','mid':'n>500 && n<=650','long':'n>650',
              'midlong':'n>500','shortmid':'n<=650','shortlong':'n<=500 || n>650'}[group]
        text=replace_once(text,'else { explore(); if (alive) refine(); }',
                         'else { explore(); if (alive) { if ('+gate+') intervalSweepRetry(); else refine(); } }')
        description='Predict a candidate interval, exhaust its raw integer cells, reserve41 reads/three turns for first-pass retry; on unresolved right edge continue right and verify a second interval; preserve cached fallback and final parking'
        if name.startswith('interval_sweep_retry_v2') or name=='interval_early_handoff':
            description=description.replace('reserve41','reserve49')
        if name=='interval_early_handoff':
            description+='; early coarse handoff on two declines and always a bounded right audit before accepting first interval'
        description+='; gate '+gate
    elif name.startswith('triplet_band_') or name.startswith('triplet_union_'):
        bounds=list(map(int,name.split('_')[2:]))
        if len(bounds)%2 or not bounds:
            raise ValueError('Interval endpoints required')
        intervals=list(zip(bounds[::2],bounds[1::2]))
        if any(not 501<=a<=b<=650 for a,b in intervals) or any(intervals[i][1]>=intervals[i+1][0] for i in range(len(intervals)-1)):
            raise ValueError('Disjoint ordered subintervals of501..650 required')
        gate=' || '.join(f'(n>={a} && n<={b})' for a,b in intervals)
        text=replace_once(text,'n>500 && n<=650 && f.significant',
                         '('+gate+') && f.significant')
        description='Official-total disjoint interval fit: enable the unchanged three-point action only for '+str(intervals)+'; every other N retains original baseline behavior'
    elif name in ['sparse_forward_pair','inner_forward_pair']:
        loop='for (int x=next+2;x<=next+2;++x)' if name=='sparse_forward_pair' else 'for (int x=next+1;x<=next+1;++x)'
        text=replace_once(text,'for (int x=next+1;x<=next+2;++x)',loop)
        text=replace_once(text,'                    ++adjacentReads;',
                         '                    adjacentReads+=2;')
        description='Keep the original two-cell forward reach and six-event cap, but query only the outer auxiliary point; omit the middle query to test its information/cost tradeoff; same learned N gate'
        if name=='inner_forward_pair':
            description='Use only the immediate forward neighbor at each confirmation, same six-event cap and learned N gate; trade lower query cost and one-cell reach against original triplet coverage'
    elif name in ['triplets_lower_mid','triplets_upper_mid']:
        gate='n>500 && n<=575' if name=='triplets_lower_mid' else 'n>575 && n<=650'
        text=replace_once(text,'n>500 && n<=650 && f.significant',
                         '('+gate+') && f.significant')
        description='Disjoint refinement of the learned 501..650 action gate: keep forward triplets only in '+gate+'; all other cases revert to original baseline sampling'
    elif name=='forward_five':
        text=replace_once(text,'adjacentReads+2<=12','adjacentReads+4<=12')
        text=replace_once(text,'next+2<=limit && q+2<=128','next+4<=limit && q+4<=128')
        text=replace_once(text,'for (int x=next+1;x<=next+2;++x)',
                         'for (int x=next+1;x<=next+4;++x)')
        text=text.replace('Read a forward contiguous triplet','Read a forward contiguous five-point block')
        description='Replace three-point forward confirmations by five-point contiguous blocks with the same 12-read auxiliary cap; unchanged learned N gate, raw maxima, frontier and parking guards'
    elif name=='priority_only_planner':
        helper=r'''
    vector<int> priorityPlan(vector<Point> candidates,int budget,bool descending) {
        sort(candidates.begin(),candidates.end(),[&](const Point& a,const Point& b) {
            if (a.priority!=b.priority) return a.priority>b.priority;
            if (abs(a.x-best)!=abs(b.x-best)) return abs(a.x-best)<abs(b.x-best);
            return tieBetter(a.x,b.x);
        });
        vector<int> plan;
        for (const auto& point:candidates) {
            if (static_cast<int>(plan.size())>=budget) break;
            plan.push_back(point.x);
        }
        return orient(move(plan),descending);
    }
'''
        text=replace_once(text,'    void refine() {',helper+'    void refine() {')
        text=replace_once(text,'            vector<int> plan=selectPlan(candidates,budget,descending,f);',
                         '            vector<int> plan=priorityPlan(candidates,budget,descending);')
        description='Deterministic evidence-priority refinement planning instead of finite-scenario scoring and annealing; same candidate pool, budgets, monotone route and parking admission'
    elif name=='single_pass_refine':
        text=replace_once(text,'for (int round=0;round<2 && q<QMAX-1 && seconds()<7.5;++round)',
                         'for (int round=0;round<1 && q<QMAX-1 && seconds()<7.5;++round)')
        text=replace_once(text,r'''            if (round==0 && static_cast<int>(candidates.size())>available)
                budget=max(7,available-min(48,available/3));''',
                         '            // One pass uses the shared quota; only terminal parking is reserved.')
        description='One globally planned monotone refinement pass, full shared query quota instead of reserving a second directional pass; original model completion retained'
    elif name=='spike_stress_scenarios':
        text=replace_once(text,'        vector<int> peaks=f.peaks;',r'''        // Every read cell has an audit entry, even with two low endpoints.
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1],b=f.x[i];
            if (b-a>1) add((a+b)/2,63+0.01*(b-a));
        }
        vector<int> peaks=f.peaks;''')
        text=replace_once(text,r'''        return result;
    }
    bool routeSafe''',r'''        vector<pair<double,int>> gaps;
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1],b=f.x[i];
            if (b-a<=1) continue;
            const double h=(max(value[a],value[b])-f.floor)/max(1.0,f.contrast);
            gaps.emplace_back((b-a)*(0.25+h*h),(a+b)/2);
        }
        sort(gaps.begin(),gaps.end(),greater<pair<double,int>>());
        for (size_t i=0;i<min(size_t{4},gaps.size());++i) {
            Scenario c=result.front();
            const int x=gaps[i].second;
            c.value[x]=min(VMAX,bestValue+max(1LL,static_cast<long long>(0.1*f.contrast+3*f.noise)));
            c.target=0;
            for (int y=1;y<n;++y) if (better(y,c.value[y],c.target,c.value[c.target])) c.target=y;
            result.push_back(move(c));
        }
        // Stress cases are decision heuristics, not calibrated probabilities.
        return result;
    }
    bool routeSafe''')
        description='Add unread-cell midpoint actions and four sharp hidden-peak stress scenarios preserving all replies; model weights heuristic, no confidence claim; no new external I/O'
    elif name=='irreversible_cost_guard':
        text=replace_once(text,'        int p=pos,d=direction,o=turns; long long m=travel;\n        moveTo(x,p,d,o,m);',r'''        int p=pos,d=direction,o=turns; long long m=travel;
        moveTo(x,p,d,o,m);
        // These spent costs cannot decrease after any later observation.
        // A new winner may save parking, so use the cost at x, not old-best parking.
        if (!terminal && m+max(q,wire.queries())+1+o>=3000) return false;''')
        description='Stop optional queries whose already-spent M+Q+O would reach3000 even before parking/R/d; exact zero-score lower bound, independent of unknown target; final observed-winner parking retained'
    elif name=='follow_new_peak':
        text=replace_once(text,
            '        for (int round=0;round<2 && q<QMAX-1 && seconds()<7.5;++round) {',
            '        int adjacentReplans=0;\n        for (int round=0;round<2 && q<QMAX-1 && seconds()<7.5;++round) {')
        text=replace_once(text,r'''            bool progress=false;
            for (int x:plan) {
                if (!sample(x)) break;
                progress=true;
                if (certificate()) return;
            }''',r'''            bool progress=false;
            for (size_t index=0;index<plan.size();++index) {
                const int x=plan[index],oldBest=best;
                const long long oldValue=bestValue;
                if (!sample(x)) break;
                progress=true;
                if (certificate()) return;
                if (oldBest>=0 && bestValue>oldValue && abs(best-oldBest)>3 && adjacentReplans<6) {
                    const int dir=index+1<plan.size() ? signum(plan[index+1]-x) : direction;
                    vector<int> tail(plan.begin()+static_cast<ptrdiff_t>(index+1),plan.end());
                    for (int k=1;k<=2;++k) {
                        const int y=x+k*dir;
                        if (dir && y>=0 && y<=rightmost && value[y]<0) tail.push_back(y);
                    }
                    tail=canonical(move(tail),dir<0);
                    const int capacity=QMAX-1-q;
                    if (static_cast<int>(tail.size())>capacity) tail.resize(max(0,capacity));
                    if (routeSafe(tail)) {
                        plan.resize(index+1);
                        plan.insert(plan.end(),tail.begin(),tail.end());
                        ++adjacentReplans;
                    }
                }
            }''')
        description='Replan the remaining monotone refinement tail on a strictly higher winner displaced by >3: merge its next two directional neighbors, max six updates, drop far tail if budget full; preserve route/parking checks'
    elif name in ['hard_frontier_guard','final_peak_core','reserved_final_core']:
        if name=='hard_frontier_guard':
            text=replace_once(text,'        if (o>OMAX) return false;',r'''        if (o>OMAX) return false;
        // Candidate-relative protection only, not knowledge of the true target.
        // 196 leaves three cells for a target just left of the observed winner.
        if (!terminal && x>rightmost && best>=0 && x>best+196) return false;''')
            description='Before any new rightward frontier query, enforce x<=observed-best+196; allow all backward/local checks and parking; heuristic protection for unknown true-R'
        else:
            helper=r'''
    void finalPeakCore() {
        vector<int> plan;
        const int b=best;
        if (b<0 || bestValue==VMAX) return;
        for (int x=max(0,b-6);x<=min(rightmost,b+6);++x)
            if (value[x]<0) plan.push_back(x);
        plan=orient(move(plan),pos>=b);
        if (!routeSafe(plan)) return;
        for (int x:plan) if (!sample(x) || certificate()) return;
    }
'''
            text=replace_once(text,'    void refine() {',helper+'    void refine() {')
            text=replace_once(text,'            const int available=QMAX-1-q;',
                             '            const int available=max(0,QMAX-1-q-12);')
            if name=='reserved_final_core':
                text=replace_once(text,'            const int available=max(0,QMAX-1-q-12);',
                                 '            const int available=max(0,QMAX-1-q-12);\n            if (!available) break;')
                text=replace_once(text,'                budget=max(7,available-min(48,available/3));',
                                 '                budget=min(available,max(7,available-min(48,available/3)));')
            text=replace_once(text,'else { explore(); if (alive) refine(); }',
                             'else { explore(); if (alive) refine(); if (alive) finalPeakCore(); }')
            description='Reserve 12 reads from general refinement plans for an explicit final raw best+-6 audit within covered frontier; route and parking checks remain; does not prove global d<=3'
    elif name=='preserve_coarse_grid':
        text=replace_once(text,'        int flatRuns=0, adjacentReads=0;',
                         '        int flatRuns=0, adjacentReads=0, adjacentTail=0;')
        text=replace_once(text,'            int next=min({n-1,rightmost+step,limit});',
                         '            int next=min({n-1,rightmost+step-adjacentTail,limit});')
        text=replace_once(text,'            const long long previousBest=bestValue;',
                         '            adjacentTail=0;\n            const long long previousBest=bestValue;')
        text=replace_once(text,'                    ++adjacentReads;',
                         '                    ++adjacentReads; adjacentTail=rightmost-next;')
        description='Mechanism control on a scored inline-triplet parent: keep coarse anchor phase after adjacent reads; preserve all neighbor observations and raw targets'
    elif name=='near_vertex_triplets':
        text=replace_once(text,'            // Read a forward contiguous triplet at a newly improving concave',r'''
            bool nearVertex=false;
            if (f.x.size()>=2 && f.x.back()<next) {
                const int a=f.x[f.x.size()-2],b=f.x.back();
                const double sl=static_cast<double>(value[b]-value[a])/(b-a);
                const double sr=static_cast<double>(value[next]-value[b])/(next-b);
                const double curve=(sr-sl)/(next-a);
                if (curve<0) {
                    const double v=(a+b)/2.0-sl/(2*curve);
                    nearVertex=isfinite(v) && abs(v-next)<=2.0*step;
                }
            }
            // Read a forward contiguous triplet at a newly improving concave''')
        text=replace_once(text,'&& f.significant && f.curvature<0 &&',
                         '&& f.significant && f.curvature<0 && nearVertex &&')
        description='Spend inline contiguous-triplet budget only when the irregular-grid quadratic extrapolated vertex is within two coarse steps; raw maximum still authoritative'
    elif name=='dense_basin_long':
        helper=r'''
    void denseBasin() {
        if (best<0 || bestValue==VMAX) return;
        const int originalBest=best;
        vector<int> local;
        for (int x=min(rightmost,originalBest+10);x>=max(0,originalBest-10);--x)
            if (value[x]<0) local.push_back(x);
        if (!routeSafe(local)) return;
        for (int x:local) if (!sample(x) || certificate()) return;
        vector<int> shoulder;
        for (int x=best+8;x<=rightmost;++x) if (value[x]<0) shoulder.push_back(x);
        // Whole-route admission includes parking. Do not consume the last read.
        if (!routeSafe(shoulder)) return;
        for (int x:shoulder) if (!sample(x) || certificate()) return;
    }
'''
        text=replace_once(text,'    void refine() {',helper+'    void refine() {')
        text=replace_once(text,'else { explore(); if (alive) refine(); }',
                         'else { explore(); if (alive && n>600) denseBasin(); if (alive) refine(); }')
        description='For N>600, exhaust raw best+-10 then its observed right shoulder before model stopping; complete route checks and raw target ordering retained'
    elif name.startswith('inline_triplets_'):
        parts=name.split('_')
        mode=parts[2]
        if mode not in ['raw','clean']:
            raise ValueError(mode)
        gate={'all':'true','short':'n<=500','mid':'n>500 && n<=650','long':'n>650',
              'shortmid':'n<=650','midlong':'n>500','shortlong':'n<=500 || n>650'}[parts[3]]
        text=replace_once(text,'        int flatRuns=0;', '        int flatRuns=0, adjacentReads=0;')
        text=replace_once(text,'            if (next<=rightmost || !sample(next)) break;',r'''
            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;
            // Read a forward contiguous triplet at a newly improving concave
            // shoulder. No backward movement and no independent revisit sweep.
            if (INLINE_GATE && f.significant && f.curvature<0 &&
                value[next]>previousBest && adjacentReads+2<=12 &&
                next+2<=limit && q+2<=128) {
                for (int x=next+1;x<=next+2;++x) {
                    if (!sample(x)) break;
                    ++adjacentReads;
                }
            }'''.replace('INLINE_GATE',gate))
        if mode=='clean':
            helper=r'''
    double trendValue(int x) const {
        if (x>0 && x+1<n && value[x-1]>=0 && value[x+1]>=0) {
            array<long long,3> local{value[x-1],value[x],value[x+1]};
            sort(local.begin(),local.end());
            return static_cast<double>(local[1]);
        }
        return static_cast<double>(value[x]);
    }
'''
            text=replace_once(text,'    Features features() {',helper+'    Features features() {')
            text=replace_once(text,
                'f.slopes.push_back(static_cast<double>(value[x]-value[f.x[i-1]])/h);',
                'f.slopes.push_back((trendValue(x)-trendValue(f.x[i-1]))/h);')
            text=replace_once(text,
                'residual.push_back(value[x]-(value[a]+t*(value[b]-value[a])));',
                'residual.push_back(trendValue(x)-(trendValue(a)+t*(trendValue(b)-trendValue(a))));')
            text=replace_once(text,
                'const double delta=static_cast<double>(value[f.x[i]]-value[f.x[i-1]]);',
                'const double delta=trendValue(f.x[i])-trendValue(f.x[i-1]);')
        description=f'Forward-only contiguous triplets at improving concave shoulders; max 12 additional reads; {mode} trend; raw targets retained; gate {gate}'
    elif name.startswith('neighbor_confirm_') or name.startswith('neighbor_clean_'):
        parts=name.split('_')
        count=int(parts[2])
        if count not in [3,5]:
            raise ValueError('Unsupported peak count')
        gate={'all':'true','short':'n<=500','mid':'n>500 && n<=650','long':'n>650'}[parts[3]]
        helper=r'''
    void confirmNeighbors(int count) {
        const vector<int> xs=observed();
        if (xs.size()<3 || best<0 || bestValue==VMAX) return;
        vector<int> peaks{best};
        for (size_t i=1;i+1<xs.size();++i) {
            const int x=xs[i];
            if (x!=best && value[x]>=value[xs[i-1]] && value[x]>=value[xs[i+1]])
                peaks.push_back(x);
        }
        sort(peaks.begin(),peaks.end(),[&](int a,int b) {
            return better(a,value[a],b,value[b]);
        });
        if (static_cast<int>(peaks.size())>count) peaks.resize(count);
        vector<int> plan;
        for (int x:peaks) for (int y:{x-1,x+1})
            if (y>=0 && y<=rightmost && value[y]<0) plan.push_back(y);
        sort(plan.begin(),plan.end(),greater<int>());
        plan.erase(unique(plan.begin(),plan.end()),plan.end());
        if (static_cast<int>(plan.size())>QMAX-1-q-24 || !routeSafe(plan)) return;
        // Adjacent observations inform structure; no raw maximum is discarded.
        for (int x:plan) if (!sample(x) || certificate()) return;
    }
'''
        text=replace_once(text,'    void refine() {',helper+'    void refine() {')
        text=replace_once(text,'else { explore(); if (alive) refine(); }',
                         'else { explore(); if (alive && ('+gate+')) confirmNeighbors('+str(count)+'); if (alive) refine(); }')
        description=f'Confirm x-1 and x+1 around top {count} unmerged raw local maxima in one descending pass before refinement; raw winners retained; gate {gate}'
        if name.startswith('neighbor_clean_'):
            helper2=r'''
    double trendValue(int x) const {
        if (x>0 && x+1<n && value[x-1]>=0 && value[x+1]>=0) {
            array<long long,3> local{value[x-1],value[x],value[x+1]};
            sort(local.begin(),local.end());
            return static_cast<double>(local[1]);
        }
        return static_cast<double>(value[x]);
    }
'''
            text=replace_once(text,'    Features features() {',helper2+'    Features features() {')
            text=replace_once(text,
                'f.slopes.push_back(static_cast<double>(value[x]-value[f.x[i-1]])/h);',
                'f.slopes.push_back((trendValue(x)-trendValue(f.x[i-1]))/h);')
            text=replace_once(text,
                'residual.push_back(value[x]-(value[a]+t*(value[b]-value[a])));',
                'residual.push_back(trendValue(x)-(trendValue(a)+t*(trendValue(b)-trendValue(a))));')
            text=replace_once(text,
                'const double delta=static_cast<double>(value[f.x[i]]-value[f.x[i-1]]);',
                'const double delta=trendValue(f.x[i])-trendValue(f.x[i-1]);')
            description+='; spatial median-of-three only for slopes and residual trend, raw best/peaks/ties unchanged'
    elif name.startswith('gap_audit_'):
        parts=name.split('_')
        budget=int(parts[2])
        if budget not in [8,16,24]:
            raise ValueError('Unsupported audit quota')
        gate={'all':'true','short':'n<=500','mid':'n>500 && n<=650','long':'n>650'}[parts[3]]
        helper=r'''
    void auditUnreadGaps(int credit) {
        // Raw observations only: do not change shape-state votes just to rank gaps.
        const vector<int> xs=observed();
        if (xs.size()<3 || best<0 || bestValue==VMAX) return;
        long long low=bestValue;
        for (int x:xs) low=min(low,value[x]);
        const double scale=max(1.0,static_cast<double>(bestValue-low));
        vector<pair<double,int>> gaps;
        for (size_t i=1;i<xs.size();++i) {
            const int a=xs[i-1],b=xs[i],h=b-a;
            if (h<=1) continue;
            const double height=(max(value[a],value[b])-low)/scale;
            // Endpoint height is a priority, never a claimed upper bound.
            // A nonzero geometry term also admits low-endpoint blind cells.
            const double priority=(0.25+height*height)*h;
            gaps.emplace_back(priority,(a+b)/2);
        }
        sort(gaps.begin(),gaps.end(),[](const auto& a,const auto& b) {
            return a.first!=b.first ? a.first>b.first : a.second>b.second;
        });
        vector<int> plan;
        credit=min(credit,max(0,QMAX-1-q-24));
        for (const auto& gap:gaps) {
            if (static_cast<int>(plan.size())>=credit) break;
            plan.push_back(gap.second);
        }
        sort(plan.begin(),plan.end(),greater<int>());
        if (!routeSafe(plan)) return;
        for (int x:plan) if (!sample(x) || certificate()) return;
    }
'''
        text=replace_once(text,'    void refine() {',helper+'    void refine() {')
        text=replace_once(text,'else { explore(); if (alive) refine(); }',
                         'else { explore(); if (alive && ('+gate+')) auditUnreadGaps('+str(budget)+'); if (alive) refine(); }')
        description=f'Before model stopping, audit up to {budget} existing gaps in one descending pass; raw height plus gap geometry priority; reserve 24 refinement reads; gate {gate}'
    else:
        raise ValueError(name)
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/(name+'_'+hashlib.sha256(parent.read_bytes()).hexdigest()[:12]+'.cpp')
    contents=text.encode('utf-8')
    if path.exists() and path.read_bytes()!=contents:
        raise ValueError('Refusing to overwrite a frozen candidate')
    path.write_bytes(contents)
    meta=dict(name=name,source=str(path),description=description,parent=str(parent),
              parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
              sha256=hashlib.sha256(contents).hexdigest())
    path.with_suffix('.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('name')
    p.add_argument('--parent',type=Path,default=ROOT/'data/versions/main_online_210599.cpp')
    a=p.parse_args()
    generate(a.name,a.parent)
