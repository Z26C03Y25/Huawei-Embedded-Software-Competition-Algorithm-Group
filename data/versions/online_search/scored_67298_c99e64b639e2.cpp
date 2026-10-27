#include <bits/stdc++.h>
using namespace std;

int N, cur = 0, qcnt = 0;
long long bestVal = -1;
int bestPos = -1;
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
        bestVal = v;
        bestPos = idx;
    }
}

long long ask(int idx) {
    if (has[idx]) { cur = idx; return val[idx]; }   // 已知点：跳过查询只更新位置
    printf("%d\n", idx);
    fflush(stdout);
    long long v;
    if (scanf("%lld", &v) != 1) exit(0);
    ++qcnt;
    cur = idx;
    has[idx] = 1;
    val[idx] = v;
    update(idx, v);
    return v;
}

int main() {
    if (scanf("%d", &N) != 1) return 0;
    val.assign(N, 0);
    has.assign(N, 0);

    ask(0);
    long long curVal = val[0];
    long long prevVal = -1;
    int prevStep = 0;

    // 关键参数
    const int BUDGET = 30;     // 允许的 max_right - bestPos（远小于 200）
    const int MAX_STEP = 15;
    const int MIN_STEP = 3;

    // 初值步长按 N 自适应
    int initStep = max(4, min(MAX_STEP, N / 50));

    // ==== 阶段 1：动态窗口粗扫 ====
    while (cur < N - 1 && qcnt < 100) {
        int remaining = (bestPos + BUDGET) - cur;
        if (remaining <= 0) break;                       // 窗口用尽

        // 值早停：明显下降且已离 bestPos 足够远
        if (cur > bestPos + 4 && curVal * 3 < bestVal) break;

        int step;
        if (prevVal < 0) {
            step = initStep;                             // 首次
        } else if (curVal < prevVal) {
            step = max(MIN_STEP, remaining / 3);         // 下降：收紧
        } else {
            step = max(MIN_STEP, remaining / 2);         // 上升/持平：激进
        }
        step = min(MAX_STEP, step);
        step = min(step, remaining);

        int next = min(N - 1, cur + step);
        if (next <= cur) break;

        prevVal = curVal;
        prevStep = step;
        curVal = ask(next);
    }

    // ==== 阶段 2：从最右向左逐步细化 ====
    int W = prevStep + 2;
    if (W < 4) W = 4;
    int L = max(0, bestPos - W);

    // 步长 2 向左扫回 L
    for (int i = cur - 2; i >= L; i -= 2) {
        if (qcnt >= 180) break;
        ask(i);
    }

    // 在 bestPos ± 3 步长 1 补点，保证 d ≤ 1~2
    for (int i = max(0, bestPos - 3); i <= min(N - 1, bestPos + 3); ++i) {
        if (qcnt >= 190) break;
        ask(i);
    }

    // 最后停在 bestPos（含平局规则）
    if (cur != bestPos) ask(bestPos);

    printf("DONE\n");
    fflush(stdout);
    return 0;
}