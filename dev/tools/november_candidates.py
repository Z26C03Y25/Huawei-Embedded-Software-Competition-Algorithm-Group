"""Freeze explicit structural candidates; never uploads or edits the incumbent."""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261101'

def generate(name,parent):
    parent=parent.resolve()
    text=parent.read_text(encoding='utf-8-sig')
    if name in ['doubao_incumbent_coarse','doubao_resolved_coarse','doubao_resolved_coarse_v2']:
        if 'namespace af_super' not in text:
            raise RuntimeError('Doubao follow-up requires its scored source as parent')
        coarse_score=216233 if name.startswith('doubao_resolved_coarse') else 212686
        incumbent=(ROOT/f'data/versions/main_online_{coarse_score}.cpp').read_text(encoding='utf-8-sig')
        begin=incumbent.index('    bool coarseRivalEvidence(')
        end=incumbent.index('    optional<double> vertex',begin)
        coarse=incumbent[begin:end].replace('certificate()','certificateStrong()')
        if name.endswith('_v2'):
            coarse=coarse.replace('max(q,wire.queries())','q')
        begin=text.index('    int frontierLimit(')
        end=text.index('    optional<double> vertex',begin)
        text=text[:begin]+coarse+text[end:]
        old='    int votes=0;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected Doubao state')
        text=text.replace(old,old+'\n    int rivalChecks=0,rivalReleases=0,rivalMaxBeyondBest=0,sentinelTrials=0,sentinelForBest=-1,sentinelMidpoints=0;',1)
        description='Causal Doubao follow-up: retain its fine planner, ensemble, narrow model confidence and diagnostics, but graft officially scored'+str(coarse_score)+' coarse sampling/budgets/frontier/sentinel/rebound/adjacent-triplet/stopping policies. Test whether its coarse rewrite dominates the observed191308 loss.'
    elif name in ['compact_expert_noisy','compact_expert_clean']:
        template=(ROOT/'data/versions/online_search/scored_212535_15148f0a31e6.cpp').read_text(encoding='utf-8-sig')
        start=text.index('    vector<int> selectPlan(')
        end=text.index('    void refine() {',start)
        base=(ROOT/'data/versions/main_online_212686.cpp').read_text(encoding='utf-8-sig')
        if text[start:end]!=base[base.index('    vector<int> selectPlan('):base.index('    void refine() {')]:
            raise RuntimeError('Parent planner differs from the measured baseline')
        original=text[start:end].replace('vector<int> selectPlan(','vector<int> selectPlanBaseline(',1)
        compact=template[template.index('    vector<int> selectPlan('):template.index('    void refine() {')]
        compact=compact.replace('vector<int> selectPlan(','vector<int> selectPlanCompact(',1)
        gate='f.noisy' if name.endswith('noisy') else '!f.noisy'
        dispatch='''    vector<int> selectPlan(const vector<Point>& candidates,int budget,bool descending,const Features& f) {
        return ('''+gate+''') ? selectPlanCompact(candidates,budget,descending,f)
                          : selectPlanBaseline(candidates,budget,descending,f);
    }
'''
        text=text[:start]+original+compact+dispatch+text[end:]
        description='Enable the scored compact fine-route algorithm only when '+gate+' at plan selection; preserve original planner otherwise. No extra features() calls or coarse changes. Measure shape contribution rather than globally shrinking fine search.'
    elif name=='median_frontier_lease':
        helper=r'''
    bool medianFrontierRise(const Features& f) const {
        if (f.x.size()<9 || best<rightmost-16 || f.plateau) return false;
        const size_t first=f.x.size()-9;
        array<double,3> level{};
        for (size_t k=0;k<3;++k) {
            array<long long,3> block{};
            for (size_t j=0;j<3;++j) block[j]=value[f.x[first+3*k+j]];
            sort(block.begin(),block.end()); level[k]=block[1];
        }
        const double rise=max(0.5*f.noise,0.002*f.contrast);
        if (level[1]-level[0]<=rise || level[2]-level[1]<=rise) return false;
        long long older=-1;
        for (int x:f.x) if (x<=rightmost-48) older=max(older,value[x]);
        return older>=0 && bestValue>older;
    }
'''
        anchor='    int frontierLimit(const Features& f) {'
        if text.count(anchor)!=1:
            raise RuntimeError('Unexpected frontier interface')
        text=text.replace(anchor,helper+anchor,1)
        old='        return min(n-1,f.left+199);'
        if text.count(old)!=1:
            raise RuntimeError('Parent already has another frontier policy')
        text=text.replace(old,'''        int limit=min(n-1,f.left+199);
        if (rightmost>=limit-16 && medianFrontierRise(f))
            limit=max(limit,min(n-1,best+24));
        return limit;''',1)
        description='At an expiring high-band boundary, three rising median blocks plus a frontier raw winner strictly beating older observed points allow a24-cell bracketing lease. This handles modest raw wiggles that blocked the prior clean-rise experiment; raw values define the winner and all parent stop/parking guards remain. No universal R guarantee.'
    elif name=='renew_rising_frontier':
        old='        return min(n-1,f.left+199);'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected significant frontier')
        text=text.replace(old,'''        int limit=min(n-1,f.left+199);
        // A new strictly higher forward shoulder should not inherit a stale
        // near-equal old peak's left-band boundary without one bracket lease.
        if (best>=rightmost-8 && f.rises>=2 && f.falls==0 && !f.plateau) {
            long long previous=-1;
            for (int x:f.x) if (x<=rightmost-24) previous=max(previous,value[x]);
            if (previous>=0 && bestValue-previous>max(2*f.noise,0.005*f.contrast))
                limit=max(limit,min(n-1,best+32));
        }
        return limit;''',1)
        description='Repair stale high-band frontier for a newly superior rising forward shoulder: only when recent rises are consistent, best is at the frontier and exceeds all points at least24 cells behind by a noise margin, grant a renewable32-cell bracket lease. Retain resolved-descent stop and raw maxima. A heuristic release, not global R certification.'
    elif name=='stratified_long_grid':
        old='        int flatRuns=0, adjacentReads=0;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected coarse state')
        text=text.replace(old,old+'''
        int randomBlock=-1;
        array<int,3> anchors{};
        uint64_t localSeed=0xd1b54a32d192ed03ULL ^ static_cast<uint64_t>(n)*1000003ULL;
        auto scoutRandom=[&]() { localSeed^=localSeed<<13; localSeed^=localSeed>>7; localSeed^=localSeed<<17; return localSeed; };''',1)
        old='            int next=min({n-1,rightmost+step,limit});'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected anchor position')
        text=text.replace(old,old+'''
            if (!f.flat && n>650) {
                const int block=rightmost/32;
                if (block!=randomBlock) {
                    randomBlock=block;
                    anchors={block*32+1+static_cast<int>(scoutRandom()%15),
                             block*32+17+static_cast<int>(scoutRandom()%15),
                             min(n-1,(block+1)*32)};
                    sort(anchors.begin(),anchors.end());
                }
                next=min(n-1,(block+1)*32);
                for (int x:anchors) if (x>rightmost) { next=x; break; }
                next=min({n-1,next,limit});
            }''',1)
        description='Long-array sampling expert: N>650 nonflat intervals use a fixed32-cell endpoint plus two fixed-seed stratified random interiors; retain parent adjacent bursts, winner, stopping and fine planner. Other N and flat histories remain on parent trajectory. Independent of prior hull/model-cell changes.'
    elif name=='dense_midpoints_current':
        base=(ROOT/'data/versions/main_online_212686.cpp').read_text(encoding='utf-8-sig')
        fstart='    Features features() {'
        fend='    bool coarseRivalEvidence('
        if text[text.index(fstart):text.index(fend)]!=base[base.index(fstart):base.index(fend)]:
            raise RuntimeError('Parent features differ from known incumbent')
        coarse=text[text.index(fend):text.index('    optional<double> vertex')]
        template=(ROOT/'data/versions/online_search/scored_212243_bacbbba94c9d.cpp').read_text(encoding='utf-8-sig')
        begin=template.index(fend)
        end=template.index('    optional<double> vertex',begin)
        text=template[:begin]+coarse+template[end:]
        begin=text.index('    void explore() {')
        end=text.index('    optional<double> vertex',begin)
        chunk=text[begin:end]
        anchor='            if (next<=rightmost || !sample(next)) break;'
        if chunk.count(anchor)!=1:
            raise RuntimeError('Unexpected coarse query interface')
        chunk=chunk.replace(anchor,'''            if (n<=500 && !f.flat && next-rightmost>=4) {
                const int midpoint=(next+rightmost)/2;
                auditAux[midpoint]=1;
                if (!sample(midpoint)) { auditAux[midpoint]=0; break; }
            }
'''+anchor,1)
        for a,b in [('q<128','q<((n<=500)?160:128)'),('q+3<=128','q+3<=((n<=500)?160:128)'),
                    ('q+2<=128','q+2<=((n<=500)?160:128)'),('remaining=128-q','remaining=((n<=500)?160:128)-q')]:
            chunk=chunk.replace(a,b)
        text=text[:begin]+chunk+text[end:]
        anchor='        // Auxiliary probes remain raw winner candidates; only the roughness'
        text=text.replace(anchor,'        if (n<=500) {\n'+anchor,1)
        text=text.replace('        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;',
                          '        }\n        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;',1)
        description='Preserve the scored parent coarse/stop policy, insert every8-cell interval midpoint only on nonflat N<=500, and estimate noise from anchor provenance. Other N follow the parent exactly. Coarse cap160 for short arrays retains fine/parking budget; no random point placement.'
    elif name=='dense_midpoints_short':
        text=(ROOT/'data/versions/online_search/scored_212243_bacbbba94c9d.cpp').read_text(encoding='utf-8-sig')
        text=text.replace('        int auditBlock=-1,auditTarget=-1;\n','',1)
        text=text.replace('        uint64_t auditSeed=0x94d049bb133111ebULL ^ static_cast<uint64_t>(n)*1000003ULL;\n','',1)
        begin=text.index('            if (!f.flat && !(n>=539 && n<=613)) {')
        end=text.index('            if (next<=rightmost || !sample(next)) break;',begin)
        text=text[:begin]+'''            if (n<=500 && !f.flat && next-rightmost>=4) {
                const int midpoint=(next+rightmost)/2;
                auditAux[midpoint]=1;
                if (!sample(midpoint)) { auditAux[midpoint]=0; break; }
            }
'''+text[end:]
        begin=text.index('    void explore() {')
        end=text.index('    optional<double> vertex',begin)
        text=text[:begin]+text[begin:end].replace('160','((n<=500) ? 160 : 128)')+text[end:]
        anchor='        // Auxiliary probes remain raw winner candidates; only the roughness'
        if text.count(anchor)!=1:
            raise RuntimeError('Unexpected provenance feature block')
        text=text.replace(anchor,'        if (n<=500) {\n'+anchor,1)
        text=text.replace('        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;',
                          '        }\n        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;',1)
        description='Short-array narrow-peak coverage: retain8-cell anchor endpoints and insert every interval midpoint while nonflat on N<=500; estimate roughness on anchor skeleton and reserve fine/parking by coarse cap160. Other N retain the incumbent sampling/noise/budget. No random placement or extra travel per interval.'
    elif name=='cell_complete_model':
        old='                    vector<int> probe;'
        new='''                    // Close the complete observed cell around the raw winner.
                    const int cellLo=min(modelLo,*prev(it));
                    const int cellHi=max(modelHi,*next(it));
                    vector<int> probe;'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected model probe interface')
        text=text.replace(old,new,1)
        old='for (int x=modelHi;x>=modelLo;--x)'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected probe loop')
        text=text.replace(old,'for (int x=cellHi;x>=cellLo;--x)',1)
        description='Keep coarse exploration and planner; before model completion exhaust the full observed cell bracketing the raw winner, combined with existing predicted interval; route/parking admission unchanged.'
    elif name=='halve_postpeak_scout':
        old='                if (best>=(n-1)/2) scout=min(scout,16);'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected post-peak scout interface')
        text=text.replace(old,old+'\n                scout=max(16,scout/2);',1)
        description='Test aggregate redundancy/movement cost rather than assuming zeros: halve the post-peak scout distance, retaining a16-cell minimum for existing local model support. All coarse anchors, rebound tests, fine planner, Q/O and final parking unchanged.'
    elif name in ['right_width_stop','asymmetric_width_stop']:
        old='''                if (f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound)
                    scout=max(16,scout/2);'''
        if text.count(old)!=1:
            raise RuntimeError('Right-width budget requires the scored216233 stop rule')
        gate=' && f.halfRight<0.6*f.halfLeft' if name=='asymmetric_width_stop' else ''
        new='''                if (f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound'''+gate+''') {
                    const int observedTailBudget=max(16,static_cast<int>(ceil(1.5*f.halfRight)));
                    scout=min(max(16,scout/2),observedTailBudget);
                }'''
        if name=='asymmetric_width_stop':
            new+=''' else if (f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound)
                    scout=max(16,scout/2);'''
        text=text.replace(old,new,1)
        description='Replace left-width/N-driven excess tail budget by the measured right half-height width after the established resolved descent. Cap by the proven parent half-scout, preserve16 minimum and all rival/rebound/significance checks.'
        if gate:
            description+=' Only asymmetric narrow-right tails use the new cap; all others retain216233.'
    elif name=='median_descent_stop':
        helper=r'''
    bool resolvedTailDescent(const Features& f) const {
        if (f.falls>=3 && f.rises==0) return true;
        if (f.x.size()<9) return false;
        const size_t first=f.x.size()-9;
        if (f.x[first]<=best+8) return false;
        array<double,3> level{};
        for (size_t k=0;k<3;++k) {
            array<long long,3> block{};
            for (size_t j=0;j<3;++j) block[j]=value[f.x[first+3*k+j]];
            sort(block.begin(),block.end()); level[k]=block[1];
        }
        const double drop=max(f.noise,0.005*f.contrast);
        return level[0]-level[1]>drop && level[1]-level[2]>drop;
    }
