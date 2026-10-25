# Autofocus Lab

An interactive peak-search study based on the 2026 Huawei Embedded Software Competition, algorithm track.

[中文](../README.md) · [Documentation](README.md) · [Quick start](guides/quickstart.md) · [Contributing](../.github/CONTRIBUTING.md)

This repository contains a single-file C++17 solver, a Python interactive checker, reproducible synthetic benchmarks, scored source archives, and optional browser-assisted submission tools. The recorded best official total is **199291 as of 2026-10-25**. The official hidden test set is not included.

## Run locally

Install Python 3.10+ and GCC g++ with C++17 support, then run from the repository root:

~~~bash
python dev/run.py smoke
python dev/run.py check
~~~

These commands are offline and never upload. Reports go to dev/build/. Python development tools use the standard library; Playwright is only needed for live browser commands.

## The problem

The solver receives only N. Each query moves a motor and reveals one fixed raw value. The last query determines the final position. The target is the raw global maximum, with ties resolved by distance to the array center and then by lower index.

For a valid run, **score=max(0,3000-200*d-Q-M-O-R)**:

| Symbol | Meaning | Requirement |
| --- | --- | --- |
| Q | Actual queries | ≤199 |
| M | Total movement from position 0 | Score cost |
| O | Direction changes | ≤6 |
| R | Furthest-right excursion beyond the true target | ≤199 |
| d | Final-position error | ≤3 |

Moving back cannot undo redundancy. The default heuristic enforces query and turn budgets but cannot certify global success or true redundancy on arbitrary arrays. Strict-redundancy mode trades coverage for a provable bound.

## Explore

- [Problem and scoring](concepts/problem-and-score.md): costs, constraints and tie rules.
- [Solver walkthrough](concepts/solver-walkthrough.md): exploration, simulated annealing and parking.
- [Reproduction](guides/reproduction.md): seeds, hashes, trajectories and paired comparisons.
- [Known limitations](reference/known-limitations.md): retained counterexamples and diagnostic failures.
- [Automation](../automation/README.md): resumable work and separate quota windows.

Annealing iterations optimize an in-memory query plan and are not physical queries. Synthetic scores must not be presented as official results. The normal check covers tooling, protocol regressions and archive integrity. Run the broader diagnostics separately; known failures remain:

~~~bash
python dev/run.py diagnostics
~~~

The submission entry is main.cpp. Historical documents are preserved under docs/archive/ with navigation at their old paths.

No project license has been selected. The statement belongs to its original publisher. This is an independent learning repository.
