#include <bits/stdc++.h>
using namespace std;

namespace af_super {
constexpr long long VMAX = 2147483647LL;
constexpr int QMAX = 199, OMAX = 6;
constexpr int ENSEMBLE_CNT = 12;

#define OPS(X) \
 X(A01) X(A02) X(A03) X(A04) X(A05) X(A06) X(A07) X(A08) \
 X(B01) X(B02) X(B03) X(B04) X(B05) X(B06) X(B07) X(B08) \
 X(C01) X(C02) X(C03) X(C04) X(C05) X(C06) X(C07) X(C08) \
 X(D01) X(D02) X(D03) X(D04) X(D05) X(D06) X(D07) X(D08) \
 X(E01) X(E02) X(E03) X(E04) X(E05) X(E06) X(E07) X(E08) \
 X(F01) X(F02) X(F03) X(F04) X(F05) X(F06) X(F07) X(F08) \
 X(G01) X(G02) X(G03) X(G04) X(G05) X(G06) X(G07) X(G08) \
 X(H01) X(H02) X(H03) X(H04) X(H05) X(H06) X(H07) X(H08) \
 X(I01) X(I02) X(I03) X(I04) X(I05) X(I06) X(I07) X(I08) \
 X(J01) X(J02) X(J03) X(J04) X(J05) X(J06) X(J07) X(J08) \
 X(K01) X(K02) X(K03) X(K04) X(K05) X(K06) X(K07) X(K08) \
 X(L01) X(L02) X(L03) X(L04) X(L05) X(L06) X(L07) X(L08) \
 X(S01) X(S02) X(S03) X(S04) X(S05) X(S06) X(S07) X(S08)

enum class Op {
#define ENUM(x) x,
    OPS(ENUM)
#undef ENUM
    Count
};
const char* const opNames[] = {
#define NAME(x) #x,
    OPS(NAME)
#undef NAME
};
#undef OPS

enum class Shape { Flat, Rising, Falling, Smooth, Broad, Multi, Rough };
const char* const shapeNames[] = {"flat","rising","falling","smooth","broad","multi","rough"};

enum CertLevel { CERT_NONE, CERT_WEAK, CERT_STRONG };

int signum(int x) { return (x > 0) - (x < 0); }

double median(vector<double> a) {
    if (a.empty()) return 0;
    size_t m = a.size()/2;
    nth_element(a.begin(), a.begin()+static_cast<ptrdiff_t>(m), a.end());
    double hi = a[m];
    return a.size()%2 ? hi : (hi+*max_element(a.begin(),a.begin()+static_cast<ptrdiff_t>(m)))/2;
}

double mad(const vector<double>& a) {
    const double m = median(a);
    vector<double> d;
    for(double x:a) d.push_back(fabs(x-m));
    return 1.4826*median(d);
}

struct Features {
    vector<int> x, peaks;
    vector<double> slopes;
    double floor=0, contrast=0, noise=0, tolerance=1, halfLeft=0, halfRight=0, curvature=0;
    double prominence=0, baselineSlope=0;
    int left=0, right=0, plateauLeft=0, plateauRight=0, maxGap=0, rises=0, falls=0, equalSteps=0;
    bool flat=true, significant=false, rebound=false, leftEdge=false, plateau=false, noisy=false;
    vector<int> transientSpikes;
    Shape shape=Shape::Flat;
};

struct Point { int x; double priority; int cluster; bool isTransientSpike; };

struct Scenario {
    vector<long long> value;
    int target=0;
    enum DisturbType {NOISE, MOTION_JUMP, BIMODAL, PLATEAU} type;
};

struct PlanRisk {
    int delta_osc;
    int delta_step;
    int est_redundant_inc;
    bool hard_violate;
};

struct Solver {
    int n, q=0, pos=0, direction=0, turns=0, rightmost=0, best=-1, coarseFrontier=0;
    long long travel=0, bestValue=-1;
    vector<long long> value;
    array<int,static_cast<size_t>(Op::Count)> uses{};
    array<int,7> visits{};
    bool trace, strict, lateFlat, alive=true, oldPeakRisk=false;
    Shape state=Shape::Flat, pending=Shape::Flat;
    int votes=0;
    uint64_t rng=0x9e3779b97f4a7c15ULL;
    chrono::steady_clock::time_point started=chrono::steady_clock::now();
    CertLevel certLevel = CERT_NONE;

    void use(Op op) { ++uses[static_cast<size_t>(op)]; }

    double seconds() const {
        return chrono::duration<double>(chrono::steady_clock::now()-started).count();
    }

    uint64_t random64() { rng^=rng<<13; rng^=rng>>7; rng^=rng<<17; return rng; }
    int randomInt(int count) { return static_cast<int>(random64()%static_cast<uint64_t>(count)); }

    bool tieBetter(int a,int b) const {
        if (b<0) return true;
        int da=abs(2*a-(n-1)), db=abs(2*b-(n-1));
        return da!=db ? da<db : a<b;
    }

    bool better(int a,long long va,int b,long long vb) const {
        return va!=vb ? va>vb : tieBetter(a,b);
    }