'''
        anchor='    void explore() {'
        if text.count(anchor)!=1:
            raise RuntimeError('Unexpected exploration interface')
        text=text.replace(anchor,helper+anchor,1)
        old='f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound'
        if text.count(old)!=1:
            raise RuntimeError('Median descent requires scored resolved-stop parent')
        text=text.replace(old,'f.halfLeft>0 && f.halfRight>0 && resolvedTailDescent(f) && !f.rebound',1)
        description='On the improved resolved-stop parent, retain all existing clean descent triggers; additionally allow three strictly declining post-peak median blocks to establish trend despite isolated modest rises. Both half-height flanks and original significance/rebound/rival checks remain mandatory; raw maxima untouched.'
    elif name in ['resolved_descent_short','resolved_descent_mid','resolved_descent_long']:
        gate={'resolved_descent_short':'n<=500','resolved_descent_mid':'n>500 && n<=650','resolved_descent_long':'n>650'}[name]
        old='                if (best>=(n-1)/2) scout=min(scout,16);'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected post-peak scout')
        text=text.replace(old,old+'\n                if (('+gate+') && f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound)\n                    scout=max(16,scout/2);',1)
        description='Measure disjoint N contribution of the officially improved216233 resolved-descent stopping rule only for '+gate+'; other N retain original212686 scout. This is a causal group test, not a repeat of the global source.'
    elif name=='resolved_descent_half_scout':
        old='                if (best>=(n-1)/2) scout=min(scout,16);'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected post-peak scout')
        text=text.replace(old,old+'''
                if (f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound)
                    scout=max(16,scout/2);''',1)
        description='Reduce post-peak M/R only after observing both half-height flanks and at least three recent significant falls with no rises/rebound; retain original scout on ambiguous, broad unresolved or rising tails. A new conditional policy, not a repeat of the unconfirmed global half-scout source.'
    elif name=='validated_quadratic_stop':
        helper=r'''
    bool resolvedQuadraticTail(const Features& f) {
        if (!f.significant || f.noisy || f.rebound || f.plateau || best<=16 ||
            rightmost-best<32 || f.x.size()<9) return false;
        vector<int> xs;
        vector<double> y,coef;
        for (int x:f.x) if (abs(x-best)<=32) {
            xs.push_back(x); y.push_back(static_cast<double>(value[x])-bestValue);
        }
        if (xs.size()<7 || xs.front()>best-16 || xs.back()<best+24 ||
            !robustFit(xs,2,y,coef)) return false;
        auto global=quadPeak(coef);
        auto local=multiModelVertex(f);
        if (!global || !local || abs(*global-*local)>0.75 || abs(*global-best)>4.5)
            return false;
        const double error=max(2.0,0.02*abs(coef[2]));
        for (size_t k=0;k<xs.size();++k) {
            const double t=(xs[k]-best)/16.0;
            if (abs(y[k]-coef[0]-coef[1]*t-coef[2]*t*t)>error) return false;
        }
        return true;
    }
