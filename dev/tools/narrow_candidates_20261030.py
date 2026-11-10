"""Pure source transforms for online narrow-peak/N-budget experiments.

Import ``variants`` (a list of dictionaries with name, description and apply).
Every apply(source) returns C++ text or raises ValueError if its anchor is absent
or the same mechanism is already present. This module never uploads a source.
"""
from __future__ import annotations

from typing import Callable


def _replace(source: str, old: str, new: str, name: str) -> str:
    marker = f"// narrow_20261030:{name}"
    if marker in source:
        raise ValueError(f"{name} is already present")
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{name}: expected one anchor, found {count}")
    return source.replace(old, marker + "\n" + new, 1)


def short_flat4(source: str) -> str:
    return _replace(
        source,
        "                step=flatRuns>=8 ? 8 : 12;",
        "                step=n<=500 ? 4 : (flatRuns>=8 ? 8 : 12);",
        "short_flat4",
    )


def initial_phase23(source: str) -> str:
    return _replace(
        source,
        "        for (int x:{0,4,12,24}) {",
        "        for (int x:{0,4,11,23}) {",
        "initial_phase23",
    )


def _edits(source: str, changes: list[tuple[str, str]], name: str) -> str:
    marker = f"// narrow_20261030:{name}"
    if marker in source:
        raise ValueError(f"{name} is already present")
    for old, _ in changes:
        count = source.count(old)
        if count != 1:
            raise ValueError(f"{name}: expected one anchor, found {count}")
    for old, new in changes:
        source = source.replace(old, new, 1)
    return marker + "\n" + source


_NEXT = "            int next=min({n-1,rightmost+step,limit});"
_READ_NEXT = "            if (next<=rightmost || !sample(next)) break;"
_FLAT_COUNTER = "        int flatRuns=0;"


def short_rising_half(source: str) -> str:
    probe = r'''            // Probe before the ordinary endpoint, preserving forward motion.
            if (n<=500 && narrowShortCredits>0 && !f.flat && f.significant &&
                !f.noisy && rightmost-best<=16 && (f.rises>0 || f.rebound) &&
                next-rightmost>=6 && q+2<=128) {
                const int midpoint=rightmost+(next-rightmost)/2;
                if (!sample(midpoint)) break;
                --narrowShortCredits;
            }
'''
    return _edits(source, [
        (_FLAT_COUNTER, _FLAT_COUNTER + "\n        int narrowShortCredits=20;"),
        (_READ_NEXT, probe + _READ_NEXT),
    ], "short_rising_half")


def acceleration_half(source: str) -> str:
    probe = r'''            // Allocate a few extra samples to an accelerating positive flank.
            if (narrowAccelerationCredits>0 && !f.flat && f.slopes.size()>=2 &&
                next-rightmost>=6 && q+2<=128) {
                const double recent=f.slopes.back();
                const double before=f.slopes[f.slopes.size()-2];
                if (before>=0 && recent>max(2*f.noise/max(1,step),1.6*before) &&
                    recent>0 && rightmost-best<=16) {
                    const int midpoint=rightmost+(next-rightmost)/2;
                    if (!sample(midpoint)) break;
                    --narrowAccelerationCredits;
                }
            }
'''
    return _edits(source, [
        (_FLAT_COUNTER, _FLAT_COUNTER + "\n        int narrowAccelerationCredits=n<=500 ? 20 : (n<=650 ? 12 : 6);"),
        (_READ_NEXT, probe + _READ_NEXT),
    ], "acceleration_half")


def sparse_phase_walk(source: str) -> str:
    prefix = r'''            // One seven-position stride per eight real reads walks grid phase.
            // Other strides stay eight; this is not a global seven-position grid.
            if (!f.flat && step==8 && q%8==(n/8)%8) step=7;
'''
    return _replace(source, _NEXT, prefix + _NEXT, "sparse_phase_walk")


def quantized_step4(source: str) -> str:
    return _replace(
        source,
        "                    use(Op::G07); step=min(step,8);",
        "                    use(Op::G07); step=min(step,4);",
        "quantized_step4",
    )


