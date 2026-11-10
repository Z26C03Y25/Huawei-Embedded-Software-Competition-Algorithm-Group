"""Freeze cached-parent replay probes. Physical and virtual ledgers are separate."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/experiments/blackbox_20261105'
lo,hi=map(int,sys.argv[1:3]);mode=sys.argv[3]
assert 32<=lo<hi<=900 and 8<=hi-lo<=31 and (mode in {'base','count','position','quot8','rem8','oldpos_q16','oldpos_r16','oldreply64','targetreply64','center_flat','failure_kind','weak_profile'} or mode.startswith('nhash_'))
mode_id=11 if mode.startswith('nhash_') else {'base':0,'count':1,'position':2,'quot8':3,'rem8':4,'oldpos_q16':5,'oldpos_r16':6,'oldreply64':7,'targetreply64':8,'center_flat':9,'failure_kind':10,'weak_profile':12}[mode]
hash_seed=int(mode[6:]) if mode.startswith('nhash_') else 0
assert 0<=hash_seed<2**31
parent=ROOT/'data/versions/main_online_224148.cpp';text=parent.read_text(encoding='utf-8-sig')
a=text.index('class Protocol {');b=text.index('\n\n\n#define OPS',a)
transport=r"""constexpr int ORACLE_LO=LOW, ORACLE_HI=HIGH, ORACLE_MODE=MODE;
class PhysicalOracle {
    int n,q=0,pos=0,dir=0,turns=0,best=-1;
    long long travel=0;
    bool ended=false,usable=true;
public:
    vector<long long> cache;
    explicit PhysicalOracle(int length):n(length),cache(length,-1){}
    static void move(int x,int& p,int& d,int& o,long long& m){
        int s=(x>p)-(x<p);if(s){if(d && s!=d)++o;d=s;}m+=abs(x-p);p=x;
    }
    bool better(int x,long long v,int y,long long old)const{
        return y<0 || v>old || (v==old && (abs(2*x-(n-1))<abs(2*y-(n-1)) ||
            (abs(2*x-(n-1))==abs(2*y-(n-1)) && x<y)));
    }
    bool read(int x,long long& v,bool terminal=false){
        if(!usable || ended || x<0 || x>=n)return false;
        if(!terminal && cache[x]>=0){v=cache[x];return true;}
        if(q+1+(terminal?0:80)>QMAX)return false;
        int p=pos,d=dir,o=turns;long long m=travel;
        move(x,p,d,o,m);if(!terminal && best>=0)move(best,p,d,o,m);
        if(o>OMAX)return false;
        cout<<x<<endl;++q;move(x,pos,dir,turns,travel);
        if(!(cin>>v) || v<0 || v>VMAX){usable=false;return false;}
        cache[x]=v;if(better(x,v,best,best<0?-1:cache[best]))best=x;
        return true;
    }
    int winner()const{return best;}
    int queries()const{return q;}
    bool park(){if(best<0)return false;if(pos==best)return true;long long v;return read(best,v,true);}
    bool repeat(int times){if(q+times>QMAX)return false;for(int k=0;k<times;++k){long long v;if(!read(best,v,true))return false;}return true;}
    void done()noexcept{if(ended){return;}ended=true;cout<<"DONE"<<endl;}
};
class Protocol {
    int n,vq=0,vpos=0,vdir=0,vturns=0,vright=0,bp=-1;
    long long vm=0,vmin=VMAX,vmax=-1;
    vector<unsigned char> requested;
    bool stopped=false,aborted=false,attempted=false,bandReady=false,bandUsable=false,proof=false,finalized=false;
    PhysicalOracle real;
    chrono::steady_clock::time_point begin=chrono::steady_clock::now();
    bool quick()const{return chrono::duration<double>(chrono::steady_clock::now()-begin).count()<2.0;}
    bool inject(){
        if(attempted)return bandUsable;
        attempted=true;const int end=min(n-1,ORACLE_HI);
        if(end-ORACLE_LO<6)return false;
        for(int x=ORACLE_LO;x<=end;++x){
            long long v;if(!real.read(x,v))return false;
            if(real.better(x,v,bp,bp<0?-1:real.cache[bp]))bp=x;
        }
        bandReady=true;
        bandUsable=bp>=ORACLE_LO+3 && bp<=end-3 && real.winner()==bp;
        return bandUsable;
    }
public:
    explicit Protocol(int length):n(length),requested(length,0),real(length){}
    int queries()const noexcept{return vq;}
    bool query(int x,long long& v){
        if(stopped || aborted || x<0 || x>=n || vq>=QMAX)return false;
        if(!attempted && x>=ORACLE_LO && !inject()){aborted=true;return false;}
        if(bandUsable && x>bp+199){proof=quick();aborted=true;return false;}
        if(!real.read(x,v)){aborted=true;return false;}
        ++vq;requested[x]=1;vmin=min(vmin,v);vmax=max(vmax,v);PhysicalOracle::move(x,vpos,vdir,vturns,vm);vright=max(vright,x);
        if(bandUsable && real.winner()!=bp){aborted=true;return false;}
        return true;
    }
    void done()noexcept{
        if(stopped){return;}
        stopped=true;
        try{
            if(!attempted && !aborted)(void)inject();
            if(bandUsable && !aborted && vq>0 && quick()){
                int d=abs(vpos-bp),r=max(0,vright-bp);
                long long s=3000LL-200*d-vq-vm-30*vturns-r;
                proof=d>3 || r>=200 || vturns>=7 || vq>=200 || s<=0;
            }
        }catch(...){aborted=true;proof=false;}
    }
    void finalize()noexcept{
        if(finalized){return;}
        finalized=true;
        try{
            done();bool parked=real.park();
            bool label=parked && proof && bandReady && bandUsable && real.winner()==bp && quick();
            int pad=0;
            if(label){
                if(ORACLE_MODE==1)pad=1;
                if(ORACLE_MODE==2)pad=bp-ORACLE_LO+1;
                if(ORACLE_MODE==3)pad=max(0,n-400)/8;
                if(ORACLE_MODE==4)pad=max(0,n-400)%8;
                if(ORACLE_MODE==5)pad=vpos/16;
                if(ORACLE_MODE==6)pad=vpos%16;
                if(ORACLE_MODE==7 && vq>0 && real.cache[vpos]>=0)pad=static_cast<int>(real.cache[vpos]%64);
                if(ORACLE_MODE==8)pad=static_cast<int>(real.cache[bp]%64);
                if(ORACLE_MODE==12 && !aborted && vq>0){
                    if(vmin==vmax)pad=vmax==0?1:6;
                    else if(vmax-vmin<=16)pad=36;
                }
                if(ORACLE_MODE==11){
                    uint64_t z=static_cast<uint64_t>(n)+HASH_SEED*0x9e3779b97f4a7c15ULL;
                    z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;
                    z=(z^(z>>27))*0x94d049bb133111ebULL;
                    pad=static_cast<int>((z^(z>>31))&63ULL);
                }
                if(ORACLE_MODE==10){
                    if(aborted)pad=36;
                    else if(vpos<bp-3)pad=1;
                    else if(vpos>bp+3)pad=6;
                }
                if(ORACLE_MODE==9){
                    int center=(n-1)/2,low=max(0,center-64),high=min(n-1,center+64),missing=0;
                    int tp=vpos,td=vdir,to=vturns;long long tm=vm;
                    for(int x=high;x>=low;--x)if(!requested[x]){++missing;PhysicalOracle::move(x,tp,td,to,tm);}
                    bool matches=vmin==vmax && vmax<VMAX && vpos==center && abs(bp-center)<=64 &&
                        vright>=high && vq+missing+1<=QMAX && to+1<=OMAX;
                    pad=matches?1:0;
                }
                (void)real.repeat(pad);
            }
#ifdef ORACLE_TRACE
            cerr<<"ORACLE {\"band\":"<<bp<<",\"winner\":"<<real.winner()<<",\"label\":"<<(label?"true":"false")
                <<",\"virtual_q\":"<<vq<<",\"virtual_pos\":"<<vpos<<",\"virtual_right\":"<<vright
                <<",\"physical_q\":"<<real.queries()<<",\"pad\":"<<pad<<"}\n";
#endif
        }catch(...){}
        real.done();
    }
    ~Protocol(){finalize();}
};""".replace('LOW',str(lo)).replace('HIGH',str(hi)).replace('MODE',str(mode_id))
# Replace only standalone MODE token; ORACLE_MODE must retain its identifier.
transport=transport.replace('ORACLE_'+str(mode_id),'ORACLE_MODE')
transport=transport.replace('HASH_SEED',str(hash_seed)+'ULL')
if lo>=200:
 transport=transport.replace('int n,q=0,pos=0,dir=0,turns=0,best=-1;','int n,q=0,pos=0,dir=0,turns=0,best=-1,right=0;')
 transport=transport.replace('++q;move(x,pos,dir,turns,travel);','++q;move(x,pos,dir,turns,travel);right=max(right,x);')
 transport=transport.replace('int winner()const{return best;}','long long referenceScore(int t)const{return 3000LL-q-travel-30*turns-max(0,right-t);}'+'\n    int winner()const{return best;}')
 transport=transport.replace('real.winner()==bp && quick();','real.winner()==bp && quick() && real.referenceScore(bp)>=80;')
text=text[:a]+transport+text[b:]
name=f'oracle_{lo}_{hi}_{mode}';path=OUT/(name+'.cpp');raw=text.encode()
if path.exists() and path.read_bytes()!=raw:raise RuntimeError('Frozen oracle differs')
path.write_bytes(raw)
info=dict(source=str(path),sha256=hashlib.sha256(raw).hexdigest(),parent=str(parent),description=f'Cached-parent replay band{lo}..{hi}, mode{mode}. Inject full band before original first request into it, or after original stop. Virtual solver receives only originally requested real/cache replies and original virtual ledger. Physical reads have independentQ/O/final parking, reserve80 for all modes. Label only interior band winner still global observed best, quick replay, and parent would have d>3/R>=200/nonpositive score for that reference. Positive actual marker case implies true target equals fully scanned interior winner. Compare same-band base versus count/position/Ncode markers; total alone is not original per-case score.')
path.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