'''
        old='    void explore() {'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected exploration interface')
        text=text.replace(old,helper+old,1)
        old='                if (best>=(n-1)/2) scout=min(scout,16);'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected scout interface')
        text=text.replace(old,old+'\n                if (!rival && resolvedQuadraticTail(f)) scout=min(scout,32);',1)
        description='Save post-peak M/R only after clean significant nonrebounding local data fits one concave quadratic across>=7 points spanning both sides, every residual is small relative to curvature and local/multiscale vertices agree within0.75. Retain ordinary scout for all other shapes; not a global unimodality proof.'
    elif name=='marginal_signal_tail_guard':
        helper=r'''
    optional<int> marginalTailLimit(const Features& f) const {
        if (n<=650 || f.flat || f.significant || !f.noisy || f.x.size()<12 ||
            best<0 || f.contrast<=8*max(1.0,f.noise)) return nullopt;
        const size_t first=f.x.size()-9;
        if (f.x[first]<=best+16) return nullopt;
        array<double,3> level{};
        for (size_t k=0;k<3;++k) {
            array<long long,3> block{};
            for (size_t j=0;j<3;++j) block[j]=value[f.x[first+3*k+j]];
            sort(block.begin(),block.end()); level[k]=block[1];
        }
        const double drop=max(1.5*f.noise,0.01*f.contrast);
        if (level[0]-level[1]<=drop || level[1]-level[2]<=drop ||
            bestValue-level[2]<=max(4*f.noise,0.15*f.contrast)) return nullopt;
        return min(n-1,f.left+192);
    }
