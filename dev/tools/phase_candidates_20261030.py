"""Pure startup-phase diagnostics; no upload or score-based selection.

Each item in ``variants`` exports name, description and apply(source)->str.
The startup loop can have either 0,4,12,24 or the accepted 0,4,11,23 form;
the first three positions are always preserved from the supplied parent.
These are sampling-alias experiments, not guarantees of detecting narrow peaks.
"""
from __future__ import annotations

import re
from typing import Callable


_STARTUP = re.compile(
    r"^(?P<indent>[ \t]*)for\s*\(\s*int\s+x\s*:\s*\{\s*"
    r"(?P<a>\d+)\s*,\s*(?P<b>\d+)\s*,\s*(?P<c>\d+)\s*,\s*(?P<d>\d+)"
    r"\s*\}\s*\)\s*\{",
    re.MULTILINE,
)


def _startup(source: str, name: str):
    marker = f"// phase_20261030:{name}"
    if marker in source:
        raise ValueError(f"{name} is already present")
    matches = list(_STARTUP.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected one four-literal startup loop, found {len(matches)}")
    match = matches[0]
    seeds = tuple(int(match[k]) for k in ("a", "b", "c", "d"))
    if not all(a < b for a, b in zip(seeds, seeds[1:])):
        raise ValueError(f"{name}: startup seeds must be increasing")
    return marker, match, seeds


def _absolute(source: str, final_seed: int, name: str) -> str:
    if any(f"// phase_20261030:{part}" in source
           for part in ("long_plus1", "long_plus4", "mid_plus1", "mid_plus4")):
        raise ValueError(f"{name}: apply global phase changes before segmented phase changes")
    marker, match, seeds = _startup(source, name)
    a, b, c, old_final = seeds
    if final_seed <= c or final_seed == old_final:
        raise ValueError(f"{name}: new last seed must exceed seed three and change the parent")
    replacement = f"{match['indent']}for (int x:{{{a},{b},{c},{final_seed}}}) {{"
    return marker + "\n" + source[:match.start()] + replacement + source[match.end():]


def seed21(source: str) -> str:
    return _absolute(source, 21, "seed21")


def seed25(source: str) -> str:
    return _absolute(source, 25, "seed25")


def seed28(source: str) -> str:
    return _absolute(source, 28, "seed28")


def seed30(source: str) -> str:
    return _absolute(source, 30, "seed30")


def _segmented(source: str, condition: str, name: str, delta: int = 4) -> str:
    band = name.split("_", 1)[0]
    for old in (f"{band}_plus1", f"{band}_plus4"):
        if f"// phase_20261030:{old}" in source:
            raise ValueError(f"{name}: the same N band already has {old}; use a parent without that band")
    marker, match, seeds = _startup(source, name)
    _, _, _, d = seeds
    indent = match["indent"]
    # Keep the literal seed list so the mutually exclusive N bands can compose.
    # The loop variable is a value copy; the original list remains unchanged.
    replacement = match[0] + f"\n{indent}    if (x=={d} && ({condition})) x+={delta};"
    return marker + "\n" + source[:match.start()] + replacement + source[match.end():]


def long_plus4(source: str) -> str:
    return _segmented(source, "n>650", "long_plus4")


def mid_plus4(source: str) -> str:
    return _segmented(source, "n>=501 && n<=650", "mid_plus4")


def mid_plus1(source: str) -> str:
    return _segmented(source, "n>=501 && n<=650", "mid_plus1", 1)


def long_plus1(source: str) -> str:
    return _segmented(source, "n>650", "long_plus1", 1)


variants: list[dict[str, str | Callable[[str], str]]] = [
    dict(name="seed21", description="Set only the fourth startup position to 21; preserve the parent's first three positions.", apply=seed21),
    dict(name="seed25", description="Set only the fourth startup position to 25; preserve the parent's first three positions.", apply=seed25),
    dict(name="seed28", description="Set only the fourth startup position to 28; preserve the parent's first three positions.", apply=seed28),
    dict(name="seed30", description="Set only the fourth startup position to 30; preserve the parent's first three positions.", apply=seed30),
    dict(name="long_plus4", description="Only for N>650, move the parent's fourth startup position four places right; other N values retain all four parent seeds.", apply=long_plus4),
    dict(name="mid_plus4", description="Only for 501<=N<=650, move the parent's fourth startup position four places right; other N values retain all four parent seeds.", apply=mid_plus4),
    dict(name="mid_plus1", description="Only for 501<=N<=650, move the parent's fourth startup position one place right; refuses another phase change in that same N band.", apply=mid_plus1),
    dict(name="long_plus1", description="Only for N>650, move the parent's fourth startup position one place right; refuses another phase change in that same N band.", apply=long_plus1),
]
