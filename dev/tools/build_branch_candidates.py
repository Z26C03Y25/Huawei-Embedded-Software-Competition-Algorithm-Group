"""Generate isolated branch operators and a portfolio from a frozen local parent."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'data/experiments/robust_total_20261026/flat175_desc.cpp'
OUT=ROOT/'data/experiments/branch_lab_20261026'

def change(text,old,new):
    if text.count(old)!=1:raise ValueError('Expected exactly one patch target: '+old[:70])
    return text.replace(old,new)

def build(name,stair=False,rival=False,noise=False,edge=False,rival_clean_only=False,edge_model_guard=False):
    text=PARENT.read_text(encoding='utf-8')
    text=change(text,'    array<int,7> visits{};','    array<int,7> visits{};\n    array<int,4> branchUses{};')
    text=change(text,r'            cerr<<"}}\n";',r'''            cerr<<"}}\n";
            cerr<<"BRANCHES {\"stair\":"<<branchUses[0]<<",\"rival\":"<<branchUses[1]
                <<",\"noise\":"<<branchUses[2]<<",\"edge\":"<<branchUses[3]<<"}\n";''')
    if stair:
        text=change(text,'            monotoneLimit=min(n-1,f.plateauRight+175);',r'''            double smallest=static_cast<double>(VMAX),largest=0;
            for (size_t i=1;i<f.x.size();++i) {
                const double drop=static_cast<double>(value[f.x[i-1]]-value[f.x[i]]);
                if (drop>0) { smallest=min(smallest,drop);largest=max(largest,drop); }
            }
            const bool stair=f.equalSteps>=max(3,static_cast<int>(f.slopes.size()/3)) &&
                             smallest>0 && largest<=2.25*smallest;
            if (stair) { monotoneLimit=min(n-1,f.plateauRight+175);++branchUses[0]; }''')
    if rival:
        text=change(text,'            auto it=lower_bound(f.x.begin(),f.x.end(),best);',r'''            if (f.significant && !f.flat && f.peaks.size()>1) {
                int rival=-1;
                for (int x:f.peaks) if (abs(x-best)>=8 && abs(x-best)<=32 &&
                    value[x]>=bestValue-max(3*f.noise,0.06*f.contrast) &&
                    (rival<0 || better(x,value[x],rival,value[rival]))) rival=x;
                if (rival>=0) {
                    vector<int> audit;
                    for (int center:{best,rival}) for (int x=max(0,center-3);x<=min(rightmost,center+3);++x)
                        if (value[x]<0) audit.push_back(x);
                    sort(audit.begin(),audit.end(),greater<int>());
                    audit.erase(unique(audit.begin(),audit.end()),audit.end());
                    if (!audit.empty() && audit.size()<=12 && routeSafe(audit)) {
                        ++branchUses[1];
                        for (int x:audit) { if (!sample(x)) return; if (certificate()) return; }
                        f=features();
                    }
                }
            }
            auto it=lower_bound(f.x.begin(),f.x.end(),best);''')
    if rival_clean_only:
        text=change(text,'if (f.significant && !f.flat && f.peaks.size()>1)',
                    'if (f.significant && !f.flat && !f.noisy && f.peaks.size()>1)')
    if noise:
        text=change(text,'                    const int modelLo=', '                    int modelLo=')
        text=change(text,'                    const int modelHi=', '                    int modelHi=')
        text=change(text,'                    const int coarseWinner=best;',r'''                    const int oldLo=modelLo,oldHi=modelHi;
                    if (f.noisy) {
                        const int a=*prev(it),b=*it,c=*next(it);
                        const double sl=static_cast<double>(value[b]-value[a])/(b-a);
                        const double sr=static_cast<double>(value[c]-value[b])/(c-b);
                        const double curvature=abs((sr-sl)/(c-a));
                        const int radius=clamp(static_cast<int>(ceil(min(8.0,sqrt(2*f.noise/max(1e-9,curvature))))),3,8);
                        modelLo=max(0,modelLo-(radius-3));modelHi=min(rightmost,modelHi+(radius-3));
                    }
                    const int coarseWinner=best;''')
        text=change(text,'                    if (routeSafe(probe)) {',r'''                    if (!routeSafe(probe) && (modelLo!=oldLo || modelHi!=oldHi)) {
                        modelLo=oldLo;modelHi=oldHi;probe.clear();
                        for (int x=modelHi;x>=modelLo;--x) if (value[x]<0) probe.push_back(x);
                    }
                    if (routeSafe(probe)) {
                        if (modelLo!=oldLo || modelHi!=oldHi) ++branchUses[2];''')
    if edge:
        text=change(text,'    void refine() {',r'''    vector<int> plateauEntry(const Features& f) const {
        if (!f.significant || f.flat || f.right-f.left<40) return {};
        map<long long,vector<int>> levels;
        for (int x:f.x) if (value[x]>=bestValue-max(3*f.noise,0.06*f.contrast) &&
                           value[x]>f.floor+0.5*f.contrast) levels[value[x]].push_back(x);
        int first=n;
        for (const auto& level:levels) if (level.second.size()>=3 &&
            level.second.back()-level.second.front()>=24) first=min(first,level.second.front());
        vector<int> audit;
        if (first<n) for (int x=first+1;x<=min(rightmost,first+3);++x) if (value[x]<0) audit.push_back(x);
        return audit;
    }
    void refine() {''')
        text=change(text,'            if (plan.empty() || !routeSafe(plan)) break;',r'''            if (round==0 && !plan.empty()) {
                auto extra=plateauEntry(f);
                if (!extra.empty()) {
                    vector<int> trial=plan;trial.insert(trial.end(),extra.begin(),extra.end());
                    sort(trial.begin(),trial.end(),greater<int>());
                    trial.erase(unique(trial.begin(),trial.end()),trial.end());
                    if (trial.size()>plan.size() && routeSafe(trial)) { plan=move(trial);++branchUses[3]; }
                }
            }
            if (plan.empty() || !routeSafe(plan)) break;''')
    if edge_model_guard:
        text=change(text,'if (uniquePeak && !f.plateau && f.significant',
                    'if (uniquePeak && plateauEntry(f).empty() && !f.plateau && f.significant')
    path=OUT/(name+'.cpp');raw=text.replace('\n','\r\n').encode('utf-8')
    if path.exists() and path.read_bytes()!=raw:raise ValueError('Frozen candidate differs; choose a new name')
    path.write_bytes(raw)
    info=dict(name=name,source=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),
        parent_sha256=hashlib.sha256((ROOT/'data/versions/main_online_203239.cpp').read_bytes()).hexdigest(),
        derived_local_parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
        switches=dict(stair=stair,rival=rival,noise=noise,edge=edge,rival_clean_only=rival_clean_only,edge_model_guard=edge_model_guard),official_score=None,
        parameters=dict(stair_equal_min=3,stair_equal_fraction=1/3,stair_drop_ratio=2.25,
            rival_distance=[8,32],rival_max_gap_contrast=.06,rival_radius=3,rival_max_reads=12,
            noise_radius=[3,8],noise_scale=2,edge_equal_witnesses=3,edge_span_min=24,edge_reads=3),
        note='Only observed replies/features, query and route ledger. No case names, generator IDs, seeds or hidden target access.')
    (OUT/(name+'.json')).write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    return info

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    infos=[build('stair_gate',stair=True),build('rival_audit',rival=True),
           build('noise_radius',noise=True),build('plateau_route',edge=True),
           build('portfolio',stair=True,rival=True,noise=True,edge=True),
           build('noise_rival',noise=True,rival=True),
           build('noise_rival_tree',noise=True,rival=True,rival_clean_only=True),
           build('plateau_guard',edge=True,edge_model_guard=True)]
    (OUT/'candidates.json').write_text(json.dumps(infos,indent=2)+'\n',encoding='utf-8')
    print('Created isolated operators and portfolio:',[x['name'] for x in infos])
if __name__=='__main__':main()