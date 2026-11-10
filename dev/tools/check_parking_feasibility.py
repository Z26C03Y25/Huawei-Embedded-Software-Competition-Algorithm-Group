"""Check the score geometry theorem, not a synthetic performance benchmark."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev'))
from tools.local_judge import score_path

def main():
    checked=0
    for n in [400,650,1000]:
        for r in [202,203,300,n-1]:
            if r>=n:
                continue
            cut=max(0,r-199)
            for parking in range(max(0,cut-5),min(n,cut+2)):
                possible=any(r-t<=199 and abs(parking-t)<=3 for t in range(n))
                assert possible==(parking>=max(0,cut-3))
                checked+=1
    values=[0]*400
    values[0],values[298],values[299]=100,99,200
    old=score_path(values,[0,298,300,0])
    rescued=score_path(values,[0,298,300,298])
    assert old['score']==0 and rescued['score']>0
    assert 0<300-202 and 298>=300-202
    boundary=[0]*400
    boundary[98],boundary[101],boundary[299]=100,200,99
    preserved=score_path(boundary,[98,299,300,98])
    assert preserved['score']>0 and not 98<300-202
    early=[0]*400
    early[0],early[298]=200,99
    assert score_path(early,[0,298,300,298])['score']==0
    print(json.dumps(dict(boundary_positions_checked=checked,
                         hypothetical_old=old['score'],hypothetical_rescue=rescued['score'],
                         equality_boundary_preserved=preserved['score'],official=False)))

if __name__=='__main__':
    main()
