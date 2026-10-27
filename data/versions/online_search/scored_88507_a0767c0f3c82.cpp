#include <bits/stdc++.h>
using namespace std;

int N;
int lastIdx = -1;

long long ask(int idx) {
    printf("%d\n", idx);
    fflush(stdout);

    long long v;
    if (scanf("%lld", &v) != 1) {
        exit(0);
    }
    lastIdx = idx;
    return v;
}

// 清晰度更高优先；清晰度相同按题目平局规则：
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

    // 可调参数：
    // STEP 越大，粗扫次数越少，但漏掉真峰风险增加
    // R 越大，复查范围越大，但搜索步数、时间、冗余会增加
    const int STEP = 12;
    const int R = 56;

    int bestIdx = 0;
    long long bestVal = -1;

    // 第一阶段：粗扫。保证查询 0 和 N-1。
    int idx = 0;
    while (true) {
        long long v = ask(idx);

        if (bestVal < 0 || better(v, idx, bestVal, bestIdx)) {
            bestVal = v;
            bestIdx = idx;
        }

        if (idx == N - 1) break;

        int nxt = idx + STEP;
        if (nxt >= N - 1) {
            idx = N - 1;
        } else {
            idx = nxt;
        }
    }

    // 第二阶段：在粗最高点左右 R 范围内逐点复查。
    int left = max(0, bestIdx - R);
    int right = min(N - 1, bestIdx + R);

    long long localBestVal = bestVal;
    int localBestIdx = bestIdx;

    // 从右向左扫描
    for (int i = right; i >= left; --i) {
        if (i == bestIdx) continue; // 粗扫已经读过

        long long v = ask(i);

        if (better(v, i, localBestVal, localBestIdx)) {
            localBestVal = v;
            localBestIdx = i;
        }
    }

    // 最后把电机停到目标点。
    // 如果最后查询的位置已经是目标点，则不再额外查询。
    if (lastIdx != localBestIdx) {
        ask(localBestIdx);
    }

    printf("DONE\n");
    fflush(stdout);

    return 0;
}