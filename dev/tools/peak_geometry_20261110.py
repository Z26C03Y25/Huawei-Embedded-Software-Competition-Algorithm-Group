"""Waveform geometry hypotheses; no online side effects."""
WHY={
 'tent_envelope':'Competing-cell upper estimate also considers the intersection of measured positive left and negative right slopes, allowing a pointed summit between low endpoints.',
 'tent_probe':'Probe a competitive pointed-summit intersection before ordinary whole-cell refinement, leaving the established curvature scanner intact.',
 'tent_pool':'Include pointed-summit intersection and adjacent integers in query planning even when raw endpoints fail the old height filter.',
 'local_descent':'Fast confirmation requires monotone observed descent on the right side of the summit; a smooth summit fit alone cannot confirm a recovering tail.',
 'floor_return':'A fitted summit may use short stopping only after the observed right tail falls below its spatially weighted background-plus-scatter level.',
 'local_precision':'After coarse search, completely read the two measured gaps enclosing the raw winner before model-based refinement; reserve the normal final return.',
}
def rep(s,a,b):
 if s.count(a)!=1:raise ValueError('Geometry anchor '+a)
 return s.replace(a,b,1)
HELPER=r"""
    optional<pair<double,double>> tentIntersection(const vector<int>& xs,size_t i) const {
        if (i<2 || i+1>=xs.size()) return nullopt;
        const int a=xs[i-1],b=xs[i],l=xs[i-2],r=xs[i+1];
        if (b-a<=1) return nullopt;
        const double rising=static_cast<double>(value[a]-value[l])/(a-l);
        const double falling=static_cast<double>(value[r]-value[b])/(r-b);
        const double chord=static_cast<double>(value[b]-value[a])/(b-a);
        if (!(rising>0 && falling<0 && rising>chord && chord>falling)) return nullopt;
        const double location=a+(value[b]-value[a]-falling*(b-a))/(rising-falling);
        if (!isfinite(location) || location<=a || location>=b) return nullopt;
        return pair<double,double>{location,value[a]+rising*(location-a)};
    }
"""
def apply(code,mode):
 if mode.startswith('tent_'):
  code=rep(code,'    vector<Point> pool(const Features& f) {',HELPER+'    vector<Point> pool(const Features& f) {')
 if mode=='tent_envelope':
  code=rep(code,'            const double upper=max(value[a],value[b])+uncertainty+bend*gap*gap/4;',
   '            double upper=max(value[a],value[b])+uncertainty+bend*gap*gap/4;\n            if (auto tent=tentIntersection(f.x,i)) upper=max(upper,tent->second+uncertainty);')
 elif mode=='tent_pool':
  anchor='        if (!f.flat) for (size_t i=1;i<f.x.size();++i) {'
  code=rep(code,anchor,r"""
        for (size_t i=2;i+1<f.x.size();++i) if (auto tent=tentIntersection(f.x,i)) {
            if (tent->second+max(1.0,3*f.noise)<bestValue) continue;
            const int center=static_cast<int>(llround(tent->first));
            for (int x=center-1;x<=center+1;++x) add(x,110-abs(x-tent->first));
        }
"""+anchor)
 elif mode=='tent_probe':
  helper=r"""
    void pointedCompetitors() {
        const Features f=features();
        if (f.flat || best<0 || q>=QMAX-8) return;
        vector<pair<double,int>> ranked;
        for (size_t i=2;i+1<f.x.size();++i) if (auto tent=tentIntersection(f.x,i)) {
            if (tent->second+max(1.0,3*f.noise)<bestValue) continue;
            const int x=static_cast<int>(llround(tent->first));
            if (x>f.x[i-1] && x<f.x[i] && value[x]<0) ranked.push_back({tent->second,x});
        }
        sort(ranked.rbegin(),ranked.rend());
        const int budget=min(static_cast<int>(ceil(sqrt(QMAX-1-q))),QMAX-8-q);
        vector<int> plan;
        for (const auto& item:ranked) { if (static_cast<int>(plan.size())>=budget) break;plan.push_back(item.second); }
        plan=orient(move(plan),true);
        if (routeSafe(plan)) for (int x:plan) if (!sample(x) || certificate()) return;
    }
"""
  code=rep(code,'    void refine() {',helper+'    void refine() {\n        pointedCompetitors();')
 elif mode=='local_descent':
  anchor='        if (!(dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total)) return reject();'
  code=rep(code,anchor,r"""
        for (size_t i=1;i<xs.size();++i) if (xs[i-1]>=best && value[xs[i]]>value[xs[i-1]]) return reject();
"""+anchor)
 elif mode=='floor_return':
  anchor='        if (!(dominant && total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total)) return reject();'
  code=rep(code,anchor,'        if (value[xs.back()]>background+scatter) return reject();\n'+anchor)
 elif mode=='local_precision':
  code=rep(code,'    void refine() {',r"""
    void preciseWinnerCell() {
        if (best<0 || q>=QMAX-1) return;
        const vector<int> xs=observed();
        const auto at=lower_bound(xs.begin(),xs.end(),best);
        const int left=at==xs.begin() ? best : *prev(at);
        const int right=next(at)==xs.end() ? best : *next(at);
        vector<int> plan;
        for (int x=left+1;x<right;++x) if (value[x]<0) plan.push_back(x);
        if (q+static_cast<int>(plan.size())+8>QMAX) return;
        plan=orient(move(plan),true);
        if (routeSafe(plan)) for (int x:plan) if (!sample(x) || certificate()) return;
    }
    void refine() {
        preciseWinnerCell();
""")
 else:raise ValueError(mode)
 return code
