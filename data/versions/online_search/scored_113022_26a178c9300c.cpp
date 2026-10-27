#include <bits/stdc++.h>
using namespace std;

int N;
int lastIdx = -1;

long long ask(int idx) {
    printf("%d\n", idx);
    fflush(stdout);
    long long v;
    if (scanf("%lld", &v) != 1) exit(0);
    lastIdx = idx;
    return v;
}

bool better(long long val, int idx, long long curVal, int curIdx) {
    if (val != curVal) return val > curVal;
    long long d1 = llabs(2LL * idx - (N - 1));
    long long d2 = llabs(2LL * curIdx - (N - 1));
    if (d1 != d2) return d1 < d2;
    return idx < curIdx;
}

int main() {
    if (scanf("%d", &N) != 1) return 0;

    const int GAP = 50;
    const int R1 = 45;
    const int R2 = 45;

    int bestIdx = -1;
    long long bestVal = -1;
    unordered_set<int> visited;

    auto updateBest = [&](long long v, int idx) {
        if (bestIdx == -1 || better(v, idx, bestVal, bestIdx)) {
            bestVal = v;
            bestIdx = idx;
        }
    };

    auto query = [&](int idx) -> long long {
        long long v = ask(idx);
        visited.insert(idx);
        updateBest(v, idx);
        return v;
    };

    // 阶段1：初筛向右
    int idx = 0;
    while (true) {
        long long v = query(idx);
        
        if (idx == N - 1) break;
        
        int nxt = idx + GAP;
        if (nxt >= N) nxt = N - 1;
        
        // 提前停止：如果当前点已经是 N-1，或者下一个点可能下降
        if (idx > 0 && v < bestVal) {
            // 当前点低于历史最高，已过峰（或假峰），停止粗扫
            // 但需要把当前点纳入考虑（可能当前点就是下降的第一个点）
            break;
        }
        
        if (nxt == idx) break;
        idx = nxt;
    }

    // 阶段2：复查1，在 bestIdx ± R1 内从右向左
    int left1 = max(0, bestIdx - R1);
    int right1 = min(N - 1, bestIdx + R1);

    long long localBestVal = bestVal;
    int localBestIdx = bestIdx;

    for (int i = right1; i >= left1; --i) {
        if (visited.count(i)) continue;
        long long v = query(i);
        if (better(v, i, localBestVal, localBestIdx)) {
            localBestVal = v;
            localBestIdx = i;
        }
    }

    // 阶段3：如果需要，复查2向右
    // 触发条件：localBestIdx 接近 right1，说明峰可能在右侧
    bool needRight2 = (localBestIdx >= right1 - 5) && (right1 < N - 1);
    
    if (needRight2) {
        int left2 = right1 + 1;
        int right2 = min(N - 1, right1 + R2);
        
        for (int i = left2; i <= right2; ++i) {
            if (visited.count(i)) continue;
            long long v = query(i);
            if (better(v, i, localBestVal, localBestIdx)) {
                localBestVal = v;
                localBestIdx = i;
            }
        }
    }

    // 阶段4：让电机停在目标点
    if (lastIdx != localBestIdx) {
        ask(localBestIdx);
    }

    printf("DONE\n");
    fflush(stdout);
    return 0;
}