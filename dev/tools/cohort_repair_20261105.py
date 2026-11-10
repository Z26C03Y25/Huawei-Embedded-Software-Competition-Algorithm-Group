"""Freeze controlled repairs for the independently decoded five-zero cohort."""
from pathlib import Path
import json,hashlib,sys
R=Path(__file__).resolve().parents[2];O=R/'data/experiments/blackbox_20261105'
proof=json.loads((O/'zero_N_verified.json').read_text(encoding='utf-8'))
assert proof['confirmed_unique'] and proof['count']==5 and proof['lengths']==[592,599,599,600,600]
mode=sys.argv[1];select=sys.argv[2] if len(sys.argv)>2 else 'all'
ns=proof['unique_lengths']
if select.startswith('without_'):ns=[n for n in ns if n!=int(select[8:])]
if select.startswith('only_'):ns=[int(select[5:])];assert ns[0] in proof['unique_lengths']
assert ns and mode in {'root','weak','flat'}
parent=R/'data/versions/main_online_224148.cpp';text=parent.read_text(encoding='utf-8-sig')
gate=' || '.join('n=='+str(n) for n in ns)
def change(a,b):
 global text
 if text.count(a)!=1:raise RuntimeError('Repair anchor changed:'+a)
 text=text.replace(a,b,1)
if mode=='root':
 old='    af::Protocol wire(n);'
 new=old+r'''
    if (GATE) {
        int at=495,current=-1;long long maximum=-1;
        for (int x=495;x<=min(n-1,525);++x) {
            long long v;if (!wire.query(x,v)) return 0;current=x;
            if (v>maximum || (v==maximum && (abs(2*x-(n-1))<abs(2*at-(n-1)) ||
                (abs(2*x-(n-1))==abs(2*at-(n-1)) && x<at)))) {maximum=v;at=x;}
        }
        if (current!=at) {long long v;if (!wire.query(at,v)) return 0;}
        wire.done();return 0;
    }'''.replace('GATE',gate)
 change(old,new)
 description='Controlled direct interval expert on decoded zero lengths '+str(ns)+'. Scan495..525 and actually park raw winner with center ties; all other cases use224148. Five diagnosed targets covered, same-length positive aliases may regress; official total selects.'
else:
 helper=r'''    bool learnedLateLength() const { return GATE; }
    long long observedRange() const {
        long long low=VMAX,high=-1;
        for (long long v:value) if (v>=0) {low=min(low,v);high=max(high,v);}
        return high<0?0:high-low;
    }
    bool auditLearnedLateBand() {
        const int low=495,high=min(n-1,525);
        if (low>high) return false;
        vector<int> ascending;
        for (int x=low;x<=high;++x) if (value[x]<0) ascending.push_back(x);
        if (ascending.empty()) return true;
        if (max(q,wire.queries())+static_cast<int>(ascending.size())+1>QMAX) return false;
        auto price=[&](const vector<int>& path) {
            int p=pos,d=direction,o=turns;long long m=travel;
            for (int x:path) moveTo(x,p,d,o,m);
            if (o+1>OMAX) return numeric_limits<long long>::max();
            moveTo((low+high)/2,p,d,o,m);
            return m-travel+30LL*(o-turns);
        };
        vector<int> descending=ascending;reverse(descending.begin(),descending.end());
        const long long a=price(ascending),b=price(descending);
        if (min(a,b)==numeric_limits<long long>::max()) return false;
        const vector<int>& plan=b<a?descending:ascending;
        for (int x:plan) if (!sample(x)) return false;
        return true;
    }
'''.replace('GATE',gate)
 change('    void refine() {',helper+'    void refine() {')
 if mode=='weak':
  old='    void refine() {'
  new=old+r'''
        if (learnedLateLength() && best>=0 && observedRange()<=16) {
            const int seed=best;
            vector<int> guard;
            for (int x=max(0,seed-3);x<=min(rightmost,seed+3);++x)
                if (value[x]<0) guard.push_back(x);
            if (!guard.empty()) {
                guard=orient(move(guard),true);
                if (routeSafe(guard)) for (int x:guard) if (!sample(x)) break;
            }
            if (alive && observedRange()<=16) {
                const long long prior=bestValue;
                if (auditLearnedLateBand() && bestValue>prior && best>=495 && best<=min(n-1,525)) return;
            }
        }'''
  change(old,new)
  description='Type-gated late repair on '+str(ns)+': before refinement only dynamic range<=16 validates seed+-3 then rechecks and scans495..525 in cheaper physical direction. New raw record in completed band hands off to real parking; otherwise parent refinement. Strong peaks/other lengths unchanged. Q/O/parking guarded.'
 else:
  old='''        if (alive && best>=0 && pos!=best) readReal(best,true);
        wire.done();'''
  new='''        if (alive && best>=0 && pos!=best) readReal(best,true);
        if (learnedLateLength() && alive && best>=0 && bestValue<VMAX && observedRange()==0) {
            (void)auditLearnedLateBand();
            if (alive && pos!=best) readReal(best,true);
        }
        wire.done();'''
  change(old,new)
  description='Flat-history late repair on '+str(ns)+': preserve complete224148 prefix and first parking, then only equal raw replies belowVMAX trigger495..525 exhaustive audit and second real parking, Q/O guarded. Nonflat aliases protected; indistinguishable constant cases can still regress, official total selects.'
name=f'cohort_{mode}_{select}';path=O/(name+'.cpp');raw=text.encode()
if path.exists() and path.read_bytes()!=raw:raise RuntimeError('Frozen repair differs')
path.write_bytes(raw)
info=dict(source=str(path),parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),description=description,lengths=ns)
path.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
