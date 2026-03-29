#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct triple {
    int a;
    int b;
    int c;
};

static struct triple triples[84];
static int num_triples;
static int owner[16];
static int chosen[16];
static long long p1_wins;
static long long p2_wins;
static long long draws;
static int target_sum;
static int max_num;

static bool check_win(int player) {
    for (int i = 0; i < num_triples; ++i) {
        const struct triple t = triples[i];
        if (owner[t.a] == player && owner[t.b] == player && owner[t.c] == player) {
            return true;
        }
    }
    return false;
}

static void dfs(int depth) {
    const int player = (depth % 2 == 1) ? 1 : 2;

    for (int num = 1; num <= max_num; ++num) {
        if (owner[num] != 0) {
            continue;
        }

        chosen[depth] = num;
        owner[num] = player;

        if (check_win(player)) {
            if (player == 1) {
                ++p1_wins;
            } else {
                ++p2_wins;
            }
        } else if (depth == max_num) {
            ++draws;
        } else {
            dfs(depth + 1);
        }

        owner[num] = 0;
    }
}

static void print_usage(void) {
    puts("Usage: ./gameN <target> [<max-number>]");
    puts(" ");
    puts("  target      integer sum to win");
    puts("  max-number  highest pickable number (default: auto)");
    puts(" ");
    puts("Examples:");
    puts("  ./gameN 15 9   classic Game of 15");
    puts("  ./gameN 12 8   Game of 12, numbers 1-8");
    puts("  ./gameN 10     Game of 10, auto range");
}

static void generate_triples(void) {
    num_triples = 0;
    for (int a = 1; a <= max_num; ++a) {
        for (int b = a + 1; b <= max_num; ++b) {
            const int c = target_sum - a - b;
            if (c > b && c <= max_num) {
                triples[num_triples].a = a;
                triples[num_triples].b = b;
                triples[num_triples].c = c;
                ++num_triples;
            }
        }
    }
}

static void display_rules(void) {
    const int all_nums_sum = max_num * (max_num + 1) / 2;

    puts(" ");
    puts("=========================================");
    printf("  The Game of %d\n", target_sum);
    puts("=========================================");
    puts(" ");
    puts("Rules:");
    puts("  - Two players alternate picking a number");
    printf("    from {1, 2, ..., %d}. No repeats.\n", max_num);
    puts("  - A player wins when any three of their");
    printf("    chosen numbers sum to %d.\n", target_sum);
    puts("  - If all numbers are used with no winner,");
    puts("    the game is a draw.");
    puts(" ");
    printf("Number pool: 1 to %d (%d numbers)\n", max_num, max_num);
    printf("Sum of all numbers: %d\n", all_nums_sum);
    puts(" ");

    if (num_triples == 0) {
        puts("No winning triples exist!");
        puts("This game always ends in a draw.");
    } else {
        printf("Winning triples (%d):\n", num_triples);
        for (int i = 0; i < num_triples; ++i) {
            printf("  {%d, %d, %d}\n",
                triples[i].a, triples[i].b, triples[i].c);
        }
    }
    puts(" ");

    if (target_sum == 15 && max_num == 9) {
        puts("Note: This is the classic Game of 15,");
        puts("isomorphic to Tic-Tac-Toe via the 3x3 magic square.");
        puts(" ");
    }

    if (num_triples == 0) {
        puts("With no winning triples, every game is a draw.");
        puts("Not very exciting!");
        puts(" ");
    } else if (num_triples < 4) {
        puts("Few winning triples: games tend to end in draws.");
        puts(" ");
    } else if (num_triples >= 8) {
        puts("Many winning triples: games tend to end quickly.");
        puts(" ");
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        print_usage();
        return 0;
    }

    target_sum = atoi(argv[1]);
    if (argc >= 3) {
        max_num = atoi(argv[2]);
    } else {
        max_num = target_sum - 3;
        if (max_num > 15) {
            max_num = 15;
        }
        if (max_num < 3) {
            max_num = 3;
        }
    }

    if (max_num > 15) {
        puts("Error: max-number cannot exceed 15.");
        return 0;
    }
    if (max_num < 3) {
        puts("Error: need at least 3 numbers.");
        return 0;
    }
    if (target_sum < 6) {
        puts("Error: target must be >= 6 (min triple is 1+2+3).");
        return 0;
    }

    memset(owner, 0, sizeof(owner));
    memset(chosen, 0, sizeof(chosen));
    generate_triples();
    display_rules();

    if (max_num <= 9) {
        puts("Enumerating all possible games...");
        puts(" ");
        p1_wins = 0;
        p2_wins = 0;
        draws = 0;
        dfs(1);
        puts("Results:");
        puts("========");
        printf("  Player 1 wins: %10lld\n", p1_wins);
        printf("  Player 2 wins: %10lld\n", p2_wins);
        printf("  Draws:         %10lld\n", draws);
        printf("  Total games:   %10lld\n", p1_wins + p2_wins + draws);
    } else {
        puts("(Too many numbers to enumerate");
        puts(" all games. Use max <= 9.)");
    }

    puts(" ");
    return 0;
}
