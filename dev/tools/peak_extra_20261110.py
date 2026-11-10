"""Pure, controlled waveform transformations for the frozen November 10 parent.

No execution, submission, state mutation, or exact-case lookup is performed here.
Each transformation leaves the transport, raw winner ledger and parking unchanged.
"""

WHY = {
    'basin_rearm': (
        'Rearm spent forward fine-scan allowances only when an observed valley '
        'separates the previous crest from a strictly higher new raw winning basin; '
        'retain the original coarse and total query bounds.'
    ),
    'tail_order_veto': (
        'Two consecutive strict rises after a sampled post-peak valley veto both '
        'quick termination paths while that shape reversal persists; no threshold '
        'scaled by the old summit amplitude or global noise is required.'
    ),
    'valley_separated_rivals': (
        'Treat nearby observed maxima as separate competitors when their sampled '
        'intervening valley has significant relief, instead of merging them solely '
        'because their positions are within the old 24/32 distance thresholds.'
    ),
}


def _replace(code, old, new):
    if code.count(old) != 1:
        raise ValueError('Nonunique source anchor: ' + old)
    return code.replace(old, new, 1)


def apply(code, mode):
    """Return transformed C++ text; reject an unknown mode or changed parent anchor."""
    if not isinstance(code, str):
        raise TypeError('apply expects decoded C++ text')
    if mode == 'basin_rearm':
        old = '        int flatRuns=0, adjacentReads=0,apexReads=0; bool apexActive=false;'
        code = _replace(code, old, old + '''
        int burstCrest=best;
        long long burstCrestValue=bestValue;
        bool burstValleySeen=false;''')
        old = '''            const Features f=features();
            if (certificate()) return;
            int limit=frontierLimit(f);'''
        code = _replace(code, old, '''            const Features f=features();
            if (certificate()) return;
            // A rising shoulder does not replenish its own precision budget.
            // Only a measured dip followed by a new raw record starts a basin.
            if (bestValue>burstCrestValue) {
                if (burstValleySeen && best>burstCrest &&
                    (adjacentReads>0 || apexReads>0)) {
                    adjacentReads=0;apexReads=0;apexActive=false;
                }
                burstCrest=best;burstCrestValue=bestValue;burstValleySeen=false;
            }
            if (rightmost>burstCrest &&
                burstCrestValue-value[rightmost]>max(1.0,f.tolerance))
                burstValleySeen=true;
            int limit=frontierLimit(f);''')
        return code

    if mode == 'tail_order_veto':
        helper = '''    bool tailOrderReversal(const Features& f) const {
        if (best<0 || f.x.size()<4 || rightmost<=best) return false;
        const size_t last=f.x.size()-1;
        const int valley=f.x[last-2],middle=f.x[last-1],end=f.x[last];
        // The observed winner precedes a lower point, then two separate
        // forward measurements rise. An isolated one-point bump cannot vote.
        return valley>best && value[valley]<bestValue &&
            value[valley]<value[middle] && value[middle]<value[end];
    }

'''
        code = _replace(code, '    void explore() {', helper + '    void explore() {')
        old = '            const bool rival=coarseRivalEvidence(f);'
        code = _replace(code, old, old + '\n            const bool orderedTailRise=tailOrderReversal(f);')
        code = _replace(
            code,
            'if (f.significant && rightmost-best>=scout && !f.rebound && !rival &&',
            'if (f.significant && rightmost-best>=scout && !f.rebound && !rival && !orderedTailRise &&',
        )
        code = _replace(
            code,
            'f.falls>=2 && !f.rebound && !rival && f.significant && !f.noisy) break;',
            'f.falls>=2 && !f.rebound && !rival && !orderedTailRise && f.significant && !f.noisy) break;',
        )
        return code

    if mode == 'valley_separated_rivals':
        helper = '''    bool separateObservedBasins(int a,int b,const Features& f) const {
        if (a==b || value[a]<0 || value[b]<0) return false;
        if (a>b) swap(a,b);
        const double lowerCrest=static_cast<double>(min(value[a],value[b]));
        const double localRelief=max(0.0,lowerCrest-f.floor);
        const double required=max({1.0,3*f.noise,0.025*localRelief});
        for (int x:f.x) {
            if (x<=a) continue;
            if (x>=b) break;
            if (lowerCrest-value[x]>required) return true;
        }
        return false;
    }

'''
        code = _replace(code, '    vector<Point> pool(const Features& f) {',
                        helper + '    vector<Point> pool(const Features& f) {')
        code = _replace(
            code,
            'for (int other:groups) if (abs(p-other)<=24) { close=true; break; }',
            'for (int other:groups) if (abs(p-other)<=24 && !separateObservedBasins(p,other,f)) { close=true; break; }',
        )
        code = _replace(
            code,
            'for (int x:f.peaks) if (abs(x-best)>32 && value[x]>bestValue-0.25*f.contrast) uniquePeak=false;',
            'for (int x:f.peaks) if ((abs(x-best)>32 || separateObservedBasins(x,best,f)) && value[x]>bestValue-0.25*f.contrast) uniquePeak=false;',
        )
        return code

    raise ValueError('Unknown extra mode: ' + mode)
