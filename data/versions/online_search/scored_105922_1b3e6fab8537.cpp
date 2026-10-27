#include <bits/stdc++.h>
using namespace std;

int N;
int lastIdx = -1;
int qcnt = 0;
const int MAX_Q = 190;
unordered_set<int> visited;

long long ask(int idx) {
    printf("%d\n", idx);
    fflush(stdout);

    long long v;
    if (scanf("%lld", &v) != 1) exit(0);

    lastIdx = idx;
    visited.insert(idx);
    qcnt++;
    return v;
}

// 清晰度更高优先；平局按题目规则：
// 更接近 (N-1)/2 优先，距离相同取更小下标
bool better(long long val, int idx, long long curVal, int curIdx) {
    if (val != curVal) return val > curVal;

    long long d1 = llabs(2LL * idx - (N - 1));
    long long d2 = llabs(2LL * curIdx - (N - 1));

    if (d1 != d2) return d1 < d2;
    return idx < curIdx;
}

int main() {
    if (scanf("%d", &N) != 1) return 0;

    // ================= 自适应参数 =================
    const int C_MAX = 20;      // 初筛最多点数
    const int W = 30;          // 每次右补宽度
    const int COMP_MAX = 2;    // 右补最多次数
    const int MARGIN = 5;      // 第二次右补触发余量

    // 初筛步长：保证初筛点数不超过 C_MAX
    int GAP = (N - 1 + C_MAX - 2) / (C_MAX - 1);
    if (GAP < 2) GAP = 2;

    // 自适应复查半径：按预算反推
    int budgetForR = MAX_Q - C_MAX - COMP_MAX * W - 1 - 5; // 留 5 余量
    if (budgetForR < 20) budgetForR = 20;

    double factor = 2.0 * (1.0 - 1.0 / GAP);
    int R = (int)((budgetForR - 1) / factor);
    R = max(20, min(R, 60));
    // ==============================================

    int bestIdx = -1;
    long long bestVal = -1;

    auto updateBest = [&](long long v, int idx) {
        if (bestIdx == -1 || better(v, idx, bestVal, bestIdx)) {
            bestVal = v;
            bestIdx = idx;
        }
    };

    auto query = [&](int idx) -> long long {
        long long v = ask(idx);
        updateBest(v, idx);
        return v;
    };

    // ================= 阶段1：向右初筛 =================
    {
        int idx = 0;
        long long prev = -1;
        int cnt = 0;

        while (qcnt < MAX_Q) {
            long long v = query(idx);
            cnt++;

            if (idx == N - 1) break;

            // 至少 3 点，且出现“当前值 < 前一个值 且 当前值 < 历史最高”
            // 即峰后连续下降，立即停止初筛
            if (cnt >= 3 && prev >= 0 && v < prev && v < bestVal) {
                break;
            }

            prev = v;

            int nxt = idx + GAP;
            if (nxt >= N) nxt = N - 1;
            if (nxt == idx) break;
            idx = nxt;
        }
    }

    // ================= 阶段2：左精筛（从右向左） =================
    int left1 = max(0, bestIdx - R);
    int right1 = min(N - 1, bestIdx + R);

    for (int i = right1; i >= left1; --i) {
        if (qcnt >= MAX_Q) break;
        if (visited.count(i)) continue;
        query(i);
    }

    // ================= 阶段3：右补最多两次 =================
    // 第一次默认补（抗初筛假峰）
    // 第二次仅在最佳点仍贴近新右端时补
    int lastR = right1;

    for (int comp = 0; comp < COMP_MAX; ++comp) {
        if (qcnt >= MAX_Q) break;
        if (lastR >= N - 1) break;

        bool trigger;
        if (comp == 0) {
            trigger = true;
        } else {
            trigger = (bestIdx >= lastR - MARGIN);
        }

        if (!trigger) break;

        int start = lastR + 1;
        int end = min(N - 1, lastR + W);

        for (int i = start; i <= end; ++i) {
            if (qcnt >= MAX_Q) break;
            if (visited.count(i)) continue;
            query(i);
        }

        lastR = end;
    }

    // ================= 阶段4：回目标点 =================
    if (lastIdx != bestIdx && qcnt < MAX_Q) {
        query(bestIdx);
    }

    printf("DONE\n");
    fflush(stdout);
    return 0;
}