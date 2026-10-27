#include <bits/stdc++.h>
using namespace std;

int N;
int qcnt = 0;

long long bestVal = -1;
int bestPos = -1;

bool better(int i, int j) {
    if (j < 0) return true;
    long long di = llabs(2LL * i - (N - 1));
    long long dj = llabs(2LL * j - (N - 1));
    if (di != dj) return di < dj;
    return i < j;
}

long long query(int idx) {
    printf("%d\n", idx);
    fflush(stdout);

    long long v;
    if (scanf("%lld", &v) != 1) {
        exit(0);
    }
    ++qcnt;

    if (v > bestVal || (v == bestVal && better(idx, bestPos))) {
        bestVal = v;
        bestPos = idx;
    }
    return v;
}

int main() {
    if (scanf("%d", &N) != 1) return 0;

    long long v0 = query(0);

    int cur = 0;
    long long curVal = v0;

    // 第一阶段：指数步长快速逼近峰值
    const int MAXSTEP = 12;
    int step = 1;

    while (cur < N - 1) {
        int next = min(N - 1, cur + step);
        if (next == cur) break;

        long long nv = query(next);

        if (nv > curVal) {
            // 仍在上升，继续加速
            cur = next;
            curVal = nv;
            step = min(MAXSTEP, step * 2);
        } else {
            // 首次下降，进入有限右探
            cur = next;
            curVal = nv;
            break;
        }
    }

    // 第二阶段：有限右探，防止双峰漏峰，同时控制冗余
    const int EXTRA = 55;
    int probeStep = max(6, step);

    while (cur < N - 1) {
        if (cur - bestPos >= EXTRA) break;

        int next = min(N - 1, cur + probeStep);
        if (next == cur) break;

        long long nv = query(next);
        cur = next;
        curVal = nv;

        // 已明显低于历史最优且离最优位置足够远，提前停止
        if (next > bestPos + 2 * probeStep && nv * 2 < bestVal) {
            break;
        }
    }

    // 第三阶段：小范围细化，步长 2，从右向左扫描
    int W = max(step, probeStep) + 6;
    W = min(W, 30);

    int L = max(0, bestPos - W);
    int R = min(N - 1, bestPos + W);

    // 保证右侧至少覆盖一个 step，防止真实峰在 bestPos 右侧一点
    R = max(R, min(N - 1, bestPos + step + 2));

    // 先移动到 R
    if (cur != R) {
        query(R);
        cur = R;
    }

    const int scanStep = 2;

    for (int idx = R - scanStep; idx >= L; idx -= scanStep) {
        if (qcnt >= 190) break;
        query(idx);
        cur = idx;
    }

    // 补查 L，保证左边界被覆盖
    if (cur != L && qcnt < 195) {
        query(L);
        cur = L;
    }

    // 最终查询目标点，保证电机停在该下标
    int target = bestPos;
    if (cur != target) {
        query(target);
        cur = target;
    }

    printf("DONE\n");
    fflush(stdout);

    return 0;
}