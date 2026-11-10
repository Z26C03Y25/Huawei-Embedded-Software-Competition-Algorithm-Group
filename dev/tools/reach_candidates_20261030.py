"""Larger optional reach/coverage experiments for the 2026-10-30 online queue.

Exports ``variants`` with name, description, interpretation and apply(source).
No submission or incumbent edit occurs here. Anchor mismatches are errors.
The two rival-reach variants deliberately permit irreversible R>199 relative to
the old winner in default mode; strong trend evidence is not a proof that a new
true peak exists. Strict mode and the original transport ledger stay unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

if __package__:
    from .structure_candidates_20261030 import AnchorError, replace_once, variant
else:
    from structure_candidates_20261030 import AnchorError, replace_once, variant


def rival_reach(source: str, maximum: int) -> str:
    if maximum not in (223, 255):
        raise ValueError("Unsupported frozen reach")
    # The second alternative can replay from an accepted first alternative.
    # Both boundary anchors must agree before changing either one.
    if "    int coarseRivalEvidence(const Features& f) {" in source:
        matches = re.findall(r"const int reach=strong \? (223|255) : 191;", source)
        if len(matches) != 1:
            raise AnchorError("Unrecognized incumbent rival-reach implementation")
        previous = int(matches[0])
        if previous == maximum:
            raise AnchorError("Rival-reach boundary already matches requested experiment")
        source = replace_once(source,
            f"best<0 || rightmost-best<48 || rightmost-best>={previous}) return false;",
            f"best<0 || rightmost-best<48 || rightmost-best>={maximum}) return false;")
        return replace_once(source,
            f"const int reach=strong ? {previous} : 191;",
            f"const int reach=strong ? {maximum} : 191;")
    source = replace_once(source,
        "    bool coarseRivalEvidence(const Features& f) {",
        "    int coarseRivalEvidence(const Features& f) {")
    source = replace_once(source,
        "best<0 || rightmost-best<48 || rightmost-best>=191) return false;",
        f"best<0 || rightmost-best<48 || rightmost-best>={maximum}) return false;")
    source = replace_once(source,
        "        return level[2]>=bestValue-0.15*f.contrast;",
        r'''        // Weak evidence retains the parent's 191-position lease.
        // Only two stronger median-block rises may expose the old peak beyond
        // the official redundancy bound. This is a deliberate heuristic risk.
        const double strongRise=max(3*f.noise,0.01*f.contrast);
        const bool strong=level[1]-level[0]>strongRise && level[2]-level[1]>strongRise;
        const int reach=strong ? MAXIMUM_REACH : 191;
        if (rightmost-best>=reach) return 0;
        return level[2]>=bestValue-0.15*f.contrast ? reach : 0;'''.replace("MAXIMUM_REACH", str(maximum)))
    source = replace_once(source,
        "            const bool rival=coarseRivalEvidence(f);",
        "            const int rival=coarseRivalEvidence(f);")
    return replace_once(source,
        "const int released=min(n-1,min(best+191,rightmost+48));",
        "const int released=min(n-1,min(best+rival,rightmost+48));")


def cluster_height_025(source: str) -> str:
    return replace_once(source,
        "if (value[p]<bestValue-max(6*f.noise,0.1*f.contrast))",
        "if (value[p]<bestValue-max(6*f.noise,0.25*f.contrast))")


def cluster_distance_8(source: str) -> str:
    # A plain distance control, deliberately without a new valley condition.
    return replace_once(source, "abs(p-other)<=24", "abs(p-other)<=8")


def model_gap_audit(source: str) -> str:
    return replace_once(source, r'''                    for (int x=modelHi;x>=modelLo;--x)
                        if (value[x]<0) probe.push_back(x);
                    if (routeSafe(probe)) {''', r'''                    for (int x=modelHi;x>=modelLo;--x)
                        if (value[x]<0) probe.push_back(x);
                    // Audit two large unobserved cells near the peak even when
                    // both endpoints look low. This does not exclude hidden
                    // spikes away from the audited midpoint.
                    vector<array<int,3>> auditGaps;
                    for (size_t i=1;i<f.x.size();++i) {
                        const int a=f.x[i-1],b=f.x[i],mid=(a+b)/2;
                        if (b-a<4 || abs(mid-best)>64 ||
                            (mid>=modelLo && mid<=modelHi) || value[mid]>=0) continue;
                        auditGaps.push_back({b-a,-abs(mid-best),mid});
                    }
                    sort(auditGaps.begin(),auditGaps.end(),greater<array<int,3>>());
                    for (size_t i=0;i<min(size_t{2},auditGaps.size());++i)
                        probe.push_back(auditGaps[i][2]);
                    probe=canonical(move(probe),true);
                    if (routeSafe(probe)) {''')


def n_firstpass_budget(source: str) -> str:
    return replace_once(source, r'''            if (round==0 && static_cast<int>(candidates.size())>available)
                budget=max(7,available-min(48,available/3));''', r'''            // Spend more of the available fine-search coverage in the first
            // pass and cap a short-array return trip. Coarse Q=128 is unchanged.
            if (round==0 && static_cast<int>(candidates.size())>available) {
                const int reserve=n<=500 ? 8 : (n<=650 ? 16 : 24);
                budget=max(7,available-min(reserve,available/3));
            }
            if (round==1) budget=min(budget,n<=500 ? 8 : (n<=650 ? 16 : 24));''')


variants = [
    variant("rival_reach_223", "强连续中位回升可释放到当前最佳点+223，弱回升仍+191", lambda s: rival_reach(s,223),
            "提分支持旧边界外存在可追踪第二峰；退分可能是旧峰真实冗余越199，无法回程修复。strict不变。"),
    variant("rival_reach_255", "强连续中位回升可释放到当前最佳点+255，弱回升仍+191", lambda s: rival_reach(s,255),
            "与223构成更大覆盖和不可逆冗余风险的对照；不是安全界，也不能同时叠加两档。"),
    variant("cluster_height_025", "竞争簇保留到最佳值减25%对比度，显著放宽原10%", cluster_height_025,
            "提分支持弱端点竞争峰值得补查；退分意味着更多弱簇消耗查询和长距离往返。"),
    variant("cluster_distance_8", "只将近峰合并距离24缩到8，不新增谷深判据", cluster_distance_8,
            "作为谷分隔策略的简明对照；提分支持近峰需独立保留，退分可能来自细纹波过度拆簇。"),
    variant("model_gap_audit", "模型收尾前审计最佳点64格内两个最大漏隙，不以低端点排除", model_gap_audit,
            "提分支持模型窗口外低端点漏隙存在原始高点；退分说明两个远端中点的额外路程不值。"),
    variant("n_firstpass_budget", "按N给首轮精修更多覆盖，第二轮最多8/16/24次", n_firstpass_budget,
            "提分支持减少后轮回程和细碎覆盖；退分说明需要依据首轮新回复保留更多重规划预算。"),
]


def validate(source_path: Path, out: Path) -> bool:
    if __package__:
        from .local_judge import make_suite, run_case
    else:
        from local_judge import make_suite, run_case
    root = Path(__file__).resolve().parents[2]
    compiler = root / "dev/toolchains/w64devkit/bin/g++.exe"
    source_bytes = source_path.read_bytes()
    source = source_bytes.decode("utf-8")
    out.mkdir(parents=True, exist_ok=True)
    report = dict(parent=str(source_path), parent_sha256=hashlib.sha256(source_bytes).hexdigest(),
                  purpose="Protocol-only smoke; no local scores used to choose variants.", variants=[])
    for item in variants:
        row = dict(name=item["name"], description=item["description"])
        try:
            text = item["apply"](source)
            path, exe = out/(item["name"]+".cpp"), out/(item["name"]+".exe")
            path.write_text(text, encoding="utf-8", newline="\n")
            row["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            args = [str(compiler), "-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17", str(path), "-o", str(exe)]
            result = subprocess.run(args, capture_output=True, text=True)
            row["build"] = dict(command=args, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
            if result.returncode or result.stderr:
                raise RuntimeError("Compiler error or warning")
            rows = []
            for case in make_suite("smoke"):
                r = run_case([str(exe)], case)
                positions = r["query_positions"]
                winner = min(positions, key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if positions else None
                ok = (r["status"] == "ok" and r["queries"]<=199 and r["oscillations"]<=6 and
                      positions and positions[-1] == winner)
                rows.append(dict(name=case.name, ok=bool(ok), status=r["status"], queries=r["queries"],
                                 oscillations=r["oscillations"], parked_observed_winner=bool(positions and positions[-1]==winner),
                                 error=r["error"]))
            row["smoke"] = rows
            row["passed"] = all(r["ok"] for r in rows)
        except (AnchorError, RuntimeError) as error:
            row.update(passed=False, error=str(error))
        report["variants"].append(row)
        print(item["name"], row["passed"], flush=True)
    (out/"protocol_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return all(row["passed"] for row in report["variants"])


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--source", type=Path, default=root/"main.cpp")
    parser.add_argument("--out", type=Path, default=root/"dev/build/reach_20261030_protocol")
    args = parser.parse_args()
    if args.validate:
        return 0 if validate(args.source.resolve(), args.out.resolve()) else 1
    for item in variants:
        print(item["name"], item["description"], item["interpretation"], sep="\t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
