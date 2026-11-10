"""Frozen structural follow-ups, selected one at a time using official totals."""
from pathlib import Path
import hashlib,json,sys,re
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261102'

def freeze(name,parent,text,description):
    p=OUT/(name+'.cpp'); raw=text.encode('utf-8')
    if p.exists() and p.read_bytes()!=raw: raise RuntimeError('Frozen candidate differs')
    p.write_bytes(raw)
    info=dict(parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
              source=str(p),sha256=hashlib.sha256(raw).hexdigest(),description=description)
    p.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(info,ensure_ascii=False))

def make(name):
    parent=ROOT/'data/versions/main_online_216258.cpp'
    text=parent.read_text(encoding='utf-8-sig')
    if name=='validated_forward':
        parent=OUT/'forward_peak_window.cpp'
        text=parent.read_text(encoding='utf-8-sig')
        text=text.replace('knots.size()<3','knots.size()<4',1).replace('knots.size()!=3','knots.size()!=4',1)
        old='''        return min(n-1,max(rightmost+4,static_cast<int>(ceil(predicted))+3));'''
        new='''        const int p=knots[3];
        const double previousSlope=static_cast<double>(value[a]-value[p])/(a-p);
        const double previousBend=(sl-previousSlope)/(b-p);
        if (previousBend>=-1e-12) return nullopt;
        const double previousPeak=(p+a)/2.0-previousSlope/(2*previousBend);
        const double heldPrediction=value[p]+previousSlope*(c-p)+previousBend*(c-p)*(c-a);
        if (!isfinite(previousPeak) || abs(previousPeak-predicted)>4 ||
            abs(heldPrediction-value[c])>max(2*f.noise,0.005*f.contrast)) return nullopt;
'''+old
        if text.count(old)!=1: raise RuntimeError('Unexpected forecast interface')
        text=text.replace(old,new,1)
        desc='Validate before dense commitment: an older3-knot quadratic must predict the already observed4th raw point and agree with the refreshed peak forecast. Dense step1 window/budgets/extension unchanged from scored213755. Tests online self-validation rather than unconditional curvature triggering.'
    elif name=='beam_interval_tour':
        parent=OUT/'tour_on_reference_scout.cpp'
        text=(OUT/'tour_partial_credit.cpp').read_text(encoding='utf-8-sig')
        a=text.index('    void refine() {'); b=text.index('    void finish() {',a)
        text=text[:a]+r'''    void refine() {
        const Features statistics=features();
        const double noise=statistics.noise,contrast=statistics.contrast;
        struct Plan { vector<int> ids,route; double utility=-1e100; };
        for (int pass=0;pass<2 && q<QMAX-1 && seconds()<7.5 && !certificate();++pass) {
            const TourMotion current{pos,direction,turns,travel};
            const vector<TourCell> cells=tourBeliefs(noise,contrast);
            if (cells.empty()) break;
            double mass=1;
            for (const auto& c:cells) mass+=c.weight;
            const int avail=QMAX-1-q;
            const int budget=pass ? avail : max(1,avail-max(12,avail/3));
            auto evaluate=[&](const vector<int>& ids) {
                Plan result; result.ids=ids;
                vector<int> route; vector<unsigned char> covered(cells.size(),0);
                for (int i:ids) {
                    covered[i]=1;
                    for (int x=cells[i].lo+1;x<cells[i].hi;++x) route.push_back(x);
                }
                if (static_cast<int>(route.size())>budget) return result;
                sort(route.begin(),route.end());
                for (int orientation=0;orientation<2;++orientation) {
                    if (orientation) reverse(route.begin(),route.end());
                    if (!routeSafe(route)) continue;
                    TourMotion end=current;
                    for (int x:route) tourMove(end,x);
                    const int count=static_cast<int>(route.size());
                    double value=tourScore(end,count,best);
                    for (size_t i=0;i<cells.size();++i)
                        value+=cells[i].weight*tourScore(end,count,covered[i]?cells[i].target:best,cells[i].target);
                    value/=mass;
                    if (value>result.utility) { result.utility=value; result.route=route; }
                }
                return result;
            };
            Plan winner=evaluate({});
            vector<Plan> beam{winner};
            for (int depth=0;depth<16 && !beam.empty() && seconds()<7.0;++depth) {
                vector<Plan> nextBeam;
                set<vector<int>> seen;
                for (const Plan& state:beam) for (int i=0;i<static_cast<int>(cells.size());++i) {
                    if (binary_search(state.ids.begin(),state.ids.end(),i)) continue;
                    vector<int> ids=state.ids;
                    ids.insert(lower_bound(ids.begin(),ids.end(),i),i);
                    if (!seen.insert(ids).second) continue;
                    Plan candidate=evaluate(ids);
                    if (candidate.utility<=-1e90) continue;
                    if (candidate.utility>winner.utility) winner=candidate;
                    nextBeam.push_back(move(candidate));
                }
                sort(nextBeam.begin(),nextBeam.end(),[](const Plan& x,const Plan& y) {
                    return x.utility!=y.utility ? x.utility>y.utility : x.ids<y.ids;
                });
                if (nextBeam.size()>32) nextBeam.resize(32);
                beam=move(nextBeam);
            }
            if (winner.route.empty()) break;
            for (int x:winner.route) if (!sample(x) || certificate()) return;
        }
    }
'''+text[b:]
        desc='Prize-collecting interval tours: beam-search subsets of complete cells, allowing jumps over low-belief gaps instead of forcing contiguous coverage. Evaluate both physical orientations under full Q/M/O/R and200*d partial-credit outcomes for unsearched targets. Width32/depth16 with stopping alternative and two data-replanning passes; belief weights remain uncalibrated hypotheses.'
    elif name=='rank_verified_checkpoint':
        parent=OUT/'rank_hill_stop_long.cpp'
        text=parent.read_text(encoding='utf-8-sig')
        sketch=(OUT/'forward_peak_sketch.cpp').read_text(encoding='utf-8-sig')
        a=text.index('    Features features() {'); b=text.index('    bool coarseRivalEvidence(',a)
        text=text[:a]+sketch[sketch.index('    Features features() {'):sketch.index('    bool coarseRivalEvidence(')]+text[b:]
        text=text.replace('    vector<long long> value;','    vector<long long> value;\n    vector<unsigned char> fineAux;',1)
        text=text.replace(': wire(transport),n(length),value(length,-1),trace(diagnostics)',
                          ': wire(transport),n(length),value(length,-1),fineAux(length,0),trace(diagnostics)',1)
        a=text.index('    void explore() {'); b=text.index('    optional<double> vertex',a)
        chunk=text[a:b]
        chunk=chunk.replace('        int flatRuns=0, adjacentReads=0;',
                            '        int flatRuns=0, adjacentReads=0;\n        bool checkpointDone=false; int checkpointReads=0;',1)
        for x,y in [('q<128','q<128+checkpointReads'),('q+3<=128','q+3<=128+checkpointReads'),
                    ('q+2<=128','q+2<=128+checkpointReads'),('remaining=128-q','remaining=128+checkpointReads-q')]:
            chunk=chunk.replace(x,y)
        anchor='            if (weakHillResolved(f)) break;'
        if chunk.count(anchor)!=1: raise RuntimeError('Unexpected weak-hill decision')
        chunk=chunk.replace(anchor,'''            if (!checkpointDone && turns<=1 && weakHillResolved(f)) {
                checkpointDone=true;
                auto it=lower_bound(f.x.begin(),f.x.end(),best);
                if (it!=f.x.begin() && it!=f.x.end() && next(it)!=f.x.end()) {
                    const int frontier=rightmost;
                    vector<int> probe;
                    for (int x=*next(it)-1;x>*prev(it);--x)
                        if (value[x]<0) probe.push_back(x);
                    if (!probe.empty() && q+static_cast<int>(probe.size())+2<=QMAX && routeSafe(probe)) {
                        for (int x:probe) {
                            fineAux[x]=1;
                            if (!sample(x)) { coarseFrontier=rightmost; return; }
                            ++checkpointReads;
                        }
                        if (bestValue-f.floor>max(4.0,25*f.noise)) break;
                        if (pos!=frontier) {
                            if (!readReal(frontier)) { coarseFrontier=rightmost; return; }
                            ++checkpointReads;
                        }
                        continue;
                    }
                }
            }''',1)
        text=text[:a]+chunk+text[b:]
        desc='Value-of-information checkpoint on weak rank hill: at most once, exhaust the raw-winner bracket before making irreversible stopping decision. Only stop if verified raw height clears original25*noise significance; otherwise physically return to saved frontier and resume. Tag verification points out of trend/noise sketch, charge extra reads separately, retain turn/parking reserve.'
    elif name=='tour_partial_credit':
        parent=OUT/'tour_on_reference_scout.cpp'
        text=parent.read_text(encoding='utf-8-sig')
        a=text.index('    double tourScore('); b=text.index('    void refine() {',a)
        text=text[:a]+'''    double tourScore(TourMotion m,int extra,int parkingIndex,int target) const {
        int parking=0;
        if (m.pos!=parkingIndex) { tourMove(m,parkingIndex); parking=1; }
        const int redundant=max(0,rightmost-target),distance=abs(parkingIndex-target);
        if (q+extra+parking>QMAX || m.turns>OMAX || redundant>199 || distance>3) return 0;
        return max(0.0,3000.0-200*distance-q-extra-parking-m.travel-m.turns-redundant);
    }
    double tourScore(TourMotion m,int extra,int target) const {
        return tourScore(m,extra,target,target);
    }
'''+text[b:]
        old='            double bestUtility=tourScore(current,0,best)/totalWeight;'
        new='''            double stoppingValue=tourScore(current,0,best);
            for (const TourCell& c:cells) stoppingValue+=c.weight*tourScore(current,0,best,c.target);
            double bestUtility=stoppingValue/totalWeight;'''
        if text.count(old)!=1: raise RuntimeError('Unexpected tour stopping score')
        text=text.replace(old,new,1)
        old='''                        for (size_t k=first;k<=last;++k)
                            utility+=cells[k].weight*tourScore(end,reads,cells[k].target);'''
        new='''                        for (size_t k=0;k<cells.size();++k) {
                            const bool found=k>=first && k<=last;
                            utility+=cells[k].weight*tourScore(end,reads,found?cells[k].target:best,cells[k].target);
                        }'''
        if text.count(old)!=1: raise RuntimeError('Unexpected target outcome score')
        text=text.replace(old,new,1)
        desc='Correct expected utility to include partial credit when parking within3 of an unqueried true target, with actual200*d penalty, rather than treating every unsearched target as zero. Score every selected/unselected target hypothesis under the complete tour cost; keep interval search space unchanged.'
    elif name in ['paired_lattice_long','paired_lattice_mirror_long','paired_lattice_mid']:
        gate='n>500 && n<=650' if name=='paired_lattice_mid' else 'n>650'
        pair='9 : 7' if 'mirror' in name else '7 : 9'
        a=text.index('    void explore() {'); b=text.index('    optional<double> vertex',a)
        chunk=text[a:b]
        anchor='        int flatRuns=0, adjacentReads=0;'
        chunk=chunk.replace(anchor,anchor+'\n        bool shortGap=true;',1)
        anchor='            const Features f=features();'
        chunk=chunk.replace(anchor,anchor+'\n            const int regularStep=('+gate+') ? (shortGap ? '+pair+') : 8;',1)
        chunk=chunk.replace('step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;','step=regularStep;',1)
        chunk=chunk.replace('if (f.noisy) step=8;','if (f.noisy) step=regularStep;',1)
        chunk=chunk.replace('else step=f.noisy || state==Shape::Rough ? 8 : 8;','else step=regularStep;',1)
        chunk=chunk.replace('if (f.rebound) { use(Op::K05); step=8; }',
                            'if (f.rebound) { use(Op::K05); step=regularStep; }',1)
        chunk=chunk.replace('use(Op::G07); step=min(step,8);','use(Op::G07); step=min(step,regularStep);',1)
        anchor='            if (next<=rightmost || !sample(next)) break;'
        chunk=chunk.replace(anchor,anchor+'\n            if (('+gate+') && !f.flat) shortGap=!shortGap;',1)
        text=text[:a]+chunk+text[b:]
        desc='Moment-balanced sampling lattice on '+gate+': alternate7/9-cell nonflat steps with mean8. For local quadratics, neighboring gap sum stays16 and product63 stays constant, retaining curvature/noise scale while perturbing aliasing. No extra query budget; preserve parent flat search, stops, fine search and physical ledgers.'
        if 'mirror' in name: desc+=' Reverse the lattice phase9/7 as a distinct deterministic placement policy.'
    elif name in ['long_dense_grid','long_sparse_grid','mid_dense_grid','short_dense_grid']:
        gate={'long_dense_grid':'n>650','long_sparse_grid':'n>650',
              'mid_dense_grid':'n>500 && n<=650','short_dense_grid':'n<=500'}[name]
        step={'long_dense_grid':6,'long_sparse_grid':10,'mid_dense_grid':6,'short_dense_grid':4}[name]
        cap=176 if name=='long_dense_grid' else 128
        a=text.index('    void explore() {'); b=text.index('    optional<double> vertex',a)
        chunk=text[a:b]
        anchor='        int flatRuns=0, adjacentReads=0;'
        chunk=chunk.replace(anchor,anchor+'\n        const int regularStep=('+gate+') ? '+str(step)+' : 8;\n        const int coarseCap=('+gate+') ? '+str(cap)+' : 128;',1)
        chunk=chunk.replace('step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;','step=regularStep;',1)
        chunk=chunk.replace('if (f.noisy) step=8;','if (f.noisy) step=regularStep;',1)
        chunk=chunk.replace('else step=f.noisy || state==Shape::Rough ? 8 : 8;','else step=regularStep;',1)
        for x,y in [('q<128','q<coarseCap'),('q+3<=128','q+3<=coarseCap'),
                    ('q+2<=128','q+2<=coarseCap'),('remaining=128-q','remaining=coarseCap-q')]:
            chunk=chunk.replace(x,y)
        text=text[:a]+chunk+text[b:]
        desc='Regular-resolution specialist on '+gate+': use'+str(step)+'-cell nonflat anchors and coarse budget'+str(cap)+', keeping uniform geometry instead of mixing auxiliary points. Other N retain216258. Dense long budget preserves full-array coverage and at least22 fine/parking reads; scout/stop/fine models otherwise unchanged.'
    elif name=='rank_hill_stop_long':
        helper=r'''    static double rankTrend(const vector<long long>& values) {
        const int count=static_cast<int>(values.size());
        if (count<8) return 0;
        int statistic=0;
        for (int i=0;i<count;++i) for (int j=i+1;j<count;++j)
            statistic+=(values[j]>values[i])-(values[j]<values[i]);
        vector<long long> sorted=values;
        sort(sorted.begin(),sorted.end());
        double tied=0;
        for (int i=0;i<count;) {
            int j=i+1;
            while (j<count && sorted[j]==sorted[i]) ++j;
            const double t=j-i;
            tied+=t*(t-1)*(2*t+5); i=j;
        }
        const double variance=(static_cast<double>(count)*(count-1)*(2*count+5)-tied)/18;
        return variance>0 ? (statistic-(statistic>0)+(statistic<0))/sqrt(variance) : 0;
    }
    bool weakHillResolved(const Features& f) const {
        if (n<=650 || f.flat || f.significant || f.x.size()<20 ||
            f.contrast<=max(4.0,4*f.noise) || rightmost-best<64 || rightmost-best>144)
            return false;
        int apex=-1;
        long long level=-1;
        for (int i=8;i+8<static_cast<int>(f.x.size());++i) {
            array<long long,5> window{};
            for (int j=-2;j<=2;++j) window[j+2]=value[f.x[i+j]];
            sort(window.begin(),window.end());
            if (window[2]>level || (window[2]==level && apex>=0 &&
                abs(f.x[i]-best)<abs(f.x[apex]-best))) { apex=i; level=window[2]; }
        }
        if (apex<0 || abs(f.x[apex]-best)>48 || level<bestValue-max(4*f.noise,0.2*f.contrast))
            return false;
        vector<long long> left,right;
        for (int i=max(0,apex-13);i<=apex-2;++i) left.push_back(value[f.x[i]]);
        for (int i=apex+2;i<=min(static_cast<int>(f.x.size())-1,apex+13);++i)
            right.push_back(value[f.x[i]]);
        return rankTrend(left)>2.0 && rankTrend(right)<-2.0;
    }
'''
        anchor='    void explore() {'
        text=text.replace(anchor,helper+anchor,1)
        anchor='            int limit=frontierLimit(f);'
        if text.count(anchor)!=1: raise RuntimeError('Unexpected scout decision')
        text=text.replace(anchor,'            if (weakHillResolved(f)) break;\n'+anchor,1)
        desc='Weak-SNR long curves: use tie-corrected Mann-Kendall rising and falling evidence around a5-point median apex, not raw prominence25*noise. Stop only after two separated rank trends pass|Z|>2, raw winner is near that apex, and64..144 cells of tail exist. Existing significant curves unchanged; default R remains heuristic.'
    elif name=='tour_on_reference_scout':
        independent=(OUT/'tour_solver.cpp').read_text(encoding='utf-8-sig')
        a=independent.index('    vector<Cell> beliefs() const {')
        b=independent.index('    bool safePath(',a)
        methods=independent[a:b]
        a=independent.index('    void refine() {')
        b=independent.index('\npublic:',a)
        refinement=independent[a:b]
        replacements=dict(Cell='TourCell',Motion='TourMotion',moveTo='tourMove',y='value',
                          high='bestValue',points='observed',preferred='tieBetter',TOP='VMAX',
                          QLIMIT='QMAX',TLIMIT='OMAX',right='rightmost',proven='certificate',
                          terminalScore='tourScore',safePath='routeSafe',beliefs='tourBeliefs',motor='current')
        def adapt(code):
            return re.sub(r'\b('+ '|'.join(replacements)+r')\b',lambda m:replacements[m.group()],code)
        methods=adapt(methods).replace('tourBeliefs() const','tourBeliefs(double noise,double contrast) const',1)
        methods=re.sub(r'\bstride\b','8.0',methods)
        refinement=adapt(refinement)
        refinement=refinement.replace('    void refine() {','''    void refine() {
        const Features statistics=features();
        const double noise=statistics.noise,contrast=statistics.contrast;''',1)
        refinement=refinement.replace('            const vector<TourCell> cells=tourBeliefs();',
            '            const TourMotion current{pos,direction,turns,travel};\n            const vector<TourCell> cells=tourBeliefs(noise,contrast);',1)
        support='''    struct TourCell { int lo,hi,target; double weight; };
    struct TourMotion { int pos=0,dir=0,turns=0; long long travel=0; };
    static void tourMove(TourMotion& m,int x) {
        const int d=(x>m.pos)-(x<m.pos);
        if (d) { if (m.dir && d!=m.dir) ++m.turns; m.dir=d; }
        m.travel+=abs(x-m.pos); m.pos=x;
    }
'''
        a=text.index('    void refine() {'); b=text.index('    void finish() {',a)
        text=text[:a]+support+methods+refinement+'\n'+text[b:]
        desc='Isolate the independently designed expected-score interval-tour planner on the proven216258 scout. Enumerate complete-cell routes in both orientations and compare with stopping, then replan. This separates belief/route losses from the independent scout that scored168395.'
    elif name in ['batched_peak_cells','batched_validated_cells']:
        sketch=(OUT/'forward_peak_sketch.cpp').read_text(encoding='utf-8-sig')
        a=text.index('    Features features() {'); b=text.index('    bool coarseRivalEvidence(',a)
        text=text[:a]+sketch[sketch.index('    Features features() {'):sketch.index('    bool coarseRivalEvidence(')]+text[b:]
        text=text.replace('    vector<long long> value;','    vector<long long> value;\n    vector<unsigned char> fineAux;',1)
        text=text.replace(': wire(transport),n(length),value(length,-1),trace(diagnostics)',
                          ': wire(transport),n(length),value(length,-1),fineAux(length,0),trace(diagnostics)',1)
        component=OUT/('validated_forward.cpp' if name=='batched_validated_cells' else 'forward_peak_window.cpp')
        forecast=component.read_text(encoding='utf-8-sig')
        helper=forecast[forecast.index('    optional<int> forwardPeakWindow('):forecast.index('    void explore() {')]
        old='''            if (knots.empty() || knots.back()-*it>=4) knots.push_back(*it);'''
        if helper.count(old)!=1: raise RuntimeError('Unexpected prediction knots')
        helper=helper.replace(old,'            if (!fineAux[*it] && (knots.empty() || knots.back()-*it>=4)) knots.push_back(*it);',1)
        text=text.replace('    void explore() {',helper+'    void explore() {',1)
        a=text.index('    void explore() {'); b=text.index('    optional<double> vertex',a)
        chunk=text[a:b]
        chunk=chunk.replace('        int flatRuns=0, adjacentReads=0;',
                            '        int flatRuns=0, adjacentReads=0;\n        int denseTarget=-1,denseExtra=0,lastDenseStart=-64;',1)
        for x,y in [('q<128','q<128+denseExtra'),('q+3<=128','q+3<=128+denseExtra'),
                    ('q+2<=128','q+2<=128+denseExtra'),('remaining=128-q','remaining=128+denseExtra-q')]:
            chunk=chunk.replace(x,y)
        anchor='            int next=min({n-1,rightmost+step,limit});'
        chunk=chunk.replace(anchor,'''            if (denseExtra<24 && rightmost>=denseTarget && rightmost-lastDenseStart>=32) {
                if (auto predicted=forwardPeakWindow(f)) {
                    denseTarget=min(limit,*predicted); lastDenseStart=rightmost;
                }
            }
'''+anchor,1)
        anchor='''            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;'''
        if chunk.count(anchor)!=1: raise RuntimeError('Unexpected anchor read')
        chunk=chunk.replace(anchor,'''            const long long previousBest=bestValue;
            const int cellStart=rightmost;
            const bool denseCell=rightmost<denseTarget && next-rightmost>=2 &&
                                 denseExtra+next-rightmost-1<=24;
            if (denseCell) for (int x=cellStart+1;x<next;++x) {
                fineAux[x]=1;
                if (!sample(x)) { coarseFrontier=rightmost; return; }
                ++denseExtra;
                if (certificate()) { coarseFrontier=rightmost; return; }
            }
            if (next<=rightmost || !sample(next)) break;
            if (denseCell && next>=denseTarget && value[next]>value[cellStart] && denseExtra+7<=24)
                denseTarget=min(limit,next+8);''',1)
        text=text[:a]+chunk+text[b:]
        desc='Batch full-cell forward fine scan: predict nearby peak, fill every internal point before the original next anchor, then update features once per anchor. Keep coarse grid cadence and legacy bursts; anchor sketch separates trend/noise from all raw maxima. Extend one full cell when still rising, total24 extra reads, reserve fine/parking.'
        if name=='batched_validated_cells': desc+=' Prediction additionally passes the held-out-point forecast check.'
    else:
        raise ValueError(name)
    freeze(name,parent,text,desc)

if __name__=='__main__': make(sys.argv[1])
