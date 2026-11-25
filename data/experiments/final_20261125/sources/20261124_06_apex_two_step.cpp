#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <numeric>
#include <vector>
using namespace std;

struct Tuning {
    int step, confirmation, model, background, extent, refine, entry, zoom;
    double drop, rivals;
};
constexpr Tuning tuning = {10, 16, 8, 1, 58, 1, 0, 8, 0.18, 0.07};

class Focus {
    struct Sample { int x; long long y; };
    struct Gap { int a,b; double merit; };
    const int size;
    vector<long long> readback;
    vector<Sample> track;
    int parked=0, direction=0, flips=0, count=0, top=-1;
    bool ok=true;

    bool better(int a,int b) const {
        if (b<0 || readback[a]!=readback[b]) return b<0 || readback[a]>readback[b];
        const int da=abs(2*a-size+1),db=abs(2*b-size+1);
        return da!=db ? da<db : a<b;
    }
    bool read(int x,bool parking=false) {
        if (!ok || x<0 || x>=size || count>=199 || (!parking && count>=198)) return false;
        if (!parking && readback[x]>=0) return true;
        const int next=(x>parked)-(x<parked);
        const int nextFlips=flips+int(next && direction && next!=direction);
        const int back=(top>x)-(top<x);
        if (nextFlips+int(!parking && top>=0 && back && (next ? next : direction) &&
                         back!=(next ? next : direction))>6) return false;
        cout<<x<<endl;
        long long val;
        if (!(cin>>val) || val<0 || val>2147483647LL) { ok=false;return false; }
        readback[x]=val;
        parked=x;
        flips=nextFlips;
        if (next) direction=next;
        ++count;
        if (better(x,top)) top=x;
        return true;
    }
    bool extend(int x) {
        if (!read(x)) return false;
        track.push_back({x,readback[x]});
        return true;
    }
    static double median(vector<double> items) {
        if (items.empty()) return 0;
        nth_element(items.begin(),items.begin()+items.size()/2,items.end());
        return items[items.size()/2];
    }
    static double slope(Sample a,Sample b) { return double(b.y-a.y)/(b.x-a.x); }
    struct Signal {
        double low, height, noise, drop, speed, previous, riseFromLow;
        int halfLeft, halfRight, tailCount, falling, rising, lastBest;
        bool flat, significant, quietPrefix;
    };
    Signal measure() const {
        Signal s{};
        const int m=int(track.size());
        vector<double> levels,errors;
        for (const Sample point:track) levels.push_back(point.y);
        sort(levels.begin(),levels.end());
        s.low=levels[levels.size()/8];
        s.height=readback[top]-s.low;
        for (int k=1;k+1<m;++k) {
            const auto a=track[k-1],b=track[k],c=track[k+1];
            errors.push_back(b.y-a.y-slope(a,c)*(b.x-a.x));
        }
        const double center=median(errors);
        for (double& e:errors) e=abs(e-center);
        s.noise=max(1.0,median(errors)*1.4826);
        s.flat=levels.back()-levels.front()<=1;
        s.significant=s.height>max(4.0,(tuning.model==3?6.0:12.0)*s.noise);
        s.drop=readback[top]-track.back().y;
        s.speed=m>=2 ? slope(track[m-2],track.back()) : 0;
        s.previous=m>=3 ? slope(track[m-3],track[m-2]) : 0;
        double rightBase=readback[top];
        s.lastBest=top;
        for (int k=0;k<m;++k) {
            const auto p=track[k];
            if (p.y==readback[top]) s.lastBest=p.x;
            if (p.x<top && p.y<=readback[top]-s.height/2) s.halfLeft=top-p.x;
            if (p.x>top) {
                ++s.tailCount;
                rightBase=min(rightBase,double(p.y));
                if (!s.halfRight && p.y<=readback[top]-s.height/2) s.halfRight=p.x-top;
            }
            if (k && p.x>top && k>=m-4) {
                const auto rise=p.y-track[k-1].y;
                if (rise>max(s.noise*1.5,0.008*s.height)) ++s.rising;
                if (rise<-max(s.noise*1.5,0.008*s.height)) ++s.falling;
            }
        }
        s.riseFromLow=track.back().y-rightBase;
        if (tuning.background && m>=4 && top<=track[1].x && track.back().y<=track.front().y) {
            const double trend=slope(track[0],track[3]);
            const double slack=max({2.0,3*s.noise,abs(trend)*track[3].x*0.08});
            const bool feasible=track[0].y+trend*(size-1)>slack;
            if (feasible && trend<0) {
                int outliers=0;
                for (int k=1;k<=3;++k)
                    outliers+=abs(track[k].y-(track[0].y+trend*track[k].x))>slack;
                const double departure=track.back().y-(track[0].y+trend*track.back().x);
                s.quietPrefix=outliers<=(tuning.background==2?1:0) &&
                    departure>=-slack*(1.0+double(track.back().x)/track[3].x);
            }
        }
        return s;
    }
    bool enough(const Signal& s,int right) const {
        if (s.quietPrefix || !s.significant || right<=s.lastBest || s.tailCount<2 ||
            s.rising>1 || s.riseFromLow>max(3*s.noise,0.025*s.height)) return false;
        int confirmation=tuning.confirmation;
        if (tuning.model==1) confirmation=max(confirmation,min(90,s.halfLeft));
        if (tuning.model==2 && s.halfRight) confirmation=min(confirmation,max(6,s.halfRight));
        if (tuning.model==4 && (s.falling<3 || !s.halfRight)) return false;
        if (tuning.model==7) {
            if (!s.halfRight || s.falling<2) return false;
            confirmation=max(confirmation,min(76,(s.halfLeft+s.halfRight)/2));
        }
        if (tuning.model==8) {
            const bool sharp=s.halfRight && s.halfLeft &&
                max(s.halfLeft,s.halfRight)<=2*min(s.halfLeft,s.halfRight)+tuning.step;
            const bool local=top>0 && top<size-1 && readback[top-1]>=0 && readback[top+1]>=0 &&
                readback[top]>max(readback[top-1],readback[top+1]);
            if (local && sharp && !s.rising) confirmation=min(confirmation,8);
            else if (s.falling<3 || !s.halfRight) return false;
        }
        if (tuning.model==9) {
            if (s.drop<0.45*s.height || (s.falling<3 && s.drop<0.70*s.height)) return false;
            if (s.halfLeft) confirmation=max(confirmation,min(80,s.halfLeft));
        }
        if (tuning.model==10) {
            const int width=max(tuning.step,s.halfLeft);
            confirmation=max(confirmation,min(85,width));
            if (!s.halfRight || s.falling<2 || s.rising) return false;
        }
        if (tuning.model==11) {
            if (s.rising || s.falling<2) return false;
            const double slopeDrop=-s.speed*tuning.step;
            if (s.drop<max(0.42*s.height,2.0*slopeDrop) && !s.halfRight) return false;
            confirmation=max(confirmation,min(72,s.halfLeft));
        }
        if (tuning.model==12) {
            if (s.rising || s.falling<2) return false;
            const bool balanced=s.halfLeft && s.halfRight &&
                max(s.halfLeft,s.halfRight)<=2*min(s.halfLeft,s.halfRight)+tuning.step;
            if (balanced) confirmation=min(confirmation,max(8,s.halfRight));
            else if (s.drop<0.70*s.height) return false;
        }
        if (tuning.model==13) {
            if (!s.halfRight || s.rising || s.falling<2) return false;
            if (s.halfRight>2*max(s.halfLeft,tuning.step))
                confirmation=max(confirmation,min(96,s.halfRight+tuning.step));
            else confirmation=max(confirmation,min(64,s.halfRight));
        }
        if (tuning.model>=14) {
            const bool local=top>0 && top+1<size && readback[top-1]>=0 && readback[top+1]>=0 &&
                readback[top]>max(readback[top-1],readback[top+1]);
            const bool balanced=s.halfLeft && s.halfRight &&
                max(s.halfLeft,s.halfRight)<=2*min(s.halfLeft,s.halfRight)+tuning.step;
            if (s.rising) return false;
            if (tuning.model==14) {
                if (local && s.falling>=2) confirmation=min(confirmation,10);
                else if (!s.halfRight || s.falling<3) return false;
            }
            if (tuning.model==15) {
                if (balanced && s.falling>=2) confirmation=min(confirmation,max(8,s.halfRight));
                else if (s.falling<3 || (!s.halfRight && s.drop<0.65*s.height)) return false;
            }
            if (tuning.model==16) {
                if (local && balanced) confirmation=min(confirmation,8);
                else if (!s.halfRight || s.falling<2) return false;
                if (s.drop<0.5*s.height && s.speed>=s.previous*0.4) return false;
            }
            if (tuning.model==17) {
                if (local && balanced) confirmation=min(confirmation,10);
                else if (s.falling<3 || !s.halfRight)
                    confirmation=max(confirmation,min(70,max(24,s.halfLeft)));
                if (!local && !balanced && s.drop<0.55*s.height) return false;
            }
            if (tuning.model==18) {
                if (local && balanced) confirmation=min(confirmation,8);
                else if (!s.halfRight || s.falling<3) return false;
                else if (s.halfRight>2*max(s.halfLeft,tuning.step))
                    confirmation=max(confirmation,min(60,s.halfRight+tuning.step));
            }
        }
        if (tuning.model==5 && s.rising) return false;
        return right-s.lastBest>=confirmation &&
               s.drop>max(4*s.noise,tuning.drop*s.height) &&
               (s.falling>=2 || (s.falling>=1 && s.drop>0.65*s.height));
    }
    void scan() {
        const array<int,4> seeds=tuning.entry==1 ? array<int,4>{0,2,7,17} :
            tuning.entry==2 ? array<int,4>{0,7,15,26} : array<int,4>{0,4,11,23};
        for (int x:seeds) if (x<size && !extend(x)) return;
        const int budget=std::clamp(198-tuning.extent,90,160);
        int sampledAt=-1;
        while (ok && count<budget && track.back().x<size-1) {
            const Signal s=measure();
            const int right=track.back().x;
            int boundary=size-1;
            if (s.significant && !s.quietPrefix)
                boundary=min(boundary,s.lastBest+192);
            if (s.flat) boundary=min(boundary,(size-1)/2+192);
            if (right>=boundary) break;
            if (enough(s,right)) {
                if (tuning.model==6 && sampledAt!=top && right<top+65 &&
                    s.speed>=s.previous*0.3 && s.drop<0.7*s.height) {
                    const int target=min(boundary,right+max(8,tuning.step));
                    sampledAt=top;
                    if (extend(target)) continue;
                }
                break;
            }
            int step=tuning.step;
            if (s.quietPrefix) step=max(step,tuning.background==3 ? 20 : 12);
            if (s.flat) step=max(step,tuning.zoom==3 ? 16 : 9);
            if (s.significant && top==right && s.speed>0 && s.previous>s.speed) {
                const auto a=track[track.size()-2];
                const double toTop=s.speed*(right-a.x)/(s.previous-s.speed);
                if (toTop<2*step && tuning.zoom)
                    step=max(tuning.zoom==2?1:2,min(step,int(toTop+1)/2));
            }
            if (tuning.zoom>=2 && s.significant && right>top && right-top<=3 && s.drop<0.2*s.height)
                step=min(step,2);
            if (tuning.zoom>=5 && s.significant && right>top && right-top<=3 &&
                s.drop<0.18*s.height) step=2;
            if (tuning.zoom==5 && !s.significant && !s.flat)
                step=max(step,14);
            if (tuning.zoom==6 && s.significant && s.rising>=1 && s.riseFromLow>4*s.noise)
                step=max(4,step/2);
            if (tuning.zoom==7 && !s.significant && !s.flat)
                step=max(step,16)+(count%2);
            if (tuning.zoom==4 && !s.flat && !s.significant)
                step=max(2,step+(count%3-1));
            if (tuning.zoom==8 && s.significant && right>=top && right-top<=2 &&
                s.drop<0.14*s.height && s.speed<=s.previous && track.size()>=5)
                step=min(step,2);
            if (tuning.zoom==9 && s.significant && s.rising && s.riseFromLow>max(4*s.noise,0.05*s.height))
                step=min(step,5);
            if (tuning.zoom==10 && s.significant && top==right && s.speed>0 && s.previous>s.speed)
                step=min(step,3);
            if (tuning.zoom==11 && s.significant && right>top && s.falling>=2 && s.drop>0.6*s.height)
                step=min(step,6);
            if (tuning.zoom==12 && s.significant && top==right && s.speed>s.previous && s.previous>0)
                step=min(step,7);
            if (top==right && count>budget/2)
                step=max(step,(size-1-right+budget-count-1)/(budget-count));
            int next=min(boundary,right+step);
            const int middle=(size-1)/2;
            if (s.flat && right<middle && next>middle) next=middle;
            if (!extend(next)) return;
        }
    }
    void searchGaps() {
        if (track.size()<2 || top<0) return;
        const Signal s=measure();
        vector<Gap> gaps;
        const double peak=readback[top], slack=max(3*s.noise,tuning.rivals*s.height);
        for (size_t i=1;i<track.size();++i) {
            const auto a=track[i-1],b=track[i];
            if (b.x-a.x<=1) continue;
            const double chord=slope(a,b);
            double upper=max(a.y,b.y);
            if (tuning.refine>=1 && i>=2 && i+1<track.size()) {
                const double up=slope(track[i-2],a),down=slope(b,track[i+1]);
                if (up>max(0.0,chord) && down<min(0.0,chord)) {
                    const double dx=(b.y-a.y-down*(b.x-a.x))/(up-down);
                    upper=max(upper,a.y+up*dx);
                }
                if (tuning.refine==2)
                    upper+=0.2*(b.x-a.x)*max(abs(chord-up),abs(down-chord));
            }
            const int distance=max({0,a.x-top,top-b.x});
            const bool adjacent=distance==0;
            const double travel=max(0,top-b.x);
            double localSlack=slack;
            if (tuning.refine==4 && !adjacent) localSlack=max(2*s.noise,slack-travel*0.002*s.height);
            if (tuning.refine==5 && !adjacent && abs(a.x-top)>3*tuning.step)
                localSlack*=0.45;
            if (adjacent || upper>=peak-localSlack) {
                double merit=upper-(distance ? 0.02*distance : 0);
                if (adjacent) merit+=s.height+slack;
                gaps.push_back({a.x,b.x,merit});
            }
        }
        sort(gaps.begin(),gaps.end(),[](const Gap& a,const Gap& b){
            return a.merit!=b.merit ? a.merit>b.merit : a.a>b.a;
        });
        if (tuning.refine==3) {
            for (auto& gap:gaps)
                gap.merit-=0.08*(gap.b-gap.a-1)*max(1.0,s.noise);
            sort(gaps.begin(),gaps.end(),[](const Gap& a,const Gap& b) {
                return a.merit!=b.merit ? a.merit>b.merit : a.a>b.a;
            });
        }
        vector<int> plan;
        const int limit=min(tuning.extent,198-count);
        for (const Gap& g:gaps) {
            if (int(plan.size())+g.b-g.a-1>limit) {
                if (tuning.refine==6 && int(plan.size())<limit) plan.push_back((g.a+g.b)/2);
                continue;
            }
            for (int x=g.a+1;x<g.b;++x) plan.push_back(x);
        }
        sort(plan.rbegin(),plan.rend());
        for (int x:plan) {
            if (!read(x)) break;
            if (readback[top]==2147483647LL && top==(size-1)/2) break;
        }
    }
public:
    explicit Focus(int n):size(n),readback(n,-1) {}
    void run() {
        scan();
        if (ok) searchGaps();
        if (ok && top>=0 && parked!=top) read(top,true);
        if (ok) cout<<"DONE"<<endl;
    }
};
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (cin>>n && n>0 && n<=1000) Focus(n).run();
}


