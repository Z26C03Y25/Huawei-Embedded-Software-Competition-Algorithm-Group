import java.io.BufferedInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.TreeSet;

public class Main {
    // Empirically validated positions, not unconditional stopping commands.
    private static final int[] PRIOR = {30, 202, 213, 586, 662, 774};
    private static final int Q_LIMIT = 199;
    private static final int TURN_LIMIT = 6;
    private static final long TOP = 2147483647L;

    private final Input input;
    private final PrintWriter output = new PrintWriter(System.out);
    private final int n;
    private final long[] raw;
    private final boolean[] anchor;
    private final boolean usePrior, fastStop, trace;
    private final long started = System.nanoTime();
    private int queries, position, direction, turns, frontier, best = -1;
    private long travel, maximum = -1;
    private boolean priorStop;

    private Main(Input input, int n, boolean usePrior, boolean fastStop, boolean trace) {
        this.input = input;
        this.n = n;
        this.usePrior = usePrior;
        this.fastStop = fastStop;
        this.trace = trace;
        raw = new long[n];
        Arrays.fill(raw, -1);
        anchor = new boolean[n];
    }

    private double seconds() {
        return (System.nanoTime() - started) / 1e9;
    }

    private boolean tieBetter(int x, int y) {
        if (y < 0) return true;
        long a = Math.abs(2L * x - (n - 1L));
        long b = Math.abs(2L * y - (n - 1L));
        return a < b || (a == b && x < y);
    }

    private boolean better(int x, long value, int y, long old) {
        return value > old || (value == old && tieBetter(x, y));
    }

    private static final class Motion {
        int pos, dir, turns;
        long distance;
        Motion(int pos, int dir, int turns, long distance) {
            this.pos = pos; this.dir = dir; this.turns = turns; this.distance = distance;
        }
        void move(int x) {
            int next = Integer.compare(x, pos);
            if (next != 0) {
                if (dir != 0 && dir != next) ++turns;
                dir = next;
            }
            distance += Math.abs(x - pos);
            pos = x;
        }
    }

    private Motion motion() {
        return new Motion(position, direction, turns, travel);
    }

    private boolean canRead(int x, boolean terminal) {
        if (x < 0 || x >= n || queries + 1 + (terminal ? 0 : 1) > Q_LIMIT)
            return false;
        Motion m = motion();
        m.move(x);
        // Reserve parking if the old observed winner remains the winner.
        if (!terminal && best >= 0) m.move(best);
        return m.turns <= TURN_LIMIT;
    }

    private boolean read(int x, boolean terminal, boolean structural) throws IOException {
        if (!canRead(x, terminal)) return false;
        output.println(x);
        output.flush();
        long value = input.nextLong();
        if (value < 0 || value > TOP) throw new IOException("Reply outside range");
        Motion m = motion();
        m.move(x);
        position = m.pos; direction = m.dir; turns = m.turns; travel = m.distance;
        ++queries;
        frontier = Math.max(frontier, x);
        raw[x] = value;
        anchor[x] |= structural;
        if (better(x, value, best, maximum)) { best = x; maximum = value; }
        return true;
    }

    private boolean sample(int x, boolean structural) throws IOException {
        if (x < 0 || x >= n) return false;
        if (raw[x] >= 0) { anchor[x] |= structural; return true; }
        return read(x, false, structural);
    }

    private List<Integer> observed(boolean structural) {
        List<Integer> xs = new ArrayList<>();
        for (int x = 0; x < n; ++x)
            if (raw[x] >= 0 && (!structural || anchor[x])) xs.add(x);
        return xs;
    }

    private static double median(List<Double> values) {
        if (values.isEmpty()) return 0;
        List<Double> copy = new ArrayList<>(values);
        Collections.sort(copy);
        int m = copy.size() / 2;
        return copy.size() % 2 == 0 ? (copy.get(m - 1) + copy.get(m)) / 2 : copy.get(m);
    }

    private static double mad(List<Double> values) {
        double center = median(values);
        List<Double> deviations = new ArrayList<>();
        for (double value : values) deviations.add(Math.abs(value - center));
        return 1.4826 * median(deviations);
    }

