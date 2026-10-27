#include <bits/stdc++.h>
using namespace std;

int N, cur = 0, qcnt = 0;
long long bestVal = -1;
int bestPos = -1, maxRight = 0;
vector<long long> val;
vector<char> has;

bool better(int i, int j) {
    if (j < 0) return true;
    long long di = llabs(2LL*i - (N-1));
    long long dj = llabs(2LL*j - (N-1));
    return (di != dj) ? (di < dj) : (i < j);
}

void update(int idx, long long v) {
    if (v > bestVal || (v == bestVal && better(idx, bestPos))) {
        bestVal = v; bestPos = idx;
    }
}

long long ask(int idx) {
    if (has[idx]) { cur = idx; return val[idx]; }
    printf("%d\n", idx); fflush(stdout);
    long long v;
    if (scanf("%lld", &v) != 1) exit(0);
    ++qcnt; cur = idx;
    has[idx] = 1; val[idx] = v;
    update(idx, v);
    maxRight = max(maxRight, idx);
    return v;
}

int main() {
    scanf("%d", &N);
    val.assign(N, 0); has.assign(N, 0);

    ask(0);
    long long curVal = val[0];
    long long prevVal = -1;

    const int BUDGET   = 100;
    const int MAX_STEP = 12;    // 网格变细
    const int MIN_STEP = 3;

    // 阶段 1：动态窗口粗扫
    while (cur < N - 1 && qcnt < 100) {
        int remain = bestPos + BUDGET - cur;
        if (remain <= 0) break;

        int step = (int)((long long)remain * MAX_STEP / BUDGET);
        step = min(MAX_STEP, max(MIN_STEP, step));
        step = min(step, remain);

        if (prevVal >= 0 && curVal < prevVal) step = max(MIN_STEP, step / 2);

        int next = min(N - 1, cur + step);
        if (next <= cur) break;
        prevVal = curVal;
        curVal = ask(next);
    }

    // 阶段 2：bestPos±30 步长 2 外圈细化（从 cur 向左）
    int L2 = max(0, bestPos - 30);
    for (int i = cur - 2; i >= L2; i -= 2) {
        if (qcnt >= 175) break;
        if (!has[i]) ask(i);
    }

    // 阶段 3：bestPos±8 步长 1 精扫，锁定 d=0
    int L3 = max(0, bestPos - 8);
    int R3 = min(N - 1, bestPos + 8);
    for (int i = L3; i <= R3; ++i) {
        if (qcnt >= 190) break;
        if (!has[i]) ask(i);
    }

    if (cur != bestPos) ask(bestPos);

    printf("DONE\n"); fflush(stdout);
    return 0;
}