'''
        old='    int frontierLimit(const Features& f) {'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected frontier interface')
        text=text.replace(old,helper+old,1)
        old='        if (!f.significant) return n-1;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected weak-signal frontier')
        text=text.replace(old,'''        if (!f.significant) {
            if (auto limit=marginalTailLimit(f)) return *limit;
            return n-1;
        }''',1)
        description='Coarse-only protection for marginal-SNR long curves: three post-winner median blocks must decline strongly with contrast>8 noise before limiting to observed high-band left+192. Fine model confidence remains unchanged; true target/R still unknown.'
    elif name=='early_rebound_pilot':
        old='            int limit=frontierLimit(f);'
        new='''            const bool pilot=n>650 && best<(n-1)/3 && f.significant && f.noisy && f.halfLeft>=16;
            int limit=frontierLimit(f);
            if (pilot) limit=max(limit,min(n-1,best+176));'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected frontier decision')
        text=text.replace(old,new,1)
        text=text.replace('best+191,rightmost+48','best+((pilot)?399:191),rightmost+48',1)
        text=text.replace('if (f.leftEdge && rightmost-best>=48)',
                          'if (f.leftEdge && rightmost-best>=48 && !pilot)',1)
        text=text.replace('rightmost-best>=scout && !f.rebound && !rival &&',
                          'rightmost-best>=scout && !f.rebound && !rival && !(pilot && rightmost<best+176) &&',1)
        old='best<0 || rightmost-best<48 || rightmost-best>=191) return false;'
        new='best<0 || rightmost-best<48 || rightmost-best>=(n>650 && best<(n-1)/3 && f.noisy && f.halfLeft>=16 ? 399 : 191)) return false;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected rival horizon')
        text=text.replace(old,new,1)
        old='        return level[2]>=bestValue-0.15*f.contrast;'
        new='''        if (!(n>650 && best<(n-1)/3 && f.noisy && f.halfLeft>=16))
            return level[2]>=bestValue-0.15*f.contrast;
        const double slope=(level[2]-level[1])/(f.x[first+7]-f.x[first+4]);
        const int horizon=min(n-1,best+399);
        const double projected=level[2]+slope*(horizon-f.x[first+7]);
        return level[2]>=bestValue-0.5*f.contrast && projected>bestValue+max(2*f.noise,0.01*f.contrast);'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected robust rebound evidence')
        text=text.replace(old,new,1)
        description='For broad moderately noisy early peaks on N>650, pilot toward best+176 first. Only three rising median blocks with projected value beating the old peak allow renewable forward leases up to best+399. This explicitly wagers against the old peak; Q/O/parking guards remain.'
    elif name in ['viability_parking','viability_parking_v2']:
        old='        if (alive && best>=0 && pos!=best) readReal(best,true);'
        new='''        int parking=best;
        // A positive-score target must be >=rightmost-199. A parking point
        // below that target window minus3 cannot score positively for any target.
        if (alive && best>=0 && best<rightmost-202) {
            int feasible=-1;
            for (int x=max(0,rightmost-202);x<n;++x) {
                if (value[x]<0 || (x!=pos && !canRead(x,true))) continue;
                if (feasible<0 || better(x,value[x],feasible,value[feasible])) feasible=x;
            }
            if (feasible>=0) parking=feasible;
        }
        if (alive && parking>=0 && pos!=parking) readReal(parking,true);'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected final parking interface')
        if name=='viability_parking_v2':
            new=new.replace('int parking=best;','int parking=best;\n        bool rescue=false;',1)
            new=new.replace('(x!=pos && !canRead(x,true))','!canRead(x,true)',1)
            new=new.replace('if (feasible>=0) parking=feasible;',
                            'if (feasible>=0) { parking=feasible; rescue=true; }',1)
            new=new.replace('pos!=parking)', '(pos!=parking || rescue))',1)
        text=text.replace(old,new,1)
        description='Keep the entire212686 trajectory until finish. Only when old raw-best parking is mathematically impossible to score (best<rightmost-202), select a legal observed candidate in the viable parking window. Old positive-score parking cases are unchanged.'
        if name=='viability_parking_v2':
            description+=' A rescue always emits a legal final query of an already observed point, so its unchanged right frontier and impossible-old-parking proof are verifiable from the trace.'
    elif name=='prefix_complete_audit':
        text=(ROOT/'data/versions/online_search/scored_212243_bacbbba94c9d.cpp').read_text(encoding='utf-8-sig')
        old='''        for (int x:{0,4,12,24}) {
            if (x>=n || !sample(x)) break;
            if (certificate()) return;
        }'''
        new='''        int prefixReads=0;
        for (int x=0;x<=min(n-1,24);++x) {
            const bool anchor=x==0 || x==4 || x==12 || x==24;
            auditAux[x]=!anchor;
            if (!sample(x)) break;
            if (!anchor) ++prefixReads;
            if (certificate()) return;
        }'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected seed initialization')
        text=text.replace(old,new,1)
        text=text.replace('        int auditBlock=-1,auditTarget=-1;\n','',1)
        text=text.replace('        uint64_t auditSeed=0x94d049bb133111ebULL ^ static_cast<uint64_t>(n)*1000003ULL;\n','',1)
        begin=text.index('            if (!f.flat && !(n>=539 && n<=613)) {')
        end=text.index('            if (next<=rightmost || !sample(next)) break;',begin)
        text=text[:begin]+text[end:]
        text=text.replace('f.flat && q%7==0','f.flat && (q-prefixReads)%7==0',1)
        description='Exhaust the entire initial0..24 bracket in ascending order, tagging21 extra points separately for noise estimation and flat-grid timing. Continue from the original final seed24; reserve fine/parking with coarse cap160, no random probes thereafter.'
    elif name=='flat_random_burst':
        text=(ROOT/'data/versions/online_search/scored_212243_bacbbba94c9d.cpp').read_text(encoding='utf-8-sig')
        old='if (!f.flat && !(n>=539 && n<=613)) {'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected anchored random gate')
        text=text.replace(old,'if (f.flat) {',1)
        text=text.replace('int auditBlock=-1,auditTarget=-1;',
                          'int auditBlock=-1,auditTarget=-1,auditReads=0;',1)
        old='''                if (auditTarget>rightmost && auditTarget<next) {
                    auditAux[auditTarget]=1;
                    if (!sample(auditTarget)) { auditAux[auditTarget]=0; break; }
                }'''
        new='''                if (auditTarget>rightmost && auditTarget<next && q+4<=160) {
                    for (int x=auditTarget;x<min(next,auditTarget+3);++x) {
                        auditAux[x]=1;
                        if (!sample(x)) { auditAux[x]=0; break; }
                        ++auditReads;
                    }
                }'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected random tag block')
        text=text.replace(old,new,1)
        text=text.replace('f.flat && q%7==0','f.flat && (q-auditReads)%7==0',1)
        description='Silent-region discovery: only while observed data are flat, insert a fixed-seed forward burst of up to3 adjacent raw points per32-cell block. Keep the original anchor phase by excluding burst counts from flat-grid jitter, and estimate noise on tagged anchor skeleton.'
    elif name.startswith('skeleton_expert_'):
        if hashlib.sha256(parent.read_bytes()).hexdigest()!='93616283c893e0fc03451decda7dc9f42130ab69b93b14e0f910f86e07a9d61c':
            raise RuntimeError('Expert gate is relative to frozen212686 incumbent')
        template=ROOT/'data/versions/online_search/scored_212243_bacbbba94c9d.cpp'
        text=template.read_text(encoding='utf-8-sig')
        group=name.removeprefix('skeleton_expert_')
        gate={'short':'n<=500','mid':'n>500 && n<=650','long':'n>650',
              'shortmid':'n<=650','midlong':'n>500','shortlong':'n<=500 || n>650'}[group]
        text=text.replace('if (!f.flat && !(n>=539 && n<=613)) {',
                          'if (!f.flat && !(n>=539 && n<=613) && ('+gate+')) {',1)
        start=text.index('    void explore() {')
        end=text.index('    optional<double> vertex',start)
        text=text[:start]+text[start:end].replace('160','(('+gate+') ? 160 : 128)')+text[end:]
        start='        // Auxiliary probes remain raw winner candidates; only the roughness'
        if text.count(start)!=1:
            raise RuntimeError('Unexpected provenance feature block')
        text=text.replace(start,'        if ('+gate+') {\n'+start,1)
        text=text.replace('        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;',
                          '        }\n        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;',1)
        description='Gated complete scored212243 anchored-random+provenance-noise expert to '+gate+'; preserve original212686 sampling, coarse quota and residual estimator outside gate.'
    elif name=='optimistic_interval_refine':
        helper=r'''
    void optimisticIntervalRefine() {
        // Empirical Lipschitz optimism, not a certified upper bound for unread data.
        struct Cell { int a,b; double upper; };
        for (int round=0;round<2 && alive && seconds()<7.5;++round) {
            if (bestValue==VMAX) { refine(); return; }
            const vector<int> xs=observed();
            double slope=0;
            long long low=bestValue;
            for (size_t i=0;i<xs.size();++i) {
                low=min(low,value[xs[i]]);
                if (i) slope=max(slope,abs(static_cast<double>(value[xs[i]]-value[xs[i-1]]))/(xs[i]-xs[i-1]));
            }
            if (low==bestValue) { refine(); return; }
            const double lipschitz=max(1.0,1.5*slope);
            vector<Cell> cells;
            for (size_t i=1;i<xs.size();++i) {
                const int a=xs[i-1],b=xs[i];
                if (b-a<=1) continue;
                const double upper=min(static_cast<double>(VMAX),
                    (static_cast<double>(value[a])+value[b]+lipschitz*(b-a))/2);
                if (upper>bestValue) cells.push_back({a,b,upper});
            }
            sort(cells.begin(),cells.end(),[&](const Cell& a,const Cell& b) {
                if (a.upper!=b.upper) return a.upper>b.upper;
                if (a.b-a.a!=b.b-b.a) return a.b-a.a>b.b-b.a;
                return abs(a.a+a.b-2*best)<abs(b.a+b.b-2*best);
            });
            const int available=QMAX-1-q;
            const int budget=round ? available : available-min(32,available/3);
            vector<int> plan;
            for (const auto& cell:cells) {
                if (static_cast<int>(plan.size())+cell.b-cell.a-1>budget) continue;
                for (int x=cell.a+1;x<cell.b;++x) plan.push_back(x);
            }
            if (plan.empty()) return;
            plan=orient(move(plan),round==0);
            if (!routeSafe(plan)) return;
            for (int x:plan) if (!sample(x) || certificate()) return;
        }
    }
'''
        old='    void refine() {'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected fine-search interface')
        text=text.replace(old,helper+old,1)
        old='else { explore(); if (alive) refine(); }'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected controller interface')
        text=text.replace(old,'else { explore(); if (alive) optimisticIntervalRefine(); }',1)
        description='Keep scored coarse search; rank every unread observed cell by empirical Lipschitz cone upper value, choose only complete cells within two monotone-pass budgets, rescore after real observations. No finite-scenario annealing; optimism is heuristic, not a proof.'
    elif name=='skeleton_noise_audit':
        old='    vector<long long> value;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected raw-cache declaration')
        text=text.replace(old,old+'\n    vector<char> auditAux;',1)
        text=text.replace('value(length,-1),trace(diagnostics)',
                          'value(length,-1),auditAux(length,0),trace(diagnostics)',1)
        old='                if (auditTarget>rightmost && auditTarget<next && !sample(auditTarget)) break;'
        new='''                if (auditTarget>rightmost && auditTarget<next) {
                    auditAux[auditTarget]=1;
                    if (!sample(auditTarget)) { auditAux[auditTarget]=0; break; }
                }'''
        if text.count(old)!=1:
            raise RuntimeError('Expected the scored anchored-audit policy')
        text=text.replace(old,new,1)
        old='        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;'
        new='''        // Auxiliary probes remain raw winner candidates; only the roughness
        // channel uses the fixed-anchor provenance skeleton.
        vector<int> skeleton;
        for (int x:f.x) if (!auditAux[x]) skeleton.push_back(x);
        residual.clear();
        for (size_t i=1;i+1<skeleton.size();++i) {
            const int a=skeleton[i-1],x=skeleton[i],b=skeleton[i+1];
            const double t=static_cast<double>(x-a)/(b-a);
            residual.push_back(value[x]-(value[a]+t*(value[b]-value[a])));
        }
'''+old
        if text.count(old)!=1:
            raise RuntimeError('Unexpected feature contrast interface')
        text=text.replace(old,new,1)
        description='On scored anchored random audit, tag auxiliary sample provenance and estimate residual roughness from the non-auxiliary skeleton only; retain every random raw value for winner ranking, slopes and contrast.'
    elif name in ['geometry_residual','audit_geometry_residual']:
        sys.path.insert(0,str(ROOT/'dev'))
        from tools.noise_sampling_candidates_20261030 import curvature_scaled_noise
        text=curvature_scaled_noise(text)
        description='On the scored random-hull parent, compensate unequal point spacing and local median curvature in interpolation residuals, retaining the rest of the hybrid policy. Heuristic scale estimate, not a known noise bound.'
        if name=='audit_geometry_residual':
            description=description.replace('random-hull','anchored-random-audit')
    elif name=='anchored_random_audit':
        start=text.index('    void explore() {')
        end=text.index('    optional<double> vertex',start)
        chunk=text[start:end]
        old='        int flatRuns=0, adjacentReads=0;'
        if chunk.count(old)!=1:
            raise RuntimeError('Unexpected explore state')
        chunk=chunk.replace(old,old+'''
        int auditBlock=-1,auditTarget=-1;
        uint64_t auditSeed=0x94d049bb133111ebULL ^ static_cast<uint64_t>(n)*1000003ULL;''',1)
        old='            if (next<=rightmost || !sample(next)) break;'
        new='''            if (!f.flat && !(n>=539 && n<=613)) {
                const int block=rightmost/32;
                if (block!=auditBlock) {
                    auditBlock=block;
                    auditSeed^=auditSeed<<13; auditSeed^=auditSeed>>7; auditSeed^=auditSeed<<17;
                    auditTarget=block*32+1+static_cast<int>(auditSeed%31);
                }
                if (auditTarget>rightmost && auditTarget<next && !sample(auditTarget)) break;
            }
'''+old
        if chunk.count(old)!=1:
            raise RuntimeError('Unexpected anchor query')
        chunk=chunk.replace(old,new,1).replace('128','160')
        text=text[:start]+chunk+text[end:]
        description='Keep fixed incumbent anchors; add one reproducible random position per32-cell block on the forward path, outside the already profitable539..613 band. Reserve39 reads by coarse cap160; no extra right reach or reversal for each audit.'
    elif name in ['hybrid_random_hull','hybrid_random_only','hull_priority_only'] or name.startswith('hybrid_expert_'):
        old='        int flatRuns=0, adjacentReads=0;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected exploration state')
        text=text.replace(old,old+'''
        int randomBlock=-1;
        array<int,3> anchors{};
        uint64_t localSeed=0xd1b54a32d192ed03ULL ^ static_cast<uint64_t>(n)*1000003ULL;
        auto scoutRandom=[&]() { localSeed^=localSeed<<13; localSeed^=localSeed>>7; localSeed^=localSeed<<17; return localSeed; };''',1)
        old='            int next=min({n-1,rightmost+step,limit});'
        new=old+'''
            if (!f.flat) {
                const int block=rightmost/32;
                if (block!=randomBlock) {
                    randomBlock=block;
                    anchors={block*32+1+static_cast<int>(scoutRandom()%15),
                             block*32+17+static_cast<int>(scoutRandom()%15),
                             min(n-1,(block+1)*32)};
                    sort(anchors.begin(),anchors.end());
                }
                next=min(n-1,(block+1)*32);
                for (int x:anchors) if (x>rightmost) { next=x; break; }
                next=min({n-1,next,limit});
            }'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected exploration next-point interface')
        text=text.replace(old,new,1)
        old='(n>=539 && n<=613)'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected adjacent-confirmation gate')
        text=text.replace(old,'(f.noisy || f.rebound || f.curvature<0)',1)
        old='next+2<=limit && q+2<=128'
        text=text.replace(old,'next+2<=limit && next+2<=32*(next/32+1) && q+2<=128',1)
        old='        vector<int> peaks=f.peaks;'
        new='''        // Upper hull guides interval priority; raw candidates remain intact.
        vector<int> hull;
        for (int x:f.x) {
            while (hull.size()>=2) {
                const int a=hull[hull.size()-2],b=hull.back();
                const long double cross=static_cast<long double>(b-a)*(value[x]-value[b])-
                    static_cast<long double>(value[b]-value[a])*(x-b);
                if (cross<0) break;
                hull.pop_back();
            }
            hull.push_back(x);
        }
        for (int x:hull) {
            if (value[x]<threshold) continue;
            auto it=lower_bound(f.x.begin(),f.x.end(),x);
            const int lo=it==f.x.begin()?x:*prev(it);
            const int hi=next(it)==f.x.end()?x:*next(it);
            for (int y=lo+1;y<hi;++y) add(y,109-0.05*abs(y-x));
        }
