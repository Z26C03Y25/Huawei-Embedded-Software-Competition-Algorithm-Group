"""Offline Java protocol checks and illustrative ablations; never upload."""
from pathlib import Path
import json
import math
import sys
import hashlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev'))
from tools.local_judge import Case, make_suite, run_case, target_index

JAVA = ROOT / 'dev/toolchains/temurin21/jdk-21.0.13+9/bin/java.exe'
BASE = [str(JAVA), '-cp', str(ROOT / 'temp/hybrid'), 'Main', '--trace']
KNOWN = [30, 202, 213, 586, 662, 774]


def gaussian(n, center, width, height=100000):
    return [100 + round(height * math.exp(-0.5 * ((x-center)/width)**2)) for x in range(n)]


def check(row, case):
    path = row['query_positions']
    winner = min(set(path), key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if path else None
    row['parked_observed_winner'] = bool(path) and row['final_position'] == winner
    row['hard_pass'] = (row['status'] == 'ok' and row['queries'] <= 199 and
                        row['oscillations'] <= 6 and row['parked_observed_winner'])
    return row


def main():
    smoke = [check(run_case(BASE, c), c) for c in make_suite('smoke', 2026)]
    boundaries = [
        Case('single_point', (7,)),
        Case('two_equal_points', (7, 7)),
        Case('full_scan198_tie', (7,) * 198),
        Case('all_intmax1000', (2147483647,) * 1000),
    ]
    boundary_rows = [check(run_case(BASE, c), c) for c in boundaries]
    cases = []
    for p in KNOWN:
        for width in [8, 48]:
            cases.append(Case(f'known_{p}_w{width}', tuple(gaussian(1000, p, width))))
    cases.append(Case('unknown_517_w24', tuple(gaussian(1000, 517, 24))))
    cases.append(Case('unknown_143_w5', tuple(gaussian(1000, 143, 5))))
    left, right = gaussian(1000, 662, 8, 80000), gaussian(1000, 774, 12, 100000)
    cases.append(Case('local_662_but_global_774', tuple(max(a, b) for a, b in zip(left, right)), difficulty='challenging'))
    left, right = gaussian(1000, 202, 2, 80000), gaussian(1000, 213, 2, 100000)
    cases.append(Case('local_202_but_global_213', tuple(max(a, b) for a, b in zip(left, right)), difficulty='challenging'))
    for p in [662, 774]:
        v = [100] * 1000
        v[p] = 100000
        cases.append(Case(f'flat_then_known_spike_{p}', tuple(v), difficulty='challenging'))

    results = {}
    for mode, flags in [('hybrid', []), ('no_fast_stop', ['--no-fast-stop']), ('no_prior', ['--no-prior'])]:
        rows = [check(run_case(BASE + flags, c), c) for c in cases]
        results[mode] = rows
        print(mode, json.dumps(dict(cases=len(rows), hard_failures=sum(not r['hard_pass'] for r in rows),
                                    zeros=sum(r['score'] == 0 for r in rows)), ensure_ascii=False))
    report = dict(official=False, selection_note='Mechanism examples, not official performance evidence.',
                  source_sha256=hashlib.sha256((ROOT/'temp/hybrid/Main.java').read_bytes()).hexdigest(),
                  smoke=smoke, boundaries=boundary_rows, experiments=results)
    output = ROOT / 'dev/tmp/hybrid_java_checks.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('smoke', dict(cases=len(smoke), hard_failures=sum(not r['hard_pass'] for r in smoke),
                        max_queries=max(r['queries'] for r in smoke), max_turns=max(r['oscillations'] for r in smoke)))
    print('boundaries', dict(cases=len(boundary_rows), hard_failures=sum(not r['hard_pass'] for r in boundary_rows),
                             max_queries=max(r['queries'] for r in boundary_rows)))
    for i, c in enumerate(cases):
        print(c.name, 'target='+str(target_index(c.values)),
              ' '.join(f"{mode}={rows[i]['score']}/q{rows[i]['queries']}/d{rows[i]['distance']}" for mode, rows in results.items()))
    if any(not r['hard_pass'] for r in smoke + boundary_rows) or any(not r['hard_pass'] for rows in results.values() for r in rows):
        raise SystemExit('Protocol/budget/parking regression; inspect report')


if __name__ == '__main__':
    main()