    static void moveTo(int x,int& p,int& dir,int& o,long long& m) {
        int d=signum(x-p);
        if (d) { if (dir && d!=dir) ++o; dir=d; }
        m+=abs(x-p); p=x;
    }

    int certifiedLeft() const {
        int left=best<0 ? 0 : best;
        for(int x=0;x<n;++x)
            if(value[x]<0 && (bestValue<VMAX || tieBetter(x,best))) left=min(left,x);
        return left;
    }

    bool certificateStrong() {
        if(bestValue!=VMAX) return false;
        use(Op::D07);
        for(int x=0;x<n;++x) if(value[x]<0 && tieBetter(x,best)) return false;
        certLevel = CERT_STRONG;
        return true;
    }

    bool certificateWeak(const Features& f) {
        if(best<0) return false;
        bool ok=true;
        for(int x=0;x<n;++x){
            if(value[x]>=0) continue;
            double upperBoundEst = f.noisy ? bestValue : bestValue + 2.5*f.noise;
            if(upperBoundEst >= bestValue && tieBetter(x,best)) { ok=false; break; }
        }
        if(ok) certLevel=CERT_WEAK;
        return ok;
    }

    bool canRead(int x,bool terminal) {
        use(Op::I01); use(Op::I02); use(Op::I03);
        if (!alive || x<0 || x>=n || q+1+(terminal?0:1)>QMAX) return false;
        if (!terminal && seconds()>8.0) { use(Op::I07); return false; }
        int p=pos,d=direction,o=turns; long long m=travel;
        moveTo(x,p,d,o,m);
        if (!terminal && best>=0) moveTo(best,p,d,o,m);
        if (o>OMAX) return false;
        use(Op::I04);
        return !strict || max(rightmost,x)<=certifiedLeft()+199;
    }

    bool readReal(int x,bool terminal=false) {
        if (!canRead(x,terminal)) return false;
        cout<<x<<'\n'<<flush;
        long long answer;
        if (!(cin>>answer) || answer<0 || answer>VMAX) { alive=false; return false; }
        moveTo(x,pos,direction,turns,travel);
        ++q; rightmost=max(rightmost,x); value[x]=answer;
        if (better(x,answer,best,bestValue)) {
            if (best>=0 && x>best && answer>bestValue) use(Op::F08);
            best=x; bestValue=answer;
        }
        rng^=static_cast<uint64_t>(answer)+static_cast<uint64_t>(x+1)*1000003ULL;
        use(Op::I08);
        oldPeakRisk=best>=0 && best<rightmost-199;
        if (oldPeakRisk) use(Op::K08);
        return true;
    }

    bool sample(int x) {
        if (x<0 || x>=n) return false;
        if (value[x]>=0) { use(Op::I06); return true; }
        return readReal(x);
    }

    vector<int> observed() const {
        vector<int> xs;
        for(int x=0;x<n;++x) if(value[x]>=0) xs.push_back(x);
        return xs;
    }