    private static final class Features {
        double floor, contrast, noise;
        int leftWidth, rightWidth, falls, rises;
        boolean flat, significant, rebound;
    }

    private Features features() {
        Features f = new Features();
        List<Integer> xs = observed(true);
        f.floor = maximum;
        for (int x : xs) f.floor = Math.min(f.floor, raw[x]);
        f.contrast = Math.max(0, maximum - f.floor);
        List<Double> residuals = new ArrayList<>();
        for (int i = 1; i + 1 < xs.size(); ++i) {
            int a = xs.get(i - 1), x = xs.get(i), b = xs.get(i + 1);
            double interpolation = raw[a] + (double) (raw[b] - raw[a]) * (x - a) / (b - a);
            // Normalize mixed-gap curvature to an8-by8-cell scale before MAD.
            residuals.add((raw[x] - interpolation) * 64.0 / ((x - a) * (b - x)));
        }
        f.noise = mad(residuals) / 1.2247448714;
        f.flat = f.contrast == 0;
        f.significant = f.contrast > Math.max(4, 25 * f.noise);
        for (int i = Math.max(1, xs.size() - 5); i < xs.size(); ++i) {
            double delta = raw[xs.get(i)] - raw[xs.get(i - 1)];
            if (delta > Math.max(1, 1.5 * f.noise)) ++f.rises;
            if (delta < -Math.max(1, 1.5 * f.noise)) ++f.falls;
        }
        double valley = maximum;
        for (int x : observed(false)) {
            if (x < best && raw[x] <= maximum - 0.5 * f.contrast)
                f.leftWidth = best - x;
            if (x > best) {
                valley = Math.min(valley, raw[x]);
                if (f.rightWidth == 0 && raw[x] <= maximum - 0.5 * f.contrast)
                    f.rightWidth = x - best;
            }
        }
        f.rebound = frontier > best + 24 && raw[frontier] - valley >
                Math.max(3 * f.noise, 0.025 * f.contrast);
        return f;
    }

    private boolean known(int x) {
        if (!usePrior) return false;
        for (int p : PRIOR) if (x == p) return true;
        return false;
    }

    private boolean summit(int p) {
        return p > 0 && p + 1 < n && raw[p - 1] >= 0 && raw[p] >= 0 && raw[p + 1] >= 0 &&
                raw[p] > raw[p - 1] && raw[p] > raw[p + 1];
    }

    private int risingApproach(int p) {
        List<Integer> xs = observed(true);
        List<Integer> left = new ArrayList<>();
        for (int x : xs) if (x < p) left.add(x);
        int rising = 0;
        for (int i = Math.max(1, left.size() - 4); i < left.size(); ++i)
            if (raw[left.get(i)] > raw[left.get(i - 1)]) ++rising;
        return rising;
    }

    private boolean nearbyPriorPending() {
        if (!usePrior) return false;
        for (int p : PRIOR)
            if (p < n && p > frontier && p > best && p - best <= 16) return true;
        return false;
    }

