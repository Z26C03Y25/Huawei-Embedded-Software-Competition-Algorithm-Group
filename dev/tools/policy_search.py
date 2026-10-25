"""Reproducible policy mutations and verified online-score bookkeeping.

Every generated policy starts from the immutable 159487-point archive. This
tool never uploads; automation/online_judge/judge.py remains the only submission path.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/versions/main_strategy_159487.cpp"
OUT = ROOT / "data/versions/online_search"
BASE_HASH = "d98855c0f56b0c302f939252804ac8e7b38080e39bd06d43014020f1a8877336"


def generate(name, config):
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_HASH:
        raise ValueError("Graded baseline changed")
    s = BASE.read_text(encoding="utf-8")
    def replace(a, b):
        nonlocal s
        if a == b:
            return
        if s.count(a) != 1:
            raise ValueError(f"Mutation target is not unique: {a}")
        s = s.replace(a, b)
    defaults = {"flat":144, "coarse":88, "up":12, "down":8, "noise_step":12,
                "flat_step":16, "guard":180, "prom":12, "scout_min":96,
                "scout_max":144, "scout_width":1.2, "edge":48, "band_noise":3,
                "band_contrast":0.04, "band_offset":0.02, "group":0.45,
                "radius":16, "rounds":2, "reserve":48, "anneal":True,
                "initial":[0,4,12,24], "trend":0, "noise_abs":0.8,
                "noise_local":1,"noise_global":1,"late_scout":0,
                "comp_noise":3,"comp_frac":0.04,"plateau_follow":False,
                "noise_order":2,"drop_noise":3,"drop_frac":0.08,
                "model_finish":False,"freeze_noise":False,"small_prom":0,"n_split":600,
                "small_step":0}
    unknown = set(config)-set(defaults)
    if unknown:
        raise ValueError(f"Unknown parameters: {unknown}")
    cfg = defaults | config
    if cfg == defaults:
        raise ValueError("Unchanged baseline does not need another upload")
    config={k:v for k,v in config.items() if v!=defaults[k]}
    if not 4 <= cfg["coarse"] <= 160 or not 1 <= cfg["rounds"] <= 3:
        raise ValueError("Invalid phase budget")
    if not cfg["initial"] or min(cfg["initial"])<0 or max(cfg["initial"])>199:
        raise ValueError("Initial probing must stay within [0,199]")
    replace("(n-1)/2+144", f"(n-1)/2+{cfg['flat']}")
    replace("q<88", f"q<{cfg['coarse']}")
    replace("const int remaining=88-q;", f"const int remaining={cfg['coarse']}-q;")
    replace("for (int x:{0,4,12,24})", "for (int x:{"+",".join(map(str,cfg['initial']))+"})")
    replace("step=flatRuns>=8 ? 16 : 12;", f"step=flatRuns>=8 ? {cfg['flat_step']} : 12;")
    replace("step=f.curvature<-max(0.1,f.noise/12) ? 8 : 12;",
            f"step=f.curvature<-max(0.1,f.noise/12) ? {cfg['down']} : {cfg['up']};")
    replace("if (f.noisy) step=12;", f"if (f.noisy) step={cfg['noise_step']};")
    replace("else step=f.noisy || state==Shape::Rough ? 12 : 8;",
            f"else step=f.noisy || state==Shape::Rough ? {cfg['noise_step']} : {cfg['down']};")
    if cfg['small_step']:
        replace("int next=min({n-1,rightmost+step,limit});",
                f"if (n<={cfg['n_split']}) step={cfg['small_step']};\n            int next=min({{n-1,rightmost+step,limit}});")
    replace("return min(n-1,f.left+180);", f"return min(n-1,f.left+{cfg['guard']});")
    if cfg['plateau_follow']:
        replace(f"return min(n-1,f.left+{cfg['guard']});",f'''int anchor=f.left;
        if (best<(n-1)/2 && value[rightmost]==bestValue) {{
            int repeats=0;
            for (auto it=f.x.rbegin();it!=f.x.rend() && value[*it]==bestValue;++it) ++repeats;
            if (repeats>=4) anchor=best;
        }}
        return min(n-1,anchor+{cfg['guard']});''')
    prom_expr=(f"(n<={cfg['n_split']} ? {cfg['small_prom']} : {cfg['prom']})" if cfg['small_prom'] else str(cfg['prom']))
    replace("f.significant=f.contrast>max(4.0,12*f.noise);",
            f"f.significant=f.contrast>max(4.0,{prom_expr}*f.noise);")
    replace("rightmost-best>=48", f"rightmost-best>={cfg['edge']}")
    replace("bestValue-value[rightmost]>max(3*f.noise,0.08*f.contrast)",
            f"bestValue-value[rightmost]>max({cfg['drop_noise']}*f.noise,{cfg['drop_frac']}*f.contrast)")
    replace("clamp(static_cast<int>(f.halfLeft*1.2),96,144)",
            f"clamp(static_cast<int>(f.halfLeft*{cfg['scout_width']}),{cfg['scout_min']},{cfg['scout_max']})")
    if cfg['late_scout']:
        expr=f"const int scout=clamp(static_cast<int>(f.halfLeft*{cfg['scout_width']}),{cfg['scout_min']},{cfg['scout_max']});"
        replace(expr,expr.replace('const int','int')+f"\n                if (best>=(n-1)/2) scout=min(scout,{cfg['late_scout']});")
    replace("f.tolerance=max({1.0,3*f.noise,0.04*f.contrast});",
            f"f.tolerance=max({{1.0,{cfg['comp_noise']}*f.noise,{cfg['comp_frac']}*f.contrast}});")
    replace("max({1.0,3*f.noise+0.02*f.contrast,0.04*f.contrast})",
            f"max({{1.0,{cfg['band_noise']}*f.noise+{cfg['band_offset']}*f.contrast,{cfg['band_contrast']}*f.contrast}})")
    replace("bestValue-max(6*f.noise,0.45*f.contrast)",
            f"bestValue-max(6*f.noise,{cfg['group']}*f.contrast)")
    replace("for (int x=best-16;x<=best+16;++x)",
            f"for (int x=best-{cfg['radius']};x<=best+{cfg['radius']};++x)")
    replace("round<2", f"round<{cfg['rounds']}")
    replace("available-min(48,available/3)", f"available-min({cfg['reserve']},available/3)")
    replace("0.8*median(absoluteResidual)", f"{cfg['noise_abs']}*median(absoluteResidual)")
    if cfg['noise_global']!=1 or cfg['noise_local']!=1:
        replace("mad(residual),mad(local)",f"{cfg['noise_global']}*mad(residual),{cfg['noise_local']}*mad(local)")
    if cfg['noise_order']==3:
        replace("f.contrast=bestValue-f.floor; f.flat=f.contrast==0;",'''if (f.x.size()>=11) {
            vector<double> high;
            for (size_t i=2;i+2<f.x.size();++i) {
                const int center=f.x[i];
                const int near[]={f.x[i-2],f.x[i-1],f.x[i+1],f.x[i+2]};
                double predicted=0,variance=1;
                for (int j=0;j<4;++j) {
                    double weight=1;
                    for (int k=0;k<4;++k) if (k!=j)
                        weight*=static_cast<double>(center-near[k])/(near[j]-near[k]);
                    predicted+=weight*value[near[j]];variance+=weight*weight;
                }
                high.push_back((value[center]-predicted)/sqrt(variance));
            }
            residual=move(high);
        }
        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;''')
        marker=f"f.tolerance=max({{1.0,{cfg['comp_noise']}*f.noise,{cfg['comp_frac']}*f.contrast}});"
        replace(marker,"if (f.x.size()>=11) f.noise*=1.2247448714;\n        "+marker)
    if cfg['freeze_noise']:
        replace("void refine() {","void refine() {\n        const double frozenNoise=features().noise;")
        replace("Features f=features();\n            vector<Point> candidates=pool(f);",
                "Features f=features();\n            f.noise=max(f.noise,frozenNoise);\n            f.noisy=f.noise>max(1.0,0.01*f.contrast);\n            vector<Point> candidates=pool(f);")
    if cfg['model_finish']:
        replace("void refine() {",'''void refine() {
        if (bestValue<VMAX && q<188) {
            Features f=features();
            auto it=lower_bound(f.x.begin(),f.x.end(),best);
            bool uniquePeak=true;
            for (int x:f.peaks) if (abs(x-best)>32 && value[x]>bestValue-0.25*f.contrast) uniquePeak=false;
            if (uniquePeak && !f.plateau && f.significant && f.noise<0.005*f.contrast &&
                it!=f.x.begin() && it!=f.x.end() && next(it)!=f.x.end()) {
                vector<int> near;
                for (int x:f.x) if (abs(x-best)<=32) near.push_back(x);
                auto v1=vertex(*prev(it),*it,*next(it));
                auto v2=fittedVertex(near);
                if (v1 && v2 && abs(*v1-*v2)<0.75) {
                    const int center=static_cast<int>(llround((*v1+*v2)/2));
                    vector<int> probe;
                    for (int x=min(rightmost,center+6);x>=max(0,center-6);--x)
                        if (value[x]<0) probe.push_back(x);
                    if (routeSafe(probe)) {
                        for (int x:probe) if (!sample(x)) return;
                        if (certificate() || (bestValue<VMAX && abs(best-center)<=5)) return;
                    }
                }
            }
        }''')
    if not cfg["anneal"]:
        replace("const auto cases=scenarios(f);", "return orient(move(plan),descending);\n        const auto cases=scenarios(f);")
    if cfg["trend"]:
        factor = cfg["trend"]
        block = f'''\n        vector<double> trend;
        for (size_t i=0;i<f.x.size();++i) {{
            vector<double> window;
            const size_t lo=i ? i-1 : 0, hi=min(f.x.size()-1,i+1);
            for (size_t j=lo;j<=hi;++j) window.push_back(static_cast<double>(value[f.x[j]]));
            trend.push_back(median(move(window)));
        }}
        if (trend.size()>=7) {{
            auto sorted=trend; sort(sorted.begin(),sorted.end());
            if (sorted.back()-sorted[sorted.size()/5]>max(4.0,{factor}*f.noise)) f.significant=true;
        }}'''
        target = f"f.significant=f.contrast>max(4.0,{prom_expr}*f.noise);"
        replace(target, target+block)
    OUT.mkdir(exist_ok=True)
    path = OUT / (name+".cpp")
    data = ("// Online policy: "+json.dumps(config, sort_keys=True)+"\n"+s).encode("utf-8")
    if path.exists() and path.read_bytes()!=data:
        raise ValueError("Never overwrite an existing experiment")
    path.write_bytes(data)
    info = {"name":name,"config":config,"path":str(path),"sha256":hashlib.sha256(data).hexdigest()}
    path.with_suffix(".json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
    return info


def record(job_id, name=None):
    j = json.loads((ROOT/"automation/online_judge/runs"/job_id/"job.json").read_text(encoding="utf-8"))
    if j["state"] != "completed" or not isinstance(j.get("score"),int):
        raise ValueError("Record only independently confirmed completed jobs")
    snapshot = Path(j["snapshot_path"]).read_bytes()
    if hashlib.sha256(snapshot).hexdigest()!=j["sha256"]:
        raise ValueError("Snapshot hash mismatch")
    OUT.mkdir(exist_ok=True)
    archive=OUT/f"scored_{j['score']}_{j['sha256'][:12]}.cpp"
    if archive.exists() and archive.read_bytes()!=snapshot:
        raise ValueError("Score archive collision")
    archive.write_bytes(snapshot)
    p = OUT/"results.json"
    rows = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    row = {"job_id":job_id,"name":name or job_id,"score":j["score"],"sha256":j["sha256"],
           "submission_id":j.get("bound_submission_id"),"submitted_at":j["record"]["submitted_at"],
           "source_path":j["source_path"]}
    for key in ("ranking_after", "ranking_error"):
        if key in j:
            row[key] = j[key]
    manifest=Path(j["source_path"]).with_suffix(".json")
    row["config"]=json.loads(manifest.read_text(encoding="utf-8")).get("config",{}) if manifest.exists() else {}
    if not any(x["job_id"]==job_id for x in rows): rows.append(row)
    p.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    best = max(rows,key=lambda x:x["score"])
    if best["score"]>159487:
        contents=(ROOT/"automation/online_judge/runs"/best["job_id"]/"main.cpp").read_bytes()
    else:
        contents=BASE.read_bytes()
    (ROOT/"main.cpp").write_bytes(contents)
    lines=["# 持续线上优化记录", "", "仅记录线上任务连续确认完成后的正式成绩；源码快照不可变。", "",
           f"当前最高正式分：**{max(159487,best['score'])}**。main.cpp 自动保留最高正式分源码。", "",
           "| 时间（北京时间） | 实验 | 正式分数 | 参数 | 源码 SHA256 |", "| --- | --- | ---: | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['submitted_at']} | {r['name']} | {r['score']} | {json.dumps(r.get('config',{}),ensure_ascii=False)} | {r['sha256']} |")
    (ROOT/'docs/持续线上优化记录.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {"recorded":row,"best_score":max(159487,best["score"])}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    g=sub.add_parser("generate"); g.add_argument("name"); g.add_argument("config")
    r=sub.add_parser("record"); r.add_argument("job_id"); r.add_argument("--name")
    a=parser.parse_args()
    result=generate(a.name,json.loads(a.config)) if a.command=="generate" else record(a.job_id,a.name)
    print(json.dumps(result,ensure_ascii=False,indent=2))
