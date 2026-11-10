
    bool recoverOpenBoundary() {
        bool advanced=false;
        while (alive && best==rightmost && rightmost<n-1 && q<QMAX-1 && seconds()<7.0) {
            const int available=QMAX-1-q;
            const int reserve=min(available/2,max(7,2*static_cast<int>(ceil(sqrt(available)))));
            const int reads=max(1,available-reserve);
            const int cover=max(1,(n-1-rightmost+reads-1)/reads);
            // Even if the old legal target was3positions left of the winner,
            // a single probe no farther than199-3 cannot itself overrun it.
            const int step=min(199-3,cover);
            const int target=min(n-1,rightmost+step);
            if (!sample(target)) break;
            advanced=true;
            if (certificate()) break;
        }
        return advanced;
    }
    void refine() {
        recoverOpenBoundary();
        localRefine();
        if (best==rightmost && rightmost<n-1 && recoverOpenBoundary()) localRefine();
    }
