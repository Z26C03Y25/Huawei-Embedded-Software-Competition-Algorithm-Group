"""Replayable structural autofocus experiments, with protocol-only smoke checks.

``variants`` is a list of dictionaries exposing name, description and
apply(source)->str. Each mutation starts from the supplied incumbent, requires
unique anchors and preserves the transport/physical-query ledger byte for byte
after newline normalization. Nothing in this module submits or edits main.cpp.

The mechanisms are heuristics, not certificates for arbitrary hidden arrays.
Run ``python/runtime/python.exe dev/tools/structure_candidates_20261030.py
--validate`` to compile each independent mutation of main.cpp and check its 26
pipe interactions. Local performance is deliberately not a selection criterion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Callable


class AnchorError(ValueError):
    pass


def replace_once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise AnchorError(f"Expected one anchor, found {count}: {old[:100]!r}")
    return source.replace(old, new, 1)


def protected(source: str) -> tuple[str, str, str]:
    def section(start: str, end: str) -> str:
        if source.count(start) != 1 or source.count(end) != 1:
            raise AnchorError(f"Missing/ambiguous protected section {start!r}")
        return source[source.index(start):source.index(end)]
    return (
        section("class Protocol {", "#define OPS(X)"),
        section("    static void moveTo(", "    vector<int> observed() const {"),
        section("constexpr long long VMAX =", "// Only this transport"),
    )


def variant(name: str, description: str, transform: Callable[[str], str],
            interpretation: str) -> dict:
    marker = f"// Structure experiment 20261030: {name}\n"

    def apply(source: str) -> str:
        source = source.replace("\r\n", "\n")
        if marker in source:
            raise AnchorError(f"Already applied: {name}")
        before = protected(source)
        changed = transform(source)
        if changed == source:
            raise AnchorError(f"Mutation had no effect: {name}")
        if protected(changed) != before:
            raise AnchorError(f"Mutation altered protected transport/ledger: {name}")
        return marker + changed

    return dict(name=name, description=description, apply=apply,
                interpretation=interpretation)


def model_residual_validate(source: str) -> str:
    source = replace_once(source, "                    vector<int> probe;", r'''                    // Validate new replies against the pre-query local quadratic.
                    // Agreement between correlated vertex models is insufficient.
                    const int qa=*prev(it),qb=*it,qc=*next(it);
                    const double qs=static_cast<double>(value[qb]-value[qa])/(qb-qa);
                    const double qr=static_cast<double>(value[qc]-value[qb])/(qc-qb);
                    const double qcurve=(qr-qs)/(qc-qa);
                    const double predictiveTolerance=max(2.0,3*f.noise+0.005*f.contrast);
                    bool predictiveMatch=true;
                    vector<int> probe;''')
    return replace_once(source, r'''                        for (int x:probe) if (!sample(x)) return;
                        if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;''', r'''                        for (int x:probe) {
                            if (!sample(x)) return;
                            const double prediction=value[qa]+qs*(x-qa)+qcurve*(x-qa)*(x-qb);
                            if (abs(value[x]-prediction)>predictiveTolerance) predictiveMatch=false;
                        }
                        if (certificate() || (predictiveMatch && bestValue<VMAX &&
                                              best>modelLo && best<modelHi)) return;''')


def model_close_peak_audit(source: str) -> str:
    return replace_once(source, r'''                    for (int x=modelHi;x>=modelLo;--x)
                        if (value[x]<0) probe.push_back(x);
                    if (routeSafe(probe)) {''', r'''                    for (int x=modelHi;x>=modelLo;--x)
                        if (value[x]<0) probe.push_back(x);
                    // Close peaks were not rejected by the distant-rival test.
                    // Audit their raw neighborhoods before model-only completion.
                    for (int p:f.peaks) {
                        if (abs(p-best)<=4 || abs(p-best)>32 ||
                            value[p]<bestValue-max(3*f.noise,0.15*f.contrast)) continue;
                        for (int x=max(0,p-3);x<=min(rightmost,p+3);++x)
                            if (value[x]<0) probe.push_back(x);
                    }
                    probe=canonical(move(probe),true);
                    if (routeSafe(probe)) {''')


def valley_separated_clusters(source: str) -> str:
    return replace_once(source,
        "            for (int other:groups) if (abs(p-other)<=24) { close=true; break; }",
        r'''            for (int other:groups) if (abs(p-other)<=24) {
                long long valley=min(value[p],value[other]);
                for (int x:f.x) if (x>min(p,other) && x<max(p,other))
                    valley=min(valley,value[x]);
                // A resolved valley retains two nearby competing raw peaks.
                const double depth=min(value[p],value[other])-valley;
                if (depth<=max(2*f.noise,0.02*f.contrast)) { close=true; break; }
            }''')


def competitive_cell_priority(source: str) -> str:
    return replace_once(source, "        vector<int> peaks=f.peaks;", r'''        // Complete the immediate interpolation cell around competitive maxima
        // before spending a limited plan on lower-priority broad interiors.
        for (size_t i=1;i+1<f.x.size();++i) {
            const int a=f.x[i-1],p=f.x[i],b=f.x[i+1];
            if (value[p]<value[a] || value[p]<value[b] ||
                value[p]<bestValue-max(3*f.noise,0.10*f.contrast)) continue;
            if (p-a<=8 && b-p<=8)
                for (int x=a+1;x<b;++x) add(x,111-0.1*abs(x-p));
        }
        vector<int> peaks=f.peaks;''')


NOISY_TREND_HELPER = r'''
    optional<int> noisyTrendLimit(const Features& f) const {
        if (f.flat || !f.noisy || f.significant || f.x.size()<19) return nullopt;
        vector<double> level;
        vector<int> anchors;
        for (size_t i=2;i+2<f.x.size();++i) {
            array<long long,5> block{};
            for (size_t j=0;j<5;++j) block[j]=value[f.x[i+j-2]];
            sort(block.begin(),block.end());
            level.push_back(static_cast<double>(block[2])); anchors.push_back(f.x[i]);
        }
        const size_t peak=static_cast<size_t>(max_element(level.begin(),level.end())-level.begin());
        if (peak<3 || peak+4>=level.size()) return nullopt;
        const double low=*min_element(level.begin(),level.begin()+static_cast<ptrdiff_t>(peak+1));
        const double height=level[peak]-low;
        const size_t last=level.size()-1;
        if (height<=max(8.0,4*f.noise) ||
            level[peak]-level[last]<=max(2*f.noise,0.15*height) ||
            level[last]>level[last-1]+f.noise || level[last-1]>level[last-2]+f.noise)
            return nullopt;
        // Median trend evidence limits further exposure; it does not prove a
        // raw maximum or exclude an unseen second peak. Raw winners stay intact.
        return min(n-1,anchors[peak]+176);
    }
'''


def noisy_trend_frontier(source: str) -> str:
    source = replace_once(source, "    int frontierLimit(const Features& f) {",
                          NOISY_TREND_HELPER + "    int frontierLimit(const Features& f) {")
    return replace_once(source, "        if (!f.significant) return n-1;", r'''        if (!f.significant) {
            if (auto limit=noisyTrendLimit(f)) return *limit;
            return n-1;
        }''')


def chunked_refinement(source: str) -> str:
    source = replace_once(source,
        "        for (int round=0;round<2 && q<QMAX-1 && seconds()<7.5;++round) {",
        "        for (int round=0;round<6 && q<QMAX-1 && seconds()<7.5;++round) {")
    source = replace_once(source, "            bool progress=false;\n            for (int x:plan) {",
        "            bool progress=false; int batchReads=0;\n            for (int x:plan) {")
    return replace_once(source, r'''                progress=true;
                if (certificate()) return;
            }
            if (!progress) break;''', r'''                progress=true;
                if (certificate()) return;
                // Rebuild candidates after genuinely new evidence rather than
                // blindly executing the entire old plan. Ledger limits remain.
                if (++batchReads>=12) break;
            }
            if (!progress) break;''')


def evidence_budget(source: str) -> str:
    return replace_once(source, r'''            if (round==0 && static_cast<int>(candidates.size())>available)
                budget=max(7,available-min(48,available/3));''', r'''            if (round==0 && static_cast<int>(candidates.size())>available) {
                int urgent=0;
                set<int> unresolvedGroups;
                for (const auto& point:candidates) {
                    if (point.priority>=100) ++urgent;
                    if (point.cluster>=0) unresolvedGroups.insert(point.cluster);
                }
                // Allocate the first pass to unresolved evidence. Leave the
                // remaining queries for a second pass after actual best updates.
                const int evidenceQuota=urgent+4*static_cast<int>(unresolvedGroups.size());
                budget=min(available,max(16,min(evidenceQuota,available-available/3)));
            }''')


MANDATORY_SUFFIX_HELPER = r'''
    bool structuralSuffixStop(const vector<int>& suffix,const vector<Point>& required) {
        if (suffix.empty() || best<0 || bestValue>=VMAX) return false;
        for (const auto& point:required)
            if (point.priority>=100 && value[point.x]<0) return false;
        for (int x=max(0,best-3);x<=min(n-1,best+3);++x)
            if (value[x]<0) return false;
        const auto savedRng=rng;
        const auto savedState=state,savedPending=pending;
        const int savedVotes=votes;
        const auto savedVisits=visits;
        const auto savedUses=uses;
        const Features fresh=features();
        bool eligible=fresh.significant && !fresh.noisy && !fresh.plateau;
        for (int x:fresh.peaks)
            if (abs(x-best)>32 && value[x]>bestValue-0.25*fresh.contrast) eligible=false;
        bool stop=false;
        if (eligible) {
            const auto cases=scenarios(fresh);
            const vector<Point> noCoverageBonus;
            const double parked=planScore({},cases,noCoverageBonus);
            stop=parked>0 && parked>=planScore(suffix,cases,noCoverageBonus);
        }
        rng=savedRng;state=savedState;pending=savedPending;votes=savedVotes;
        visits=savedVisits;uses=savedUses;
        // Finite interpolation scenarios are a heuristic, not a certificate.
        return stop;
    }
'''


def mandatory_suffix(source: str) -> str:
    source = replace_once(source, "    void refine() {", MANDATORY_SUFFIX_HELPER+"    void refine() {")
    return replace_once(source, r'''            for (int x:plan) {
                if (!sample(x)) break;
                progress=true;
                if (certificate()) return;
            }''', r'''            for (size_t at=0;at<plan.size();++at) {
                if (!sample(plan[at])) break;
                progress=true;
                if (certificate()) return;
                const vector<int> suffix(plan.begin()+static_cast<ptrdiff_t>(at+1),plan.end());
                if (structuralSuffixStop(suffix,candidates)) { use(Op::K07); return; }
            }''')


variants = [
    variant("model_residual_validate", "模型收尾加入新读取点的预测残差验证", model_residual_validate,
            "提分支持模型误收尾是损失来源；退分说明额外fallback成本或模型误差门槛过严。"),
    variant("model_close_peak_audit", "模型收尾前补查4至32格内竞争峰±3", model_close_peak_audit,
            "提分支持近峰被单峰收尾遗漏；退分说明额外查询/回程超过命中收益。"),
    variant("valley_separated_clusters", "近峰若有明确谷分隔则不因24格距离合并", valley_separated_clusters,
            "提分支持距离聚类吞掉近邻峰；退分说明纹波被过度拆成竞争簇。"),
    variant("competitive_cell_priority", "将竞争局部峰相邻小间隔完整补查提高到优先级111", competitive_cell_priority,
            "提分支持未读峰间单元优先；退分说明它挤占顶点或其他有效候选。"),
    variant("noisy_trend_frontier", "弱显著噪声曲线以五点中位宽趋势限制继续右探", noisy_trend_frontier,
            "提分支持粗噪声下存在可用宽趋势；退分可能是晚峰漏搜或中位峰与原始峰错位。"),
    variant("chunked_refinement", "精修按12次真实读取重建计划，最多六轮且保留原账本", chunked_refinement,
            "提分支持早期新最佳值值得重规划；退分可能来自额外反向或分批覆盖不足。"),
    variant("evidence_budget", "首轮额度按高优先级点和未决簇分配，预留后续修正", evidence_budget,
            "提分支持盲目用满首轮低价值；退分说明较小首轮使关键覆盖或后轮路线受损。"),
    variant("mandatory_suffix", "当轮高优先级候选已查完后允许正预测收益的经济止损", mandatory_suffix,
            "昨日仅离线验证；线上提分支持低价值后缀可省，退分暴露有限场景未覆盖的竞争。"),
]


def validate(source_path: Path, out: Path) -> bool:
    if __package__:
        from .local_judge import make_suite, run_case
    else:
        from local_judge import make_suite, run_case

    root = Path(__file__).resolve().parents[2]
    source_bytes = source_path.read_bytes()
    source = source_bytes.decode("utf-8")
    out.mkdir(parents=True, exist_ok=True)
    compiler = root / "dev/toolchains/w64devkit/bin/g++.exe"
    flags = ["-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17"]
    report = dict(parent=str(source_path), parent_sha256=hashlib.sha256(source_bytes).hexdigest(),
                  purpose="Compile and protocol checks only; local scores are not used for selection.",
                  compiler=str(compiler), flags=flags, variants=[])
    cases = make_suite("smoke")
    for item in variants:
        row = dict(name=item["name"], description=item["description"])
        try:
            changed = item["apply"](source)
            path, exe = out / (item["name"]+".cpp"), out / (item["name"]+".exe")
            path.write_text(changed, encoding="utf-8", newline="\n")
            row["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            build = subprocess.run([str(compiler), *flags, str(path), "-o", str(exe)],
                                   capture_output=True, text=True)
            row["build"] = dict(exit_code=build.returncode, stdout=build.stdout, stderr=build.stderr)
            if build.returncode or build.stderr:
                raise RuntimeError("Compiler error or warning; inspect build output")
            rows = []
            for case in cases:
                result = run_case([str(exe)], case)
                positions = result["query_positions"]
                winner = min(positions, key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if positions else None
                ok = (result["status"] == "ok" and result["queries"] <= 199 and
                      result["oscillations"] <= 6 and positions and positions[-1] == winner)
                rows.append(dict(name=case.name, ok=bool(ok), status=result["status"],
                                 queries=result["queries"], oscillations=result["oscillations"],
                                 parked_observed_winner=bool(positions and positions[-1] == winner),
                                 error=result["error"]))
            row["smoke"] = rows
            row["passed"] = all(r["ok"] for r in rows)
        except (AnchorError, RuntimeError) as error:
            row["passed"] = False
            row["error"] = str(error)
        report["variants"].append(row)
        print(item["name"], row["passed"], flush=True)
    (out / "protocol_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return all(row["passed"] for row in report["variants"])


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--source", type=Path, default=root/"main.cpp")
    parser.add_argument("--out", type=Path, default=root/"dev/build/structure_20261030_protocol")
    args = parser.parse_args()
    if args.validate:
        return 0 if validate(args.source.resolve(), args.out.resolve()) else 1
    for item in variants:
        print(item["name"], item["description"], item["interpretation"], sep="\t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