def bracket_midpoint_once(source: str) -> str:
    anchor = "            const Features f=features();\n            if (certificate()) return;"
    audit = r'''            // A single bracket check can cost two turns; retain four for later.
            // All real movement still goes through the original canRead ledger.
            if (!narrowBracketAudited && !f.flat && f.significant && !f.noisy &&
                rightmost>best && rightmost-best<=16 && f.falls>0 &&
                turns<=2 && q<126) {
                const auto peak=lower_bound(f.x.begin(),f.x.end(),best);
                if (peak!=f.x.begin() && peak!=f.x.end() && next(peak)!=f.x.end()) {
                    const int left=*prev(peak),right=*next(peak);
                    const int probe=best-left>right-best ? (left+best)/2 : (best+right)/2;
                    if (probe>=0 && value[probe]<0 && canRead(probe,false)) {
                        narrowBracketAudited=true;
                        if (!sample(probe)) break;
                        continue; // Recompute features before any forward action.
                    }
                }
            }
'''
    return _edits(source, [
        (_FLAT_COUNTER, _FLAT_COUNTER + "\n        bool narrowBracketAudited=false;"),
        (anchor, anchor + "\n" + audit),
    ], "bracket_midpoint_once")


def short_pool12(source: str) -> str:
    anchor = "        for (int x=best-8;x<=best+8;++x) add(x,82-0.5*abs(x-best));"
    replacement = r'''        // Short arrays have more remaining coverage capacity for local raw peaks.
        const int narrowPoolRadius=n<=500 ? 12 : (n<=650 ? 10 : 8);
        for (int x=best-narrowPoolRadius;x<=best+narrowPoolRadius;++x)
            add(x,82-0.5*abs(x-best));'''
    return _replace(source, anchor, replacement, "short_pool12")


def near_peak_model_guard(source: str) -> str:
    anchor = "            if (uniquePeak && !f.plateau && f.significant && f.noise<0.05*f.contrast &&"
    guard = r'''            // A nearby rival outside the parking tolerance also blocks model finish.
            for (int x:f.peaks)
                if (abs(x-best)>3 && value[x]>bestValue-max(4*f.noise,0.05*f.contrast))
                    uniquePeak=false;
'''
    return _replace(source, anchor, guard + anchor, "near_peak_model_guard")


variants: list[dict[str, str | Callable[[str], str]]] = [
    dict(name="short_flat4", description="N<=500 only: four-position scans while all observed values remain equal; nonflat step and original stopping rules remain.", apply=short_flat4),
    dict(name="initial_phase23", description="Initial anchors 0,4,11,23; shifts the following eight-position grid without imposing a denser global grid.", apply=initial_phase23),
    dict(name="short_rising_half", description="N<=500: at most 20 forward midpoints on significant nonnoisy rising/rebounding flanks; original endpoints and stopping rules remain.", apply=short_rising_half),
    dict(name="acceleration_half", description="Forward midpoints only on accelerating positive flanks; additional-query credits 20/12/6 by N<=500/<=650/>650.", apply=acceleration_half),
    dict(name="sparse_phase_walk", description="Nonflat eight-position scan takes one stride of seven per eight queries, walking residue phase without global step seven.", apply=sparse_phase_walk),
    dict(name="quantized_step4", description="The existing equal-step/weak-rise quantization guard becomes a true four-position local scan instead of its current step-eight no-op.", apply=quantized_step4),
    dict(name="bracket_midpoint_once", description="After the first significant descent near an observed peak, audit one largest adjacent bracket midpoint; no more than one extra reversal pair.", apply=bracket_midpoint_once),
    dict(name="short_pool12", description="Raw-best fine pool radius is 12/10/8 by N<=500/<=650/>650; no change to coarse density, stop rules or hard limits.", apply=short_pool12),
    dict(name="near_peak_model_guard", description="Block model early finish when an observed competitive peak exists outside best +/-3, including nearby peaks ignored by the old distance-32 guard.", apply=near_peak_model_guard),
]
