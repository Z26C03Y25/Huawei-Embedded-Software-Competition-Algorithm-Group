#include <bits/stdc++.h>
using namespace std;

int N, cur = 0, qcnt = 0;
int lastOutput = -1;              // 最近一次真正输出给判题器的下标
long long bestVal = -1;
int bestPos = -1;
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

// 若已知则跳过，但会修改内部 cur（用于内部步长计算）
long long ask(int idx) {
    if (has[idx]) { cur = idx; return val[idx]; }
    printf("%d\n", idx); fflush(stdout);
    long long v;
    if (scanf("%lld", &v) != 1) exit(0);
    ++qcnt; cur = idx; lastOutput = idx;
    has[idx] = 1; val[idx] = v;
    update(idx, v);
    return v;
}

// 强制输出，即使已知（用于保证最终停靠点）
void forceAsk(int idx) {
    printf("%d\n", idx); fflush(stdout);
    long long v;
    if (scanf("%lld", &v) != 1) exit(0);
    ++qcnt; cur = idx; lastOutput = idx;
    has[idx] = 1; val[idx] = v;
    update(idx, v);
}

int main() {
    if (scanf("%d", &N) != 1) return 0;
    val.assign(N, 0); has.assign(N, 0);

    ask(0);
    long long curVal = val[0];
    long long prevVal = -1;

    const int BUDGET   = 100;
    const int MAX_STEP = 12;
    const int MIN_STEP = 3;

    // 阶段 1：动态窗口粗扫（bestPos 更新自动续命）
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

    // 阶段 3：bestPos±8 步长 1 精扫（先到 R3，再逐点向左到 L3）
    int L3 = max(0, bestPos - 8);
    int R3 = min(N - 1, bestPos + 8);
    if (cur != R3 && qcnt < 190) ask(R3);
    for (int i = R3 - 1; i >= L3; --i) {
        if (qcnt >= 190) break;
        if (!has[i]) ask(i);
    }

    // ★关键修复：确保最后一条协议行是 bestPos
    if (lastOutput != bestPos) {
        forceAsk(bestPos);
    }

    printf("DONE\n"); fflush(stdout);
    return 0;
}