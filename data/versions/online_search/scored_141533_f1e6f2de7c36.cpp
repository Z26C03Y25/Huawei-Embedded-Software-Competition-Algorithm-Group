#include <bits/stdc++.h>
using namespace std;

int N, cur = 0, qcnt = 0;
long long bestVal = -1;
int bestPos = -1;
int maxRight = 0;
vector<long long> val;
vector<char> has;

bool better(int i, int j) {
    if (j < 0) return true;
    long long di = llabs(2LL * i - (N - 1));
    long long dj = llabs(2LL * j - (N - 1));
    if (di != dj) return di < dj;
    return i < j;
}

void update(int idx, long long v) {
    if (v > bestVal || (v == bestVal && better(idx, bestPos))) {
        bestVal = v; bestPos = idx;
    }
}

long long ask(int idx) {
    printf("%d\n", idx);
    fflush(stdout);
    long long v;
    if (scanf("%lld", &v) != 1) exit(0);
    ++qcnt; cur = idx;
    has[idx] = 1; val[idx] = v;
    update(idx, v);
    maxRight = max(maxRight, idx);
    return v;
}

int main() {
    if (scanf("%d", &N) != 1) return 0;
    val.assign(N, 0); has.assign(N, 0);

    ask(0);
    long long curVal = val[0];
    long long prevVal = -1;
    int prevStep = 0;

    const int BUDGET   = 188;   // 用满冗余窗口（<200 留缓冲）
    const int MAX_STEP = 22;
    const int MIN_STEP = 2;

    // 阶段1：动态窗口粗扫
    while (cur < N - 1 && qcnt < 100) {
        int remain = bestPos + BUDGET - cur;   // 剩余窗口
        if (remain <= 0) break;

        // 核心：步长按剩余占比动态调整
        int step = (int)((long long)remain * MAX_STEP / BUDGET);
        step = min(MAX_STEP, step);
        step = max(MIN_STEP, step);
        step = min(step, remain);

        // 斜率辅助：下降趋势收紧
        if (prevVal >= 0 && curVal < prevVal) {
            step = max(MIN_STEP, step / 2);
        }

        int next = min(N - 1, cur + step);
        if (next <= cur) break;

        prevVal = curVal;
        prevStep = step;
        curVal = ask(next);
    }

    // 阶段2：从最右向左细化（步长 2）
    int W = min(32, max(prevStep, MAX_STEP / 2) + 8);
    int L = max(0, bestPos - W);

    for (int i = cur - 2; i >= L; i -= 2) {
        if (qcnt >= 180) break;
        if (!has[i]) ask(i);
    }

    // 阶段3：bestPos ±3 逐点补全
    for (int i = max(0, bestPos - 3); i <= min(N - 1, bestPos + 3); ++i) {
        if (qcnt >= 190) break;
        if (!has[i]) ask(i);
    }

    // 最后停在 bestPos（保证 d=0）
    if (cur != bestPos) ask(bestPos);

    printf("DONE\n");
    fflush(stdout);
    return 0;
}