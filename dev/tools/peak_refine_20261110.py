"""Controlled refinement ablations from the frozen table-free waveform solver.

These transformations retain the existing transport, raw maximum and final
parking kernel.  The interpolation envelope is a heuristic, not a bound on an
arbitrary unobserved waveform.
"""

WHY = {
    'fractional_cells': (
        'Preserve every affordable full competitive-cell scan, then spend only '
        'its unused allocation on midpoints of competitive cells skipped '
        'because their complete interiors did not fit. Reserve stays intact.'
    ),
    'envelope_finish': (
        'Use the same local-curvature gap envelope for refinement termination '
        'as for competitor admission; low endpoints alone must not declare '
        'an unscanned competitive gap resolved.'
    ),
}


def replace(code, before, after):
    if code.count(before) != 1:
        raise ValueError('Expected one refinement anchor: ' + before)
    return code.replace(before, after, 1)


ENVELOPE = r'''
    bool competitiveGapOpen(const Features& f) const {
        const double uncertainty=max(1.0,f.noise)*sqrt(2*log(2.0+f.x.size()));
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1],b=f.x[i],gap=b-a;
            if (gap<=1) continue;
            const double chord=static_cast<double>(value[b]-value[a])/gap;
            double bend=0;
            if (i>=2) {
                const int before=f.x[i-2];
                const double slope=static_cast<double>(value[a]-value[before])/(a-before);
                bend=max(bend,abs(chord-slope)/(b-before));
            }
            if (i+1<f.x.size()) {
                const int after=f.x[i+1];
                const double slope=static_cast<double>(value[after]-value[b])/(after-b);
                bend=max(bend,abs(slope-chord)/(after-a));
            }
            // Exactly the admission envelope in completeCompetitors().
            // Matching this heuristic is not a certificate of global optimality.
            const double upper=max(value[a],value[b])+uncertainty+bend*gap*gap/4;
            if (upper>=bestValue-uncertainty) return true;
        }
        return false;
    }

'''


def apply(code, mode):
    if mode == 'fractional_cells':
        old = '''        vector<int> plan;
        for (const Cell& cell:cells) {
            if (static_cast<int>(plan.size())+cell.right-cell.left-1>budget) continue;
            for (int x=cell.left+1;x<cell.right;++x) if (value[x]<0) plan.push_back(x);
        }
        plan=orient(move(plan),true);'''
        new = '''        vector<int> plan;
        vector<Cell> skippedCells;
        for (const Cell& cell:cells) {
            if (static_cast<int>(plan.size())+cell.right-cell.left-1>budget) {
                skippedCells.push_back(cell);
                continue;
            }
            for (int x=cell.left+1;x<cell.right;++x) if (value[x]<0) plan.push_back(x);
        }
        // Keep the original affordable full-cell set. Only otherwise unused
        // allocation can inspect a rejected cell, so the fine reserve survives.
        for (const Cell& cell:skippedCells) {
            if (static_cast<int>(plan.size())>=budget) break;
            const int midpoint=cell.left+(cell.right-cell.left)/2;
            if (value[midpoint]<0) plan.push_back(midpoint);
        }
        plan=orient(move(plan),true);'''
        return replace(code, old, new)
    if mode == 'envelope_finish':
        code = replace(code, '    bool observedTopResolved() {',
                       ENVELOPE + '    bool observedTopResolved() {')
        old = '''        const double allowance=max(4*f.noise,0.025*f.contrast);
        for (size_t i=1;i<f.x.size();++i) {
            const int a=f.x[i-1], b=f.x[i];
            if (b-a>1 && max(value[a],value[b])>=bestValue-allowance) return false;
        }
        return true;'''
        code = replace(code, old, old.replace('        return true;',
                       '        if (competitiveGapOpen(f)) return false;\n        return true;'))
        old = '                        if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi)) return;'
        new = '''                        if (certificate() || (bestValue<VMAX && best>modelLo && best<modelHi &&
                                              !competitiveGapOpen(features()))) return;'''
        return replace(code, old, new)
    raise ValueError('Unknown refinement experiment: ' + mode)
