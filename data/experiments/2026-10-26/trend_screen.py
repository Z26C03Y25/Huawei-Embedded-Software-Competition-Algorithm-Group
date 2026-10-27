"""A separate trend-evidence branch for noisy broad peaks; no uploads."""
from pathlib import Path
import json,sys,importlib.util
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(D));from derive import derive
spec=importlib.util.spec_from_file_location('daily',D/'session.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
state=json.loads((D/'session.json').read_text(encoding='utf-8'));b=max(state['results'],key=lambda x:x['score'])
parent=dict(source=str(Path(b['source_path']).relative_to(ROOT)).replace('\\','/'),sha256=b['sha256'],config=b['parameters'],score=b['score'])
records=[]
for width,factor in ((3,8),(3,12),(5,8)):
    marker='f.significant=f.contrast>max(4.0,24*f.noise);'
    block='''
        if (!f.significant && f.x.size()>=11) {
            vector<double> trend;
            for (size_t i=0;i<f.x.size();++i) {
                vector<double> window;
                const size_t lo=i>WIDTH ? i-WIDTH : 0, hi=min(f.x.size()-1,i+WIDTH);
                for (size_t j=lo;j<=hi;++j) window.push_back(static_cast<double>(value[f.x[j]]));
                trend.push_back(median(move(window)));
            }
            auto sorted=trend; sort(sorted.begin(),sorted.end());
            const double span=sorted.back()-sorted[sorted.size()/5];
            if (span>max(4.0,FACTOR*f.noise)) f.significant=true;
        }'''.replace('WIDTH',str(width//2)).replace('FACTOR',str(factor))
    name=f'trend_w{width}_factor{factor}'
    item=derive(name,parent,[(marker,marker+block)],f'Noisy broad trend evidence: median window{width} span>{factor}*MAD; retain raw champion and all execution limits',dict(trend_window=width,trend_prominence=factor))
    item['offline']=d.validate(item);records.append(item);d.save(D/'trend_screening.json',records)
    print(json.dumps(dict(name=name,**item['offline'])),flush=True)
