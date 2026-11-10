
        vector<pair<double,double>> levels;
        double mass=0,squareMass=0;
        for (size_t i=0;i<xs.size();++i) {
            const int left=i ? xs[i-1] : xs[i];
            const int right=i+1<xs.size() ? xs[i+1] : xs[i];
            const double weight=max(0.5,0.5*(right-left));
            levels.push_back({static_cast<double>(value[xs[i]]),weight});
            mass+=weight;squareMass+=weight*weight;
        }
        auto weightedMedian=[](vector<pair<double,double>> data) {
            sort(data.begin(),data.end());
            double totalWeight=0,cumulative=0;
            for (const auto& entry:data) totalWeight+=entry.second;
            for (const auto& entry:data) {
                cumulative+=entry.second;
                if (2*cumulative>=totalWeight) return entry.first;
            }
            return data.back().first;
        };
        const double background=weightedMedian(levels);
        for (auto& entry:levels) entry.first=abs(entry.first-background);
        const double scatter=max(1.0,1.4826*weightedMedian(levels));
        const double effective=mass*mass/max(1e-12,squareMass);
        const bool dominant=bestValue-background>scatter*sqrt(2*log(2.0+effective));
