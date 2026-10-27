#include <bits/stdc++.h>
using namespace std;

int N;
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
    if (scanf("%lld", &v) != 1) exit(0);
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

    const int STEP = 3;
    const int MAX_PROBES = 190;
    int probes = 0;
    int maxRight = 0;

    while (probes < MAX_PROBES && cur + STEP < N) {
        cur += STEP;
        long long nv = query(cur);
        ++probes;
        curVal = nv;
        maxRight = max(maxRight, cur);
    }

    // 回退到已知最高点
    int target = bestPos;
    if (cur != target) {
        query(target);
    }

    printf("DONE\n");
    fflush(stdout);
    return 0;
}