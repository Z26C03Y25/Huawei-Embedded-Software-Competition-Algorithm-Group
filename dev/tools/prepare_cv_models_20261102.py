"""Select a peak family by held-out real observations rather than vertex voting."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
parent=ROOT/'data/versions/main_online_216258.cpp'
text=parent.read_text(encoding='utf-8-sig')
start=text.index('    optional<double> multiModelVertex(')
end=text.index('    vector<Point> pool(',start)
replacement=r'''    optional<double> multiModelVertex(const Features& f) {
        vector<int> xs;
        for (int x:f.x) if (abs(x-best)<=32) xs.push_back(x);
        if (xs.size()<5) return nullopt;
        double winnerLoss=numeric_limits<double>::infinity();
        optional<double> winner;
        for (int family=0;family<3;++family) {
            const int degree=family==1 ? 3 : 2;
            if (xs.size()<static_cast<size_t>(degree+3)) continue;
            auto response=[&](int x) {
                return family==2 ? log(static_cast<double>(value[x])-f.floor+1.0)
                                 : static_cast<double>(value[x])-bestValue;
            };
            auto peak=[&](const vector<double>& coef) {
                return family==1 ? cubicPeak(coef) : quadPeak(coef);
            };
            double loss=0,weights=0;
            vector<double> jackknife;
            bool valid=true;
            for (size_t held=0;held<xs.size();++held) {
                vector<int> train;
                vector<double> y,coef;
                for (size_t k=0;k<xs.size();++k) if (k!=held) {
                    train.push_back(xs[k]); y.push_back(response(xs[k]));
                }
                if (!robustFit(train,degree,y,coef)) { valid=false; break; }
                const double t=(xs[held]-best)/16.0;
                double prediction=0,power=1;
                for (double c:coef) { prediction+=c*power; power*=t; }
                if (family==2)
                    prediction=f.floor-1+exp(clamp(prediction,-50.0,log(static_cast<double>(VMAX)+1)));
                else prediction+=bestValue;
                const double weight=1/(1+abs(xs[held]-best)/16.0);
                loss+=weight*abs(prediction-value[xs[held]]); weights+=weight;
                auto v=peak(coef);
                if (v && *v>=xs.front() && *v<=xs.back()) jackknife.push_back(*v);
            }
            if (!valid || jackknife.size()+2<xs.size()) continue;
            const auto range=minmax_element(jackknife.begin(),jackknife.end());
            if (*range.second-*range.first>12) continue;
            vector<double> y,coef;
            for (int x:xs) y.push_back(response(x));
            if (!robustFit(xs,degree,y,coef)) continue;
            auto v=peak(coef);
            if (!v || *v<xs.front() || *v>xs.back()) continue;
            // Validation error is in original raw-value units for every family.
            // Observed raw maxima still govern actual winner/parking decisions.
            const double meanLoss=loss/max(1.0,weights);
            if (meanLoss<winnerLoss) { winnerLoss=meanLoss; winner=v; }
        }
        return winner ? winner : fittedVertex(xs);
    }
'''
text=text[:start]+replacement+text[end:]
p=ROOT/'data/experiments/blackbox_20261102/cross_validated_models.cpp'
raw=text.encode('utf-8')
if p.exists() and p.read_bytes()!=raw: raise RuntimeError('Frozen source differs')
p.write_bytes(raw)
info=dict(parent=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),description='Replace vertex averaging by leave-one-out family selection: quadratic/raw cubic/log-quadratic predictions judged in raw units, reject unstable jackknife roots, then fit chosen family. Preserve coarse216258, real exhaustive model window, original raw winners and route/budget guards.')
p.with_suffix('.metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