    Features features() {
        Features f; f.x=observed();
        if(f.x.empty()) return f;
        use(Op::A01); use(Op::A02); use(Op::A03); use(Op::A07); use(Op::A08);
        f.floor=static_cast<double>(value[f.x.front()]);
        vector<double> residual;
        for(size_t i=0;i<f.x.size();++i) {
            int x=f.x[i];
            f.floor=min(f.floor,static_cast<double>(value[x]));
            if(i) {
                int h=x-f.x[i-1]; f.maxGap=max(f.maxGap,h);
                f.slopes.push_back(static_cast<double>(value[x]-value[f.x[i-1]])/h);
                if(value[x]==value[f.x[i-1]]) ++f.equalSteps;
            }
            if(i && i+1<f.x.size()) {
                int a=f.x[i-1], b=f.x[i+1];
                double t=static_cast<double>(x-a)/(b-a);
                residual.push_back(value[x]-(value[a]+t*(value[b]-value[a])));
            }
        }
        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;
        vector<double> local;
        if(!residual.empty()) {
            size_t start=residual.size()>18 ? residual.size()-18 : 0;
            local.assign(residual.begin()+static_cast<ptrdiff_t>(start),residual.end());
        }
        vector<double> absoluteResidual;
        for(double r:residual) absoluteResidual.push_back(fabs(r));
        f.noise=max({mad(residual),mad(local),0*median(absoluteResidual)})/1.2247448714;
        f.tolerance=max({1.0,3*f.noise,0.04*f.contrast});
        f.significant=f.contrast>max(4.0,24*f.noise);
        f.noisy=f.noise>max(1.0,0.01*f.contrast);
        if(f.x.size()>1) f.baselineSlope=static_cast<double>(value[f.x.back()]-value[f.x.front()])/(f.x.back()-f.x.front());
        double leftValley=static_cast<double>(bestValue),rightValley=leftValley;
        for(int x:f.x) {
            if(x<best) leftValley=min(leftValley,static_cast<double>(value[x]));
            if(x>best) rightValley=min(rightValley,static_cast<double>(value[x]));
        }
        f.prominence=min(bestValue-leftValley,bestValue-rightValley);
        use(Op::A04); use(Op::A05); use(Op::A06); use(Op::H07);
        if(f.slopes.size()>1) f.curvature=f.slopes.back()-f.slopes[f.slopes.size()-2];
        size_t recent=f.x.size()>6 ? f.x.size()-6 : 1;
        for(size_t i=max(size_t{1},recent);i<f.x.size();++i) {
            double delta=static_cast<double>(value[f.x[i]]-value[f.x[i-1]]);
            if(delta>max(1.0,1.5*f.noise)) ++f.rises;
            if(delta<-max(1.0,1.5*f.noise)) ++f.falls;
        }
        f.left=best; f.right=best; f.plateauLeft=best; f.plateauRight=best;
        int firstHigh=best;
        for(int x:f.x) if(value[x]>=bestValue-f.tolerance) {
            f.left=min(f.left,x); f.right=max(f.right,x); firstHigh=min(firstHigh,x);
            if(value[x]==bestValue) { f.plateauLeft=min(f.plateauLeft,x); f.plateauRight=max(f.plateauRight,x); }
        }
        auto it=lower_bound(f.x.begin(),f.x.end(),firstHigh);
        if(it!=f.x.begin()) f.left=*prev(it);
        for(auto rit=f.x.rbegin();rit!=f.x.rend();++rit)
            if(*rit<best && value[*rit]<=bestValue-0.5*f.contrast) { f.halfLeft=best-*rit; break; }
        for(int x:f.x) if(x>best && value[x]<=bestValue-0.5*f.contrast) { f.halfRight=x-best; break; }
        f.leftEdge=best<=12 && f.falls>=3 && f.rises==0 && f.significant && f.noise<0.04*f.contrast;
        f.plateau=!f.flat && f.plateauRight-f.plateauLeft>=24;
        if(f.flat) use(Op::G01);
        if(f.plateau) { use(Op::E01); use(Op::G03); use(Op::G04); }
        double valley=static_cast<double>(value[f.x.back()]);
        for(auto rit=f.x.rbegin();rit!=f.x.rend() && *rit>best;++rit)
            valley=min(valley,static_cast<double>(value[*rit]));
        f.rebound=rightmost>best+24 && value[f.x.back()]-valley>max(3*f.noise,0.025*f.contrast);

        // ===== 新增：瞬态运动尖峰检测器 S01 =====
        for(size_t i=1;i+1<f.x.size();i++){
            int xi=f.x[i];
            long long vc=value[xi], vl=value[f.x[i-1]], vr=value[f.x[i+1]];
            long long d1=llabs(vc-vl),d2=llabs(vc-vr);
            if(d1>max(6.0*f.noise, 0.08*f.contrast) && d2>max(6.0*f.noise,0.08*f.contrast)){
                f.transientSpikes.push_back(xi);
                use(Op::S01);
            }
        }

        f.peaks.clear();
        for(size_t i=0;i<f.x.size();++i) {
            int x=f.x[i];
            bool leftOK=(i==0)||(value[x]>=value[f.x[i-1]]);
            bool rightOK=(i+1==f.x.size())||(value[x]>=value[f.x[i+1]]);
            bool nonflat=(i&&value[x]>value[f.x[i-1]])||(i+1<f.x.size()&&value[x]>value[f.x[i+1]]);
            if(leftOK && rightOK && nonflat) f.peaks.push_back(x);
        }
        if(f.flat) f.shape=Shape::Flat;
        else if(f.rebound && f.peaks.size()>1) { f.shape=Shape::Multi; use(Op::F01); }
        else if(f.plateau || f.right-firstHigh>=24 || (f.noisy && f.right-f.left>24)) f.shape=Shape::Broad;
        else if(f.rises>=2 && f.falls==0) f.shape=Shape::Rising;
        else if(f.falls>=2 && f.rises==0) f.shape=Shape::Falling;
        else if(f.significant && rightmost>best) f.shape=Shape::Smooth;
        else f.shape=Shape::Rough;
        if(f.shape==Shape::Rough) use(Op::H04);
        if(f.peaks.size()>1) use(Op::F06);
        use(Op::K02); use(Op::K03);
        if(f.shape==state) votes=0;
        else if(f.shape==Shape::Multi || f.shape==Shape::Rough) { state=f.shape; votes=0; use(Op::H08); }
        else {
            if(pending==f.shape) ++votes; else { pending=f.shape; votes=1; }
            if(votes>=2) { state=f.shape; votes=0; }
        }
        ++visits[static_cast<size_t>(state)];
        return f;
    }

    int frontierLimit(const Features& f) {
        double scaleN = (double)n / 700.0;
        if(strict) return min(n-1,certifiedLeft()+199);
        if(f.flat) {
            use(Op::G08);
            return lateFlat ? n-1 : min(n-1,(n-1)/2+(int)(144*scaleN));
        }
        if(!f.significant) return n-1;
        use(Op::E02);
        int lim = (int)(f.left + 180*scaleN);
        return min(n-1, lim);
    }