    private boolean shouldStop(Features f) {
        if (maximum == TOP && best == (n - 1) / 2) return true;
        if (f.flat) {
            int limit = Math.min(n - 1, (n - 1) / 2 + 144);
            // Position-table mode deliberately checks late known spikes even
            // after a perfectly flat prefix. This can zero truly flat arrays
            // through irreversible redundancy; --no-prior is the control.
            if (usePrior) for (int p : PRIOR)
                if (p < n) limit = Math.max(limit, Math.min(n - 1, p + 1));
            return frontier >= limit;
        }
        if (fastStop && known(best) && summit(best) && frontier >= best + 1 &&
                frontier - best <= 16 && !nearbyPriorPending() &&
                f.contrast > Math.max(4, 8 * f.noise) && risingApproach(best) >= 2 && !f.rebound) {
            // This is an empirical local-shape rule, not a global certificate.
            priorStop = true;
            return true;
        }
        if (!f.significant) return false;
        if (!fastStop && usePrior && best >= 550) {
            // A controlled alternative: compare all remaining known points
            // that keep the current observed winner inside a199-cell lease.
            for (int p : PRIOR)
                if (p < n && p > frontier && p + 1 - best <= 199) return false;
        }
        if (best <= 8 && frontier - best >= 48 && f.falls >= 3 && f.rises == 0)
            return true;
        boolean resolved = f.leftWidth > 0 && f.rightWidth > 0 &&
                f.falls >= 3 && f.rises == 0 && !f.rebound;
        int scout = n <= 500 ? 32 : (n <= 650 ? 96 : 128);
        if (best >= (n - 1) / 2) scout = 16;
        if (resolved) scout = Math.min(Math.max(16, scout / 2),
                Math.max(16, (int) Math.ceil(1.5 * f.rightWidth)));
        if (fastStop && known(best) && resolved) scout = Math.min(scout, 24);
        if (!f.rebound && f.rises == 0 && frontier - best >= scout &&
                maximum - raw[frontier] > Math.max(3 * f.noise, 0.08 * f.contrast))
            return true;
        // Default redundancy control is heuristic because the true target is hidden.
        return !f.rebound && f.rises == 0 && frontier - best >= 184;
    }

    private void explore() throws IOException {
        for (int x : new int[]{0, 4, 12, 24})
            if (x < n && !sample(x, true)) return;
        int grid = 32;
        while (queries < 144 && frontier < n - 1 && seconds() < 7.0) {
            Features f = features();
            if (shouldStop(f)) return;
            int step = frontier >= 550 ? 12 : 8;
            while (grid <= frontier) grid += step;
            int target = Math.min(n - 1, grid);
            if (f.flat && frontier < (n - 1) / 2)
                target = Math.min(target, (n - 1) / 2);

            int prior = -1;
            if (usePrior) for (int p : PRIOR)
                if (p < n && p > frontier && p <= target) { prior = p; break; }
            if (prior >= 0) {
                // Insert in increasing order; never jump past an unprocessed known point.
                int end = Math.min(n - 1, prior + 1);
                for (int x = Math.max(frontier + 1, prior - 1); x <= end; ++x) {
                    if (!sample(x, false)) return;
                    if (queries >= 144) return;
                }
            } else {
                if (!sample(target, true)) return;
                if (target == grid) grid += step;
            }
        }
    }

    private double fittedCenter(List<Integer> xs) {
        double[][] matrix = new double[3][4];
        int count = 0;
        for (int x : xs) {
            if (Math.abs(x - best) > 32) continue;
            ++count;
            double t = (x - best) / 16.0, weight = 1 / (1 + Math.abs(t));
            double[] basis = {1, t, t * t};
            for (int i = 0; i < 3; ++i) {
                for (int j = 0; j < 3; ++j)
                    matrix[i][j] += weight * basis[i] * basis[j];
                matrix[i][3] += weight * basis[i] * (raw[x] - maximum);
            }
        }
        if (count < 5) return best;
        for (int i = 0; i < 3; ++i) {
            int pivot = i;
            for (int j = i + 1; j < 3; ++j)
                if (Math.abs(matrix[j][i]) > Math.abs(matrix[pivot][i])) pivot = j;
            double[] swap = matrix[i]; matrix[i] = matrix[pivot]; matrix[pivot] = swap;
            if (Math.abs(matrix[i][i]) < 1e-10) return best;
            double scale = matrix[i][i];
            for (int k = i; k < 4; ++k) matrix[i][k] /= scale;
            for (int j = 0; j < 3; ++j) if (j != i) {
                double factor = matrix[j][i];
                for (int k = i; k < 4; ++k) matrix[j][k] -= factor * matrix[i][k];
            }
        }
        if (matrix[2][3] >= -1e-10) return best;
        double vertex = best - 8 * matrix[1][3] / matrix[2][3];
        return Double.isFinite(vertex) && Math.abs(vertex - best) <= 16 &&
                vertex >= 0 && vertex <= frontier ? vertex : best;
    }

    private static final class Scenario {
        final long[] values;
        int target;
        Scenario(long[] values) { this.values = values; }
    }

