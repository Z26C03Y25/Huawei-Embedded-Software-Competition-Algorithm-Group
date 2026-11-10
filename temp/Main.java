import java.io.BufferedInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.PrintWriter;

public class Main {
    // Configure the inclusive scan interval here.
    private static final int LEFT = 150;
    private static final int RIGHT = 125;

    public static void main(String[] args) throws IOException {
        BufferedInputStream input = new BufferedInputStream(System.in);
        PrintWriter output = new PrintWriter(System.out);
        try {
            long length = nextLong(input);
            if (length <= 0 || length > 1000) return;
            int n = (int) length;

            int a = RIGHT;
            int b = LEFT;

            if (a < b) {
                int temporary = a;
                a = b;
                b = temporary;
            }
            b = Math.max(b, 0);
            if (n <= a) {
                output.println(0);
                output.flush();
                nextLong(input);
                output.println("DONE");
                output.flush();
                return;
            }

            int bestPos = b;
            long bestVal = -1;
            for (int i = b; i <= a; ++i) {
                output.println(i);
                output.flush();
                long value = nextLong(input);
                long distance = Math.abs(2L * i - (n - 1L));
                long bestDistance = Math.abs(2L * bestPos - (n - 1L));
                if (value > bestVal ||
                    (value == bestVal &&
                     (distance < bestDistance ||
                      (distance == bestDistance && i < bestPos)))) {
                    bestVal = value;
                    bestPos = i;
                }
            }

            // Always issue the final parking query.
            output.println(bestPos);

            // output.println(213);

            output.flush();
            nextLong(input);
            output.println("DONE");
            output.flush();
        } catch (EOFException ignored) {
            // Stop when the judge closes input.
        }





    }

    private static long nextLong(BufferedInputStream input) throws IOException {
        int c;
        do {
            c = input.read();
            if (c < 0) throw new EOFException();
        } while (c <= ' ');
        boolean negative = c == '-';
        if (negative) c = input.read();
        long number = 0;
        boolean digitSeen = false;
        while (c > ' ') {
            if (c < '0' || c > '9') throw new IOException("Invalid integer");
            digitSeen = true;
            number = number * 10 + c - '0';
            c = input.read();
        }
        if (!digitSeen) throw new IOException("Missing integer");
        return negative ? -number : number;
    }
}
