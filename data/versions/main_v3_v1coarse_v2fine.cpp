#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <vector>

// Standalone interactive submission. Diagnostics must never go to stdout.
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

        // Even at N=1000, stride 8 needs at most 126 coarse queries.
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
                if (persistent_drop || lookahead_used) break;
            }
            if (x == n_ - 1) break;
        }

        // Inline the V2 refinement noise estimator without changing V1 coarse search.
        const auto fine_noise = [&]() {
        std::vector<double> residual;
        for (int j = 1; j + 1 < static_cast<int>(coarse_.size()); ++j) {
            const int a = coarse_[j - 1], b = coarse_[j], c = coarse_[j + 1];
            const double prediction = static_cast<double>(values_[a]) +
                (static_cast<double>(values_[c]) - values_[a]) * (b - a) / (c - a);
            residual.push_back(std::abs(values_[b] - prediction));
        }
        return median(residual);
        };

        // Rank every unsampled position by its interpolated raw clarity.
        // All plausible points receive the remaining budget; this can cover a
        // 100-point noisy summit instead of committing to +/-16 at a noisy max.
        struct Candidate { int index; double predicted; bool mandatory; };
        std::vector<Candidate> candidates;
        const double jitter = fine_noise();
        const double contrast = static_cast<double>(values_[best_] - floor);
        const double allowance = std::max(1.0, 3.0 * jitter + 0.02 * contrast);
        const double threshold = static_cast<double>(values_[best_]) - allowance;
        for (int j = 0; j + 1 < static_cast<int>(coarse_.size()); ++j) {
            const int a = coarse_[j], b = coarse_[j + 1];
            for (int p = a + 1; p < b; ++p) {
                const double predicted = static_cast<double>(values_[a]) +
                    (static_cast<double>(values_[b]) - values_[a]) * (p - a) / (b - a);
                const bool boundary = (values_[a] >= threshold) != (values_[b] >= threshold);
                const bool mandatory = std::abs(p - best_) <= 16 || boundary;
                if (mandatory || std::max(values_[a], values_[b]) >= threshold)
                    candidates.push_back({p, predicted, mandatory});
            }
        }
        std::sort(candidates.begin(), candidates.end(), [this](const Candidate& a,
                                                             const Candidate& b) {
            if (a.mandatory != b.mandatory) return a.mandatory;
            if (a.predicted != b.predicted) return a.predicted > b.predicted;
            return std::abs(a.index - best_) < std::abs(b.index - best_);
        });
        const int budget = kQueryLimit - 1 - queries_;
        if (static_cast<int>(candidates.size()) > budget) candidates.resize(budget);
        std::sort(candidates.begin(), candidates.end(), [](const Candidate& a,
                                                          const Candidate& b) {
            return a.index > b.index;
        });
        for (const auto& p : candidates) query(p.index);
        (void)rightmost;
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
