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

        // Rank coarse candidates by raw value and the exact statement tie rule.
        // Spend the remaining budget on contiguous neighborhoods of the best
        // candidates. All probes run right-to-left, so there are at most two
        // direction reversals including the final return to the best position.
        std::vector<int> ranked;
        for (int j = 0; j < static_cast<int>(coarse_.size()); ++j) {
            const int x = coarse_[j];
            const bool left_better = j > 0 && better(coarse_[j - 1], x);
            const bool right_better = j + 1 < static_cast<int>(coarse_.size()) &&
                better(coarse_[j + 1], x);
            // A flat, low baseline can itself have a local maximum under the
            // center tie rule. Revisiting it would waste hundreds of motor steps.
            // Only refine secondary peaks in the top half of observed contrast.
            const bool competitive = 2 * (values_[best_] - values_[x]) <=
                values_[best_] - floor;
            if (!left_better && !right_better && competitive) ranked.push_back(x);
        }
        std::sort(ranked.begin(), ranked.end(), [this](int a, int b) {
            return better(a, b);
        });
        std::vector<bool> selected(n_, false);
        int remaining = std::min(100, kQueryLimit - 1 - queries_);
        int windows = 0;
        // Make the true array center available for a flat peak/constant array.
        // It is queried only if it lies inside a selected local neighborhood.
        for (int center : ranked) {
            std::vector<int> neighborhood;
            for (int x = std::max(0, center - 2 * stride);
                 x <= std::min(rightmost, center + 2 * stride); ++x) {
                if (values_[x] < 0 && !selected[x]) neighborhood.push_back(x);
            }
            if (neighborhood.empty()) continue;
            // Keep each refinement window whole; a partial window introduces
            // an arbitrary bias toward one edge of the interval.
            if (static_cast<int>(neighborhood.size()) > remaining) continue;
            for (int x : neighborhood) selected[x] = true;
            remaining -= static_cast<int>(neighborhood.size());
            if (++windows == 3 || remaining == 0) break;
        }
        // V3 changes ONLY refinement. Keep the V1 core windows and spend
        // additional queries on competitive regions that those windows miss.
        // Reserve one real parking query: at most 198 queries for official N.
        const int fine_limit = 197;
        const int fine_budget = std::max(0, fine_limit - queries_);
        int core_count = static_cast<int>(std::count(selected.begin(), selected.end(), true));
        auto prediction = [&](int x, const std::vector<int>& known) {
            const auto it = std::lower_bound(known.begin(), known.end(), x);
            if (it == known.begin() || it == known.end())
                return static_cast<double>(values_[best_]);
            const int l = *(it - 1), r = *it;
            const double t = static_cast<double>(x - l) / (r - l);
            return values_[l] * (1.0 - t) + values_[r] * t;
        };
        // V1 can use 198 non-parking queries. If its core already fills that
        // limit, discard only one predicted-low point for V3's stricter cap.
        while (core_count > fine_budget) {
            int drop = -1;
            double lowest = std::numeric_limits<double>::infinity();
            for (int x = 0; x <= rightmost; ++x) {
                if (!selected[x]) continue;
                const double predicted = prediction(x, coarse_);
                if (drop < 0 || predicted < lowest ||
                    (predicted == lowest && std::abs(x - best_) > std::abs(drop - best_))) {
                    drop = x;
                    lowest = predicted;
                }
            }
            if (drop < 0) break;
            selected[drop] = false;
            --core_count;
        }
        // An all-equal coarse scan retains V1's entire refinement path. No
        // center-only shortcut or additional flat-prefix exploration is added.
        const int extra_budget = fine_budget - core_count;
        if (values_[best_] > floor && extra_budget > 0) {
            std::vector<double> residuals;
            for (int j = 1; j + 1 < static_cast<int>(coarse_.size()); ++j) {
                const double a = static_cast<double>(values_[coarse_[j - 1]]);
                const double b = static_cast<double>(values_[coarse_[j]]);
                const double c = static_cast<double>(values_[coarse_[j + 1]]);
                residuals.push_back(std::abs(b - (a + c) * 0.5));
            }
            const double noise = median(residuals);
            const double cutoff = values_[best_] -
                std::max(3.0 * noise, 0.02 * (values_[best_] - floor));
            std::vector<bool> eligible(n_, false);
            for (int j = 0; j + 1 < static_cast<int>(coarse_.size()); ++j) {
                const int l = coarse_[j], r = coarse_[j + 1];
                if (std::max(values_[l], values_[r]) >= cutoff) {
                    for (int x = l; x <= r; ++x) eligible[x] = true;
                }
            }
            std::vector<int> pool;
            for (int x = 0; x <= rightmost; ++x) {
                if (eligible[x] && values_[x] < 0 && !selected[x]) pool.push_back(x);
            }
            if (static_cast<int>(pool.size()) <= extra_budget) {
                for (int x : pool) selected[x] = true;
            } else {
                // Cover extra regions before deciding where their remaining
                // fine queries go. Core V1 windows are never taken away here.
                const int middle_count = std::min(24, extra_budget / 3);
                for (int j = middle_count - 1; j >= 0; --j) {
                    const auto k = static_cast<std::size_t>(
                        (2LL * j + 1) * pool.size() / (2 * middle_count));
                    if (queries_ < fine_limit) query(pool[k]);
                }
                std::vector<int> known;
                for (int x = 0; x <= rightmost; ++x) {
                    if (values_[x] >= 0) known.push_back(x);
                }
                const double updated_cutoff = values_[best_] -
                    std::max(3.0 * noise, 0.02 * (values_[best_] - floor));
                struct Extra { int x; double priority; };
                std::vector<Extra> extras;
                for (int x : pool) {
                    if (values_[x] >= 0) continue;
                    const auto it = std::lower_bound(known.begin(), known.end(), x);
                    if (it == known.begin() || it == known.end()) continue;
                    const int l = *(it - 1), r = *it;
                    if (std::max(values_[l], values_[r]) < updated_cutoff) continue;
                    const double uncertainty = 0.20 * std::abs(values_[r] - values_[l]);
                    extras.push_back({x, prediction(x, known) + uncertainty});
                }
                std::sort(extras.begin(), extras.end(), [this](const Extra& a, const Extra& b) {
                    if (a.priority != b.priority) return a.priority > b.priority;
                    const int da = std::abs(a.x - best_), db = std::abs(b.x - best_);
                    return da != db ? da < db : a.x < b.x;
                });
                int room = extra_budget - middle_count;
                for (const auto& item : extras) {
                    if (room-- <= 0) break;
                    selected[item.x] = true;
                }
                if (middle_count > 0) {
                    // Rightward coarse -> leftward middle -> rightward fine
                    // -> optional final return: at most three reversals.
                    for (int x = 0; x <= rightmost; ++x) {
                        if (selected[x] && queries_ < fine_limit) query(x);
                    }
                    finish();
                    return;
                }
            }
        }

        for (int x = rightmost; x >= 0; --x) {
            if (selected[x] && queries_ < fine_limit) query(x);
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