    void explore() {
        use(Op::B01); use(Op::J01);
        for(int x:{0,4,12,24}) {
            if(x>=n || !sample(x)) break;
            if(certificateStrong()) return;
        }
        int flatRuns=0;
        int coarseBudgetMax = (int)(128 * ((double)n/700.0));
        while(q<coarseBudgetMax && rightmost<n-1 && seconds()<7.0) {
            Features f=features();
            if(certificateStrong()) return;
            int limit=frontierLimit(f);
            if(rightmost>=limit) break;
            int step=12;
            if(f.flat) { ++flatRuns; use(Op::B02); step=flatRuns>=8?8:12; }
            else {
                flatRuns=0;
                if(f.rises>=2 && f.falls==0) { use(Op::B03); step=f.curvature<-max(0.1,f.noise/12)?8:8; if(step==8) use(Op::B04); if(f.noisy) step=8; }
                else step=f.noisy || state==Shape::Rough ? 8 :8;
                if(f.leftEdge && rightmost-best>=48) { use(Op::H01); break; }
                int scout=clamp(static_cast<int>(f.halfLeft*1.2),96,144);
                if(best>=(n-1)/2) scout=min(scout,16);
                if(f.significant && rightmost-best>=scout && !f.rebound && bestValue-value[rightmost]>max(3*f.noise,0.08*f.contrast)) { use(Op::K07); break; }
                if(rightmost>best+24) use(Op::F02);
                if(f.rebound) { use(Op::K05); step=8; }
                if(f.equalSteps>=3 && f.rises && f.contrast<max(8.0,4*f.noise)) { use(Op::G07); step=min(step,8); }
                bool unbracketed=f.rises>0 && all_of(f.slopes.begin(),f.slopes.end(),[](double s){return s>=0;});
                if(unbracketed) {
                    int remaining=coarseBudgetMax-q;
                    int coverageStep=(n-1-rightmost+remaining-1)/remaining;
                    if(coverageStep>step) { use(Op::B03); step=coverageStep; }
                }
            }
            int next=min({n-1,rightmost+step,limit});
            int center=(n-1)/2;
            if(f.flat && rightmost<center && next>center) { next=center; use(Op::G02); }
            if(next==n-1) { use(Op::B07); use(Op::H02); }
            if(f.flat && q%7==0 && next<limit-2 && next!=center) { ++next; use(Op::B05); }
            if(next<=rightmost || !sample(next)) break;
        }
        coarseFrontier=rightmost;
    }

    optional<double> vertex(int a,int b,int c) {
        if(!(a<b && b<c)) return nullopt;
        use(Op::C01);
        double sl=static_cast<double>(value[b]-value[a])/(b-a);
        double sr=static_cast<double>(value[c]-value[b])/(c-b);
        double curvature=(sr-sl)/(c-a);
        if(curvature>=-1e-12) return nullopt;
        double at=(a+b)/2.0-sl/(2*curvature);
        if(!isfinite(at)||at<a||at>c) return nullopt;
        return at;
    }

    optional<double> fittedVertex(const vector<int>& xs) {
        if(xs.size()<5) return nullopt;
        use(Op::C02);
        vector<double> robustWeight(xs.size(),1.0);
        array<double,3> coeff{};
        for(int iter=0;iter<3;++iter){
            double mat[3][4]{};
            for(size_t k=0;k<xs.size();++k){
                int x=xs[k];
                double t=(x-best)/16.0;
                double basis[]={1,t,t*t};
                double w=robustWeight[k]/(1+fabs(t));
                for(int i=0;i<3;++i){
                    for(int j=0;j<3;++j) mat[i][j]+=w*basis[i]*basis[j];
                    mat[i][3]+=w*basis[i]*(value[x]-bestValue);
                }
            }
            for(int i=0;i<3;++i){
                int pivot=i;
                for(int j=i+1;j<3;++j) if(fabs(mat[j][i])>fabs(mat[pivot][i])) pivot=j;
                for(int j=i;j<4;++j) swap(mat[i][j],mat[pivot][j]);
                if(fabs(mat[i][i])<1e-10) return nullopt;
                double div=mat[i][i];
                for(int j=i;j<4;++j) mat[i][j]/=div;
                for(int row=0;row<3;++row) if(row!=i){
                    double k=mat[row][i];
                    for(int j=i;j<4;++j) mat[row][j]-=k*mat[i][j];
                }
            }
            for(int i=0;i<3;++i) coeff[i]=mat[i][3];
            vector<double> res;
            for(int x:xs){
                double t=(x-best)/16.0;
                res.push_back(value[x]-bestValue-coeff[0]-coeff[1]*t-coeff[2]*t*t);
            }
            double scale=max(1.0,mad(res));
            for(size_t i=0;i<xs.size();++i) robustWeight[i]=min(1.0,1.5*scale/max(1.0,fabs(res[i])));
        }
        if(coeff[2]>=-1e-10) return nullopt;
        double at=best-8*coeff[1]/coeff[2];
        if(!isfinite(at)||at<xs.front()||at>xs.back()) return nullopt;
        return at;
    }

