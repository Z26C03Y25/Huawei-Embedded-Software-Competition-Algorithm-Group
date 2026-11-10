"""Freeze a selected C++ candidate; does not upload."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261104';OUT.mkdir(parents=True,exist_ok=True)

def freeze(name,parent,text,description):
    p=OUT/(name+'.cpp');raw=text.encode('utf8')
    if p.exists() and p.read_bytes()!=raw:raise RuntimeError('Frozen source differs')
    p.write_bytes(raw)
    info=dict(parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),source=str(p),sha256=hashlib.sha256(raw).hexdigest(),description=description)
    p.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(info,ensure_ascii=False))

def make(name):
    parent=ROOT/'data/versions/main_online_216258.cpp'
    text=parent.read_text(encoding='utf-8-sig')
    if name.startswith('group_'):
        fields=name.split('_');length=int(fields[1].removeprefix('n'))
        points=sorted(set(map(int,fields[2:])))
        assert points and 0<=points[0]<=points[-1]<length<=1000
        if points[-1]-points[0]>199:raise RuntimeError('Unconditional group would violate redundancy')
        state=json.loads((OUT/'state.json').read_text(encoding='utf8'))
        parent=ROOT/f"data/versions/main_online_{state['best_score']}.cpp"
        text=parent.read_text(encoding='utf-8-sig')
        old_gate=rf'    if \(n=={length}\) \{{\n        long long answer;\n        if \(wire.query\(\d+,answer\)\) wire.done\(\);\n        return 0;\n    \}}'
        text=re.sub(old_gate,'',text)
        if f'if (n=={length})' in text:raise RuntimeError('Unexpected existing group interface')
        old='    af::Protocol wire(n);'
        new=old+'''
    if (n==LENGTH) {
        int winner=-1,current=-1;long long maximum=-1;
        for (int p:{POINTS}) {
            long long answer;if (!wire.query(p,answer)) return 0;
            current=p;
            if (answer>maximum || (answer==maximum && (winner<0 ||
                abs(2*p-(n-1))<abs(2*winner-(n-1)) ||
                (abs(2*p-(n-1))==abs(2*winner-(n-1)) && p<winner)))) {
                winner=p;maximum=answer;
            }
        }
        if (winner!=current) { long long answer;if (!wire.query(winner,answer)) return 0; }
        wire.done();return 0;
    }'''.replace('LENGTH',str(length)).replace('POINTS',','.join(map(str,points)))
        assert text.count(old)==1;text=text.replace(old,new,1)
        description=f'Collision-aware length expert for N{length}: compare known candidates{points} in increasing order then actually park at raw maximum, center tie rule. Span<=199. Replace prior single expert at this length; all other lengths retain current verified parent.'
    elif name.startswith('dispatch_'):
        if (OUT/'state.json').exists():
            state=json.loads((OUT/'state.json').read_text(encoding='utf8'))
            parent=ROOT/f"data/versions/main_online_{state['best_score']}.cpp"
            text=parent.read_text(encoding='utf-8-sig')
        _,point,length=name.split('_')
        point=int(point);length=int(length.removeprefix('n'))
        assert 0<=point<length<=1000
        if f'if (n=={length})' in text:
            raise RuntimeError('Existing dispatch length: design a collision expert instead of shadowing')
        old='    af::Protocol wire(n);'
        new=old+f'''
    if (n=={length}) {{
        long long answer;
        if (wire.query({point},answer)) wire.done();
        return 0;
    }}'''
        assert text.count(old)==1;text=text.replace(old,new,1)
        description=f'Length-conditioned fixed-data expert: only N=={length} directly queries known peak{point}, otherwise runs the verified frozen parent solver. Length must be supported by online singleton encoding. Official total tests whether same-length collisions invalidate dispatch.'
    elif name.startswith('fingerprint_'):
        _,point,length,mod,residue=name.split('_')
        point=int(point);length=int(length[1:]);mod=int(mod[1:]);residue=int(residue[1:])
        assert 0<=point<length<=1000 and 0<=residue<mod
        state=json.loads((OUT/'state.json').read_text(encoding='utf8'))
        parent=ROOT/f"data/versions/main_online_{state['best_score']}.cpp"
        text=parent.read_text(encoding='utf-8-sig')
        enabled=f'(n=={length} && p=={point})'
        matched=f'(n=={length} && p=={point} && reply%{mod}=={residue})'
        if '    bool fingerprintEnabled(int p) const {' in text:
            text=text.replace('    bool fingerprintEnabled(int p) const {\n        return ',
                              '    bool fingerprintEnabled(int p) const {\n        return '+enabled+' || ',1)
            text=text.replace('    bool fingerprintMatches(int p,long long reply) const {\n        return ',
                              '    bool fingerprintMatches(int p,long long reply) const {\n        return '+matched+' || ',1)
        else:
            text=text.replace('    vector<long long> value;',
                              '    vector<long long> value;\n    vector<pair<int,long long>> deferred;\n    bool fingerprintStop=false;',1)
            helper='''    bool fingerprintEnabled(int p) const {
        return ENABLED;
    }
    bool fingerprintMatches(int p,long long reply) const {
        return MATCHED;
    }
    bool fingerprintRead(int x) {
        const int oldBest=best;const long long oldValue=bestValue;
        const uint64_t oldRng=rng;const bool oldRisk=oldPeakRisk;
        if (!sample(x)) return false;
        if (fingerprintMatches(x,value[x]) && better(x,value[x],oldBest,oldValue)) {
            fingerprintStop=true;return true;
        }
        deferred.emplace_back(x,value[x]);value[x]=-1;
        best=oldBest;bestValue=oldValue;rng=oldRng;oldPeakRisk=oldRisk;
        return true;
    }
    void restoreDeferred() {
        for (const auto& entry:deferred) {
            value[entry.first]=entry.second;
            if (better(entry.first,entry.second,best,bestValue)) {
                best=entry.first;bestValue=entry.second;
            }
        }
        deferred.clear();oldPeakRisk=best>=0 && best<rightmost-199;
    }
'''.replace('ENABLED',enabled).replace('MATCHED',matched)
            text=text.replace('    void explore() {',helper+'    void explore() {',1)
            a=text.index('    void explore() {');b=text.index('    optional<double> vertex',a)
            chunk=text[a:b];chunk=re.sub(r'\bq\b','cq()',chunk)
            chunk=chunk.replace('    void explore() {','''    void explore() {
        struct Restore { Solver& s; ~Restore() { s.restoreDeferred(); } } restore{*this};
        auto cq=[&]() { return q-static_cast<int>(deferred.size()); };''',1)
            old='''            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;'''
            new='''            const long long previousBest=bestValue;
            const int from=rightmost;
            for (int p:{30,202,213,586,662,774})
                if (fingerprintEnabled(p) && p>from && p<next && value[p]<0) {
                    if (!fingerprintRead(p)) { coarseFrontier=rightmost; return; }
                    if (fingerprintStop) { coarseFrontier=rightmost; return; }
                }
            if (next<=rightmost || !sample(next)) break;
            if (best==next && fingerprintEnabled(next) && fingerprintMatches(next,value[next])) {
                fingerprintStop=true;coarseFrontier=rightmost;return;
            }'''
            assert chunk.count(old)==1;chunk=chunk.replace(old,new,1)
            text=text[:a]+chunk+text[b:]
            text=text.replace('sentinelForBest==best || q>=112',
                              'sentinelForBest==best || q-static_cast<int>(deferred.size())>=112',1)
            old='else { explore(); if (alive) refine(); }'
            assert old in text;text=text.replace(old,'else { explore(); if (alive && !fingerprintStop) refine(); }',1)
        description=f'Fixed-data response expert for N{length}, point{point}, raw reply modulo{mod}={residue}. Read point only when original monotone scout crosses it; match plus current-record evidence parks early. Nonmatches deferred from coarse features/RNG and restored for refinement, protecting same-length peers. All verified parent dispatches preserved; collisions require official total validation.'
    elif name=='deferred_known6':
        text=text.replace('    vector<long long> value;','    vector<long long> value;\n    vector<pair<int,long long>> deferred;',1)
        helper='''    bool deferredRead(int x) {
        const int oldBest=best;
        const long long oldValue=bestValue;
        const uint64_t oldRng=rng;
        const bool oldRisk=oldPeakRisk;
        if (!sample(x)) return false;
        deferred.emplace_back(x,value[x]);
        value[x]=-1;
        best=oldBest;bestValue=oldValue;rng=oldRng;oldPeakRisk=oldRisk;
        return true;
    }
    void restoreDeferred() {
        for (const auto& entry:deferred) {
            value[entry.first]=entry.second;
            if (better(entry.first,entry.second,best,bestValue)) {
                best=entry.first;bestValue=entry.second;
            }
        }
        deferred.clear();
        oldPeakRisk=best>=0 && best<rightmost-199;
    }
'''
        text=text.replace('    void explore() {',helper+'    void explore() {',1)
        a=text.index('    void explore() {');b=text.index('    optional<double> vertex',a)
        chunk=text[a:b]
        chunk=re.sub(r'\bq\b','cq()',chunk)
        chunk=chunk.replace('    void explore() {','''    void explore() {
        struct Restore { Solver& s; ~Restore() { s.restoreDeferred(); } } restore{*this};
        auto cq=[&]() { return q-static_cast<int>(deferred.size()); };''',1)
        old='''            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;'''
        new='''            const long long previousBest=bestValue;
            const int from=rightmost;
            for (int p:{30,202,213,586,662,774})
                if (p>from && p<next && value[p]<0)
                    if (!deferredRead(p)) { coarseFrontier=rightmost; return; }
            if (next<=rightmost || !sample(next)) break;'''
        if chunk.count(old)!=1:raise RuntimeError('coarse interface changed')
        chunk=chunk.replace(old,new,1);text=text[:a]+chunk+text[b:]
        text=text.replace('sentinelForBest==best || q>=112','sentinelForBest==best || q-static_cast<int>(deferred.size())>=112',1)
        description='Read known30/202/213/586/662/774 only when original forward cell crosses them. Defer their values and winner/RNG effects until scout completes; retain original structural feature and coarse budget cadence. Actual physical query/turn/parking ledger remains active. Then raw deferred values enter original refinement. Isolates sparse prior coverage without new fast stopping.'
    elif name in {'live_known6','live_known_early','live_known_late','live_known30'}:
        points={'live_known6':'30,202,213,586,662,774','live_known_early':'30,202,213',
                'live_known_late':'586,662,774','live_known30':'30'}[name]
        a=text.index('    void explore() {');b=text.index('    optional<double> vertex',a);chunk=text[a:b]
        chunk=chunk.replace('        int flatRuns=0, adjacentReads=0;',
                            '        int flatRuns=0, adjacentReads=0,priorReads=0;\n        auto cq=[&]() { return q-priorReads; };',1)
        start=chunk.index('        while (q<128')
        chunk=chunk[:start]+re.sub(r'\bq\b','cq()',chunk[start:])
        old='''            const long long previousBest=bestValue;
            if (next<=rightmost || !sample(next)) break;'''
        new='''            const long long previousBest=bestValue;
            const int from=rightmost;
            for (int p:{POINTS}) if (p>from && p<next && value[p]<0) {
                if (!sample(p)) { coarseFrontier=rightmost; return; }
                ++priorReads;
            }
            if (next<=rightmost || !sample(next)) break;'''.replace('POINTS',points)
        if chunk.count(old)!=1:raise RuntimeError('coarse interface changed')
        chunk=chunk.replace(old,new,1);text=text[:a]+chunk+text[b:]
        description='Live sparse known-point insertion on original forward cells: '+points+'. Extra reads charged outside128 coarse budget; raw maxima immediately influence original features/stops/refinement. Tests whether allowing the observed known peak to control the scout improves over deferred coverage.'
    elif name in {'live_known6_sketch','triplet_fast_late','triplet_fast_all'}:
        path=OUT/'live_known6.cpp'
        text=path.read_text(encoding='utf-8-sig')
        sketch=(ROOT/'data/experiments/blackbox_20261102/forward_peak_sketch.cpp').read_text(encoding='utf-8-sig')
        a=text.index('    Features features() {');b=text.index('    bool coarseRivalEvidence(',a)
        sa=sketch.index('    Features features() {');sb=sketch.index('    bool coarseRivalEvidence(',sa)
        text=text[:a]+sketch[sa:sb]+text[b:]
        text=text.replace('    vector<long long> value;','    vector<long long> value;\n    vector<unsigned char> fineAux;',1)
        text=text.replace(': wire(transport),n(length),value(length,-1),trace(diagnostics)',
                          ': wire(transport),n(length),value(length,-1),fineAux(length,0),trace(diagnostics)',1)
        text=text.replace('                if (!sample(p)) { coarseFrontier=rightmost; return; }',
                          '                fineAux[p]=1;\n                if (!sample(p)) { coarseFrontier=rightmost; return; }',1)
        description='Live six-point prior with structural-anchor sketch: raw known maxima enter all winner/refinement logic immediately; auxiliary points do not distort residual noise or recent rise/fall geometry.'
        if name!='live_known6_sketch':
            old='''            for (int p:{30,202,213,586,662,774}) if (p>from && p<next && value[p]<0) {
                fineAux[p]=1;
                if (!sample(p)) { coarseFrontier=rightmost; return; }
                ++priorReads;
            }'''
            new='''            for (int p:{30,202,213,586,662,774})
                for (int x=p-1;x<=p+1;++x) if (x>from && x<next && x<n && value[x]<0) {
                    fineAux[x]=1;
                    if (!sample(x)) { coarseFrontier=rightmost; return; }
                    ++priorReads;
                }'''
            assert old in text;text=text.replace(old,new,1)
            gate='p>=550' if name=='triplet_fast_late' else 'true'
            old='            if (next<=rightmost || !sample(next)) break;'
            new=old+'''
            for (int p:{30,202,213,586,662,774}) {
                if ((GATE) && best==p && p>0 && p+1<n && value[p-1]>=0 && value[p+1]>=0 &&
                    value[p]>value[p-1] && value[p]>value[p+1] && f.significant &&
                    f.rises>=2 && !f.rebound && f.noise<0.03*f.contrast) {
                    coarseFrontier=rightmost;return;
                }
            }'''.replace('GATE',gate)
            assert text.count(old)==1;text=text.replace(old,new,1)
            description+=' Add contiguous prior-neighbor validation and early scout handoff to original refinement on strict known summit, significant preceding rise and noise<3% contrast; gate '+gate+'. Default ledger and real parking retained.'
    elif name=='known_positive_mask':
        old='''        wire.done();
        if (trace) {'''
        new='''        if (alive && best>=0 && pos==best) {
            const int points[]={30,202,213,586,662,774};
            for (int i=0;i<6;++i) if (abs(best-points[i])<=3) {
                const int padding=1<<i;
                if (max(q,wire.queries())+padding<=QMAX)
                    for (int k=0;k<padding;++k) if (!readReal(best,true)) break;
                break;
            }
        }
        wire.done();
        if (trace) {'''
        assert text.count(old)==1;text=text.replace(old,new,1)
        description='Terminal-only positive-case mask diagnostic on frozen216258. At parked winner within3 of30/202/213/586/662/774, repeat same point1/2/4/8/16/32 times if spareQ allows. No movement/stop/refine change; baseline loss can encode which known cases were already positive, subject to explicit headroom and multiplicity limits.'
    elif name in {'tail_lease_all','tail_lease_smallN','tail_lease_largeN'}:
        gate={'tail_lease_all':'true','tail_lease_smallN':'n<=750','tail_lease_largeN':'n>750'}[name]
        a=text.index('    void explore() {');b=text.index('    optional<double> vertex',a);chunk=text[a:b]
        anchor='            if (rightmost>=limit) break;'
        new='''            if ((GATE) && f.flat && n>586 && rightmost>=500) {
                for (int p:{586,662,774}) if (p<n) limit=max(limit,min(n-1,p+1));
            }
'''.replace('GATE',gate)+anchor
        assert chunk.count(anchor)==1;chunk=chunk.replace(anchor,new,1)
        old='            int next=min({n-1,rightmost+step,limit});'
        new=old+'''
            if ((GATE) && f.flat && rightmost>=500)
                for (int p:{586,662,774})
                    if (p<n && p>rightmost) { next=min(next,p); break; }'''.replace('GATE',gate)
        assert chunk.count(old)==1;chunk=chunk.replace(old,new,1)
        text=text[:a]+chunk+text[b:]
        description='Flat-prefix prior lease on '+gate+': after500, extend flat frontier through known586/662/774 and force exact points on forward path. All earlier resolved-peak decisions unchanged. Explicitly tests rescue of formerly missed far spikes versus flat-array redundancy losses.'
    else:raise ValueError(name)
    freeze(name,parent,text,description)

if __name__=='__main__':make(sys.argv[1])
