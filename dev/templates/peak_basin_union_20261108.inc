
    void completeCompetitors() {
        if (!alive || best<0 || q>=QMAX-1 || certificate()) return;
        const Features f=features();
        if (f.flat || f.x.size()<4) { legacyCompetitors(); return; }
        struct Cell { int left,right; double upper; };
        vector<Cell> cells;
        const double uncertainty=max(1.0,f.noise)*sqrt(2*log(2.0+f.x.size()));
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1],b=f.x[i],gap=b-a;
            if (gap<=1) continue;
            const double chord=static_cast<double>(value[b]-value[a])/gap;
            double bend=0;
            if (i>=2) {
                const int before=f.x[i-2];
                const double slope=static_cast<double>(value[a]-value[before])/(a-before);
                bend=max(bend,abs(chord-slope)/(b-before));
            }
            if (i+1<f.x.size()) {
                const int after=f.x[i+1];
                const double slope=static_cast<double>(value[after]-value[b])/(after-b);
                bend=max(bend,abs(slope-chord)/(after-a));
            }
            // A heuristic interpolation envelope, never a proof of exclusion.
            const double upper=max(value[a],value[b])+uncertainty+bend*gap*gap/4;
            if (upper>=bestValue-uncertainty) cells.push_back({a,b,upper});
        }
        sort(cells.begin(),cells.end(),[&](const Cell& a,const Cell& b) {
            if (a.upper!=b.upper) return a.upper>b.upper;
            return abs((a.left+a.right)/2-best)<abs((b.left+b.right)/2-best);
        });
        const int reserve=max(7,static_cast<int>(ceil(log2(2.0+n))));
        const int budget=max(0,QMAX-1-q-reserve);
        vector<int> plan;
        for (const Cell& cell:cells) {
            if (static_cast<int>(plan.size())+cell.right-cell.left-1>budget) continue;
            for (int x=cell.left+1;x<cell.right;++x) if (value[x]<0) plan.push_back(x);
        }
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return;
        for (int x:plan) if (!sample(x) || certificate()) return;
    }
