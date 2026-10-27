// OptimalFocus v2: independent autofocus solver.
// Large adaptive coarse step (cheap queries) + parabola refinement, with a
// conservative redundancy frontier for flat regions and a bounded rebound scout.
#include <bits/stdc++.h>
using namespace std;

namespace of {

constexpr long long VMAX = 2147483647LL;
constexpr int QMAX = 199, OMAX = 6;

class Solver {
    int n, q=0, pos=0, dir=0, turns=0, rightmost=0, best=-1;
    long long travel=0, bestValue=-1;
    vector<long long> value;
    bool alive=true, foundSig=false;

    void moveTo(int x){
        int d=(x>pos)-(x<pos);
        if(d){ if(dir && d!=dir) ++turns; dir=d; }
        travel += abs(x-pos); pos=x;
    }
    bool tieBetter(int a,int b) const {
        if(b<0) return true;
        int da=abs(2*a-(n-1)), db=abs(2*b-(n-1));
        return da!=db ? da<db : a<b;
    }
    bool better(int a,long long va,int b,long long vb) const {
        return va!=vb ? va>vb : tieBetter(a,b);
    }
    bool routeOK(int x,bool terminal){
        if(!alive || x<0 || x>=n || q+1+(terminal?0:1)>QMAX) return false;
        int p=pos,d=dir,o=turns; long long m=travel;
        auto step=[&](int t){ int dd=(t>p)-(t<p); if(dd){ if(d&&dd!=d) o++; d=dd; } m+=abs(t-p); p=t; };
        step(x);
        if(!terminal && best>=0) step(best);
        return o<=OMAX;
    }
    bool query(int x,bool terminal=false){
        if(!routeOK(x,terminal)) return false;
        cout<<x<<'\n'<<flush;
        long long a;
        if(!(cin>>a) || a<0 || a>VMAX){ alive=false; return false; }
        moveTo(x); ++q; rightmost=max(rightmost,x); value[x]=a;
        if(better(x,a,best,bestValue)){ best=x; bestValue=a; }
        return true;
    }
    bool readAt(int x){ if(x<0||x>=n) return false; if(value[x]>=0) return true; return query(x); }
    vector<int> observed(){ vector<int> xs; for(int x=0;x<n;x++) if(value[x]>=0) xs.push_back(x); return xs; }
    static double median(vector<double> a){
        if(a.empty()) return 0;
        size_t m=a.size()/2;
        nth_element(a.begin(), a.begin()+m, a.end());
        double hi=a[m];
        return a.size()%2 ? hi : (hi+*max_element(a.begin(),a.begin()+m))/2.0;
    }
    double noise(){
        auto xs=observed();
        if(xs.size()<3) return 1.0;
        vector<double> resid;
        for(size_t i=1;i+1<xs.size();i++){
            int a=xs[i-1], b=xs[i], c=xs[i+1];
            double t=(double)(b-a)/(c-a);
            double pred=value[a]+t*(value[c]-value[a]);
            resid.push_back((double)value[b]-pred);
        }
        vector<double> absr;
        for(double r:resid) absr.push_back(abs(r));
        if(absr.empty()) return 1.0;
        return max(1.0, 1.4826*median(absr));
    }
    long long floorValue(){
        auto xs=observed(); if(xs.empty()) return 0;
        long long f=value[xs[0]];
        for(int x:xs) f=min(f,value[x]);
        return f;
    }
    double vertexAt(int a,int b,int c){
        if(!(a<b && b<c)) return -1;
        double sl=(double)(value[b]-value[a])/(b-a);
        double sr=(double)(value[c]-value[b])/(c-b);
        double curv=(sr-sl)/(c-a);
        if(curv>=-1e-12) return -1;
        double at=(a+b)/2.0 - sl/(2*curv);
        if(!isfinite(at) || at<a || at>c) return -1;
        return at;
    }
    void refine(){
        if(best<0) return;
        if(!foundSig){
            // Flat / no significant peak: the tie rule pins the target at the midpoint.
            int mid=(n-1)/2;
            for(int x=min(rightmost,mid+3); x>=max(0,mid-3); --x)
                if(x>=0 && x<=rightmost && value[x]<0) if(!readAt(x)) return;
            return;
        }

        auto xs=observed();
        int idx=-1; for(size_t i=0;i<xs.size();i++) if(xs[i]==best){ idx=(int)i; break; }
        double v=-1;
        if(idx>0 && idx+1<(int)xs.size()) v=vertexAt(xs[idx-1], xs[idx], xs[idx+1]);
        int center=best;
        if(v>0) center=max(0,min(n-1,(int)llround(v)));
        const int R=4;
        vector<int> probe;
        for(int x=center-R;x<=center+R;x++)
            if(x>=0 && x<=rightmost && value[x]<0) probe.push_back(x);
        for(int x:probe){ if(!readAt(x)) break; }
    }
    void finish(){
        if(alive && best>=0 && pos!=best) query(best,true);
        cout<<"DONE\n"<<flush;
    }

public:
    Solver(int length):n(length),value(length,-1){}
    void run(){
        if(n<=198){ for(int x=0;x<n;x++) if(!query(x)) break; finish(); return; }
        for(int x:{0,4,12,24}){ if(x>=n || !query(x)) break; }
        int step=16;
        int flatRuns=0;
        bool scouting=false; int scoutLeft=0;
        const int mid=(n-1)/2;
        while(alive && q<150 && rightmost<n-1){
            auto xs=observed();
            double nz=noise();
            long long fl=floorValue();
            long long contrast=bestValue-fl;
            bool significant = contrast > max(4.0, 24.0*nz);
            if(significant) foundSig=true;
            // redundancy frontier
            int frontier=n-1;
            if(!significant){
                frontier=min(n-1, mid+144);
            } else {
                // high-region left edge
                double tol=max(1.0, 3*nz+0.04*contrast);
                int peakLeft=best;
                for(int x:xs) if(value[x]>=bestValue-tol) peakLeft=min(peakLeft,x);
                frontier=min(n-1, peakLeft+180);
            }
            if(rightmost>=frontier) break;
            int next=min((long long)n-1, (long long)rightmost+step);
            next=min(next, frontier);
            if(next<=rightmost) break;
            if(!query(next)) break;
            // trend + step adaptation
            bool flat=false, rising=false;
            if(xs.size()>=1){
                double diff=(double)(value[next]-value[xs.back()]);
                if(abs(diff)<max(2.0,1.5*nz)) flat=true;
                else if(diff>0) rising=true;
            }
            // peak passed + rebound scout
            double dropTh=max(4.0,3.0*nz);
            bool passed = significant && best>=0 && next>best && value[next] < bestValue - dropTh;
            if(passed){
                if(!scouting){ scouting=true; scoutLeft=96; }
                else if(scoutLeft>0){ scoutLeft--; }
                if(scoutLeft<=0) break;
            } else {
                scouting=false; scoutLeft=0;
            }
            // adaptive step
            if(flat){ flatRuns++; step = flatRuns>=4 ? 32 : 24; }
            else { flatRuns=0; step=8; }
        }
        refine();
        finish();
    }
};
} // namespace of

int main(){
    ios::sync_with_stdio(false); cin.tie(nullptr);
    int n;
    if(!(cin>>n) || n<=0 || n>1000) return 0;
    of::Solver(n).run();
    return 0;
}
