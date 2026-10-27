#include <bits/stdc++.h>
using namespace std;

int N, cur = 0, qcnt = 0;
long long bestVal = -1;
int bestPos = -1;

vector<long long> cache;
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
    printf("%d\n", idx);
    fflush(stdout);

    long long v;
    if (scanf("%lld", &v) != 1) exit(0);

    ++qcnt;
    cur = idx;
    update(idx, v);

    if (idx >= 0 && idx < N) {
        if (!has[idx]) {
            has[idx] = 1;
            cache[idx] = v;
        }
    }
    return v;
}

int main() {
    if (scanf("%d", &N) != 1) return 0;

    cache.assign(N, 0);
    has.assign(N, 0);

    ask(0);
    long long curVal = cache[0];

    // 自适应粗扫参数
    int minStep = 6;
    int maxStep = 18;
    int step = max(minStep, min(maxStep, N / 60));

    // 早停参数：冗余尽量压在 200 以内
    const int EXTRA = 85;   // 软早停
    const int HARD  = 140;  // 硬早停

    while (cur < N - 1 && qcnt < 130) {
        int next = min(N - 1, cur + step);
        if (next == cur) break;

        long long nv = ask(next);

        if (nv >= curVal) {
            // 仍在上升或持平，适度加速
            step = min(maxStep, step + 2);
        } else {
            // 开始下降，减速
            step = max(minStep, step / 2);
        }

        curVal = nv;

        // 已经明显越过当前最优位置，且值明显低于最优值，提前停
        if (cur > bestPos + EXTRA && nv * 2 < bestVal) break;

        // 硬冗余保护
        if (cur > bestPos + HARD) break;
    }

    // 小范围细化：步长 2，覆盖 bestPos 左右
    int W = min(28, max(8, step + 4));
    int L = max(0, bestPos - W);
    int R = min(N - 1, bestPos + W);

    // 先到左边界
    if (cur != L) ask(L);

    // 从左到右隔点扫描
    for (int idx = L + 2; idx <= R; idx += 2) {
        if (qcnt >= 185) break;
        if (idx != cur) ask(idx);
    }

    // bestPos 附近逐点补查，保证 d <= 2
    int l2 = max(0, bestPos - 2);
    int r2 = min(N - 1, bestPos + 2);
    for (int idx = l2; idx <= r2; ++idx) {
        if (qcnt >= 190) break;
        if (idx != cur) ask(idx);
    }

    // 最后停到最优位置
    int target = bestPos;
    if (cur != target) {
        ask(target);
    }

    printf("DONE\n");
    fflush(stdout);
    return 0;
}