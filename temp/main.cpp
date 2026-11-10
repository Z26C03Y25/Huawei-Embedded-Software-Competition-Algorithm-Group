#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    if (!(cin >> N) || N <= 0) return 0;

    // Only change these two endpoints. Both endpoints are included.
    int a = 800;
    int b = 750;

    if (a < b) swap(a, b);
    b = max(b, 0);

    if (N <= a) {
        cout << 0 << endl;
        long long value;
        if (!(cin >> value)) return 0;
        cout << "DONE" << endl;
        return 0;
    }

    long long bestVal = -1;
    int bestPos = b;
    for (int i = b; i <= a; ++i) {
        cout << i << endl;
        long long value;
        if (!(cin >> value)) return 0;

        const long long distance = abs(2LL * i - (N - 1));
        const long long bestDistance = abs(2LL * bestPos - (N - 1));
        if (value > bestVal ||
            (value == bestVal &&
             (distance < bestDistance ||
              (distance == bestDistance && i < bestPos)))) {
            bestVal = value;
            bestPos = i;
        }
    }

    // Always issue this query, even if bestPos equals the last scanned point.
    cout << bestPos << endl;
    long long value;
    if (!(cin >> value)) return 0;
    cout << "DONE" << endl;
    return 0;
}
