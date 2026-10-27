#include <bits/stdc++.h>
using namespace std;

int N;
int queryCount = 0;

long long globalMaxVal = -1;   // 所有已查询点中的最大值
int globalMaxIdx = -1;         // 按平局规则选出的最佳下标
long long strictMaxVal = -1;   // 严格最大值，用于早停
int strictMaxIdx = -1;         // 严格最大值位置

// 判断 i 是否比 j 更适合作为主峰：值相同则更接近中心，再相同取小下标
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
    ++queryCount;

    if (v > globalMaxVal || (v == globalMaxVal && better(idx, globalMaxIdx))) {
        globalMaxVal = v;
        globalMaxIdx = idx;
    }

    if (v > strictMaxVal || strictMaxIdx < 0) {
        strictMaxVal = v;
        strictMaxIdx = idx;
    }

    return v;
}

int main() {
    if (scanf("%d", &N) != 1) return 0;

    long long v0 = query(0);

    int cur = 0;
    long long curVal = v0;

    int step = max(1, N / 32);
    int minStep = max(1, N / 64);
    int maxStep = max(1, N / 24);
    maxStep = min(maxStep, 30);
    minStep = min(minStep, maxStep);
    step = min(max(step, minStep), maxStep);

    // 允许超过当前最优点的最大右探距离
    const int EXTRA = 120;

    // 第一阶段：斜率自适应扫描
    while (cur < N - 1 && queryCount < 80) {
        int next = min(N - 1, cur + step);
        if (next == cur) break;

        long long nv = query(next);

        if (nv > curVal) {
            // 上升趋势，增大步长
            step = min(maxStep, max(step, step * 2));
        } else {
            // 下降或持平，缩小步长
            step = max(minStep, step * 2 / 3);
        }

        cur = next;
        curVal = nv;

        // 已经越过严格最优点足够远，认为主峰已在左侧
        if (cur > strictMaxIdx + EXTRA) {
            break;
        }
    }

    // 第二阶段：在扫描最优位置附近逐点细化
    int center = strictMaxIdx;
    int W = max(20, maxStep / 2 + 15);

    int L = max(0, center - W);
    int R = min(N - 1, center + W);

    // 先移动到 L 并查询
    if (cur != L) {
        query(L);
        cur = L;
    }

    // 从 L+1 到 R 逐点查询
    for (int idx = L + 1; idx <= R; ++idx) {
        query(idx);
        cur = idx;

        // 安全保护，远小于 200
        if (queryCount >= 195) break;
    }

    // 最终目标点
    int target = globalMaxIdx;

    // 保证最后一次查询就是目标点
    if (cur != target) {
        query(target);
    }

    printf("DONE\n");
    fflush(stdout);

    return 0;
}