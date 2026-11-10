"""Freeze an independent pilot-and-exhaust interval refinement architecture."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
parent=ROOT/'data/versions/main_online_216258.cpp'
text=parent.read_text(encoding='utf-8-sig')
start=text.index('    void refine() {')
end=text.index('    void finish() {',start)
replacement=r'''    void refine() {
        if (certificate()) return;
        Features initial=features();
        if (initial.flat) {
            const int center=(n-1)/2;
            if (center<=rightmost) sample(center);
            return;
        }
        struct Cell { int a,b; double score; };
        auto cellsFor=[&](const Features& f) {
            vector<Cell> cells;
            const double allowance=max(6*f.noise,0.15*f.contrast);
            const double localReward=max(1.0,max(f.noise,0.01*f.contrast));
            for (size_t i=1;i<f.x.size();++i) {
                const int a=f.x[i-1],b=f.x[i];
                if (b-a<=1) continue;
                const long long high=max(value[a],value[b]);
                if (high<bestValue-allowance) continue;
                const double distance=min(abs(a-best),abs(b-best));
                // Raw endpoint evidence plus a local allocation preference;
                // neither is a certified upper bound for unseen narrow peaks.
                cells.push_back({a,b,static_cast<double>(high)+localReward/(1+distance)});
            }
            sort(cells.begin(),cells.end(),[](const Cell& a,const Cell& b) {
                if (a.score!=b.score) return a.score>b.score;
                if (a.b-a.a!=b.b-b.a) return a.b-a.a<b.b-b.a;
                return a.a<b.a;
            });
            return cells;
        };
        const int available=QMAX-1-q;
        const int pilotBudget=min(24,available/3);
        vector<int> pilot;
        for (const Cell& c:cellsFor(initial)) {
            if (static_cast<int>(pilot.size())>=pilotBudget) break;
            pilot.push_back((c.a+c.b)/2);
        }
        pilot=canonical(move(pilot),true);
        if (routeSafe(pilot)) for (int x:pilot) {
            if (!sample(x) || certificate()) return;
        }
        for (int pass=0;pass<2 && q<QMAX-1 && seconds()<7.5;++pass) {
            const Features f=features();
            const int left=QMAX-1-q;
            const int budget=pass ? left : left-min(24,left/4);
            vector<int> plan;
            for (const Cell& c:cellsFor(f)) {
                const int needed=c.b-c.a-1;
                if (static_cast<int>(plan.size())+needed>budget) continue;
                for (int x=c.a+1;x<c.b;++x) plan.push_back(x);
            }
            if (plan.empty()) break;
            // Complete cells in monotone motor passes, then rerank real data.
            plan=canonical(move(plan),pass==1);
            if (!routeSafe(plan)) break;
            for (int x:plan) if (!sample(x) || certificate()) return;
        }
    }
'''
text=text[:start]+replacement+text[end:]
p=ROOT/'data/experiments/blackbox_20261102/interval_tournament.cpp'
raw=text.encode('utf-8')
if p.exists() and p.read_bytes()!=raw: raise RuntimeError('Frozen source differs')
p.write_bytes(raw)
info=dict(parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),description='Replace model-finish and point-plan annealing by interval pilot tournament: <=24 midpoint pilots, rerank raw evidence, exhaust complete competitive cells in two monotone passes. Coarse216258 unchanged; reserve final parking and rerank between passes. Heuristic interval scores, not hidden-peak guarantees.')
p.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