    vector<Point> pool(const Features& f) {
        vector<double> priority(n,-1); vector<int> cluster(n,-1); int overlap=0;
        auto isTransient=[&](int x){
            return find(f.transientSpikes.begin(),f.transientSpikes.end(),x)!=f.transientSpikes.end();
        };
        auto add=[&](int x,double score,int group=-1,bool transient=false) {
            if(x<0||x>rightmost||value[x]>=0) return;
            if(isTransient(x)||transient) score*=0.22;
            use(Op::S02);
            if(priority[x]>=0) ++overlap;
            if(score>priority[x]) { priority[x]=score; cluster[x]=group; }
        };
        double scale=max(1.0,f.contrast);
        double threshold=bestValue-max({1.0,3*f.noise+0.02*f.contrast,0.04*f.contrast});
        use(Op::E01); use(Op::E04); use(Op::E05);
        for(size_t i=1;i<f.x.size();++i) {
            int a=f.x[i-1],b=f.x[i];
            if(value[a]<threshold && value[b]<threshold) continue;
            bool edge=(value[a]<threshold)!=(value[b]<threshold);
            if(edge) { use(Op::E06); use(Op::D06); }
            for(int x=a+1;x<b;++x) {
                double t=static_cast<double>(x-a)/(b-a);
                double pred=value[a]+t*(value[b]-value[a]);
                double score=(edge?75:35)+15*(pred-f.floor)/scale;
                if(fabs(f.baselineSlope)*rightmost>0.1*f.contrast && f.noisy) {
                    use(Op::H05);
                    double baseline=value[f.x.front()]+f.baselineSlope*(x-f.x.front());
                    score+=clamp(10*(pred-baseline)/scale,-5.0,5.0);
                }
                add(x,score);
            }
            if(b-a>=8) { use(Op::D03); add((a+b)/2,66); }
            if(b-a>16) { use(Op::D04); add(a+(b-a)/3,64); add(b-(b-a)/3,64); }
        }
        if(!f.flat) for(size_t i=1;i<f.x.size();++i) {
            int a=f.x[i-1],b=f.x[i];
            if(b-a==f.maxGap && b-a>=16 && max(value[a],value[b])>=threshold) { use(Op::B06); add((a+b)/2,68); }
        }
        use(Op::D01); use(Op::D02); use(Op::C06);
        for(int x=best-12;x<=best+12;++x) add(x,82-0.5*abs(x-best));
        for(int x=best-3;x<=best+3;++x) add(x,115-abs(x-best));
        if(best>0 && value[0]>=threshold) { use(Op::H03); for(int x=1;x<min(12,rightmost);++x) add(x,92); }

        vector<int> peaks=f.peaks;
        if(find(peaks.begin(),peaks.end(),best)==peaks.end()) peaks.push_back(best);
        sort(peaks.begin(),peaks.end(),[&](int a,int b){return better(a,value[a],b,value[b]);});
        vector<int> groups;
        for(int p:peaks) {
            bool close=false;
            for(int other:groups) if(abs(p-other)<=24) { close=true; break; }
            if(close) { use(Op::F03); continue; }
            groups.push_back(p);
        }
        for(size_t group=0;group<groups.size();++group) {
            int p=groups[group];
            if(value[p]<bestValue-max(6*f.noise,0.1*f.contrast)) { use(Op::F05); continue; }
            use(Op::E08); use(Op::F04);
            for(int x=p-8;x<=p+8;++x) add(x,52+8*(value[p]-f.floor)/scale-abs(x-p)*0.15,static_cast<int>(group));
            add(p-1,106,static_cast<int>(group)); add(p+1,106,static_cast<int>(group));
            if(value[p]==bestValue && p!=best) { use(Op::F07); use(Op::G06); }
        }
        if(!f.noisy && f.significant && !f.flat) {
            use(Op::C04);
            for(size_t i=1;i+1<f.x.size();++i) {
                int a=f.x[i-1],b=f.x[i],c=f.x[i+1];
                if(value[b]<threshold||value[b]<value[a]||value[b]<value[c]) continue;
                if(auto v=vertex(a,b,c)){ use(Op::C03); int cx=(int)llround(*v); for(int x=cx-2;x<=cx+2;++x) add(x,108-fabs(x-*v)); }
                if(c-a>24) { use(Op::C05); add(a+(int)((c-a)*0.382),71); add(a+(int)((c-a)*0.618),71); }
            }
            vector<int> near;
            for(int x:f.x) if(abs(x-best)<=40) near.push_back(x);
            if(auto v=fittedVertex(near)){ int cx=(int)llround(*v); for(int x=cx-2;x<=cx+2;++x) add(x,105-fabs(x-*v)); }
            if(f.halfLeft>0&&f.halfRight>0&&max(f.halfLeft,f.halfRight)>1.6*min(f.halfLeft,f.halfRight)){
                use(Op::C07); int side=f.halfLeft>f.halfRight?-1:1; int rad=min(40,(int)max(f.halfLeft,f.halfRight)/2);
                for(int off=17;off<=rad;++off) add(best+side*off,67-0.1*off);
            }
        }
        if(f.plateau) { use(Op::G05); add(clamp((n-1)/2,f.plateauLeft,f.plateauRight),112); }
        if(f.flat) { use(Op::G02); add((n-1)/2,130); for(int x=0;x<n;++x) if(abs(x-best)>3&&priority[x]<110) priority[x]=-1; }
        if(bestValue==VMAX) { use(Op::H06); for(int x=0;x<=rightmost;++x) if(tieBetter(x,best)) add(x,100-0.05*abs(2*x-(n-1))); }
        if(f.noisy||state==Shape::Broad||state==Shape::Rough) use(Op::E07);
        if(overlap) { use(Op::D08); use(Op::J08); }
        vector<Point> res;
        for(int x=0;x<n;++x) if(priority[x]>=0) res.push_back({x,priority[x],cluster[x],isTransient(x)});
        return res;
    }

