"""Derive independent refinement stop-loss experiments from the frozen baseline."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PARENT = ROOT / "data/versions/main_online_210599.cpp"
PARENT_SHA256 = "55f74d74926c235485d16ddb31e5e073a4fbde7ad0b71159410fa80429ad23ed"
parent_bytes = PARENT.read_bytes()
if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
    raise RuntimeError(f"Frozen parent hash mismatch: {PARENT}")
source = parent_bytes.decode("utf-8").replace("\r\n", "\n")


def emit(name: str, candidate: str, newline: str = "\n") -> None:
    """Existing experimental bytes are immutable; only verify a rerun."""
    path = OUT / f"{name}.cpp"
    expected = candidate.replace("\n", newline).encode("utf-8")
    if path.exists():
        if path.read_bytes() != expected:
            raise RuntimeError(f"Refusing to overwrite a different candidate: {path}")
    else:
        path.write_bytes(expected)

helper = r'''
    // Heuristic finite-model stop-loss, not a proof about unobserved maxima.
    // Shadow feature/scenario evaluation must not perturb the parent policy.
    bool suffixStop(const vector<int>& suffix) {
        SCOPE_GUARD
        if (suffix.empty() || best<0) return false;
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
            if (abs(x-best)>32 && value[x]>bestValue-0.25*fresh.contrast)
                eligible=false;
        bool stop=false;
        if (eligible) {
            const auto cases=scenarios(fresh);
            const vector<Point> noCoverageBonus;
            // Both alternatives include their actual final parking movement.
            const double parkingScore=planScore({},cases,noCoverageBonus);
            const double suffixScore=planScore(suffix,cases,noCoverageBonus);
            stop=parkingScore>=suffixScore;
        }
        rng=savedRng; state=savedState; pending=savedPending; votes=savedVotes;
        visits=savedVisits; uses=savedUses;
        return stop;
    }
'''
old_loop = '''            for (int x:plan) {
                if (!sample(x)) break;
                progress=true;
                if (certificate()) return;
            }'''
new_loop = '''            for (size_t at=0;at<plan.size();++at) {
                if (!sample(plan[at])) break;
                progress=true;
                if (certificate()) return;
                if (suffixStop(vector<int>(plan.begin()+static_cast<ptrdiff_t>(at+1),plan.end()))) {
                    use(Op::K07); return;
                }
            }'''
assert source.count(old_loop) == 1
for name, scope in (("short_suffix", "if (n>500) return false;"), ("all_suffix", "")):
    candidate=source.replace("    void refine() {",helper.replace("SCOPE_GUARD",scope)+"    void refine() {",1)
    candidate=candidate.replace(old_loop,new_loop,1)
    emit(name,candidate)

old_probe='''                        for (int x:probe) if (!sample(x)) return;
                        if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;'''
new_probe='''                        // Complete a continuous integer window around both
                        // predicted centers and the observed winner. This is a
                        // local model heuristic, not a global-maximum proof.
                        const int predicted1=static_cast<int>(llround(*v1));
                        const int predicted2=static_cast<int>(llround(*v2));
                        auto completeWindow=[&]() {
                            if (bestValue>=VMAX || best<=modelLo || best>=modelHi) return false;
                            const int lo=max(0,min({best,predicted1,predicted2})-3);
                            const int hi=min(n-1,max({best,predicted1,predicted2})+3);
                            // Do not weaken coverage by clipping to the probe.
                            if (lo<modelLo || hi>modelHi) return false;
                            for (int x=lo;x<=hi;++x) if (value[x]<0) return false;
                            return true;
                        };
                        for (int x:probe) {
                            if (!sample(x)) return;
                            if (completeWindow()) { use(Op::K07); return; }
                        }
                        // Preserve the original fallback when validation fails.
                        if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;'''
assert source.count(old_probe)==1
emit("model_window",source.replace(old_probe,new_probe,1))

# Both stop rules are applied independently to their original refinement phases.
combined=source.replace("    void refine() {",helper.replace("SCOPE_GUARD","")+"    void refine() {",1)
combined=combined.replace(old_loop,new_loop,1).replace(old_probe,new_probe,1)
emit("combined_suffix_window",combined)

# Preserve the parent's upper-bound/tie-certificate route: local neighborhoods
# do not rule out an equal VMAX closer to the canonical central tie position.
safe=combined.replace(
    "        if (suffix.empty() || best<0) return false;",
    "        if (suffix.empty() || best<0 || bestValue>=VMAX) return false;",
    1,
)
emit("safe_suffix_window",safe)

# Prespecified short-array fallback: the original short suffix policy plus the
# same VMAX exclusion, without the independent model-window experiment.
safe_short=source.replace(
    "    void refine() {",
    helper.replace("SCOPE_GUARD","if (n>500) return false;")+"    void refine() {",
    1,
).replace(old_loop,new_loop,1).replace(
    "        if (suffix.empty() || best<0) return false;",
    "        if (suffix.empty() || best<0 || bestValue>=VMAX) return false;",
    1,
)
# The independently frozen fallback used Windows CRLF; retain those exact bytes.
emit("safe_short_suffix",safe_short,newline="\r\n")

# Frozen mandatory-candidate revision: do not truncate a batch while any of its
# original high-priority probes remains unread. Keep its original CRLF bytes.
mandatory_helper=helper.replace("SCOPE_GUARD","").replace(
    "bool suffixStop(const vector<int>& suffix)",
    "bool suffixStop(const vector<int>& suffix,const vector<Point>& required)",
    1,
).replace(
    "        if (suffix.empty() || best<0) return false;",
    "        if (suffix.empty() || best<0 || bestValue>=VMAX) return false;\n"
    "        // Retain the parent's high-priority raw neighbors and model probes.\n"
    "        // A local maximum is insufficient while a mandatory probe is unread.\n"
    "        for (const auto& point:required)\n"
    "            if (point.priority>=100 && value[point.x]<0) return false;",
    1,
).replace(
    "stop=parkingScore>=suffixScore;",
    "stop=parkingScore>0 && parkingScore>=suffixScore;",
    1,
)
mandatory_loop=new_loop.replace(
    "static_cast<ptrdiff_t>(at+1),plan.end())))",
    "static_cast<ptrdiff_t>(at+1),plan.end()),candidates))",
    1,
)
mandatory=source.replace("    void refine() {",mandatory_helper+"    void refine() {",1)
mandatory=mandatory.replace(old_loop,mandatory_loop,1)
emit("mandatory_suffix",mandatory,newline="\r\n")