    private long bounded(double value) {
        return Math.round(Math.max(0, Math.min(TOP, value)));
    }

    private List<Scenario> scenarios(Features f) {
        List<Integer> xs = observed(false);
        double center = fittedCenter(xs);
        double left = Math.max(8, f.leftWidth > 0 ? f.leftWidth : 24);
        double right = Math.max(8, f.rightWidth > 0 ? f.rightWidth : 24);
        double height = Math.max(1, f.contrast);
        List<Scenario> cases = new ArrayList<>();
        for (int family = 0; family < 6; ++family) {
            long[] curve = new long[n];
            Arrays.fill(curve, bounded(f.floor));
            for (int i = 1; i < xs.size(); ++i) {
                int a = xs.get(i - 1), b = xs.get(i);
                for (int x = a; x <= b; ++x) {
                    double t = (double) (x - a) / (b - a);
                    double prediction = raw[a] + t * (raw[b] - raw[a]);
                    double bump = Math.max(2 * f.noise, 0.015 * height);
                    if (family == 1) prediction += 4 * t * (1 - t) * bump;
                    if (family == 2) prediction += 4 * t * (1 - t) * 3 * bump;
                    if (family >= 3 && Math.abs(x - center) <= 2 * Math.max(left, right)) {
                        double width = x < center ? left : right;
                        double z = (x - center) / width;
                        double model;
                        if (family == 3) model = f.floor + height * 1.02 * (1 - 0.5 * z * z);
                        else if (family == 4) model = f.floor + height * 1.02 * Math.exp(-Math.log(2) * z * z);
                        else model = f.floor + height * 1.03 * Math.max(0, 1 - Math.abs(z) / 2);
                        prediction = Math.max(prediction, model);
                    }
                    curve[x] = bounded(prediction);
                }
            }
            addScenario(cases, curve, xs);
        }
        // Include unobserved narrow peaks in high cells; these are hypotheses,
        // not probability estimates or upper bounds on the real curve.
        List<Integer> cells = new ArrayList<>();
        for (int i = 1; i < xs.size(); ++i) {
            int a = xs.get(i - 1), b = xs.get(i);
            if (b - a > 1 && Math.max(raw[a], raw[b]) >= maximum - Math.max(4 * f.noise, 0.12 * height))
                cells.add(i);
        }
        cells.sort((i, j) -> Long.compare(Math.max(raw[xs.get(j - 1)], raw[xs.get(j)]),
                Math.max(raw[xs.get(i - 1)], raw[xs.get(i)])));
        for (int k = 0; k < Math.min(6, cells.size()); ++k) {
            int i = cells.get(k), a = xs.get(i - 1), b = xs.get(i);
            long[] curve = cases.get(0).values.clone();
            int x = (a + b) / 2;
            curve[x] = bounded(maximum + Math.max(1, 0.01 * height));
            addScenario(cases, curve, xs);
        }
        return cases;
    }

    private void addScenario(List<Scenario> cases, long[] curve, List<Integer> xs) {
        for (int x : xs) curve[x] = raw[x];
        Scenario s = new Scenario(curve);
        for (int x = 1; x <= frontier; ++x)
            if (better(x, curve[x], s.target, curve[s.target])) s.target = x;
        cases.add(s);
    }

    private List<Integer> window(int center, int radius) {
        List<Integer> plan = new ArrayList<>();
        for (int x = Math.max(0, center - radius); x <= Math.min(frontier, center + radius); ++x)
            if (raw[x] < 0) plan.add(x);
        return plan;
    }

    private boolean routeSafe(List<Integer> plan) {
        if (queries + plan.size() + 1 > Q_LIMIT) return false;
        Motion m = motion();
        for (int x : plan) {
            if (x < 0 || x > frontier || raw[x] >= 0) return false;
            m.move(x);
        }
        // At most one additional reversal to park at any observed winner.
        return m.turns + 1 <= TURN_LIMIT;
    }

