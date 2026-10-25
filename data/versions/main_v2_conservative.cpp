#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <vector>

// Conservative alternative: retain v1 stopping and reallocate refinement.
// Diagnostics must never go to stdout.
class Autofocus {
    static constexpr int kQueryLimit = 199;
    int n_;
    int queries_ = 0;
    int position_ = 0;
    int best_ = -1;
    std::vector<std::int64_t> values_;
    std::vector<int> coarse_;

    bool better(int lhs, int rhs) const {
        if (rhs < 0) return true;
        if (values_[lhs] != values_[rhs]) return values_[lhs] > values_[rhs];
        const int dl = std::abs(2 * lhs - (n_ - 1));
        const int dr = std::abs(2 * rhs - (n_ - 1));
        return dl != dr ? dl < dr : lhs < rhs;
    }

    void query(int index) {
        // Cached reads do not move the motor; finish() explicitly parks it.
        if (values_[index] >= 0 || queries_ >= kQueryLimit - 1) return;
        std::cout << index << std::endl;
        std::int64_t value;
        if (!(std::cin >> value) || value < 0 || value > 2147483647LL) {
            // No more valid responses: stop without producing a stream of queries.
            std::exit(0);
        }
        ++queries_;
        position_ = index;
        values_[index] = value;
        if (better(index, best_)) best_ = index;
    }

    static double median(std::vector<double> items) {
        if (items.empty()) return 0.0;
        const auto mid = items.begin() + items.size() / 2;
        std::nth_element(items.begin(), mid, items.end());
        return *mid;
    }

    void finish() {
        if (best_ >= 0 && position_ != best_ && queries_ < kQueryLimit) {
            // A cached best value is not a physical return to that position.
            std::cout << best_ << std::endl;
            std::int64_t value;
            if (!(std::cin >> value)) std::exit(0);
            ++queries_;
            position_ = best_;
        }
        std::cout << "DONE" << std::endl;
    }

public:
    explicit Autofocus(int n) : n_(n), values_(n, -1) {}

