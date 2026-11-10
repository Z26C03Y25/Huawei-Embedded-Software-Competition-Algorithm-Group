"""Exact mechanism checks for feature design, not a solver or score benchmark."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]


def mad(values):
    if not values:
        return 0.0
    center = median(values)
    return 1.4826 * median(abs(x-center) for x in values)


def residuals(xs, ys):
    rows = []
    for a, b, c in zip(xs, xs[1:], xs[2:]):
        t = (b-a)/(c-a)
        rows.append(dict(r=ys[b]-(ys[a]+t*(ys[c]-ys[a])),
                         product=(b-a)*(c-b), t=t))
    return rows


def geometry_noise(rows):
    if not rows:
        return 0.0
    k = median(row["r"]/row["product"] for row in rows)
    return mad([(r["r"]-k*r["product"])/math.sqrt(1+(1-r["t"])**2+r["t"]**2)
                for r in rows])


def target(a):
    return min(range(len(a)), key=lambda x: (-a[x], abs(2*x-(len(a)-1)), x))


def audit():
    y = [100000-x*x for x in range(97)]
    layouts = dict(uniform8=list(range(0,97,8)),
                   mixed=[0,4,12,24,32,40,48,52,56,64,72,80,88,96])
    quadratic = []
    for name, xs in layouts.items():
        rows = residuals(xs, y)
        quadratic.append(dict(layout=name, samples=xs, true_observation_noise=0,
                              legacy_noise=mad([r["r"] for r in rows])/1.2247448714,
                              curvature_corrected_noise=geometry_noise(rows),
                              residuals=rows))
    assert quadratic[0]["legacy_noise"] == 0
    assert quadratic[1]["legacy_noise"] > 0
    assert all(r["curvature_corrected_noise"] == 0 for r in quadratic)

    # This is an information example, not a recommended trajectory.
    a = [max(0,1000-10*abs(x-96)) for x in range(400)]
    b = a.copy()
    b[143] = 2000
    observed = list(range(0,185,8))
    assert [a[x] for x in observed] == [b[x] for x in observed]
    assert abs(target(a)-target(b)) > 6
    alias = dict(N=400, observed_positions=observed, observed_values=[a[x] for x in observed],
                 target_a=target(a), target_b=target(b), hidden_spike=143,
                 same_observation_history=True, target_distance=abs(target(a)-target(b)),
                 consequence="No feature computed only from this history can distinguish these two arrays.")

    # Analytic Gaussian AR(1) marginal variance, not an estimated sensor model.
    correlation = []
    rho_unit = 0.95
    for h in (1,4,8,16):
        rho_h = rho_unit**h
        variance = 1.5-2*rho_h+0.5*rho_h*rho_h
        correlation.append(dict(spacing=h, assumed_unit_correlation=rho_unit,
                                residual_std_per_true_sigma=math.sqrt(variance),
                                iid_normalized_scale_per_true_sigma=math.sqrt(variance/1.5)))
    assert correlation[0]["iid_normalized_scale_per_true_sigma"] < correlation[2]["iid_normalized_scale_per_true_sigma"]

    budgets = [dict(N=n, maximum_query_density=199/n,
                    normalized_parking_tolerance=3/(n-1),
                    normalized_redundancy_limit=199/(n-1)) for n in (400,650,1000)]
    return dict(official=False, purpose="Feature identifiability and units, not candidate scoring or hidden-data inference.",
                noiseless_quadratic=quadratic, indistinguishable_histories=alias,
                assumed_correlated_noise=correlation, N_resource_geometry=budgets,
                cautions=["Curvature correction passing this check is not evidence of official improvement; trial17 scored -100.",
                          "The AR(1) example assumes a correlation model; it does not estimate the contest's noise.",
                          "Oracle target is used only to construct the ambiguity example, never as an online feature."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT/"data/experiments/feature_analysis_20261030/mechanism_checks.json")
    args = parser.parse_args()
    result = audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("Exact mechanism checks passed; no solver, network, uploads or score optimization.")
    for row in result["noiseless_quadratic"]:
        print(f"{row['layout']}: true noise=0, legacy={row['legacy_noise']:.6f}, corrected={row['curvature_corrected_noise']:.6f}")
    print(f"Indistinguishable histories: targets {result['indistinguishable_histories']['target_a']} and {result['indistinguishable_histories']['target_b']}")


if __name__ == "__main__":
    main()
