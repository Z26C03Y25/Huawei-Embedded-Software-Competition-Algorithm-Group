"""Compositional challenge factory, independent of all solver behavior.

No rejection sampling by solver score. Every family mixes nuisance mechanisms.
Fresh confirmation can include unseen interaction families, different base shapes
and independent hashed seeds. Classic V3 is preserved byte-for-byte elsewhere.
"""
from __future__ import annotations
import hashlib,math,random
from .local_judge import Case
VERSION=4
SEEDS={'development':2026102641,'selection':2026102642,'blind_shift':2026102643}
FAMILIES=('skew_correlated','shoulder_colored','three_competitors','near_equal_ripple',
 'decline_then_peak','quantized_noisy_top','noisy_flat_prefix','late_peak_echo',
 'early_echo_late_main','ramp_micropeaks','staircase_with_background','boundary_competitor',
 'variable_skew','heavy_tail_nuisance','nonstationary_chirp','heteroskedastic_peak',
 'clipped_double_top','plateau_edge_bumps','drifting_double','nonlinear_sensor',
 'multiple_quantized_ties','wave_envelope','unstructured_background','adversarial_impulse')
NOVEL=('modal_bridge','background_change_points','occluded_peak','compound_ripples')
INFO=frozenset(('unstructured_background','adversarial_impulse'))
MODELS={'development':('gaussian','exponential','triangle'),
        'selection':('lorentz','skew_exp','piecewise'),
        'blind_shift':('raised_cosine','quartic_compact','supergaussian')}

def profile(n,p,w,model,skew=1.0):
    result=[]
    for i in range(n):
        t=abs((i-p)/(w*(skew if i<p else 1)))
        if model=='gaussian':v=math.exp(-min(700,.5*t*t))
        elif model=='exponential':v=math.exp(-min(700,t**1.25))
        elif model=='triangle':v=max(0,1-t)
        elif model=='lorentz':v=1/(1+t*t)
        elif model=='skew_exp':v=math.exp(-min(700,t**1.65))
        elif model=='piecewise':v=max(0,1-t*.12) if t<.25 else max(0,.97-(t-.25)*.55)
        elif model=='raised_cosine':v=.5*(1+math.cos(math.pi*t/2)) if t<2 else 0
        elif model=='quartic_compact':v=max(0,1-(t/2)**2)**4 if t<2 else 0
        elif model=='supergaussian':v=math.exp(-min(700,t**4))
        else:raise ValueError(model)
        result.append(v)
    return result