    private double utility(List<Integer> plan, List<Scenario> cases) {
        if (!routeSafe(plan)) return -1e100;
        double sum = 0;
        for (Scenario s : cases) {
            Motion m = motion();
            int winner = best;
            long value = maximum;
            for (int x : plan) {
                m.move(x);
                if (better(x, s.values[x], winner, value)) { winner = x; value = s.values[x]; }
            }
            int parking = m.pos == winner ? 0 : 1;
            if (parking != 0) m.move(winner);
            int d = Math.abs(winner - s.target), redundant = Math.max(0, frontier - s.target);
            if (queries + plan.size() + parking <= Q_LIMIT && m.turns <= TURN_LIMIT &&
                    d <= 3 && redundant <= 199)
                sum += Math.max(0, 3000 - 200 * d - queries - plan.size() - parking - m.distance - m.turns - redundant);
        }
        return sum / cases.size();
    }

    private void refine() throws IOException {
        if (priorStop) return;
        for (int round = 0; round < 2 && queries < Q_LIMIT - 1 && seconds() < 7.5; ++round) {
            Features f = features();
            List<Scenario> cases = scenarios(f);
            TreeSet<Integer> centers = new TreeSet<>();
            centers.add(best);
            centers.add((int) Math.round(fittedCenter(observed(false))));
            for (Scenario s : cases) centers.add(s.target);
            List<Integer> selected = new ArrayList<>();
            double highest = utility(selected, cases);
            List<List<Integer>> proposals = new ArrayList<>();
            for (int center : centers) for (int radius : new int[]{2, 4, 6, 10})
                proposals.add(window(center, radius));
            for (int center : centers) {
                TreeSet<Integer> union = new TreeSet<>(window(best, 4));
                union.addAll(window(center, 4));
                proposals.add(new ArrayList<>(union));
            }
            int available = Q_LIMIT - 1 - queries;
            int budget = round == 0 ? Math.max(1, available - Math.min(20, available / 3)) : available;
            for (List<Integer> original : proposals) {
                if (original.isEmpty() || original.size() > budget) continue;
                for (int orientation = 0; orientation < 2; ++orientation) {
                    List<Integer> plan = new ArrayList<>(original);
                    if (orientation == 0) Collections.reverse(plan);
                    double score = utility(plan, cases);
                    if (score > highest + 0.01) { highest = score; selected = plan; }
                }
            }
            if (selected.isEmpty()) return;
            for (int x : selected) if (!sample(x, false)) return;
        }
    }

    private void finish() throws IOException {
        if (best >= 0 && position != best) read(best, true, false);
        output.println("DONE");
        output.flush();
        if (trace) System.err.println("TRACE queries=" + queries + " travel=" + travel +
                " turns=" + turns + " frontier=" + frontier + " best=" + best +
                " position=" + position + " prior_stop=" + priorStop);
    }

    private void run() throws IOException {
        if (n <= 198) {
            for (int x = 0; x < n; ++x) if (!sample(x, true)) break;
        } else {
            explore();
            refine();
        }
        finish();
    }

    public static void main(String[] args) throws IOException {
        boolean prior = true, stop = true, trace = false;
        for (String arg : args) {
            if (arg.equals("--no-prior")) prior = false;
            if (arg.equals("--no-fast-stop")) stop = false;
            if (arg.equals("--trace")) trace = true;
        }
        Input input = new Input();
        try {
            long n = input.nextLong();
            if (n <= 0 || n > 1000) return;
            new Main(input, (int) n, prior, stop, trace).run();
        } catch (EOFException ignored) {
            // The transport is no longer usable after EOF.
        }
    }

    private static final class Input {
        private final BufferedInputStream stream = new BufferedInputStream(System.in);
        long nextLong() throws IOException {
            int c;
            do { c = stream.read(); if (c < 0) throw new EOFException(); } while (c <= ' ');
            boolean negative = c == '-';
            if (negative) c = stream.read();
            long number = 0;
            boolean digit = false;
            while (c > ' ') {
                if (c < '0' || c > '9') throw new IOException("Invalid integer");
                digit = true;
                number = number * 10 + c - '0';
                c = stream.read();
            }
            if (!digit) throw new IOException("Missing integer");
            return negative ? -number : number;
        }
    }
}
