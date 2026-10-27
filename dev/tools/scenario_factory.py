"""Versioned stratified curves; transforms share their mother's cluster ID.

These synthetic distributions are stress tests, not an estimate of hidden cases.
The generator never queries a solver. Blind split has shifted lengths, powers,
noise persistence and ripple periods; do not tune on it after reading results.
"""
from __future__ import annotations
import math, random
from .local_judge import Case

VERSION = 3
FAMILIES = ('smooth_power','asymmetric_peak','cusp_peak','supergaussian',
 'shoulder','close_competitors','far_competitors','bump_on_hump','ar1_noise',
 'heteroskedastic_noise','periodic_ripple','chirp_ripple','quantized_top',
 'saturated_top','plateau_edge_peak','trend_with_peak','delayed_peak',
 'boundary_peak','staircase','flat_ties','random_unstructured','single_spike')
INFO = frozenset(('random_unstructured','single_spike'))
SEEDS = {'development':26102661,'selection':27102662,'blind_shift':28102663}


def make_scenarios(per_family=18, splits=None):
    if per_family < 1:
        raise ValueError('per_family must be positive')
    output=[]
    for split in splits or SEEDS:
        if split not in SEEDS:
            raise ValueError('unknown split')
        blind=split=='blind_shift'
        for fi,family in enumerate(FAMILIES):
            for j in range(per_family):
                # Independent per-case RNG makes prefixes stable when count grows.
                seed=SEEDS[split]*100000+fi*1000+j
                r=random.Random(seed)
                n=r.choice((400,401,511,999,1000)) if blind else r.randint(400,999)
                peak=r.randint(0,n-1); width=r.uniform(.025,.19)*n
                power=r.uniform(1.05,1.45) if blind else r.uniform(1.6,2.8)
                asym=r.uniform(.23,2.8)
                def profile(center=peak,w=width,p=2.0):
                    return [math.exp(-min(700,abs((i-center)/w)**p)) for i in range(n)]
                y=profile(p=power)
                params=dict(peak=peak,width=width,power=power,asymmetry=asym)
                if family=='asymmetric_peak':
                    y=[math.exp(-min(700,abs((i-peak)/(width*(asym if i<peak else 1)))**power)) for i in range(n)]
                elif family=='cusp_peak': y=profile(p=r.uniform(.45,.9))
                elif family=='supergaussian': y=profile(p=r.uniform(4.5,9) if blind else r.uniform(3,4.3))
                elif family in ('shoulder','close_competitors','far_competitors','bump_on_hump'):
                    if family=='far_competitors': a=r.randint(0,n//4); b=r.randint(3*n//4,n-1); w=width*.5
                    else:
                        gap=r.randint(10,40) if family=='close_competitors' else r.randint(35,160)
                        a=r.randint(0,n-gap-1);b=a+gap;w=width
                    ratio=r.uniform(.975,1.025) if family=='close_competitors' else r.uniform(.6,.96)
                    left=profile(a,w,power);right=profile(b,w*r.uniform(.25,1.2),power)
                    y=[max(u,ratio*v) for u,v in zip(left,right)]
                    if family in ('shoulder','bump_on_hump'):
                        broad=profile(a,width*2.3,power)
                        if family=='shoulder':
                            component_width=width*.85
                            component_power=power
                        else:
                            component_width=max(1,width*.06)
                            component_power=2
                        component=profile(b,component_width,component_power)
                        y=[.75*u+.28*v for u,v in zip(broad,component)]
                        params.update(component_width=component_width,component_power=component_power)
                    params.update(peaks=[a,b],ratio=ratio)
                elif family in ('ar1_noise','heteroskedastic_noise'):
                    rho=r.uniform(.84,.96) if blind else r.uniform(.3,.8)
                    sigma=r.uniform(.001,.025); state=0
                    for i in range(n):
                        state=rho*state+math.sqrt(1-rho*rho)*r.gauss(0,1)
                        factor=.15+abs(i-peak)/n*3 if family=='heteroskedastic_noise' else 1
                        y[i]+=state*sigma*factor
                    params.update(rho=rho,sigma=sigma)
                elif family in ('periodic_ripple','chirp_ripple'):
                    period=r.uniform(3.1,7.5) if blind else r.uniform(9,25)
                    amp=r.uniform(.002,.035);phase=r.uniform(0,2*math.pi)
                    for i in range(n):
                        frequency=i/period+(i/n)**2*13 if family=='chirp_ripple' else i/period
                        y[i]+=amp*math.sin(2*math.pi*frequency+phase)
                    params.update(period=period,ripple=amp,phase=phase)
                elif family=='quantized_top':
                    levels=r.choice((8,16,32,100));y=[round(t*levels)/levels for t in profile(p=4)]
                    params['levels']=levels
                elif family=='saturated_top': y=[min(.7,t) for t in profile(p=power)]
                elif family=='plateau_edge_peak':
                    a=r.randint(0,n-70);b=min(n-1,a+r.randint(40,260))
                    y=[1.0 if a<=i<=b else .1 for i in range(n)]
                    bump=a+r.choice((0,1,2,max(0,b-a-2),b-a))
                    bump_width=r.uniform(2,6)
                    for i in range(n): y[i]+=.025*math.exp(-((i-bump)/bump_width)**2)
                    params.update(plateau=[a,b],bump=bump)
                elif family=='trend_with_peak':
                    slope=r.uniform(-.9,.9);y=[v+slope*i/n for i,v in enumerate(y)];params['slope']=slope
                elif family=='delayed_peak':
                    peak=r.randint(3*n//5,n-2);w=r.uniform(3,40)
                    y=profile(peak,w,power);cut=max(0,peak-int(4*w))
                    y[:cut]=[0]*cut;params.update(peak=peak,width=w,flat_prefix=cut)
                elif family=='boundary_peak':
                    peak=r.choice((0,1,2,n-3,n-2,n-1));y=profile(peak,width,power);params['peak']=peak
                elif family=='staircase':
                    step=r.randint(4,35);direction=r.choice((-1,1))
                    y=[(i//step)/(n//step+1) for i in range(n)]
                    if direction<0:y.reverse()
                    params.update(step=step,direction=direction)
                elif family=='flat_ties':
                    y=[r.choice((.2,.2,.2,.2001)) for i in range(n)]
                    if j%3==0:y=[.2]*n
                elif family=='random_unstructured':y=[r.random() for i in range(n)]
                elif family=='single_spike':y=[0.0]*n;y[peak]=1.0
                amplitude=r.choice((120,3000,1000000,400000000));base=r.randint(0,max(1,amplitude//25))
                values=tuple(min(2**31-1,max(0,round(base+amplitude*v))) for v in y)
                cluster=f'{split}/{family}/{j:03d}'
                meta=dict(split=split,family=family,cluster=cluster,transform='base',seed=seed,
                          parameters=params,amplitude=amplitude,baseline=base)
                difficulty='information_limited' if family in INFO else 'structured'
                output.append((Case(cluster,values,family,difficulty),meta))
                if j==0:
                    # Transform siblings are deliberately NOT independent samples.
                    for tag,vs in [('mirror',values[::-1]),('offset',tuple(v+12345 for v in values)),
                                   ('scale',tuple(v*2 for v in values))]:
                        output.append((Case(cluster+'/'+tag,vs,family,difficulty),dict(meta,transform=tag)))
    return output
