// Day26 derived experiment: {"coarse": 128, "flat_step": 8, "group": 0.1, "late_scout": 16, "model_agreement": 10.0, "model_finish": true, "model_fit_window": 24, "model_min_radius": 3, "model_noise_fraction": 0.05, "model_prediction_margin": 3, "model_radius_mode": "asymmetric_vertex_interval", "noise_abs": 0, "noise_step": 8, "prom": 24, "radius": 8, "up": 8}
#include <bits/stdc++.h>
using namespace std;

// Fixed-array autofocus: cached values never imply physical motor movement.
namespace af {
constexpr long long VMAX = 2147483647LL;
constexpr int QMAX = 199, OMAX = 6;
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
 X(L01) X(L02) X(L03) X(L04) X(L05) X(L06) X(L07) X(L08)
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
int signum(int x) { return (x > 0) - (x < 0); }
double median(vector<double> a) {
    if (a.empty()) return 0;
    const size_t m = a.size()/2;
    nth_element(a.begin(), a.begin()+static_cast<ptrdiff_t>(m), a.end());
    const double hi = a[m];
    return a.size()%2 ? hi : (hi+*max_element(a.begin(),a.begin()+static_cast<ptrdiff_t>(m)))/2;
}
double mad(const vector<double>& a) {
    const double m = median(a);
    vector<double> d;
    for (double x:a) d.push_back(abs(x-m));
    return 1.4826*median(d);
}
struct Features {
    vector<int> x, peaks;
    vector<double> slopes;
    double floor=0, contrast=0, noise=0, tolerance=1, halfLeft=0, halfRight=0, curvature=0;
    double prominence=0, baselineSlope=0;
    int left=0, right=0, plateauLeft=0, plateauRight=0, maxGap=0, rises=0, falls=0, equalSteps=0;
    bool flat=true, significant=false, rebound=false, leftEdge=false, plateau=false, noisy=false;
    Shape shape=Shape::Flat;
};
struct Point { int x; double priority; int cluster; };
struct Scenario { vector<long long> value; int target=0; };

class Solver {
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
    void use(Op op) { ++uses[static_cast<size_t>(op)]; }
    double seconds() const {
        return chrono::duration<double>(chrono::steady_clock::now()-started).count();
    }
    uint64_t random64() { rng^=rng<<13; rng^=rng>>7; rng^=rng<<17; return rng; }
    int randomInt(int count) { return static_cast<int>(random64()%static_cast<uint64_t>(count)); }
    bool tieBetter(int a,int b) const {
        if (b<0) return true;
        const int da=abs(2*a-(n-1)), db=abs(2*b-(n-1));
        return da!=db ? da<db : a<b;
    }
    bool better(int a,long long va,int b,long long vb) const {
        return va!=vb ? va>vb : tieBetter(a,b);
    }
    static void moveTo(int x,int& p,int& dir,int& o,long long& m) {
        const int d=signum(x-p);
        if (d) { if (dir && d!=dir) ++o; dir=d; }
        m+=abs(x-p); p=x;
    }
    int certifiedLeft() const {
        int left=best<0 ? 0 : best;
        for (int x=0;x<n;++x)
            if (value[x]<0 && (bestValue<VMAX || tieBetter(x,best))) left=min(left,x);
        return left;
    }
    bool certificate() {
        if (bestValue!=VMAX) return false;
        use(Op::D07);
        for (int x=0;x<n;++x) if (value[x]<0 && tieBetter(x,best)) return false;
        return true;
    }
    bool canRead(int x,bool terminal) {
        use(Op::I01); use(Op::I02); use(Op::I03);
        if (!alive || x<0 || x>=n || q+1+(terminal?0:1)>QMAX) return false;
        if (!terminal && seconds()>8.0) { use(Op::I07); return false; }
        int p=pos,d=direction,o=turns; long long m=travel;
        moveTo(x,p,d,o,m);
        // The answer either preserves the old winner or makes x the winner.
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
        for (int x=0;x<n;++x) if (value[x]>=0) xs.push_back(x);
        return xs;
    }
    Features features() {
        Features f; f.x=observed();
        if (f.x.empty()) return f;
        use(Op::A01); use(Op::A02); use(Op::A03); use(Op::A07); use(Op::A08);
        f.floor=static_cast<double>(value[f.x.front()]);
        vector<double> residual;
        for (size_t i=0;i<f.x.size();++i) {
            const int x=f.x[i];
            f.floor=min(f.floor,static_cast<double>(value[x]));
            if (i) {
                const int h=x-f.x[i-1]; f.maxGap=max(f.maxGap,h);
                f.slopes.push_back(static_cast<double>(value[x]-value[f.x[i-1]])/h);
                if (value[x]==value[f.x[i-1]]) ++f.equalSteps;
            }
            if (i && i+1<f.x.size()) {
                const int a=f.x[i-1], b=f.x[i+1];
                const double t=static_cast<double>(x-a)/(b-a);
                residual.push_back(value[x]-(value[a]+t*(value[b]-value[a])));
            }
        }
        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;
        vector<double> local;
        if (!residual.empty()) {
            const size_t start=residual.size()>18 ? residual.size()-18 : 0;
            local.assign(residual.begin()+static_cast<ptrdiff_t>(start),residual.end());
        }
        // Subtract the median residual: smooth curvature is not independent noise.
        vector<double> absoluteResidual;
        for (double r:residual) absoluteResidual.push_back(abs(r));
        f.noise=max({mad(residual),mad(local),0*median(absoluteResidual)})/1.2247448714;
        f.tolerance=max({1.0,3*f.noise,0.04*f.contrast});
        f.significant=f.contrast>max(4.0,24*f.noise);
        f.noisy=f.noise>max(1.0,0.01*f.contrast);
        if (f.x.size()>1) f.baselineSlope=static_cast<double>(value[f.x.back()]-value[f.x.front()])/
            (f.x.back()-f.x.front());
        double leftValley=static_cast<double>(bestValue),rightValley=leftValley;
        for (int x:f.x) {
            if (x<best) leftValley=min(leftValley,static_cast<double>(value[x]));
            if (x>best) rightValley=min(rightValley,static_cast<double>(value[x]));
        }
        f.prominence=min(bestValue-leftValley,bestValue-rightValley);
        use(Op::A04); use(Op::A05); use(Op::A06); use(Op::H07);
        if (f.slopes.size()>1) f.curvature=f.slopes.back()-f.slopes[f.slopes.size()-2];
        const size_t recent=f.x.size()>6 ? f.x.size()-6 : 1;
        for (size_t i=max(size_t{1},recent);i<f.x.size();++i) {
            const double delta=static_cast<double>(value[f.x[i]]-value[f.x[i-1]]);
            if (delta>max(1.0,1.5*f.noise)) ++f.rises;
            if (delta<-max(1.0,1.5*f.noise)) ++f.falls;
        }
        f.left=best; f.right=best; f.plateauLeft=best; f.plateauRight=best;
        int firstHigh=best;
        for (int x:f.x) if (value[x]>=bestValue-f.tolerance) {
            f.left=min(f.left,x); f.right=max(f.right,x); firstHigh=min(firstHigh,x);
            if (value[x]==bestValue) { f.plateauLeft=min(f.plateauLeft,x); f.plateauRight=max(f.plateauRight,x); }
        }
        auto it=lower_bound(f.x.begin(),f.x.end(),firstHigh);
        if (it!=f.x.begin()) f.left=*prev(it);
        for (auto rit=f.x.rbegin();rit!=f.x.rend();++rit)
            if (*rit<best && value[*rit]<=bestValue-0.5*f.contrast) {
                f.halfLeft=best-*rit; break;
            }
        for (int x:f.x) if (x>best && value[x]<=bestValue-0.5*f.contrast) {
            f.halfRight=x-best; break;
        }
        f.leftEdge=best<=12 && f.falls>=3 && f.rises==0 && f.significant &&
            f.noise<0.04*f.contrast;
        f.plateau=!f.flat && f.plateauRight-f.plateauLeft>=24;
        if (f.flat) use(Op::G01);
        if (f.plateau) { use(Op::E01); use(Op::G03); use(Op::G04); }
        double valley=static_cast<double>(value[f.x.back()]);
        for (auto rit=f.x.rbegin();rit!=f.x.rend() && *rit>best;++rit)
            valley=min(valley,static_cast<double>(value[*rit]));
        f.rebound=rightmost>best+24 && value[f.x.back()]-valley>max(3*f.noise,0.025*f.contrast);
        for (size_t i=0;i<f.x.size();++i) {
            const int x=f.x[i];
            const bool leftOK=i==0 || value[x]>=value[f.x[i-1]];
            const bool rightOK=i+1==f.x.size() || value[x]>=value[f.x[i+1]];
            const bool nonflat=(i && value[x]>value[f.x[i-1]]) ||
                (i+1<f.x.size() && value[x]>value[f.x[i+1]]);
            if (leftOK && rightOK && nonflat)
                f.peaks.push_back(x);
        }
        if (f.flat) f.shape=Shape::Flat;
        else if (f.rebound && f.peaks.size()>1) { f.shape=Shape::Multi; use(Op::F01); }
        else if (f.plateau || f.right-firstHigh>=24 || (f.noisy && f.right-f.left>24)) f.shape=Shape::Broad;
        else if (f.rises>=2 && f.falls==0) f.shape=Shape::Rising;
        else if (f.falls>=2 && f.rises==0) f.shape=Shape::Falling;
        else if (f.significant && rightmost>best) f.shape=Shape::Smooth;
        else f.shape=Shape::Rough;
        if (f.shape==Shape::Rough) use(Op::H04);
        if (f.peaks.size()>1) use(Op::F06);
        use(Op::K02); use(Op::K03);
        if (f.shape==state) votes=0;
        else if (f.shape==Shape::Multi || f.shape==Shape::Rough) {
            state=f.shape; votes=0; use(Op::H08);
        } else {
            if (pending==f.shape) ++votes; else { pending=f.shape; votes=1; }
            if (votes>=2) { state=f.shape; votes=0; }
        }
        ++visits[static_cast<size_t>(state)];
        return f;
    }
    int frontierLimit(const Features& f) {
        if (strict) return min(n-1,certifiedLeft()+199);
        if (f.flat) {
            use(Op::G08);
            // Identical flat histories cannot distinguish constants from late peaks.
            return lateFlat ? n-1 : min(n-1,(n-1)/2+192);
        }
        // A one-unit quantization step or unstructured background is not a peak.
        // Before a meaningful signal exists, anchoring at its left edge would
        // terminate long, slowly emerging right-side peaks in their background.
        if (!f.significant) return n-1;
        use(Op::E02);
        return min(n-1,f.left+190);
    }
    void explore() {
        use(Op::B01); use(Op::J01);
        for (int x:{0,4,12,24}) {
            if (x>=n || !sample(x)) break;
            if (certificate()) return;
        }
        int flatRuns=0;
        while (q<128 && rightmost<n-1 && seconds()<7.0) {
            const Features f=features();
            if (certificate()) return;
            const int limit=frontierLimit(f);
            if (rightmost>=limit) break;
            int step=12;
            if (f.flat) {
                ++flatRuns; use(Op::B02);
                step=flatRuns>=8 ? 8 : 12;
            } else {
                flatRuns=0;
                if (f.rises>=2 && f.falls==0) {
                    use(Op::B03);
                    step=f.curvature<-max(0.1,f.noise/12) ? 8 : 8;
                    if (step==8) use(Op::B04);
                    if (f.noisy) step=8;
                } else step=f.noisy || state==Shape::Rough ? 8 : 8;
                if (f.leftEdge && rightmost-best>=48) { use(Op::H01); break; }
                int scout=clamp(static_cast<int>(f.halfLeft*1.2),96,144);
                if (best>=(n-1)/2) scout=min(scout,16);
                if (f.significant && rightmost-best>=scout && !f.rebound &&
                    bestValue-value[rightmost]>max(3*f.noise,0.08*f.contrast)) {
                    use(Op::K07); break;
                }
                if (rightmost>best+24) use(Op::F02);
                if (f.rebound) { use(Op::K05); step=8; }
                // Equal quantized steps followed by a small rise need denser
                // sampling; they are not enough evidence for a terminal plateau.
                if (f.equalSteps>=3 && f.rises && f.contrast<max(8.0,4*f.noise)) {
                    use(Op::G07); step=min(step,8);
                }
                // An unbracketed rising curve must not exhaust the coarse quota
                // before reaching the boundary merely because shoulder tests
                // repeatedly selected step 8. Preserve a route to the right end.
                const bool unbracketed=f.rises>0 && all_of(f.slopes.begin(),f.slopes.end(),
                                                         [](double slope) { return slope>=0; });
                if (unbracketed) {
                    const int remaining=128-q;
                    const int coverageStep=(n-1-rightmost+remaining-1)/remaining;
                    if (coverageStep>step) { use(Op::B03); step=coverageStep; }
                }
            }
            int next=min({n-1,rightmost+step,limit});
            const int center=(n-1)/2;
            if (f.flat && rightmost<center && next>center) { next=center; use(Op::G02); }
            if (next==n-1) { use(Op::B07); use(Op::H02); }
            if (f.flat && q%7==0 && next<limit-2 && next!=center) { ++next; use(Op::B05); }
            if (next<=rightmost || !sample(next)) break;
        }
        coarseFrontier=rightmost;
    }
    optional<double> vertex(int a,int b,int c) {
        if (!(a<b && b<c)) return nullopt;
        use(Op::C01);
        const double sl=static_cast<double>(value[b]-value[a])/(b-a);
        const double sr=static_cast<double>(value[c]-value[b])/(c-b);
        const double curvature=(sr-sl)/(c-a);
        if (curvature>=-1e-12) return nullopt;
        const double at=(a+b)/2.0-sl/(2*curvature);
        if (!isfinite(at) || at<a || at>c) return nullopt;
        return at;
    }
    optional<double> fittedVertex(const vector<int>& xs) {
        if (xs.size()<5) return nullopt;
        use(Op::C02);
        vector<double> robustWeight(xs.size(),1.0);
        array<double,3> coefficient{};
        for (int iteration=0;iteration<3;++iteration) {
            double mat[3][4]{};
            for (size_t k=0;k<xs.size();++k) {
                const int x=xs[k];
                const double t=(x-best)/16.0, basis[]={1,t,t*t};
                const double weight=robustWeight[k]/(1+abs(t));
                for (int i=0;i<3;++i) {
                    for (int j=0;j<3;++j) mat[i][j]+=weight*basis[i]*basis[j];
                    mat[i][3]+=weight*basis[i]*(value[x]-bestValue);
                }
            }
            for (int i=0;i<3;++i) {
                int pivot=i;
                for (int j=i+1;j<3;++j) if (abs(mat[j][i])>abs(mat[pivot][i])) pivot=j;
                for (int j=i;j<4;++j) swap(mat[i][j],mat[pivot][j]);
                if (abs(mat[i][i])<1e-10) return nullopt;
                const double divisor=mat[i][i];
                for (int j=i;j<4;++j) mat[i][j]/=divisor;
                for (int row=0;row<3;++row) if (row!=i) {
                    const double k=mat[row][i];
                    for (int j=i;j<4;++j) mat[row][j]-=k*mat[i][j];
                }
            }
            for (int i=0;i<3;++i) coefficient[i]=mat[i][3];
            vector<double> residual;
            for (int x:xs) {
                const double t=(x-best)/16.0;
                residual.push_back(value[x]-bestValue-coefficient[0]-coefficient[1]*t-coefficient[2]*t*t);
            }
            const double scale=max(1.0,mad(residual));
            for (size_t i=0;i<xs.size();++i)
                robustWeight[i]=min(1.0,1.5*scale/max(1.0,abs(residual[i])));
        }
        if (coefficient[2]>=-1e-10) return nullopt;
        const double at=best-8*coefficient[1]/coefficient[2];
        if (!isfinite(at) || at<xs.front() || at>xs.back()) return nullopt;
        return at;
    }
    vector<Point> pool(const Features& f) {
        vector<double> priority(n,-1); vector<int> cluster(n,-1); int overlap=0;
        auto add=[&](int x,double score,int group=-1) {
            if (x<0 || x>rightmost || value[x]>=0) return;
            if (priority[x]>=0) ++overlap;
            if (score>priority[x]) { priority[x]=score; cluster[x]=group; }
        };
        const double scale=max(1.0,f.contrast);
        const double threshold=bestValue-max({1.0,3*f.noise+0.02*f.contrast,0.04*f.contrast});
        use(Op::E01); use(Op::E04); use(Op::E05);
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1], b=f.x[i];
            if (value[a]<threshold && value[b]<threshold) continue;
            use(Op::D05);
            const bool edge=(value[a]<threshold)!=(value[b]<threshold);
            if (edge) { use(Op::E06); use(Op::D06); }
            for (int x=a+1;x<b;++x) {
                const double t=static_cast<double>(x-a)/(b-a);
                const double prediction=value[a]+t*(value[b]-value[a]);
                double score=(edge?75:35)+15*(prediction-f.floor)/scale;
                if (abs(f.baselineSlope)*rightmost>0.1*f.contrast && f.noisy) {
                    use(Op::H05);
                    const double baseline=value[f.x.front()]+f.baselineSlope*(x-f.x.front());
                    score+=clamp(10*(prediction-baseline)/scale,-5.0,5.0);
                }
                add(x,score);
            }
            if (b-a>=8) { use(Op::D03); add((a+b)/2,66); }
            if (b-a>16) { use(Op::D04); add(a+(b-a)/3,64); add(b-(b-a)/3,64); }
        }
        if (!f.flat) for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1],b=f.x[i];
            if (b-a==f.maxGap && b-a>=16 && max(value[a],value[b])>=threshold) {
                use(Op::B06); add((a+b)/2,68);
            }
        }
        use(Op::D01); use(Op::D02); use(Op::C06);
        for (int x=best-8;x<=best+8;++x) add(x,82-0.5*abs(x-best));
        for (int x=best-3;x<=best+3;++x) add(x,115-abs(x-best));
        if (best>0 && value[0]>=threshold) {
            use(Op::H03);
            for (int x=1;x<min(12,rightmost);++x) add(x,92);
        }
        vector<int> peaks=f.peaks;
        if (find(peaks.begin(),peaks.end(),best)==peaks.end()) peaks.push_back(best);
        sort(peaks.begin(),peaks.end(),[&](int a,int b) { return better(a,value[a],b,value[b]); });
        vector<int> groups;
        for (int p:peaks) {
            bool close=false;
            for (int other:groups) if (abs(p-other)<=24) { close=true; break; }
            if (close) { use(Op::F03); continue; }
            groups.push_back(p);
        }
        for (size_t group=0;group<groups.size();++group) {
            const int p=groups[group];
            if (value[p]<bestValue-max(6*f.noise,0.1*f.contrast)) { use(Op::F05); continue; }
            use(Op::E08); use(Op::F04);
            for (int x=p-8;x<=p+8;++x)
                add(x,52+8*(value[p]-f.floor)/scale-abs(x-p)*0.15,static_cast<int>(group));
            add(p-1,106,static_cast<int>(group)); add(p+1,106,static_cast<int>(group));
            if (value[p]==bestValue && p!=best) { use(Op::F07); use(Op::G06); }
        }
        if (!f.noisy && f.significant && !f.flat) {
            use(Op::C04);
            for (size_t i=1;i+1<f.x.size();++i) {
                const int a=f.x[i-1], b=f.x[i], c=f.x[i+1];
                if (value[b]<threshold || value[b]<value[a] || value[b]<value[c]) continue;
                if (auto v=vertex(a,b,c)) {
                    use(Op::C03);
                    const int center=static_cast<int>(llround(*v));
                    for (int x=center-2;x<=center+2;++x) add(x,108-abs(x-*v));
                }
                if (c-a>24) {
                    use(Op::C05); add(a+static_cast<int>((c-a)*0.382),71);
                    add(a+static_cast<int>((c-a)*0.618),71);
                }
            }
            vector<int> near;
            for (int x:f.x) if (abs(x-best)<=40) near.push_back(x);
            if (auto v=fittedVertex(near)) {
                const int center=static_cast<int>(llround(*v));
                for (int x=center-2;x<=center+2;++x) add(x,105-abs(x-*v));
            }
            if (f.halfLeft>0 && f.halfRight>0 &&
                max(f.halfLeft,f.halfRight)>1.6*min(f.halfLeft,f.halfRight)) {
                use(Op::C07);
                const int side=f.halfLeft>f.halfRight ? -1 : 1;
                const int radius=min(40,static_cast<int>(max(f.halfLeft,f.halfRight)/2));
                for (int offset=17;offset<=radius;++offset) add(best+side*offset,67-0.1*offset);
            }
        }
        if (f.plateau) { use(Op::G05); add(clamp((n-1)/2,f.plateauLeft,f.plateauRight),112); }
        if (f.flat) {
            use(Op::G02); add((n-1)/2,130);
            for (int x=0;x<n;++x) if (abs(x-best)>3 && priority[x]<110) priority[x]=-1;
        }
        if (bestValue==VMAX) {
            use(Op::H06);
            for (int x=0;x<=rightmost;++x)
                if (tieBetter(x,best)) add(x,100-0.05*abs(2*x-(n-1)));
        }
        if (f.noisy || state==Shape::Broad || state==Shape::Rough) use(Op::E07);
        if (overlap) { use(Op::D08); use(Op::J08); }
        vector<Point> result;
        for (int x=0;x<n;++x) if (priority[x]>=0) result.push_back({x,priority[x],cluster[x]});
        if (static_cast<int>(result.size())<=QMAX-1-q) use(Op::C08);
        return result;
    }
    vector<Scenario> scenarios(const Features& f) {
        use(Op::K06); vector<Scenario> result;
        for (int s=0;s<6;++s) {
            Scenario c; c.value.assign(n,static_cast<long long>(f.floor));
            for (size_t i=1;i<f.x.size();++i) {
                const int a=f.x[i-1], b=f.x[i];
                for (int x=a;x<=b;++x) {
                    const double t=static_cast<double>(x-a)/(b-a);
                    double prediction=value[a]+t*(value[b]-value[a]);
                    if (s && x!=a && x!=b) {
                        const double u=static_cast<double>(random64()>>11)/9007199254740992.0;
                        const double uncertainty=max(f.noise,0.015*f.contrast);
                        prediction+=sin(3.14159265358979323846*t)*uncertainty*
                            (s%2 ? 2*u-0.5 : 1.5*u);
                    }
                    c.value[x]=static_cast<long long>(llround(clamp(prediction,0.0,static_cast<double>(VMAX))));
                }
            }
            for (int x:f.x) c.value[x]=value[x];
            for (int x=1;x<n;++x) if (better(x,c.value[x],c.target,c.value[c.target])) c.target=x;
            result.push_back(move(c));
        }
        return result;
    }
    bool routeSafe(const vector<int>& path) {
        use(Op::I02);
        if (q+static_cast<int>(path.size())+1>QMAX) return false;
        int p=pos,d=direction,o=turns; long long m=travel;
        for (int x:path) {
            if (x<0 || x>rightmost || value[x]>=0) return false;
            moveTo(x,p,d,o,m);
        }
        return o+1<=OMAX; // One turn suffices to park at any observed winner.
    }
    vector<int> canonical(vector<int> plan,bool descending) const {
        sort(plan.begin(),plan.end()); plan.erase(unique(plan.begin(),plan.end()),plan.end());
        if (descending) reverse(plan.begin(),plan.end());
        return plan;
    }
    vector<int> orient(vector<int> plan,bool preferredDescending) {
        use(Op::J06);
        vector<int> preferred=canonical(plan,preferredDescending);
        vector<int> alternate=canonical(move(plan),!preferredDescending);
        auto cost=[&](const vector<int>& path) {
            if (!routeSafe(path)) return numeric_limits<long long>::max();
            int p=pos,d=direction,o=turns; long long m=travel;
            for (int x:path) moveTo(x,p,d,o,m);
            if (best>=0) moveTo(best,p,d,o,m);
            return m-travel+o-turns;
        };
        return cost(alternate)<cost(preferred) ? alternate : preferred;
    }
    double planScore(const vector<int>& path,const vector<Scenario>& cases,const vector<Point>& candidates) {
        if (!routeSafe(path)) return -1e30;
        use(Op::K01);
        double total=0,worst=3000;
        for (const auto& c:cases) {
            int p=pos,d=direction,o=turns,winner=best;
            long long m=travel,winnerValue=bestValue;
            for (int x:path) {
                moveTo(x,p,d,o,m);
                if (better(x,c.value[x],winner,winnerValue)) { winner=x; winnerValue=c.value[x]; }
            }
            const int parking=p==winner?0:1;
            if (parking) moveTo(winner,p,d,o,m);
            const int distance=abs(p-c.target), redundancy=max(0,rightmost-c.target);
            double score=0;
            if (q+static_cast<int>(path.size())+parking<=QMAX && o<=OMAX && distance<=3 && redundancy<=199)
                score=max(0.0,3000.0-200*distance-q-static_cast<int>(path.size())-parking-m-o-redundancy);
            total+=score; worst=min(worst,score);
        }
        // This finite model ensemble is a heuristic, not a calibrated distribution.
        double coverage=0;
        if (!path.empty()) for (const auto& point:candidates) {
            int gap=n;
            for (int x:path) gap=min(gap,abs(x-point.x));
            coverage+=point.priority/(1+gap);
        }
        return 0.9*total/cases.size()+0.1*worst+
            0.12*coverage/max(size_t{1},candidates.size());
    }
    vector<int> selectPlan(const vector<Point>& candidates,int budget,bool descending,const Features& f) {
        use(Op::I05); use(Op::J04); use(Op::J05);
        if (budget<=0 || candidates.empty()) return {};
        if (static_cast<int>(candidates.size())<=budget) {
            vector<int> all;
            for (const auto& point:candidates) all.push_back(point.x);
            return orient(move(all),descending);
        }
        use(Op::E03); use(Op::K04);
        vector<Point> ranked=candidates;
        sort(ranked.begin(),ranked.end(),[](const Point& a,const Point& b) {
            return a.priority!=b.priority ? a.priority>b.priority : a.x<b.x;
        });
        vector<int> plan; vector<bool> picked(n,false),eligible(n,false);
        for (const auto& point:candidates) eligible[point.x]=true;
        auto pick=[&](int x) {
            if (!picked[x] && static_cast<int>(plan.size())<budget) { picked[x]=true; plan.push_back(x); }
        };
        map<int,Point> representative;
        for (const auto& point:ranked) if (point.cluster>=0 && !representative.count(point.cluster))
            representative.emplace(point.cluster,point);
        vector<Point> separated;
        for (const auto& entry:representative) separated.push_back(entry.second);
        sort(separated.begin(),separated.end(),[](const Point& a,const Point& b) {
            return a.priority>b.priority;
        });
        for (int i=0;i<min(static_cast<int>(separated.size()),budget/5);++i) pick(separated[i].x);
        const int highQuota=min(budget,max(7,budget/3));
        for (const auto& point:ranked) {
            if (static_cast<int>(plan.size())>=highQuota) break;
            pick(point.x);
        }
        use(Op::B08); use(Op::E07);
        const int slots=budget-static_cast<int>(plan.size());
        for (int i=0;i<slots;++i)
            pick(candidates[min(candidates.size()-1,static_cast<size_t>((i+0.5)*candidates.size()/max(1,slots)))].x);
        for (const auto& point:ranked) pick(point.x);
        plan=canonical(move(plan),descending);
        if (!routeSafe(plan)) { use(Op::J07); return {}; }
        const auto cases=scenarios(f);
        double score=planScore(plan,cases,candidates),bestScore=score;
        vector<int> winner=plan;
        const int minimum=min(budget,max(7,budget*4/5));
        for (int iteration=0;iteration<112 && seconds()<6.8;++iteration) {
            vector<int> proposal=plan;
            switch (iteration%8) {
            case 0:
                use(Op::L01);
                if (static_cast<int>(proposal.size())<budget)
                    proposal.push_back(candidates[randomInt(static_cast<int>(candidates.size()))].x);
                break;
            case 1:
                use(Op::L02);
                if (static_cast<int>(proposal.size())>minimum)
                    proposal.erase(proposal.begin()+randomInt(static_cast<int>(proposal.size())));
                break;
            case 2: {
                use(Op::L03);
                if (!proposal.empty()) {
                    const int i=randomInt(static_cast<int>(proposal.size()));
                    const int x=proposal[i]+(randomInt(2)?1:-1);
                    if (x>=0 && x<n && eligible[x]) proposal[i]=x;
                }
                break;
            }
            case 3: {
                use(Op::L04); int target=candidates.front().x,gap=-1;
                for (const auto& point:candidates) {
                    int nearest=n;
                    for (int x:proposal) nearest=min(nearest,abs(x-point.x));
                    if (nearest>gap) { gap=nearest; target=point.x; }
                }
                if (!proposal.empty()) proposal[randomInt(static_cast<int>(proposal.size()))]=target;
                break;
            }
            case 4: {
                use(Op::L05);
                if (proposal.size()>=2) {
                    int closest=1;
                    for (size_t i=2;i<proposal.size();++i)
                        if (abs(proposal[i]-proposal[i-1])<abs(proposal[closest]-proposal[closest-1]))
                            closest=static_cast<int>(i);
                    proposal[closest]=candidates[randomInt(static_cast<int>(candidates.size()))].x;
                }
                break;
            }
            case 5:
                use(Op::L06); use(Op::B05); proposal.clear();
                for (int i=0;i<budget;++i) {
                    const size_t at=(static_cast<size_t>(i)*candidates.size()/budget+
                                     static_cast<size_t>(iteration/8))%candidates.size();
                    proposal.push_back(candidates[at].x);
                }
                break;
            case 6:
                use(Op::L07);
                // Replace coverage sampling by a ranked-local subplan, or vice versa.
                proposal.clear();
                for (int i=0;i<budget;++i) {
                    if ((iteration/8)%2) proposal.push_back(ranked[i].x);
                    else proposal.push_back(candidates[static_cast<size_t>(i)*candidates.size()/budget].x);
                }
                break;
            default:
                use(Op::L08); use(Op::J07);
                if (static_cast<int>(proposal.size())>minimum) proposal.pop_back();
                break;
            }
            proposal=canonical(move(proposal),descending);
            if (static_cast<int>(proposal.size())<minimum || !routeSafe(proposal)) continue;
            const double candidateScore=planScore(proposal,cases,candidates);
            const double temperature=30.0*pow(0.03,iteration/111.0);
            const double u=(static_cast<double>(random64()>>11)+0.5)/9007199254740992.0;
            if (candidateScore>=score || log(u)<(candidateScore-score)/temperature) {
                plan=move(proposal); score=candidateScore;
            }
            if (score>bestScore) { bestScore=score; winner=plan; }
        }
        bool neighborsKnown=true;
        for (int x=max(0,best-3);x<=min(rightmost,best+3);++x)
            if (value[x]<0) neighborsKnown=false;
        if (neighborsKnown && !f.noisy && bestScore<=planScore({},cases,candidates)) {
            use(Op::K07); return {};
        }
        return orient(move(winner),descending);
    }
    void refine() {
        if (bestValue<VMAX && q<188) {
            Features f=features();
            auto it=lower_bound(f.x.begin(),f.x.end(),best);
            bool uniquePeak=true;
            for (int x:f.peaks) if (abs(x-best)>32 && value[x]>bestValue-0.25*f.contrast) uniquePeak=false;
            if (uniquePeak && !f.plateau && f.significant && f.noise<0.05*f.contrast &&
                it!=f.x.begin() && it!=f.x.end() && next(it)!=f.x.end()) {
                vector<int> near;
                for (int x:f.x) if (abs(x-best)<=24) near.push_back(x);
                auto v1=vertex(*prev(it),*it,*next(it));
                auto v2=fittedVertex(near);
                if (v1 && v2 && abs(*v1-*v2)<10.0) {
                    const int center=static_cast<int>(llround((*v1+*v2)/2));
                    const int modelLo=max(0,min(center-3,static_cast<int>(floor(min(*v1,*v2)))-3));
                    const int modelHi=min(rightmost,max(center+3,static_cast<int>(ceil(max(*v1,*v2)))+3));
                    vector<int> probe;
                    for (int x=modelHi;x>=modelLo;--x)
                        if (value[x]<0) probe.push_back(x);
                    if (routeSafe(probe)) {
                        for (int x:probe) if (!sample(x)) return;
                        if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;
                    }
                }
            }
        }
        for (int round=0;round<2 && q<QMAX-1 && seconds()<7.5;++round) {
            if (certificate()) return;
            Features f=features();
            vector<Point> candidates=pool(f);
            if (candidates.empty()) break;
            const int available=QMAX-1-q;
            int budget=available;
            if (round==0 && static_cast<int>(candidates.size())>available)
                budget=max(7,available-min(48,available/3));
            const bool descending=round==0;
            if (descending) use(Op::J02); else use(Op::J03);
            vector<int> plan=selectPlan(candidates,budget,descending,f);
            if (plan.empty() || !routeSafe(plan)) break;
            bool progress=false;
            for (int x:plan) {
                if (!sample(x)) break;
                progress=true;
                if (certificate()) return;
            }
            if (!progress) break;
        }
    }
    void finish() {
        use(Op::I07);
        if (alive && best>=0 && pos!=best) readReal(best,true);
        cout<<"DONE\n"<<flush;
        if (trace) {
            cerr<<"TRACE {\"queries\":"<<q<<",\"travel\":"<<travel<<",\"oscillations\":"<<turns
                <<",\"rightmost\":"<<rightmost<<",\"coarse_frontier\":"<<coarseFrontier
                <<",\"position\":"<<pos<<",\"best\":"<<best<<",\"certified_left\":"<<certifiedLeft()
                <<",\"strict\":"<<(strict?"true":"false")<<",\"late_flat\":"<<(lateFlat?"true":"false")
                <<",\"old_peak_risk\":"<<(oldPeakRisk?"true":"false")<<",\"states\":{";
            for (size_t i=0;i<visits.size();++i) {
                if (i) cerr<<',';
                cerr<<'"'<<shapeNames[i]<<"\":"<<visits[i];
            }
            cerr<<"},\"operators\":{"; bool first=true;
            for (size_t i=0;i<uses.size();++i) if (uses[i]) {
                if (!first) cerr<<',';
                first=false; cerr<<'"'<<opNames[i]<<"\":"<<uses[i];
            }
            cerr<<"}}\n";
        }
    }
public:
    Solver(int length,bool diagnostics,bool certified,bool delayed)
        : n(length),value(length,-1),trace(diagnostics),strict(certified),lateFlat(delayed) {
        rng^=static_cast<uint64_t>(n)*1000003ULL;
    }
    void run() {
        if (n<=198) { for (int x=0;x<n;++x) if (!sample(x)) break; }
        else { explore(); if (alive) refine(); }
        finish();
    }
};
} // namespace af

int main(int argc,char** argv) {
    ios::sync_with_stdio(false); cin.tie(nullptr);
    bool trace=false,strict=false,late=false;
    for (int i=1;i<argc;++i) {
        const string arg=argv[i];
        if (arg=="--trace") trace=true;
        else if (arg=="--strict-redundancy") strict=true;
        else if (arg=="--late-flat") late=true;
    }
    int n;
    if (!(cin>>n) || n<=0 || n>1000) return 0;
    af::Solver(n,trace,strict,late).run();
    return 0;
}
