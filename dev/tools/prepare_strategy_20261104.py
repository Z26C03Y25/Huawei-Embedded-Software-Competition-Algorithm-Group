"""Prepare structural ablations against the latest confirmed official winner."""
from pathlib import Path
import json,sys
from candidates_20261104 import freeze
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/experiments/blackbox_20261104"
state=json.loads((OUT/"state.json").read_text(encoding="utf-8"))
parent=ROOT/f"data/versions/main_online_{state['best_score']}.cpp"
text=parent.read_text(encoding="utf-8-sig")
name=sys.argv[1]
def change(a,b):
    global text
    if text.count(a)!=1:raise RuntimeError("Strategy anchor changed: "+a)
    text=text.replace(a,b,1)
if name=="turn_priced_plan":
    change("return m-travel+o-turns;","return m-travel+30LL*(o-turns);")
    change("-parking-m-o-redundancy);","-parking-m-30*o-redundancy);")
    description="Empirical turn pricing30 in route orientation and scenario plan scoring only. Protocol O<=6 and official-paper local ledger unchanged. Preserve all prior dispatch/signature rules and coarse/fine candidate generation. Measures full-total benefit of corrected planning cost rather than changing scored archives."
elif name=="joint_refine":
    start=text.index("        if (bestValue<VMAX && q<188) {",text.index("    void refine() {"))
    end=text.index("        for (int round=0;round<2",start)
    text=text[:start]+text[end:]
    description="Structural ablation: remove early model-agreement probe/exit; always refine through joint candidate pool with scenario route planner. Keeps original coarse scout and prior experts. Tests whether apparently smooth single-peak shortcut hides competing narrow maxima, trading extra reads against zero rescues."
elif name in {"apex_creep","apex_creep_stop"}:
    change("int flatRuns=0, adjacentReads=0;","int flatRuns=0, adjacentReads=0,apexReads=0; bool apexActive=false;")
    anchor="            int next=min({n-1,rightmost+step,limit});"
    patch="""            // Estimate where a positive slope will reach zero using local curvature.
            // Commit at most18 forward unit reads, then restore the parent cadence.
            bool nearApex=false;
            if (f.x.size()>=3 && !f.slopes.empty() && f.significant && !f.noisy &&
                f.curvature<-max(0.1,f.noise/12) && f.slopes.back()>0 && best==rightmost) {
                const int gap=f.x.back()-f.x[f.x.size()-2];
                const double distance=f.slopes.back()*gap/(-f.curvature);
                nearApex=distance<=12.0;
            }
            if (nearApex) apexActive=true;
            if (apexActive && apexReads<18 && rightmost-best<=3 && !f.rebound) {
                step=1;++apexReads;
            }
"""
    if name=="apex_creep_stop":
        patch+="""            if (apexActive && apexReads>=3 && rightmost-best>=3 &&
                f.falls>=2 && !f.rebound && !rival && f.significant && !f.noisy) break;
"""
    change(anchor,patch+anchor)
    description="Adaptive near-apex unit sweep: slope/curvature predicts summit<=12 positions ahead, spend<=18 forward unit reads through a3-position descent, then retain parent search. All length/signature experts preserved. No backward repeated noise samples."
    if name.endswith("_stop"):description+=" After validated3-position descending bracket, hand off to original refinement early; heuristic may miss a later summit."
else:raise ValueError(name)
freeze(name,parent,text,description)
