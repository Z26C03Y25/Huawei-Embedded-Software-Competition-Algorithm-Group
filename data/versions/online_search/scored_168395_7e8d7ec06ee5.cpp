#include <bits/stdc++.h>
using namespace std;
namespace tour_search {
constexpr long long TOP=2147483647LL;
constexpr int QLIMIT=199,TLIMIT=6;
double med(vector<double> x) {
    if (x.empty()) return 0;
    const size_t k=x.size()/2;
    nth_element(x.begin(),x.begin()+static_cast<ptrdiff_t>(k),x.end());
    return x.size()%2 ? x[k] : (x[k]+*max_element(x.begin(),x.begin()+static_cast<ptrdiff_t>(k)))/2;
}
struct Motion { int pos=0,dir=0,turns=0; long long travel=0; };
void moveTo(Motion& m,int x) {
    const int d=(x>m.pos)-(x<m.pos);
    if (d) { if (m.dir && d!=m.dir) ++m.turns; m.dir=d; }
    m.travel+=abs(x-m.pos); m.pos=x;
}
struct Cell { int lo,hi,target; double weight; };
class Solver {
    int n,q=0,best=-1,right=0,stride;
    long long high=-1;
    vector<long long> y;
    Motion motor;
    bool alive=true,trace=false,strict=false,lateFlat=false;
    double noise=0,contrast=0,floorValue=0;
    chrono::steady_clock::time_point started=chrono::steady_clock::now();
    double seconds() const { return chrono::duration<double>(chrono::steady_clock::now()-started).count(); }
    bool preferred(int a,int b) const {
        if (b<0) return true;
        return pair<int,int>{abs(2*a-(n-1)),a}<pair<int,int>{abs(2*b-(n-1)),b};
    }
    int certifiedLower() const {
        int lower=best<0 ? 0 : best;
        for (int x=0;x<n;++x) if (y[x]<0 && (high<TOP || preferred(x,best))) lower=min(lower,x);
        return lower;
    }
    bool proven() const {
        if (high!=TOP) return false;
        for (int x=0;x<n;++x) if (y[x]<0 && preferred(x,best)) return false;
        return true;
    }
    bool legal(int x,bool terminal=false) const {
        if (!alive || x<0 || x>=n || q+1+(terminal?0:1)>QLIMIT) return false;
        if (!terminal && seconds()>8.0) return false;
        Motion m=motor; moveTo(m,x);
        if (!terminal && best>=0) moveTo(m,best);
        return m.turns<=TLIMIT && (!strict || max(right,x)<=certifiedLower()+199);
    }
    bool read(int x,bool terminal=false) {
        if (!legal(x,terminal)) return false;
        cout<<x<<'\n'<<flush; ++q; moveTo(motor,x); right=max(right,x);
        long long v;
        if (!(cin>>v) || v<0 || v>TOP) { alive=false; return false; }
        y[x]=v;
        if (v>high || (v==high && preferred(x,best))) { best=x; high=v; }
        return true;
    }
    bool sample(int x) { return y[x]>=0 ? true : read(x); }
    vector<int> points() const {
        vector<int> xs;
        for (int x=0;x<n;++x) if (y[x]>=0) xs.push_back(x);
        return xs;
    }
    void estimateNoise() {
        const vector<int> xs=points();
        vector<double> residual;
        floorValue=static_cast<double>(high);
        for (int x:xs) floorValue=min(floorValue,static_cast<double>(y[x]));
        contrast=high-floorValue;
        for (size_t i=1;i+1<xs.size();++i) {
            const int a=xs[i-1],x=xs[i],b=xs[i+1];
            const double t=static_cast<double>(x-a)/(b-a);
            residual.push_back(y[x]-(y[a]+t*(y[b]-y[a])));
        }
        const double center=med(residual);
        for (double& r:residual) r=abs(r-center);
        noise=1.4826*med(residual)/1.2247448714;
    }
    void scout() {
        if (!sample(0)) return;
        int evidenceBest=best;
        double evidence=0;
        while (q<96 && right<n-1 && seconds()<6.8 && !proven()) {
            estimateNoise();
            int limit=n-1;
            if (strict || high==TOP) limit=min(limit,certifiedLower()+199);
            else if (contrast>max(4.0,10*noise)) limit=min(limit,best+180);
            if (contrast==0 && !lateFlat) limit=min(limit,(n-1)/2+120);
            if (right>=limit) break;
            if (best!=evidenceBest) { evidenceBest=best; evidence=0; }
            if (right-best>=2*stride && contrast>max(4.0,10*noise)) {
                const double prior=noise<0.005*contrast ? 0.90 : (noise<0.02*contrast ? 0.75 : 0.50);
                const double odds=log(prior/(1-prior))+evidence;
                const double onePeak=1/(1+exp(-clamp(odds,-20.0,20.0)));
                const double unvisited=static_cast<double>(n-1-right)/max(1,n-1-best);
                const double futureValue=(1-onePeak)*unvisited*max(0.0,3000.0-q-motor.travel);
                if (futureValue<1+3*stride) break;
            }
            int next=min(limit,right+stride);
            const int center=(n-1)/2;
            if (contrast==0 && right<center && next>center) next=center;
            if (next<=right) break;
            const long long previous=y[right];
            if (!sample(next)) break;
            const double delta=static_cast<double>(y[next]-previous);
            const double significant=max(1.0,max(noise,0.01*contrast));
            if (delta<-significant) evidence+=log(0.90/0.50);
            else if (delta>significant) evidence+=log(0.10/0.50);
        }
        estimateNoise();
    }
    vector<Cell> beliefs() const {
        const vector<int> xs=points();
        vector<Cell> cells;
        for (size_t i=1;i<xs.size();++i) {
            const int a=xs[i-1],b=xs[i],h=b-a;
            if (h<=1) continue;
            const double sec=static_cast<double>(y[b]-y[a])/h;
            double da=sec,db=sec;
            if (i>=2) {
                const int p=xs[i-2];
                const double previous=static_cast<double>(y[a]-y[p])/(a-p);
                da=previous+(sec-previous)*static_cast<double>(a-p)/(b-p);
            }
            if (i+1<xs.size()) {
                const int c=xs[i+1];
                const double next=static_cast<double>(y[c]-y[b])/(c-b);
                db=sec+(next-sec)*static_cast<double>(b-a)/(c-a);
            }
            double upper=-1;
            int target=(a+b)/2;
            for (int j=1;j<8;++j) {
                const double t=j/8.0,t2=t*t,t3=t2*t;
                const double predicted=(2*t3-3*t2+1)*y[a]+(t3-2*t2+t)*h*da+
                                       (-2*t3+3*t2)*y[b]+(t3-t2)*h*db;
                if (predicted>upper) { upper=predicted; target=clamp(a+static_cast<int>(llround(t*h)),a+1,b-1); }
            }
            if (high==TOP) {
                bool canImprove=false;
                for (int x=a+1;x<b;++x) if (preferred(x,best)) canImprove=true;
                if (!canImprove) continue;
            }
            const double sigma=max(1.0,max(noise,0.005*contrast))*sqrt(static_cast<double>(h)/stride);
            const double weight=exp(clamp((upper-high)/sigma,-24.0,4.0))*sqrt(h-1.0)+0.02*(h-1)/n;
            cells.push_back({a,b,target,weight});
        }
        return cells;
    }
    double terminalScore(Motion m,int extra,int t) const {
        int parking=0;
        if (m.pos!=t) { moveTo(m,t); parking=1; }
        const int redundant=max(0,right-t);
        if (q+extra+parking>QLIMIT || m.turns>TLIMIT || redundant>199) return 0;
        return max(0.0,3000.0-q-extra-parking-m.travel-m.turns-redundant);
    }
    bool safePath(const vector<int>& path) const {
        if (q+static_cast<int>(path.size())+1>QLIMIT) return false;
        Motion m=motor;
        for (int x:path) moveTo(m,x);
        return m.turns+1<=TLIMIT;
    }
    void refine() {
        for (int pass=0;pass<2 && q<QLIMIT-1 && seconds()<7.5 && !proven();++pass) {
            const vector<Cell> cells=beliefs();
            if (cells.empty()) break;
            const int avail=QLIMIT-1-q;
            const int budget=pass ? avail : max(1,avail-max(12,avail/3));
            double totalWeight=1;
            for (const Cell& c:cells) totalWeight+=c.weight;
            double bestUtility=terminalScore(motor,0,best)/totalWeight;
            vector<int> winner;
            for (size_t first=0;first<cells.size();++first) {
                vector<int> pointsToRead;
                for (size_t last=first;last<cells.size();++last) {
                    for (int x=cells[last].lo+1;x<cells[last].hi;++x) pointsToRead.push_back(x);
                    if (static_cast<int>(pointsToRead.size())>budget) break;
                    for (int reverseOrder=0;reverseOrder<2;++reverseOrder) {
                        vector<int> route=pointsToRead;
                        if (reverseOrder) reverse(route.begin(),route.end());
                        if (!safePath(route)) continue;
                        Motion end=motor;
                        for (int x:route) moveTo(end,x);
                        const int reads=static_cast<int>(route.size());
                        double utility=terminalScore(end,reads,best);
                        for (size_t k=first;k<=last;++k)
                            utility+=cells[k].weight*terminalScore(end,reads,cells[k].target);
                        utility/=totalWeight;
                        if (utility>bestUtility) { bestUtility=utility; winner=move(route); }
                    }
                }
            }
            if (winner.empty()) break;
            for (int x:winner) if (!sample(x) || proven()) return;
        }
    }
public:
    Solver(int length,bool diagnostics,bool certified,bool late):n(length),stride(clamp((length+87)/88,4,12)),
        y(length,-1),trace(diagnostics),strict(certified),lateFlat(late) {}
    void run() {
        if (n<=198) { for (int x=0;x<n;++x) if (!sample(x)) break; }
        else { scout(); if (alive) refine(); }
        if (alive && best>=0 && motor.pos!=best) read(best,true);
        cout<<"DONE\n"<<flush;
        if (trace) cerr<<"TRACE {\"queries\":"<<q<<",\"travel\":"<<motor.travel
            <<",\"oscillations\":"<<motor.turns<<",\"rightmost\":"<<right
            <<",\"position\":"<<motor.pos<<",\"best\":"<<best<<"}\n";
    }
};
}
int main(int argc,char** argv) {
    ios::sync_with_stdio(false); cin.tie(nullptr);
    bool trace=false,strict=false,late=false;
    for (int i=1;i<argc;++i) {
        const string a=argv[i];
        trace|=a=="--trace"; strict|=a=="--strict-redundancy"; late|=a=="--late-flat";
    }
    int n;
    if (!(cin>>n) || n<=0 || n>1000) return 0;
    tour_search::Solver(n,trace,strict,late).run();
}