    void run() {
        // Small inputs include the statement's 12-element example. An exact
        // monotone scan plus one return fits the query budget for n <= 198.
        if (n_ <= 198) {
            for (int x = 0; x < n_; ++x) query(x);
            finish();
            return;
        }

        // Retain v1's coarse spacing for the conservative alternative.
        // Refinement has its own budget, leaving a safe margin below 199
        // while covering narrow peaks better than large jumps.
        const int stride = 8;
        double smooth_peak = -1.0;
        double previous_smooth = -1.0;
        int smooth_peak_position = 0;
        std::int64_t floor = std::numeric_limits<std::int64_t>::max();
        int falling = 0;
        int rightmost = 0;
        for (int x = 0;; x = std::min(n_ - 1, x + stride)) {
            query(x);
            coarse_.push_back(x);
            rightmost = x;
            floor = std::min(floor, values_[x]);
            const int size = static_cast<int>(coarse_.size());
            if (size >= 3) {
                const int a = coarse_[size - 3];
                const int b = coarse_[size - 2];
                const int c = coarse_[size - 1];
                const double smooth = median({static_cast<double>(values_[a]),
                                              static_cast<double>(values_[b]),
                                              static_cast<double>(values_[c])});
                if (smooth > smooth_peak) {
                    smooth_peak = smooth;
                    smooth_peak_position = b;
                    falling = 0;
                } else {
                    ++falling;
                }

                // Estimate small-scale variation from all second differences.
                // A short quiet patch in a noisy baseline must not erase the
                // noise evidence and turn an early random spike into a peak.
                // A large noise estimate delays the soft stop; it never changes
                // the final objective, which is the largest raw observed value.
                std::vector<double> residuals;
                for (int j = 1; j + 1 < size; ++j) {
                    const double v0 = static_cast<double>(values_[coarse_[j - 1]]);
                    const double v1 = static_cast<double>(values_[coarse_[j]]);
                    const double v2 = static_cast<double>(values_[coarse_[j + 1]]);
                    residuals.push_back(std::abs(v1 - (v0 + v2) * 0.5));
                }
                const double noise = median(residuals);
                const double drop_needed = std::max({1.0, 3.0 * noise,
                                                    0.10 * (smooth_peak - floor)});
                const bool distinct_peak =
                    smooth_peak - floor >= std::max(1.0, 8.0 * noise) ||
                    values_[best_] - floor >= std::max(1.0, 16.0 * noise);
                const bool recovering = values_[c] - values_[b] > std::max(1.0, noise) ||
                    smooth - previous_smooth > std::max(1.0, noise);
                const bool persistent_drop = distinct_peak && !recovering && falling >= 4 &&
                    x - smooth_peak_position >= std::max(96, 6 * stride) &&
                    x - best_ >= 96 &&
                    smooth_peak - smooth > drop_needed;

                // This is a heuristic guard relative to an OBSERVED maximum,
                // not a guarantee of redundancy relative to the unseen peak.
                const bool constant_so_far = floor == values_[best_];
                const bool lookahead_used = x - best_ >= 160 &&
                    (distinct_peak || constant_so_far);
                previous_smooth = smooth;
                // Protect the left side of a broad competitive peak before
                // using up the entire redundancy allowance on its noisy top.
                const auto cutoff = values_[best_] - (values_[best_] - floor) * 0.15;
                int jbest = static_cast<int>(std::find(coarse_.begin(), coarse_.end(), best_) - coarse_.begin());
                int jleft = jbest;
                while (jleft > 0 && values_[coarse_[jleft - 1]] >= cutoff) --jleft;
                const bool wide_band = distinct_peak && x - best_ >= 2 * stride &&
                    x - coarse_[jleft] >= 176 && values_[best_] > floor;
                if (persistent_drop || lookahead_used || wide_band) break;
            }
            if (x == n_ - 1) break;
        }

        if (values_[best_] == floor) {
            query((n_ - 1) / 2);
            finish();
            return;
        }
        std::vector<double> refine_residual;
        for (int j = 1; j + 1 < static_cast<int>(coarse_.size()); ++j) {
            const double a = static_cast<double>(values_[coarse_[j - 1]]);
            const double b = static_cast<double>(values_[coarse_[j]]);
            const double c = static_cast<double>(values_[coarse_[j + 1]]);
            refine_residual.push_back(std::abs(b - (a + c) * 0.5));
        }
        const double refine_noise = median(refine_residual);
        // Cover connected high-value intervals, instead of spending all
        // fine queries on three local noise bumps inside a single broad peak.
        const double cutoff = values_[best_] - std::max(3.0 * refine_noise, 0.02 * (values_[best_] - floor));
        std::vector<bool> eligible(n_, false);
        for (int j = 0; j + 1 < static_cast<int>(coarse_.size()); ++j) {
            int a = coarse_[j], b = coarse_[j + 1];
            if (std::max(values_[a], values_[b]) >= cutoff) {
                for (int x = a; x <= b; ++x) eligible[x] = true;
            }
        }
        std::vector<int> pool;
        for (int x = 0; x <= rightmost; ++x) {
            if (eligible[x] && values_[x] < 0) pool.push_back(x);
        }
        int budget = kQueryLimit - 1 - queries_;
        if (static_cast<int>(pool.size()) <= budget) {
            for (auto it = pool.rbegin(); it != pool.rend(); ++it) query(*it);
        } else {
            // A whole peak band may not fit. First cover it uniformly at a
            // medium resolution, then reallocate fine queries using new data.
            const int middle_count = std::min(40, budget / 3);
            std::vector<int> middle;
            for (int j = 0; j < middle_count; ++j) {
                int k = static_cast<int>((2LL * j + 1) * pool.size() / (2 * middle_count));
                middle.push_back(pool[k]);
            }
            std::sort(middle.rbegin(), middle.rend());
            for (int x : middle) query(x);
            budget = kQueryLimit - 1 - queries_;
            std::vector<int> known;
            for (int x = 0; x <= rightmost; ++x) {
                if (values_[x] >= 0) known.push_back(x);
            }
            struct Candidate { int x; double priority; };
            std::vector<Candidate> candidates;
            for (int x : pool) {
                if (values_[x] >= 0) continue;
                const auto it = std::lower_bound(known.begin(), known.end(), x);
                int r = *it, l = *(it - 1);
                const double t = double(x - l) / (r - l);
                const double predicted = values_[l] * (1.0 - t) + values_[r] * t;
                const double uncertainty = 0.20 * std::abs(values_[r] - values_[l]);
                candidates.push_back({x, predicted + uncertainty});
            }
            std::sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b) {
                return a.priority != b.priority ? a.priority > b.priority : a.x < b.x;
            });
            std::vector<int> fine;
            for (const auto& item : candidates) {
                if (static_cast<int>(fine.size()) >= budget) break;
                fine.push_back(item.x);
            }
            std::sort(fine.begin(), fine.end());
            for (int x : fine) query(x);
        }
        finish();
    }
};

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    if (!(std::cin >> n) || n < 1 || n > 1000) return 0;
    Autofocus(n).run();
    return 0;
}
