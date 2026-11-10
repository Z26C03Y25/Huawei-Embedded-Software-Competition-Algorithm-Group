
    int challengedPeak=-1;
    bool marginalPeak(const Features& f) {
        if (best<0 || challengedPeak==best || !observedPeakEvidence()) return false;
        vector<double> levels;
        for (int x:f.x) levels.push_back(value[x]);
        const double background=median(levels),spread=max(1.0,mad(levels));
        return bestValue-background<=spread*sqrt(static_cast<double>(f.x.size()));
    }
