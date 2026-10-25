// In-process protocol adapter. The solver receives only replies to its queries.
// Complete arrays belong to this checker and are never exposed to Solver.
#define main submission_main
#ifdef LAB_BASELINE
#include "../../data/versions/main_strategy_159487.cpp"
#elif defined(LAB_FLAT199)
#include "../../data/versions/main_flat199_candidate.cpp"
#elif defined(LAB_TREND)
#include "../../data/versions/main_trend_candidate.cpp"
#else
#include "../../data/versions/main_frontier_candidate.cpp"
#endif
#undef main

class ReplyBuffer : public streambuf {
    string reply;
public:
    void answer(long long x) {
        reply=to_string(x)+"\n";
        char* p=reply.data(); setg(p,p,p+reply.size());
    }
};
class QueryBuffer : public streambuf {
    const vector<long long>& a;
    ReplyBuffer& reply;
    string line;
    void accept(char c) {
        if (c!='\n') { line+=c; return; }
        if (done) throw runtime_error("output after DONE");
        if (line=="DONE") done=true;
        else {
            size_t consumed=0;
            const int x=stoi(line,&consumed);
            if (consumed!=line.size() || x<0 || x>=static_cast<int>(a.size()))
                throw runtime_error("invalid query");
            path.push_back(x); reply.answer(a[x]);
        }
        line.clear();
    }
protected:
    int_type overflow(int_type c) override {
        if (!traits_type::eq_int_type(c,traits_type::eof())) accept(traits_type::to_char_type(c));
        return traits_type::not_eof(c);
    }
    streamsize xsputn(const char* p,streamsize n) override {
        for (streamsize i=0;i<n;++i) accept(p[i]);
        return n;
    }
public:
    bool done=false;
    vector<int> path;
    QueryBuffer(const vector<long long>& input,ReplyBuffer& inputBuffer):a(input),reply(inputBuffer) {}
};

int main(int argc,char** argv) {
    ios::sync_with_stdio(false); cin.tie(nullptr);
#ifdef LAB_TREND
    if (argc>1) af::trendFactor=stod(argv[1]);
#elif !defined(LAB_BASELINE) && !defined(LAB_FLAT199)
    if (argc>1) af::profile=stoi(argv[1]);
#else
    (void)argc; (void)argv;
#endif
    int cases; cin>>cases;
    for (int k=0;k<cases;++k) {
        int n; cin>>n;
        vector<long long> a(n);
        for (auto& x:a) cin>>x;
        ReplyBuffer input;
        QueryBuffer output(a,input);
        auto* oldIn=cin.rdbuf(&input);
        auto* oldOut=cout.rdbuf(&output);
        cin.clear();
        af::Solver(n,false,false,false).run();
        cin.rdbuf(oldIn); cout.rdbuf(oldOut); cin.clear();
        if (!output.done || output.path.empty()) throw runtime_error("missing DONE/query");
        int target=0;
        for (int x=1;x<n;++x)
            if (a[x]>a[target] || (a[x]==a[target] &&
                make_pair(abs(2*x-(n-1)),x)<make_pair(abs(2*target-(n-1)),target))) target=x;
        int p=0,dir=0,o=0,r=0; long long movement=0;
        for (int x:output.path) {
            const int d=(x>p)-(x<p);
            if (d) { if (dir && d!=dir) ++o; dir=d; }
            movement+=abs(x-p); p=x; r=max(r,x);
        }
        const int q=static_cast<int>(output.path.size()),distance=abs(p-target),red=max(0,r-target);
        const long long score=q>=200 || o>=7 || red>=200 || distance>3 ? 0 :
            max(0LL,3000-200*distance-q-movement-o-red);
        cout<<score<<' '<<q<<' '<<movement<<' '<<o<<' '<<red<<' '<<distance<<' '<<p;
        for (int x:output.path) cout<<' '<<x;
        cout<<'\n';
    }
}
