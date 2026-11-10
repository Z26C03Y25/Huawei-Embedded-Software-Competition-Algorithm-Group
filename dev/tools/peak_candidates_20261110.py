"""Explicit, table-free structural ablations from the frozen official218796 source."""
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data/versions/online_search/scored_218796_5dcce0efd1f9.cpp'
BASE_SHA = '5dcce0efd1f94b7b7d602d31f956ba70d4292d6c0e8d2e09af9feff9c80a0b4f'

from peak_extra_20261110 import WHY as EXTRA_WHY, apply as extra_apply
from peak_refine_20261110 import WHY as REFINE_WHY, apply as refine_apply

from peak_geometry_20261110 import WHY as GEOMETRY_WHY, apply as geometry_apply

WHY = {
    **GEOMETRY_WHY,
    **EXTRA_WHY,
    **REFINE_WHY,
    'fresh_fit_support': 'A second temporal confirmation must add a new point to the local fitted peak window; merely advancing outside an unchanged window cannot add a confirmation vote.',
}

def replace(code, before, after):
    if code.count(before) != 1:
        raise ValueError('Nonunique source anchor: ' + before)
    return code.replace(before, after, 1)

def construction_parent(mode):
    if mode not in WHY:
        raise ValueError('Unknown reviewed mode: ' + mode)
    return dict(sha256=BASE_SHA, score=218796)

def generate(mode):
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('Frozen official parent hash mismatch')
    code = raw.decode('utf-8')
    if mode in GEOMETRY_WHY:
        code = geometry_apply(code, mode)
    elif mode in EXTRA_WHY:
        code = extra_apply(code, mode)
    elif mode in REFINE_WHY:
        code = refine_apply(code, mode)
    elif mode == 'fresh_fit_support':
        code = replace(code,
            '    int evidenceQuery=-1,evidenceVotes=0,evidenceRight=-1;',
            '    int evidenceQuery=-1,evidenceVotes=0,evidenceRight=-1,evidenceFitRight=-1;')
        code = replace(code,
            '            if (rightmost>evidenceRight) ++evidenceVotes;',
            '            if (rightmost>evidenceRight && xs[hi]>evidenceFitRight) ++evidenceVotes;')
        code = replace(code,
            '        evidenceRight=rightmost;evidenceVertex=vertexPosition;',
            '        evidenceRight=rightmost;evidenceVertex=vertexPosition;evidenceFitRight=xs[hi];')
    else:
        raise ValueError('Unknown reviewed mode: ' + mode)
    if re.search(r'fingerprint|deferred|\bn\s*==\s*\d+|\b(?:586|662|774)\b', code):
        raise ValueError('Case lookup audit failed')
    return code.encode('utf-8')
