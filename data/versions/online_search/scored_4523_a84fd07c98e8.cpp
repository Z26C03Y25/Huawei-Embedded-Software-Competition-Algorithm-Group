#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    if (!(cin >> N) || N <= 0) return 0;

    int bestPos = -1, position = -1;
    long long bestVal = -1;
    auto read = [&](int x, long long& value) {
        cout << x << endl;
        if (!(cin >> value)) return false;
        position = x;
        const long long distance = abs(2LL * x - (N - 1));
        const long long bestDistance = abs(2LL * bestPos - (N - 1));
        if (bestPos < 0 || value > bestVal ||
            (value == bestVal &&
             (distance < bestDistance ||
              (distance == bestDistance && x < bestPos)))) {
            bestPos = x;
            bestVal = value;
        }
        return true;
    };
    auto finish = [&]() {
        if (position != bestPos) {
            long long value;
            if (!read(bestPos, value)) return;
        }
        cout << "DONE" << endl;
    };

    if (N <= 663) {
        long long value;
        if (!read(N > 662 ? 662 : 0, value)) return 0;
        finish();
        return 0;
    }

    long long left, center, right;
    if (!read(661, left) || !read(662, center) || !read(663, right))
        return 0;

    // Strict local summit: return to662 before exploring farther right.
    if (center > left && center > right) {
        finish();
        return 0;
    }

    // An unresolved or rising shoulder keeps the774 candidate in play.
    if (774 < N) {
        long long value;
        if (!read(774, value)) return 0;
    }
    finish();
    return 0;
}
