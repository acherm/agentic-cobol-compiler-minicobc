#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const int WIN_TRIPLES[8][3] = {
    {1, 5, 9},
    {1, 6, 8},
    {2, 4, 9},
    {2, 5, 8},
    {2, 6, 7},
    {3, 4, 8},
    {3, 5, 7},
    {4, 5, 6},
};

static const int SYM_MAP[8][10] = {
    {0, 1, 2, 3, 4, 5, 6, 7, 8, 9},
    {0, 3, 6, 9, 2, 5, 8, 1, 4, 7},
    {0, 9, 8, 7, 6, 5, 4, 3, 2, 1},
    {0, 7, 4, 1, 8, 5, 2, 9, 6, 3},
    {0, 9, 6, 3, 8, 5, 2, 7, 4, 1},
    {0, 1, 4, 7, 2, 5, 8, 3, 6, 9},
    {0, 3, 2, 1, 6, 5, 4, 9, 8, 7},
    {0, 7, 8, 9, 4, 5, 6, 1, 2, 3},
};

static int owner[10];
static int chosen[10];
static long p1_wins;
static long p2_wins;
static long draws;
static long u_p1_wins;
static long u_p2_wins;
static long u_draws;
static int unique_mode;

static bool check_win(int player) {
    for (int i = 0; i < 8; ++i) {
        const int a = WIN_TRIPLES[i][0];
        const int b = WIN_TRIPLES[i][1];
        const int c = WIN_TRIPLES[i][2];
        if (owner[a] == player && owner[b] == player && owner[c] == player) {
            return true;
        }
    }
    return false;
}

static bool is_canonical(int game_len) {
    for (int sym = 1; sym < 8; ++sym) {
        for (int i = 1; i <= game_len; ++i) {
            const int transformed = SYM_MAP[sym][chosen[i]];
            if (transformed < chosen[i]) {
                return false;
            }
            if (transformed > chosen[i]) {
                break;
            }
        }
    }
    return true;
}

static void dfs(int depth) {
    const int player = (depth % 2 == 1) ? 1 : 2;

    for (int num = 1; num <= 9; ++num) {
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
            if (unique_mode && is_canonical(depth)) {
                if (player == 1) {
                    ++u_p1_wins;
                } else {
                    ++u_p2_wins;
                }
            }
        } else if (depth == 9) {
            ++draws;
            if (unique_mode && is_canonical(9)) {
                ++u_draws;
            }
        } else {
            dfs(depth + 1);
        }

        owner[num] = 0;
    }
}

int main(int argc, char **argv) {
    if (argc >= 2 && strcmp(argv[1], "--unique") == 0) {
        unique_mode = 1;
    }

    memset(owner, 0, sizeof(owner));
    memset(chosen, 0, sizeof(chosen));

    dfs(1);

    printf("Game of 0.15 - Possible Games\n");
    printf("=============================\n");
    printf("Player 1 wins: %8ld\n", p1_wins);
    printf("Player 2 wins: %8ld\n", p2_wins);
    printf("Draws:         %8ld\n", draws);
    printf("Total games:   %8ld\n", p1_wins + p2_wins + draws);

    if (unique_mode) {
        printf(" \n");
        printf("Unique games (modulo symmetry)\n");
        printf("==============================\n");
        printf("Player 1 wins: %8ld\n", u_p1_wins);
        printf("Player 2 wins: %8ld\n", u_p2_wins);
        printf("Draws:         %8ld\n", u_draws);
        printf("Total games:   %8ld\n", u_p1_wins + u_p2_wins + u_draws);
    }

    return 0;
}