def make_scenarios(per_family=18,splits=None,seed_tag=20261026401,novel=False):
    if per_family<1:raise ValueError('positive count required')
    output=[];families=FAMILIES+(NOVEL if novel else ())
    for split in splits or SEEDS:
        if split not in SEEDS:raise ValueError('unknown split')
        for family in families:
            for j in range(per_family):
                key=f'{seed_tag}/{split}/{family}/{j:03d}'
                seed=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big');r=random.Random(seed)
                n=r.choice((400,401,511,700,999,1000)) if split=='blind_shift' else r.randint(400,1000)
                tier=('medium','hard','hard','extreme')[j%4]
                sigma={'medium':(.0006,.003),'hard':(.003,.012),'extreme':(.012,.028)}[tier]
                sigma=r.uniform(*sigma);rho=r.uniform(.45,.86) if split!='blind_shift' else r.uniform(.83,.97)
                model=r.choice(MODELS[split]);p=r.randrange(n);w=n*r.uniform(.045,.18);skew=r.uniform(.3,2.5)
                def peak(center=p,width=w,m=model,s=1):return profile(n,center,max(1,width),m,s)
                y=peak();centers=[p];widths=[w];quantum=0;noise_mode='correlated'
                if family in ('skew_correlated','variable_skew'):
                    y=peak(s=skew)
                    if family=='variable_skew':y=[v+.03*math.sin(i/n*math.pi*3) for i,v in enumerate(y)]
                elif family in ('shoulder_colored','heavy_tail_nuisance'):
                    q=min(n-1,max(0,p+r.choice((-1,1))*r.randint(30,130)))
                    a=peak(p,w,'lorentz' if family=='heavy_tail_nuisance' else model,skew)
                    bw=w*r.uniform(.45,1.2);b=peak(q,bw);y=[u+.18*v for u,v in zip(a,b)]
                    centers.append(q);widths.append(bw)
                elif family in ('three_competitors','near_equal_ripple','drifting_double','clipped_double_top','multiple_quantized_ties'):
                    k=3 if family=='three_competitors' else 2
                    centers=sorted(r.sample(range(10,n-10),k));widths=[n*r.uniform(.025,.11) for _ in centers]
                    heights=[r.uniform(.86,1.04) for _ in centers]
                    components=[peak(c,ww,s=r.uniform(.5,1.8)) for c,ww in zip(centers,widths)]
                    y=[max(h*a[i] for h,a in zip(heights,components)) for i in range(n)]
                    if family=='near_equal_ripple':y=[v+.015*math.sin(i/2.9) for i,v in enumerate(y)]
                    if family=='drifting_double':y=[v+.22*i/n for i,v in enumerate(y)]
                    if family=='clipped_double_top':y=[min(.75,v) for v in y];sigma*=.1
                    if family=='multiple_quantized_ties':quantum=r.choice((.025,.05,.1));sigma=0
                elif family in ('decline_then_peak','early_echo_late_main','noisy_flat_prefix','late_peak_echo'):
                    q=r.randint(3*n//5,n-2);ww=r.uniform(8,55) if family=='late_peak_echo' else n*r.uniform(.045,.13)
                    centers=[q];widths=[ww];main=peak(q,ww)
                    if family=='decline_then_peak':y=[v+.32*(1-i/n) for i,v in enumerate(main)]
                    elif family=='early_echo_late_main':
                        a=r.randint(0,n//4);echo=peak(a,w*.5);y=[v+.55*u for v,u in zip(main,echo)];centers.append(a)
                    elif family=='late_peak_echo':
                        a=r.randint(n//5,n//2);echo=peak(a,w);y=[v+.35*u for v,u in zip(main,echo)];centers.append(a)
                    else:y=main;sigma*=.2
                elif family=='quantized_noisy_top':y=peak(m='supergaussian');quantum=r.choice((.005,.02,.04))
                elif family=='ramp_micropeaks':
                    direction=r.choice((-1,1));y=[.65*(i/n if direction>0 else 1-i/n)+.35*v for i,v in enumerate(y)]
                elif family=='staircase_with_background':
                    step=r.randint(9,35);direction=r.choice((-1,1));y=[(i//step)/(n//step+1) for i in range(n)]
                    if direction<0:y.reverse()
                    slope=r.choice((0,0,.02,-.02));y=[v+slope*i/n for i,v in enumerate(y)];sigma=0
                elif family=='boundary_competitor':
                    p=r.choice((0,2,n-3,n-1));q=r.randint(n//4,3*n//4);centers=[p,q];widths=[w,w*.5]
                    a=peak(p,w);b=peak(q,w*.5);y=[max(v,.92*u) for v,u in zip(a,b)]
                elif family in ('nonstationary_chirp','wave_envelope','compound_ripples'):
                    period=r.uniform(5,18) if split!='blind_shift' else r.uniform(2.8,8)
                    amp=r.uniform(.01,.05)
                    y=[v+amp*math.sin(2*math.pi*(i/period+9*(i/n)**2)) for i,v in enumerate(y)]
                    if family=='wave_envelope':y=[v+.025*math.cos(i*.41) for i,v in enumerate(y)]
                    if family=='compound_ripples':y=[v+.025*math.sin(i*.73+1.1) for i,v in enumerate(y)]
                elif family=='heteroskedastic_peak':noise_mode='heteroskedastic'
                elif family=='plateau_edge_bumps':
                    a=r.randint(20,n-150);b=min(n-2,a+r.randint(80,260));centers=[a+2,b-3];widths=[r.uniform(3,10),r.uniform(3,10)]
                    l=peak(centers[0],widths[0]);rr=peak(centers[1],widths[1]);y=[(.82 if a<=i<=b else .05)+.16*l[i]+.18*rr[i] for i in range(n)];sigma*=.25
                elif family=='nonlinear_sensor':
                    power=r.choice((.45,.7,2.2));y=[max(0,v)**power for v in y];quantum=r.choice((0,.002,.01))
                elif family=='modal_bridge':
                    a=r.randint(40,n//3);b=r.randint(2*n//3,n-40);centers=[a,b];widths=[w,w*.45]
                    aa=peak(a,w,'lorentz');bb=peak(b,w*.45,'raised_cosine');y=[.7*u+v+.1*math.sin(i/n*math.pi) for i,(u,v) in enumerate(zip(aa,bb))]
                elif family=='background_change_points':
                    c=r.randint(n//3,2*n//3);y=[v+(.18 if i>c else -.05)*i/n for i,v in enumerate(y)]
                elif family=='occluded_peak':
                    notch=peak(min(n-1,p+r.randint(-15,15)),max(2,w*.13),'gaussian');y=[max(0,v-.4*u) for v,u in zip(y,notch)]
                elif family=='unstructured_background':y=[r.random() for _ in range(n)];sigma=0
                elif family=='adversarial_impulse':y=[.02]*n;y[p]=1;sigma=0
                if sigma:
                    state=0;innovation=math.sqrt(1-rho*rho)
                    for i in range(n):
                        state=rho*state+innovation*r.gauss(0,1)
                        multiplier=.2+2*abs(i-p)/n if noise_mode=='heteroskedastic' else 1
                        y[i]+=sigma*state*multiplier
                if quantum:y=[round(v/quantum)*quantum for v in y]
                top=max(y)
                if top>1.9:y=[v*1.9/top for v in y]
                amplitude=r.choice((1000,50000,2000000,400000000));baseline=r.randrange(max(1,amplitude//25))
                values=tuple(max(0,min(2**31-1,round(baseline+amplitude*v))) for v in y)
                difficulty='information_limited' if family in INFO else 'structured'
                meta=dict(split=split,family=family,cluster=key,transform='base',seed=seed,tier=tier,
                    parameters=dict(model=model,centers=centers,widths=widths,skew=skew,sigma=sigma,rho=rho,quantum=quantum,amplitude=amplitude,baseline=baseline),
                    composite=True,novel_family=family in NOVEL)
                output.append((Case(key,values,family,difficulty),meta))
                if j==0:
                    for tag,vs in [('mirror',values[::-1]),('offset',tuple(v+12345 for v in values)),('scale',tuple(v*2 for v in values))]:
                        output.append((Case(key+'/'+tag,vs,family,difficulty),dict(meta,transform=tag)))
    return output