'''+old
        if text.count(old)!=1:
            raise RuntimeError('Unexpected raw-pool interface')
        text=text.replace(old,new,1)
        old='                    vector<int> probe;'
        text=text.replace(old,'''                    const int cellLo=min(modelLo,*prev(it));
                    const int cellHi=max(modelHi,*next(it));
'''+old,1)
        text=text.replace('for (int x=modelHi;x>=modelLo;--x)','for (int x=cellHi;x>=cellLo;--x)',1)
        description='Hybrid: fixed32-cell anchors plus two reproducible stratified random points per block; conditional adjacent confirmations, upper-hull candidate-cell priorities, complete raw model cell checks; original motor/parking guards retained.'
        if name in ['hybrid_random_only','hull_priority_only']:
            text=text.replace('(f.noisy || f.rebound || f.curvature<0) && f.significant',
                              '(n>=539 && n<=613) && f.significant',1)
            text=text.replace('next+2<=limit && next+2<=32*(next/32+1) && q+2<=128',
                              'next+2<=limit && q+2<=128',1)
            text=text.replace('                    const int cellLo=min(modelLo,*prev(it));\n','',1)
            text=text.replace('                    const int cellHi=max(modelHi,*next(it));\n','',1)
            text=text.replace('for (int x=cellHi;x>=cellLo;--x)',
                              'for (int x=modelHi;x>=modelLo;--x)',1)
            if name=='hybrid_random_only':
                begin=text.index('        // Upper hull guides interval priority; raw candidates remain intact.')
                end=text.index('        vector<int> peaks=f.peaks;',begin)
                text=text[:begin]+text[end:]
                description='Random-skeleton ablation only: fixed32 anchors and two stratified fixed-seed random points; original adjacent gate, fine model window and candidate planner unchanged.'
            else:
                begin=text.index('        int randomBlock=-1;')
                end=text.index('        while (q<128',begin)
                text=text[:begin]+text[end:]
                begin=text.index('            if (!f.flat) {\n                const int block=rightmost/32;')
                end=text.index('            const int center=(n-1)/2;',begin)
                text=text[:begin]+text[end:]
                description='Upper-hull priority ablation only: preserve all incumbent sampling and early model checks; prioritize complete competitive hull-vertex cells in the raw candidate planner, without discarding any raw candidate.'
        if name.startswith('hybrid_expert_'):
            group=name.removeprefix('hybrid_expert_')
            gate={'short':'n<=500','mid':'n>500 && n<=650','long':'n>650',
                  'shortmid':'n<=650','midlong':'n>500','shortlong':'n<=500 || n>650'}[group]
            text=text.replace('if (!f.flat) {\n                const int block=rightmost/32;',
                              'if (!f.flat && ('+gate+')) {\n                const int block=rightmost/32;',1)
            text=text.replace('(f.noisy || f.rebound || f.curvature<0) && f.significant',
                              '(('+gate+') ? (f.noisy || f.rebound || f.curvature<0) : (n>=539 && n<=613)) && f.significant',1)
            text=text.replace('        // Upper hull guides interval priority; raw candidates remain intact.',
                              '        if ('+gate+') {\n        // Upper hull guides interval priority; raw candidates remain intact.',1)
            text=text.replace('        vector<int> peaks=f.peaks;',
                              '        }\n        vector<int> peaks=f.peaks;',1)
            text=text.replace('const int cellLo=min(modelLo,*prev(it));',
                              'const int cellLo=('+gate+') ? min(modelLo,*prev(it)) : modelLo;',1)
            text=text.replace('const int cellHi=max(modelHi,*next(it));',
                              'const int cellHi=('+gate+') ? max(modelHi,*next(it)) : modelHi;',1)
            description+=' Entire expert gated to '+gate+'; all other N retain incumbent behavior.'
    elif name=='compact_fine_routes':
        old='''        if (static_cast<int>(candidates.size())<=budget) {
            vector<int> all;
            for (const auto& point:candidates) all.push_back(point.x);
            return orient(move(all),descending);
        }'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected full fine-sweep shortcut')
        text=text.replace(old,'        budget=min(budget,static_cast<int>(candidates.size()));',1)
        old='        const int minimum=min(budget,max(7,budget*4/5));'
        new='''        // Compare compact complete-neighborhood routes against the full plan.
        // The existing scenario model is heuristic, so retain all competing
        // candidate clusters in the original full-plan alternative.
        const int minimum=min(budget,7);
        for (int count:{7,15,31,63}) {
            vector<int> compact;
            for (int i=0;i<min(count,budget);++i) compact.push_back(ranked[i].x);
            compact=canonical(move(compact),descending);
            const double compactScore=planScore(compact,cases,candidates);
            if (compactScore>bestScore) { winner=compact; bestScore=compactScore; }
        }
        vector<int> cell;
        auto bracket=lower_bound(f.x.begin(),f.x.end(),best);
        const int cellLo=bracket==f.x.begin()?best:*prev(bracket);
        const int cellHi=next(bracket)==f.x.end()?best:*next(bracket);
        for (const auto& point:candidates)
            if (point.x>=cellLo && point.x<=cellHi) cell.push_back(point.x);
        if (!cell.empty() && static_cast<int>(cell.size())<=budget) {
            cell=canonical(move(cell),descending);
            const double cellScore=planScore(cell,cases,candidates);
            if (cellScore>bestScore) { winner=cell; bestScore=cellScore; }
        }'''
        if text.count(old)!=1:
            raise RuntimeError('Unexpected plan minimum')
        text=text.replace(old,new,1)
        description='Keep coarse lookahead and model-first refinement. Replace automatic all-candidate fine sweeps by cost-scored competition between original full routes, ranked compact routes and the complete raw-winner bracket; permit smaller annealing plans. Existing six scenario estimates are heuristic, not certified peak bounds.'
    elif name in ['wide_expert_short','wide_expert_mid','wide_expert_long']:
        gate={'wide_expert_short':'n<=500','wide_expert_mid':'n>500 && n<=650','wide_expert_long':'n>650'}[name]
        old='step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected cruise rule')
        text=text.replace(old,'step=('+gate+') && f.halfLeft>=32 && f.curvature>=0 ? 16 : 8;',1)
        description='Use the wide-cruise expert only for '+gate+' on the explicit scored parent; other inputs keep its8-cell grid. Stopping/refinement unchanged. The old global-332 result was on212686, so a different parent requires this direct combination test rather than assuming additive gains.'
    elif name=='wide_cruise_scan':
        old='step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected rising cruise rule')
        text=text.replace(old,'step=f.halfLeft>=32 && f.curvature>=0 ? 16 : 8;',1)
        description='Use phase-preserving16-cell cruise only for clean sustained rises with observed left-half-width>=32 and nonnegative slope change; return to8 when slowing, narrow, noisy or falling. Preserve initial anchors, stopping policy, raw winners and fine planner.'
    elif name=='curvature_paced_scan':
        old='step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;'
        if text.count(old)!=1:
            raise RuntimeError('Unexpected rising-step interface')
        text=text.replace(old,'step=f.curvature<-max(0.1,f.noise/12) ? 4 : 16;',1)
        description='During clean sustained rises, use4 cells on concave slowing shoulders and16 cells otherwise; noisy or non-rising branches retain8. Preserve original stopping, refinement, raw winners and movement guards.'
    else:
        raise ValueError(name)
    OUT.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256(parent.read_bytes()).hexdigest()
    path=OUT/(name+'_'+sha[:12]+'.cpp')
    contents=text.encode('utf-8')
    if path.exists() and path.read_bytes()!=contents:
        raise RuntimeError('Frozen candidate differs')
    path.write_bytes(contents)
    info=dict(name=name,parent=str(parent),parent_sha256=sha,source=str(path),
              sha256=hashlib.sha256(contents).hexdigest(),description=description)
    path.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(info,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('--parent',type=Path,default=ROOT/'data/versions/main_online_212686.cpp')
    args=parser.parse_args()
    generate(args.name,args.parent)
