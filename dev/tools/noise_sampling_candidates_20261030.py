"""Separate auxiliary midpoint samples from the original noise skeleton.

Pure C++ source transformations. No upload or local score-based selection.
All points still determine raw best, shape, slopes, fine-pool candidates and
features.x; only the residual sequence feeding noise MAD excludes the extra
midpoints inserted by the selected half-step mechanism.
"""
from __future__ import annotations

from typing import Callable

try:
    from .narrow_candidates_20261030 import short_rising_half, acceleration_half
except ImportError:  # Direct import with dev/tools on sys.path.
    from narrow_candidates_20261030 import short_rising_half, acceleration_half


def _one(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{name}: expected one source anchor, found {count}")
    return source.replace(old, new, 1)


def _skeleton(source: str, original: Callable[[str], str], credits: str, name: str) -> str:
    marker = f"// noise_sampling_20261030:{name}"
    if marker in source or "set<int> narrowAuxiliaryMidpoints;" in source:
        raise ValueError(f"{name}: an auxiliary-noise policy is already present")
    source = original(source)
    source = _one(
        source, "    vector<long long> value;",
        "    vector<long long> value;\n    set<int> narrowAuxiliaryMidpoints;", name,
    )
    # Credit decrement follows sample(midpoint)'s successful return. Reusing the
    # original insertion retains its activation rule, point location and quota.
    decrement = "--" + credits + ";"
    source = _one(source, decrement, "narrowAuxiliaryMidpoints.insert(midpoint);\n                " + decrement, name)
    anchor = "        f.contrast=bestValue-f.floor; f.flat=f.contrast==0;"
    recompute = r'''        // Preserve all-point features; only noise sees the original skeleton.
        // With no auxiliary points the original residual path is untouched.
        if (!narrowAuxiliaryMidpoints.empty()) {
            vector<int> noiseSkeleton;
            for (int x:f.x)
                if (!narrowAuxiliaryMidpoints.count(x)) noiseSkeleton.push_back(x);
            residual.clear();
            for (size_t i=1;i+1<noiseSkeleton.size();++i) {
                const int x=noiseSkeleton[i];
                const int a=noiseSkeleton[i-1], b=noiseSkeleton[i+1];
                const double t=static_cast<double>(x-a)/(b-a);
                residual.push_back(value[x]-(value[a]+t*(value[b]-value[a])));
            }
        }
'''
    source = _one(source, anchor, recompute + anchor, name)
    # Optional test-only diagnostics, excluded from normal submission builds.
    finish = "        wire.done();\n        if (trace) {"
    diagnostic = r'''        wire.done();
#ifdef NARROW_NOISE_DIAGNOSTICS
        if (trace) cerr<<"AUX_NOISE "<<narrowAuxiliaryMidpoints.size()<<'\n';
#endif
        if (trace) {'''
    source = _one(source, finish, diagnostic, name)
    return marker + "\n" + source


def short_half_skeleton_noise(source: str) -> str:
    return _skeleton(source, short_rising_half, "narrowShortCredits", "short_half_skeleton_noise")


def accel_half_skeleton_noise(source: str) -> str:
    return _skeleton(source, acceleration_half, "narrowAccelerationCredits", "accel_half_skeleton_noise")


def curvature_scaled_noise(source: str) -> str:
    name = "curvature_scaled_noise"
    marker = f"// noise_sampling_20261030:{name}"
    if marker in source or "narrowAuxiliaryMidpoints" in source or any(
            f"// narrow_20261030:{part}" in source
            for part in ("short_rising_half", "acceleration_half")):
        raise ValueError("curvature_scaled_noise is a standalone noise diagnostic, without midpoint policies")
    declaration = "        f.floor=static_cast<double>(value[f.x.front()]);\n        vector<double> residual;"
    source = _one(source, declaration, declaration + "\n        vector<double> noiseProducts,noiseFractions;", name)
    push = "                residual.push_back(value[x]-(value[a]+t*(value[b]-value[a])));"
    source = _one(source, push, push + "\n                noiseProducts.push_back(static_cast<double>(x-a)*(b-x));\n                noiseFractions.push_back(t);", name)
    old = r'''        vector<double> local;
        if (!residual.empty()) {
            const size_t start=residual.size()>18 ? residual.size()-18 : 0;
            local.assign(residual.begin()+static_cast<ptrdiff_t>(start),residual.end());
        }
        // Subtract the median residual: smooth curvature is not independent noise.
        vector<double> absoluteResidual;
        for (double r:residual) absoluteResidual.push_back(abs(r));
        f.noise=max({mad(residual),mad(local),0*median(absoluteResidual)})/1.2247448714;'''
    new = r'''        // Heuristic local constant-curvature removal, then compensate the
        // variance of an unequal-spacing three-point interpolation residual.
        auto scaledNoiseMAD=[&](size_t begin,size_t end) {
            if (begin==end) return 0.0;
            vector<double> curvature,rescaled;
            for (size_t i=begin;i<end;++i)
                curvature.push_back(residual[i]/noiseProducts[i]);
            const double k=median(curvature);
            for (size_t i=begin;i<end;++i) {
                const double t=noiseFractions[i];
                const double variance=1+(1-t)*(1-t)+t*t;
                rescaled.push_back((residual[i]-k*noiseProducts[i])/sqrt(variance));
            }
            return mad(rescaled);
        };
        const size_t localStart=residual.size()>18 ? residual.size()-18 : 0;
        // Global and recent subsets estimate their own curvature median.
        f.noise=max(scaledNoiseMAD(0,residual.size()),scaledNoiseMAD(localStart,residual.size()));'''
    source = _one(source, old, new, name)
    return marker + "\n" + source


variants: list[dict[str, str | Callable[[str], str]]] = [
    dict(name="short_half_skeleton_noise", description="Original short_rising_half midpoint policy and credits; noise MAD/local recent18 residuals use only non-auxiliary sample triples.", apply=short_half_skeleton_noise),
    dict(name="accel_half_skeleton_noise", description="Original acceleration_half midpoint policy and N credits; noise MAD/local recent18 residuals use only non-auxiliary sample triples.", apply=accel_half_skeleton_noise),
    dict(name="curvature_scaled_noise", description="Standalone unequal-spacing residual normalization: estimate median curvature separately globally/recent18 and divide residual errors by interpolation-noise standard deviation.", apply=curvature_scaled_noise),
]
