"""Freeze genuinely dual-speed coarse/fine candidates from the216258 parent."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/experiments/blackbox_20261102"
PARENT = ROOT / "data/versions/main_online_216258.cpp"


def freeze(name: str, text: str, description: str) -> None:
    path = OUT / f"{name}.cpp"
    raw = text.encode("utf-8")
    if path.exists() and path.read_bytes() != raw:
        raise RuntimeError(f"frozen candidate differs: {path}")
    path.write_bytes(raw)
    metadata = {
        "parent": str(PARENT),
        "parent_sha256": hashlib.sha256(PARENT.read_bytes()).hexdigest(),
        "source": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "description": description,
    }
    path.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False))


def make(name: str) -> None:
    if name == "cruise15_fine1":
        cruise, fine_step, fine_budget = 15, 1, 36
        cruise_expr, loop_budget = str(cruise), "112+fineReads"
    elif name == "cruise10_fine2":
        cruise, fine_step, fine_budget = 10, 2, 32
        cruise_expr, loop_budget = str(cruise), "112+fineReads"
    elif name == "cruise5_fine1":
        cruise, fine_step, fine_budget = 5, 1, 19
        # The contest-specific prior places useful peaks by roughly index900.
        # A179-read coarse allowance reaches about899 from the seed layout;
        # fine reads are charged separately up to the hard198 pre-parking cap.
        cruise_expr, loop_budget = "5", "179+fineReads"
    else:
        raise ValueError(name)

    text = PARENT.read_text(encoding="utf-8-sig")
    start = text.index("    void explore() {")
    end = text.index("    optional<double> vertex", start)
    explore = r'''    void explore() {
        use(Op::B01); use(Op::J01);
        for (int x:{0,4,12,24}) {
            if (x>=n || !sample(x)) break;
            if (certificate()) return;
        }
        const int cruiseStep=CRUISE_STEP;
        const int fineStep=FINE_STEP;
        const int fineBudget=FINE_BUDGET;
        int fineReads=0,backfills=0,forwardSweeps=0;
        vector<int> anchors=observed();
        while (q<LOOP_BUDGET && rightmost<n-1 && seconds()<7.0) {
            const Features f=features();
            if (certificate()) return;
            int limit=frontierLimit(f);
            const bool rival=coarseRivalEvidence(f);
            if (rival) {
                const int released=min(n-1,min(best+191,rightmost+48));
                if (released>limit) {
                    limit=released; ++rivalReleases;
                    rivalMaxBeyondBest=max(rivalMaxBeyondBest,released-best);
                }
            }
            if (rightmost>=limit) break;

            if (!f.flat) {
                if (f.leftEdge && rightmost-best>=48) { use(Op::H01); break; }
                int scout=n<=500 ? clamp(static_cast<int>(f.halfLeft*0.3),16,32)
                    : (n<=650 ? clamp(static_cast<int>(f.halfLeft*1.05),80,112)
                              : clamp(static_cast<int>(f.halfLeft*1.2),96,144));
                if (best>=(n-1)/2) scout=min(scout,16);
                if (f.halfLeft>0 && f.halfRight>0 && f.falls>=3 && f.rises==0 && !f.rebound) {
                    const int observedTail=max(16,static_cast<int>(ceil(1.5*f.halfRight)));
                    scout=min(max(16,scout/2),observedTail);
                }
                if (f.significant && rightmost-best>=scout && !f.rebound && !rival &&
                    bestValue-value[rightmost]>max(3*f.noise,0.08*f.contrast)) {
                    use(Op::K07); break;
                }
            }

            const int frontier=rightmost;
            bool swept=false;
            // If a cruise step has just crossed a record anchor, fill the
            // complete skipped cell backwards. This is the narrow-peak safety
            // path; it is intentionally limited to two cells.
            if (fineReads<fineBudget && backfills<2 && anchors.size()>=7) {
                const int c=anchors.back(), b=anchors[anchors.size()-2];
                const long long drop=value[b]-value[c];
                const double threshold=max(1.0,1.5*f.noise);
                bool previousRecord=true;
                for (size_t i=0;i+2<anchors.size();++i)
                    if (value[anchors[i]]>value[b]) previousRecord=false;
                if (c==frontier && c-b>=cruiseStep-1 && previousRecord && drop>threshold) {
                    const int needed=(c-b-1+fineStep-1)/fineStep;
                    if (needed>0 && fineReads+needed<=fineBudget) {
                        for (int x=c-fineStep;x>b;x-=fineStep) {
                            if (!sample(x)) { coarseFrontier=rightmost; return; }
                            ++fineReads;
                            if (certificate()) { coarseFrontier=rightmost; return; }
                        }
                        ++backfills; swept=true;
                    }
                }
            }

            // While still rising, use two successive coarse slopes to predict
            // a nearby concave summit. Commit only when the predicted summit
            // is no farther than one cruise cell plus five positions.
            if (!swept && fineReads<fineBudget && forwardSweeps<2 && anchors.size()>=7) {
                const int c=anchors.back(), b=anchors[anchors.size()-2], a=anchors[anchors.size()-3];
                if (c==frontier && a<b && b<c && best==c) {
                    const double s1=static_cast<double>(value[b]-value[a])/(b-a);
                    const double s2=static_cast<double>(value[c]-value[b])/(c-b);
                    const double bend=(s2-s1)/(c-a);
                    if (s1>0 && s2>0 && bend<0 && s2<=0.82*s1) {
                        const double peak=(a+b)/2.0-s1/(2*bend);
                        if (isfinite(peak) && peak>c && peak<=c+cruiseStep+5) {
                            int target=min(limit,max(c+4,static_cast<int>(ceil(peak))+4));
                            int consecutiveFalls=0;
                            long long previous=value[c];
                            for (int x=c+fineStep;x<=target && fineReads<fineBudget;x+=fineStep) {
                                if (!sample(x)) { coarseFrontier=rightmost; return; }
                                ++fineReads;
                                consecutiveFalls=value[x]<previous ? consecutiveFalls+1 : 0;
                                previous=value[x];
                                if (consecutiveFalls>=3 && x>=static_cast<int>(floor(peak))) break;
                            }
                            // A forecast that ended on a rise gets one small
                            // bounded extension instead of declaring failure.
                            if (fineReads<fineBudget && rightmost>=target &&
                                value[rightmost]>value[max(c,rightmost-fineStep)]) {
                                const int extension=min(limit,rightmost+4*fineStep);
                                for (int x=rightmost+fineStep;x<=extension && fineReads<fineBudget;x+=fineStep) {
                                    if (!sample(x)) { coarseFrontier=rightmost; return; }
                                    ++fineReads;
                                }
                            }
                            ++forwardSweeps; swept=true;
                        }
                    }
                }
            }
            if (swept) continue;

            int next=min({n-1,rightmost+cruiseStep,limit});
            const int center=(n-1)/2;
            if (f.flat && rightmost<center && next>center) { next=center; use(Op::G02); }
            if (next==n-1) { use(Op::B07); use(Op::H02); }
            if (next<=rightmost || !sample(next)) break;
            anchors.push_back(next);
        }
        coarseFrontier=rightmost;
    }
'''
    explore = (explore.replace("CRUISE_STEP", cruise_expr)
               .replace("FINE_STEP", str(fine_step))
               .replace("FINE_BUDGET", str(fine_budget))
               .replace("LOOP_BUDGET", loop_budget))
    text = text[:start] + explore + text[end:]
    description = (
        f"Independent dual-speed exploration: cruise {cruise} cells in short/mid low-information regions "
        f"({cruise_expr} by N), "
        f"then switch to stride {fine_step} near a predicted concave summit. On the first descent from "
        f"a record anchor, backfill the entire skipped cell to recover narrow peaks. Failed sweeps resume "
        f"cruising; at most two forward/two backward sweeps and {fine_budget} fine reads. Preserve raw "
        "winner, proven ledgers, N-dependent tail stopping, legacy refinement and parking."
    )
    freeze(name, text, description)


if __name__ == "__main__":
    make(sys.argv[1])