    vector<Scenario> scenarios(const Features& f) {
        use(Op::K06);
        vector<Scenario> res;
        for(int s=0;s<ENSEMBLE_CNT;++s) {
            Scenario c;
            c.value.assign(n,(long long)f.floor);
            Scenario::DisturbType t;
            if(s%4==0) t=Scenario::NOISE;
            else if(s%4==1) t=Scenario::MOTION_JUMP;
            else if(s%4==2) t=Scenario::BIMODAL;
            else t=Scenario::PLATEAU;
            c.type=t;
            for(size_t i=1;i<f.x.size();++i) {
                int a=f.x[i-1],b=f.x[i];
                for(int x=a;x<=b;++x) {
                    double tseg=static_cast<double>(x-a)/(b-a);
                    double pred=value[a]+tseg*(value[b]-value[a]);
                    if(s && x!=a && x!=b) {
                        double u=static_cast<double>(random64()>>11)/9007199254740992.0;
                        double unc=max(f.noise,0.015*f.contrast);
                        if(c.type==Scenario::MOTION_JUMP && (x-a)%7==0) pred+=unc*3.2*(u-0.5);
                        else pred+=sin(3.1415926535*tseg)*unc*1.4*(u*1.2-0.4);
                    }
                    c.value[x]=static_cast<long long>(llround(clamp(pred,0.0,(double)VMAX)));
                }
            }
            for(int x:f.x) c.value[x]=value[x];
            for(int x=1;x<n;++x) if(better(x,c.value[x],c.target,c.value[c.target])) c.target=x;
            res.push_back(move(c));
        }
        return res;
    }

    PlanRisk simulatePlanRisk(const vector<int>& path) {
        PlanRisk pr{};
        if(q+(int)path.size()+1>QMAX) { pr.hard_violate=true; return pr; }
        int p=pos,d=direction,o=turns; long long m=travel;
        int rr=rightmost;
        for(int x:path) {
            if(x<0||x>=n||value[x]>=0) { pr.hard_violate=true; return pr; }
            moveTo(x,p,d,o,m);
            rr=max(rr,x);
        }
        pr.delta_osc=o-turns;
        pr.delta_step=(int)path.size();
        pr.est_redundant_inc=max(0,rr-best);
        if(o>OMAX) pr.hard_violate=true;
        return pr;
    }

    bool routeSafe(const vector<int>& path) {
        auto pr=simulatePlanRisk(path);
        return !pr.hard_violate;
    }

    vector<int> canonical(vector<int> plan,bool descending) const {
        sort(plan.begin(),plan.end()); plan.erase(unique(plan.begin(),plan.end()),plan.end());
        if(descending) reverse(plan.begin(),plan.end());
        return plan;
    }

    vector<int> orient(vector<int> plan,bool preferredDescending) {
        use(Op::J06);
        vector<int> pref=canonical(plan,preferredDescending);
        vector<int> alt=canonical(move(plan),!preferredDescending);
        auto cost=[&](const vector<int>& path)->long long{
            if(!routeSafe(path)) return numeric_limits<long long>::max();
            int p=pos,d=direction,o=turns; long long m=travel;
            for(int x:path) moveTo(x,p,d,o,m);
            if(best>=0) moveTo(best,p,d,o,m);
            return m-travel+o-turns;
        };
        return cost(alt)<cost(pref)?alt:pref;
    }

    double planScore(const vector<int>& path,const vector<Scenario>& cases,const vector<Point>& candidates,const Features& f) {
        if(!routeSafe(path)) return -1e30;
        auto pr=simulatePlanRisk(path);
        (void)pr; (void)f;
        // 动态权重：余量紧张时放大振荡、冗余惩罚 S03
        double w_osc = (6-turns)<=2 ? 2.8 :1.0;
        double w_red = (rightmost-best)>40 ? 2.2 :1.0;

        double total=0,worst=3000;
        for(const auto& c:cases) {
            int p=pos,d=direction,o=turns,winner=best;
            long long m=travel,winnerValue=bestValue;
            for(int x:path) {
                moveTo(x,p,d,o,m);
                if(better(x,c.value[x],winner,winnerValue)) { winner=x; winnerValue=c.value[x]; }
            }
            int parking=(p==winner)?0:1;
            if(parking) moveTo(winner,p,d,o,m);
            int dist=abs(p-c.target);
            int red=max(0,rightmost-c.target);
            double sc=0;
            if(q+(int)path.size()+parking<=QMAX && o<=OMAX && dist<=3 && red<=199) {
                sc=max(0.0,3000.0
                       -200.0*dist
                       -(q+(int)path.size()+parking)
                       -m
                       -w_osc*o
                       -w_red*red);
            }
            total+=sc;
            worst=min(worst,sc);
        }
        double coverage=0;
        if(!path.empty()) for(const auto& pt:candidates) {
            int gap=n;
            for(int x:path) gap=min(gap,abs(x-pt.x));
            coverage+=pt.priority/(1+gap);
        }
        double avgS=total/(double)cases.size();
        return 0.80*avgS + 0.15*worst + 0.05*coverage/max(size_t{1},candidates.size());
    }

