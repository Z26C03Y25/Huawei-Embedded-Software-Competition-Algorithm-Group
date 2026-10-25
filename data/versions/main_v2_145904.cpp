#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <vector>

// Interactive solver: coarse shape detection followed by dense sampling of
// the entire plausible high-value band, rather than three fixed-size windows.
class Autofocus {
    static constexpr int kLimit = 199;
    int n_, count_ = 0, position_ = 0, best_ = -1;
    std::vector<std::int64_t> value_;
    std::vector<int> coarse_;

    bool better(int a, int b) const {
        if (b < 0) return true;
        if (value_[a] != value_[b]) return value_[a] > value_[b];
        const int da = std::abs(2 * a - n_ + 1);
        const int db = std::abs(2 * b - n_ + 1);
        return da != db ? da < db : a < b;
    }

    void query(int p) {
        if (value_[p] >= 0 || count_ >= kLimit - 1) return;
        std::cout << p << std::endl;
        std::int64_t v;
        if (!(std::cin >> v) || v < 0 || v > 2147483647LL) std::exit(0);
        ++count_;
        position_ = p;
        value_[p] = v;
        if (better(p, best_)) best_ = p;
    }

    static double median(std::vector<double> v) {
        if (v.empty()) return 0;
        auto p = v.begin() + v.size() / 2;
        std::nth_element(v.begin(), p, v.end());
        return *p;
    }

    double noise() const {
        std::vector<double> residual;
        for (int j = 1; j + 1 < static_cast<int>(coarse_.size()); ++j) {
            const int a = coarse_[j - 1], b = coarse_[j], c = coarse_[j + 1];
            const double prediction = static_cast<double>(value_[a]) +
                (static_cast<double>(value_[c]) - value_[a]) * (b - a) / (c - a);
            residual.push_back(std::abs(value_[b] - prediction));
        }
        return median(residual);
    }

    void finish() {
        if (position_ != best_ && count_ < kLimit) {
            std::cout << best_ << std::endl;
            std::int64_t response;
            if (!(std::cin >> response)) std::exit(0);
            ++count_;
        }
        std::cout << "DONE" << std::endl;
    }

public:
    explicit Autofocus(int n) : n_(n), value_(n, -1) {}

    void run() {
        if (n_ <= 198) {
            for (int i = 0; i < n_; ++i) query(i);
            finish();
            return;
        }

        // A coarser global mesh leaves enough queries to cover broad noisy
        // peaks densely; the final stage never optimizes a smoothed objective.
        const int stride = 12;
        std::int64_t floor = std::numeric_limits<std::int64_t>::max();
        double previous_smooth = 0;
        double smooth_peak = 0;
        for (int x = 0;;) {
            query(x);
            coarse_.push_back(x);
            floor = std::min(floor, value_[x]);
            const int size = static_cast<int>(coarse_.size());
            bool prominent = false;
            int band_left = best_;
            if (size >= 3) {
                const int a = coarse_[size - 3];
                const int b = coarse_[size - 2];
                const double smooth = median({static_cast<double>(value_[a]),
                    static_cast<double>(value_[b]), static_cast<double>(value_[x])});
                const double jitter = noise();
                const double contrast = static_cast<double>(value_[best_] - floor);
                smooth_peak = std::max(smooth_peak, smooth);
                prominent = smooth_peak - floor > std::max(1.0, 8.0 * jitter) ||
                    contrast > std::max(1.0, 16.0 * jitter);
                const double band_floor = value_[best_] -
                    std::max(3.0 * jitter, 0.04 * contrast);
                for (int p : coarse_) {
                    if (value_[p] >= band_floor) {
                        band_left = p;
                        break;
                    }
                }
                const bool recovering = value_[x] - value_[b] > std::max(1.0, jitter) ||
                    smooth - previous_smooth > std::max(1.0, jitter);
                // Narrow clean peaks can be localized well before an arbitrary
                // 96-step lookahead. Noisy broad peaks require a larger fall.
                const double drop = value_[best_] - smooth;
                const bool clear_descent = prominent && !recovering &&
                    x - best_ >= 36 && drop > std::max(3.0 * jitter, 0.04 * contrast);
                previous_smooth = smooth;
                // A wide high plateau may hide its true raw maximum near its
                // left edge. Anchor this guard to the competitive band, not to
                // the latest lucky coarse maximum in the middle of that band.
                if (clear_descent || (prominent && x - band_left >= 168)) break;
            }
            if (x == n_ - 1) break;
            const int next = std::min(n_ - 1, x + stride);
            if (prominent && next - band_left > 180) break;
            x = next;
        }

        // Rank every unsampled position by its interpolated raw clarity.
        // All plausible points receive the remaining budget; this can cover a
        // 100-point noisy summit instead of committing to +/-16 at a noisy max.
        struct Candidate { int index; double predicted; bool mandatory; };
        std::vector<Candidate> candidates;
        const double jitter = noise();
        const double contrast = static_cast<double>(value_[best_] - floor);
        const double allowance = std::max(1.0, 3.0 * jitter + 0.02 * contrast);
        const double threshold = static_cast<double>(value_[best_]) - allowance;
        for (int j = 0; j + 1 < static_cast<int>(coarse_.size()); ++j) {
            const int a = coarse_[j], b = coarse_[j + 1];
            for (int p = a + 1; p < b; ++p) {
                const double predicted = static_cast<double>(value_[a]) +
                    (static_cast<double>(value_[b]) - value_[a]) * (p - a) / (b - a);
                const bool boundary = (value_[a] >= threshold) != (value_[b] >= threshold);
                const bool mandatory = std::abs(p - best_) <= 16 || boundary;
                if (mandatory || std::max(value_[a], value_[b]) >= threshold)
                    candidates.push_back({p, predicted, mandatory});
            }
        }
        std::sort(candidates.begin(), candidates.end(), [this](const Candidate& a,
                                                             const Candidate& b) {
            if (a.mandatory != b.mandatory) return a.mandatory;
            if (a.predicted != b.predicted) return a.predicted > b.predicted;
            return std::abs(a.index - best_) < std::abs(b.index - best_);
        });
        const int budget = kLimit - 1 - count_;
        if (static_cast<int>(candidates.size()) > budget) candidates.resize(budget);
        std::sort(candidates.begin(), candidates.end(), [](const Candidate& a,
                                                          const Candidate& b) {
            return a.index > b.index;
        });
        for (const auto& p : candidates) query(p.index);
        finish();
    }
};

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    if (!(std::cin >> n) || n < 1 || n > 1000) return 0;
    Autofocus(n).run();
}
