
    optional<int> coarseShoulderSentinel(const Features& f) const {
        if (strict || !f.significant || f.flat || f.plateau || best<0 ||
            best>=(n-1)/2 || sentinelForBest==best || q>=QMAX-30 || f.x.size()<9) return nullopt;
        const size_t first=f.x.size()-9;
        array<double,3> level{},location{};
        for (size_t block=0;block<3;++block) {
            array<long long,3> values{};
            for (size_t j=0;j<3;++j) values[j]=value[f.x[first+3*block+j]];
            sort(values.begin(),values.end());level[block]=static_cast<double>(values[1]);
            location[block]=f.x[first+3*block+1];
        }
        if (location[0]<=best) return nullopt;
        const double firstSlope=(level[1]-level[0])/(location[1]-location[0]);
        const double lastSlope=(level[2]-level[1])/(location[2]-location[1]);
        const double acceleration=(lastSlope-firstSlope)/(0.5*(location[2]-location[0]));
        const double span=location[2]-location[0];
        if (firstSlope>=0 || lastSlope>=0 || acceleration<=max(1.0,f.noise)/(span*span)) return nullopt;
        const int cap=min(n-1,best+199);
        const double toValley=-lastSlope/acceleration;
        if (toValley>=cap-rightmost) return nullopt;
        const int extension=static_cast<int>(ceil(toValley+max(1.0,f.halfRight)));
        const int target=min(cap,rightmost+extension);
        if (target<=rightmost+max(1,f.maxGap)) return nullopt;
        return target;
    }