    vector<int> selectPlan(const vector<Point>& candidates,int budget,bool descending,const Features& f) {
        use(Op::I05); use(Op::J04); use(Op::J05);
        if(budget<=0||candidates.empty()) return {};
        if((int)candidates.size()<=budget) {
            vector<int> all; for(auto& pt:candidates) all.push_back(pt.x);
            return orient(move(all),descending);
        }
        use(Op::E03); use(Op::K04);
        vector<Point> ranked=candidates;
        sort(ranked.begin(),ranked.end(),[](const Point& a,const Point& b){
            return a.priority!=b.priority ? a.priority>b.priority : a.x<b.x;
        });
        vector<int> plan; vector<bool> picked(n,false),eligible(n,false);
        for(auto& pt:candidates) eligible[pt.x]=true;
        auto pick=[&](int x){
            if(!picked[x]&&(int)plan.size()<budget) { picked[x]=true; plan.push_back(x); }
        };
        map<int,Point> rep;
        for(auto& pt:ranked) if(pt.cluster>=0&&!rep.count(pt.cluster)) rep.emplace(pt.cluster,pt);
        vector<Point> sep;
        for(auto& e:rep) sep.push_back(e.second);
        sort(sep.begin(),sep.end(),[](const Point&a,const Point&b){return a.priority>b.priority;});
        for(int i=0;i<min((int)sep.size(),budget/5);++i) pick(sep[i].x);
        int highQ=min(budget,max(7,budget/3));
        for(auto& pt:ranked) { if((int)plan.size()>=highQ) break; pick(pt.x); }
        use(Op::B08); use(Op::E07);
        int slots=budget-(int)plan.size();
        for(int i=0;i<slots;++i) pick(candidates[min((int)candidates.size()-1,(int)((i+0.5)*candidates.size()/max(1,slots)))].x);
        for(auto& pt:ranked) pick(pt.x);
        plan=canonical(move(plan),descending);
        if(!routeSafe(plan)) { use(Op::J07); return {}; }
        auto cases=scenarios(f);
        double score=planScore(plan,cases,candidates,f),bestScore=score;
        vector<int> winner=plan;
        const int minimum=min(budget,max(7,budget*4/5));
        // === 替换随机退火：确定性多轮扰动，无温度随机漂移 S04 ===
        for(int iter=0;iter<112 && seconds()<6.8;++iter) {
            vector<int> proposal=plan;
            switch(iter%8) {
            case 0:
                use(Op::L01);
                if((int)proposal.size()<budget) proposal.push_back(candidates[iter%candidates.size()].x);
                break;
            case 1:
                use(Op::L02);
                if((int)proposal.size()>minimum) proposal.erase(proposal.begin()+(iter%proposal.size()));
                break;
            case 2:{
                use(Op::L03);
                if(!proposal.empty()){
                    int i=iter%proposal.size();
                    int x=proposal[i]+((iter&1)?1:-1);
                    if(x>=0&&x<n&&eligible[x]) proposal[i]=x;
                }
                break;
            }
            case 3:{
                use(Op::L04);
                int target=candidates[iter%candidates.size()].x,gap=-1;
                for(auto& pt:candidates){
                    int near=n;
                    for(int x:proposal) near=min(near,abs(x-pt.x));
                    if(near>gap){ gap=near; target=pt.x; }
                }
                if(!proposal.empty()) proposal[iter%proposal.size()]=target;
                break;
            }
            case 4:{
                use(Op::L05);
                if(proposal.size()>=2){
                    int clo=1;
                    for(size_t i=2;i<proposal.size();++i)
                        if(abs(proposal[i]-proposal[i-1])<abs(proposal[clo]-proposal[clo-1])) clo=(int)i;
                    proposal[clo]=candidates[iter%candidates.size()].x;
                }
                break;
            }
            case 5:
                use(Op::L06); use(Op::B05); proposal.clear();
                for(int i=0;i<budget;++i){
                    size_t at=((size_t)i*candidates.size()/budget + (size_t)(iter/8))%candidates.size();
                    proposal.push_back(candidates[at].x);
                }
                break;
            case 6:
                use(Op::L07);
                proposal.clear();
                for(int i=0;i<budget;++i){
                    if((iter/8)%2) proposal.push_back(ranked[i].x);
                    else proposal.push_back(candidates[((size_t)i*candidates.size())%candidates.size()].x);
                }
                break;
            default:
                use(Op::L08); use(Op::J07);
                if((int)proposal.size()>minimum) proposal.pop_back();
                break;
            }
            proposal=canonical(move(proposal),descending);
            if((int)proposal.size()<minimum || !routeSafe(proposal)) continue;
            double candSc=planScore(proposal,cases,candidates,f);
            // 确定性接受准则，不再随机采样 u
            if(candSc >= score) {
                plan=move(proposal); score=candSc;
            }
            if(score>bestScore) { bestScore=score; winner=plan; }
        }
        bool neighborsKnown=true;
        for(int x=max(0,best-3);x<=min(rightmost,best+3);++x) if(value[x]<0) neighborsKnown=false;
        if(neighborsKnown && !f.noisy && bestScore<=planScore({},cases,candidates,f)) { use(Op::K07); return {}; }
        return orient(move(winner),descending);
    }

