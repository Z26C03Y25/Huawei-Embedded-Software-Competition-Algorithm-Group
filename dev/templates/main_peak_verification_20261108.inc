
    bool observedPeakEvidence() {
        const vector<int> xs=observed();
        if (best<0 || xs.size()<5) return false;
        vector<double> levels;
        for (int x:xs) levels.push_back(value[x]);
        const double background=median(levels);
        const double scatter=max(1.0,mad(levels));
        if (bestValue-background>scatter*sqrt(2*log(2.0+xs.size()))) return true;
        auto at=lower_bound(xs.begin(),xs.end(),best);
        if (at==xs.end()) return false;
        const int index=static_cast<int>(at-xs.begin());
        const int lo=max(0,index-3),hi=min(static_cast<int>(xs.size())-1,index+3);
        if (hi-lo+1<5) return false;
        const double radius=max(1,max(best-xs[lo],xs[hi]-best));
        double matrix[3][4]{};
        for (int i=lo;i<=hi;++i) {
            const double t=(xs[i]-best)/radius,y=value[xs[i]]-bestValue;
            const double basis[]={1,t,t*t};
            for (int r=0;r<3;++r) {
                for (int c=0;c<3;++c) matrix[r][c]+=basis[r]*basis[c];
                matrix[r][3]+=basis[r]*y;
            }
        }
        for (int c=0;c<3;++c) {
            int pivot=c;
            for (int r=c+1;r<3;++r) if (abs(matrix[r][c])>abs(matrix[pivot][c])) pivot=r;
            if (abs(matrix[pivot][c])<1e-12) return false;
            for (int j=c;j<4;++j) swap(matrix[c][j],matrix[pivot][j]);
            const double scale=matrix[c][c];
            for (int j=c;j<4;++j) matrix[c][j]/=scale;
            for (int r=0;r<3;++r) if (r!=c) {
                const double factor=matrix[r][c];
                for (int j=c;j<4;++j) matrix[r][j]-=factor*matrix[c][j];
            }
        }
        const double constant=matrix[0][3],linear=matrix[1][3],quadratic=matrix[2][3];
        if (quadratic>=-1e-12) return false;
        const double vertexPosition=best-radius*linear/(2*quadratic);
        const bool inside=vertexPosition>=xs[lo] && vertexPosition<=xs[hi];
        const bool physicalEdge=(best==0 && vertexPosition<=0) || (best==n-1 && vertexPosition>=n-1);
        if (!inside && !physicalEdge) return false;
        double mean=0,error=0,total=0;
        for (int i=lo;i<=hi;++i) mean+=value[xs[i]]-bestValue;
        mean/=hi-lo+1;
        for (int i=lo;i<=hi;++i) {
            const double t=(xs[i]-best)/radius,y=value[xs[i]]-bestValue;
            const double residual=y-(constant+linear*t+quadratic*t*t);
            error+=residual*residual;total+=(y-mean)*(y-mean);
        }
        return total>1 && error*sqrt(static_cast<double>(hi-lo+1))<total;
    }

    void verifyWinningCell() {
        if (!alive || best<0 || q>=QMAX-1 || certificate()) return;
        vector<int> xs=observed();
        auto at=lower_bound(xs.begin(),xs.end(),best);
        if (at==xs.end()) return;
        // A fine window ending on an improving boundary is unresolved.
        if (best==rightmost && rightmost<n-1) {
            int leftAnchor=at==xs.begin() ? best : *prev(at);
            const int lease=max(1,static_cast<int>(sqrt(QMAX-1-q)));
            for (int reads=0;reads<lease && best==rightmost && q<QMAX-8;++reads) {
                const int cap=min(n-1,leftAnchor+199);
                if (rightmost>=cap) break;
                const int step=max(1,(cap-rightmost+lease-reads-1)/(lease-reads));
                const int prior=rightmost;
                if (!sample(min(cap,rightmost+step))) break;
                if (best==rightmost) leftAnchor=prior;
                if (certificate()) return;
            }
            xs=observed();at=lower_bound(xs.begin(),xs.end(),best);
            if (at==xs.end()) return;
        }
        const int left=at==xs.begin() ? max(0,best-3) : *prev(at);
        const int right=next(at)==xs.end() ? min(rightmost,best+3) : *next(at);
        vector<int> plan;
        for (int x=left+1;x<right;++x) if (value[x]<0) plan.push_back(x);
        const int available=QMAX-1-q;
        if (static_cast<int>(plan.size())>available) {
            sort(plan.begin(),plan.end(),[&](int a,int b){return abs(a-best)<abs(b-best);});
            plan.resize(available);
        }
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return;
        for (int x:plan) if (!sample(x) || certificate()) return;
    }

    void auditUnconfirmedPeak() {
        if (!alive || best<0 || q>=QMAX-1 || certificate()) return;
        const Features initial=features();
        const long long startingValue=bestValue;
        const double recordMargin=max(1.0,initial.noise);
        const int reserve=max(7,2*max(1,initial.maxGap));
        const int available=max(0,QMAX-1-q-reserve);
        if (available==0) return;
        vector<int> midpoint;
        for (size_t i=1;i<initial.x.size();++i) {
            const int a=initial.x[i-1],b=initial.x[i];
            if (b-a>1) midpoint.push_back(a+(b-a)/2);
        }
        if (midpoint.empty()) return;
        // Every unresolved gap participates; endpoint height does not suppress
        // a cell that might contain a narrow peak between background samples.
        vector<int> plan;
        if (static_cast<int>(midpoint.size())<=available) plan=midpoint;
        else for (int i=0;i<available;++i) {
            const size_t index=available==1 ? midpoint.size()/2 :
                static_cast<size_t>(i)*(midpoint.size()-1)/(available-1);
            plan.push_back(midpoint[index]);
        }
        plan=orient(move(plan),true);
        if (!routeSafe(plan)) return;
        for (int x:plan) {
            if (!sample(x)) return;
            if (certificate()) return;
            if (!__EXHAUST_AUDIT__ && (bestValue>startingValue+recordMargin ||
                (bestValue>startingValue && observedPeakEvidence()))) break;
        }
    }

    void refine() {
        const bool evidence=observedPeakEvidence();
        if (!evidence) auditUnconfirmedPeak();
        if (__VERIFY_STRONG__ || !evidence) verifyWinningCell();
        if (alive) legacyRefine();
    }
