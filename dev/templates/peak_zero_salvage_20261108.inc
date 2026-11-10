
    void refine() {
        // A legal target must be >=rightmost-199. Parking must be within3.
        // Thus parking left of rightmost-202 is already certain to score zero,
        // independent of the unseen values. Keep searching feasible cells.
        constexpr int redundancyAllowance=199,parkingAllowance=3;
        const int earliestParking=max(0,rightmost-redundancyAllowance-parkingAllowance);
        if (!alive || best<0 || best>=earliestParking) { legacyRefine(); return; }
        const int available=max(0,QMAX-1-q);
        const int reserve=min(available/2,max(7,2*static_cast<int>(ceil(sqrt(available)))));
        vector<bool> scheduled(n,false);
        for (int x=earliestParking;x<=rightmost;++x) scheduled[x]=value[x]>=0;
        vector<int> plan;
        for (int count=0;count<available-reserve;++count) {
            int chosen=-1,largest=0;
            for (int x=earliestParking;x<=rightmost;) {
                if (scheduled[x]) { ++x; continue; }
                const int first=x;
                while (x<=rightmost && !scheduled[x]) ++x;
                const int width=x-first,midpoint=first+(width-1)/2;
                if (width>largest || (width==largest && chosen>=0 && tieBetter(midpoint,chosen))) {
                    largest=width;chosen=midpoint;
                }
            }
            if (chosen<0) break;
            scheduled[chosen]=true;plan.push_back(chosen);
        }
        // Split the largest unmeasured gaps, then sweep in one direction;
        // adaptive ping-pong between gaps would consume the turn allowance.
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return;
        for (int x:plan) if (!sample(x) || certificate()) return;
        if (alive && best>=earliestParking) { legacyRefine(); return; }
        // No superior feasible winner appeared; refining the old impossible
        // parking location cannot recover this case. Original finish still
        // parks at the observed raw winner through the protected ledger.
    }