    void peakVerify(const Features& f) {
        // 候选主峰校验算子 S05：少量采样邻域排除噪声假峰
        if(best<0||f.noisy==false) return;
        int verifyBudget=4;
        for(int d:{-2,-1,1,2}){
            if(verifyBudget<=0) break;
            int x=best+d;
            if(x>=0&&x<n&&value[x]<0) { sample(x); verifyBudget--; use(Op::S05); }
        }
    }

    void refine() {
        if(bestValue<VMAX && q<188) {
            Features f=features();
            certificateWeak(f);
            auto it=lower_bound(f.x.begin(),f.x.end(),best);
            bool uniquePeak=true;
            for(int x:f.peaks) if(abs(x-best)>32 && value[x]>bestValue-0.25*f.contrast) uniquePeak=false;
            if(uniquePeak && !f.plateau && f.significant && f.noise<0.005*f.contrast && it!=f.x.begin() && it!=f.x.end() && next(it)!=f.x.end()) {
                vector<int> near;
                for(int x:f.x) if(abs(x-best)<=32) near.push_back(x);
                auto v1=vertex(*prev(it),*it,*next(it));
                auto v2=fittedVertex(near);
                if(v1&&v2&&fabs(*v1-*v2)<0.75) {
                    int center=(int)llround((*v1+*v2)/2);
                    vector<int> probe;
                    for(int x=min(rightmost,center+6);x>=max(0,center-6);--x) if(value[x]<0) probe.push_back(x);
                    if(routeSafe(probe)) { for(int x:probe) if(!sample(x)) return; if(certificateStrong()||(bestValue<VMAX&&abs(best-center)<=5)) return; }
                }
            }
        }
        for(int round=0;round<2 && q<QMAX-1 && seconds()<7.5;++round) {
            if(certificateStrong()) return;
            Features f=features();
            peakVerify(f);
            vector<Point> candidates=pool(f);
            if(candidates.empty()) break;
            int available=QMAX-1-q;
            int budget=available;
            if(round==0&&(int)candidates.size()>available) budget=max(7,available-min(48,available/3));
            bool desc=round==0;
            if(desc) use(Op::J02); else use(Op::J03);
            vector<int> plan=selectPlan(candidates,budget,desc,f);
            if(plan.empty()||!routeSafe(plan)) break;
            bool progress=false;
            for(int x:plan) {
                if(!sample(x)) break;
                progress=true;
                if(certificateStrong()) return;
            }
            if(!progress) break;
        }
    }

    void finish() {
        use(Op::I07);
        if(alive && best>=0 && pos!=best) readReal(best,true);
        cout<<"DONE\n"<<flush;
        if(trace) {
            cerr<<"TRACE {\"queries\":"<<q<<",\"travel\":"<<travel<<",\"oscillations\":"<<turns
                <<",\"rightmost\":"<<rightmost<<",\"coarse_frontier\":"<<coarseFrontier
                <<",\"position\":"<<pos<<",\"best\":"<<best<<",\"certified_left\":"<<certifiedLeft()
                <<",\"cert_level\":"<<(int)certLevel
                <<",\"strict\":"<<(strict?"true":"false")<<",\"late_flat\":"<<(lateFlat?"true":"false")<<",\"old_peak_risk\":"<<(oldPeakRisk?"true":"false")<<",\"states\":{";
            for(size_t i=0;i<visits.size();++i) { if(i) cerr<<','; cerr<<'"'<<shapeNames[i]<<"\":"<<visits[i]; }
            cerr<<"},\"operators\":{"; bool first=true;
            for(size_t i=0;i<uses.size();++i) if(uses[i]) { if(!first) cerr<<','; first=false; cerr<<'"'<<opNames[i]<<"\":"<<uses[i]; }
            cerr<<"}}\n";
        }
    }
public:
    Solver(int length,bool diagnostics,bool certified,bool delayed)
        : n(length),value(length,-1),trace(diagnostics),strict(certified),lateFlat(delayed) {
        rng^=static_cast<uint64_t>(n)*1000003ULL;
    }
    void run() {
        if(n<=198) { for(int x=0;x<n;++x) if(!sample(x)) break; }
        else { explore(); if(alive) refine(); }
        finish();
    }
};
}//namespace af_super

int main(int argc,char** argv) {
    ios::sync_with_stdio(false); cin.tie(nullptr);
    bool trace=false,strict=false,late=false;
    for(int i=1;i<argc;++i){
        string arg=argv[i];
        if(arg=="--trace") trace=true;
        else if(arg=="--strict-redundancy") strict=true;
        else if(arg=="--late-flat") late=true;
    }
    int n;
    if(!(cin>>n)||n<=0||n>1000) return 0;
    af_super::Solver(n,trace,strict,late).run();
    return 0;
}
