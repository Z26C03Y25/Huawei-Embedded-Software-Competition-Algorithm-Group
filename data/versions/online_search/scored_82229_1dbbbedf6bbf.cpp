#include <bits/stdc++.h>
using namespace std;

int N;
int lastIdx = -1;
int qcnt = 0;
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

    // ================= 保非零版参数 =================
    const int C_MAX = 50;             // 初筛最多点数
    const int R = 50;                 // 精筛半径
    const int W = 30;                 // 右补宽度（只做一次）
    const int REDUNDANT_LIMIT = 150;  // 硬保护：最右不超过 bestIdx+150
    const int SAFE_Q = 190;           // 预算内查询上限
    // ================================================

    int GAP = (N - 1 + C_MAX - 2) / (C_MAX - 1);
    if (GAP < 2) GAP = 2;

    int bestIdx = -1;
    long long bestVal = -1;
    int maxRight = 0;

    auto updateBest = [&](long long v, int idx) {
        if (bestIdx == -1 || better(v, idx, bestVal, bestIdx)) {
            bestVal = v;
            bestIdx = idx;
        }
        if (idx > maxRight) maxRight = idx;
    };

    auto query = [&](int idx) -> long long {
        long long v = ask(idx);
        updateBest(v, idx);
        return v;
    };

    // ================= 阶段1：初筛（向右） =================
    {
        int idx = 0;
        int downCount = 0;
        int coarseCnt = 0;

        while (true) {
            if (qcnt >= SAFE_Q) break;
            long long v = query(idx);
            coarseCnt++;

            if (idx == N - 1) break;
            if (coarseCnt >= C_MAX) break;

            // 连续两个新点不创新高，判定峰后下降
            if (coarseCnt >= 3) {
                if (v < bestVal) downCount++;
                else downCount = 0;
                if (downCount >= 2) break;
            }

            // 冗余硬保护
            if (idx > bestIdx + REDUNDANT_LIMIT) break;

            int nxt = idx + GAP;
            if (nxt >= N) nxt = N - 1;
            if (nxt == idx) break;
            idx = nxt;
        }
    }

    // ================= 阶段2：精筛（从右向左） =================
    int left1 = max(0, bestIdx - R);
    int right1 = min(N - 1, bestIdx + R);

    for (int i = right1; i >= left1; --i) {
        if (qcnt >= SAFE_Q) break;
        if (visited.count(i)) continue;
        query(i);
    }

    // ================= 阶段3：右补一次（默认执行） =================
    int lastR = right1;
    if (qcnt < SAFE_Q && lastR < N - 1) {
        int start = lastR + 1;
        int end = min(N - 1, lastR + W);
        for (int i = start; i <= end; ++i) {
            if (qcnt >= SAFE_Q) break;
            if (visited.count(i)) continue;
            query(i);
        }
    }

    // ================= 阶段4：回目标点 =================
    // 回目标不受 SAFE_Q 限制（前面预算已留余量）
    if (lastIdx != bestIdx) {
        query(bestIdx);
    }

    printf("DONE\n");
    fflush(stdout);
    return 0;
}