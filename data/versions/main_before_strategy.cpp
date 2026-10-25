#include <bits/stdc++.h>
using namespace std;

int N;
int pos = 0;
int last_dir = 0;
int osc = 0;
int qcnt = 0;
int max_right = 0;
long long best_val = -1;
int best_idx = -1;
unordered_map<int, long long> cache;
double mid;

bool better(int idx, long long val, int bidx, long long bval) {
    if (val > bval) return true;
    if (val < bval) return false;
    double d1 = fabs(idx - mid);
    double d2 = fabs(bidx - mid);
    if (d1 < d2 - 1e-9) return true;
    if (d1 > d2 + 1e-9) return false;
    return idx < bidx;
}

long long ask(int idx) {
    cout << idx << "\n";
    cout.flush();

    long long v;
    cin >> v;

    int dir = (idx > pos) ? 1 : (idx < pos ? -1 : 0);
    if (dir != 0) {
        if (last_dir != 0 && dir != last_dir) osc++;
        last_dir = dir;
    }

    qcnt++;
    max_right = max(max_right, idx);
    pos = idx;
    cache[idx] = v;

    if (better(idx, v, best_idx, best_val)) {
        best_idx = idx;
        best_val = v;
    }
    return v;
}

void refine(int L, int R) {
    int s = (R - L > 8) ? 2 : 1;
    for (int x = L + 1; x < R; x += s) {
        if (cache.count(x)) continue;
        ask(x);
    }
}

void finish() {
    int l = max(0, best_idx - 3);
    int r = min(N - 1, best_idx + 3);
    for (int x = l; x <= r; x++) {
        if (!cache.count(x)) {
            ask(x);
        }
    }

    if (pos != best_idx) {
        ask(best_idx);
    }

    cout << "DONE\n";
    cout.flush();
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N;
    mid = (N - 1) / 2.0;

    int init = min(4, N);
    for (int i = 0; i < init; i++) {
        ask(i);
    }

    if (N <= 4) {
        finish();
    }

    int prev_idx = init - 1;
    long long prev_val = cache[prev_idx];
    int step = 2;
    int refine_count = 0;
    const int MAX_REFINE = 5;
    const int RED_HARD = 180;
    const int Q_LIMIT = 170;

    while (true) {
        if (qcnt >= Q_LIMIT) break;
        if (max_right - best_idx >= RED_HARD) break;
        if (prev_idx >= N - 1) break;

        // 如果最佳峰已经越过中点，且冗余达到软阈值，提前停止
        if (best_idx >= mid && max_right - best_idx >= 50) break;

        int next = prev_idx + step;
        if (next >= N) {
            next = N - 1;
            if (next <= prev_idx) break;
        }

        long long v = ask(next);

        if (v < prev_val) {
            bool can_refine = (refine_count < MAX_REFINE);
            if (can_refine && (prev_val >= best_val * 0.95 || prev_idx == best_idx)) {
                refine(prev_idx, next);
                refine_count++;
                prev_idx = next;
                prev_val = cache[next];
                step = 2;
                continue;
            } else {
                prev_idx = next;
                prev_val = v;
                step = max(2, step / 2);
                continue;
            }
        } else {
            prev_idx = next;
            prev_val = v;
            step = min(step * 2, 32);
            continue;
        }
    }

    finish();
    return 0;
}