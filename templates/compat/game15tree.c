#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    VAL_P2_WINS = 1,
    VAL_DRAW = 2,
    VAL_P1_WINS = 3,
};

struct move_list {
    int count;
    int nums[9];
};

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

static int owner[10];
static unsigned char memo[19683];
static int is_last[10];
static int max_depth = 9;

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

static int compute_pos_key(void) {
    int key = 0;
    int pow3 = 1;

    for (int i = 1; i <= 9; ++i) {
        key += owner[i] * pow3;
        pow3 *= 3;
    }

    return key;
}

static int minimax(int depth) {
    const int key = compute_pos_key();
    if (memo[key] != 0) {
        return memo[key];
    }

    const int player = (depth % 2 == 1) ? 1 : 2;
    int best = (player == 1) ? VAL_P2_WINS : VAL_P1_WINS;

    for (int num = 1; num <= 9; ++num) {
        int child_val;

        if (owner[num] != 0) {
            continue;
        }

        owner[num] = player;
        if (check_win(player)) {
            child_val = (player == 1) ? VAL_P1_WINS : VAL_P2_WINS;
        } else if (depth == 9) {
            child_val = VAL_DRAW;
        } else {
            child_val = minimax(depth + 1);
        }
        owner[num] = 0;

        if (player == 1) {
            if (child_val > best) {
                best = child_val;
            }
        } else {
            if (child_val < best) {
                best = child_val;
            }
        }
    }

    memo[key] = (unsigned char)best;
    return best;
}

static void collect_optimal(int depth, struct move_list *optimal,
    struct move_list *bad) {
    const int player = (depth % 2 == 1) ? 1 : 2;
    const int parent_val = minimax(depth);

    optimal->count = 0;
    bad->count = 0;

    for (int num = 1; num <= 9; ++num) {
        int child_val;

        if (owner[num] != 0) {
            continue;
        }

        owner[num] = player;
        if (check_win(player)) {
            child_val = (player == 1) ? VAL_P1_WINS : VAL_P2_WINS;
        } else if (depth == 9) {
            child_val = VAL_DRAW;
        } else {
            child_val = minimax(depth + 1);
        }
        owner[num] = 0;

        if (child_val == parent_val) {
            optimal->nums[optimal->count++] = num;
        } else {
            bad->nums[bad->count++] = num;
        }
    }
}

static const char *value_label(int value) {
    switch (value) {
        case VAL_P1_WINS:
            return "P1 wins";
        case VAL_DRAW:
            return "Draw";
        default:
            return "P2 wins";
    }
}

static void print_node(int depth, int player, int num, int node_val,
    bool is_terminal, bool depth_limited) {
    char line[256];
    int pos = 0;

    line[0] = '\0';
    for (int lp = 1; lp < depth; ++lp) {
        pos += snprintf(line + pos, sizeof(line) - (size_t)pos, "%s",
            is_last[lp] ? "    " : "|   ");
    }
    pos += snprintf(line + pos, sizeof(line) - (size_t)pos, "%s",
        is_last[depth] ? "+-- " : "|-- ");
    pos += snprintf(line + pos, sizeof(line) - (size_t)pos, "P%d:%d [%s]",
        player, num, value_label(node_val));
    if (is_terminal) {
        pos += snprintf(line + pos, sizeof(line) - (size_t)pos, " *");
    }
    if (depth_limited) {
        pos += snprintf(line + pos, sizeof(line) - (size_t)pos, " ...");
    }

    puts(line);
}

static void print_avoid(int depth, const struct move_list *bad) {
    char line[256];
    int pos = 0;

    line[0] = '\0';
    for (int lp = 1; lp < depth; ++lp) {
        pos += snprintf(line + pos, sizeof(line) - (size_t)pos, "%s",
            is_last[lp] ? "    " : "|   ");
    }
    pos += snprintf(line + pos, sizeof(line) - (size_t)pos, "avoid:");
    for (int i = 0; i < bad->count; ++i) {
        pos += snprintf(line + pos, sizeof(line) - (size_t)pos,
            (i == 0) ? " %d" : ", %d", bad->nums[i]);
    }

    puts(line);
}

static void print_tree(int depth) {
    struct move_list optimal;
    struct move_list bad;

    collect_optimal(depth, &optimal, &bad);
    if (bad.count > 0) {
        print_avoid(depth, &bad);
    }

    for (int i = 0; i < optimal.count; ++i) {
        const int num = optimal.nums[i];
        const int player = (depth % 2 == 1) ? 1 : 2;
        int node_val;
        bool is_terminal = false;
        const bool depth_limited = (depth >= max_depth);

        is_last[depth] = (i == optimal.count - 1);
        owner[num] = player;

        if (check_win(player)) {
            node_val = (player == 1) ? VAL_P1_WINS : VAL_P2_WINS;
            is_terminal = true;
        } else if (depth == 9) {
            node_val = VAL_DRAW;
            is_terminal = true;
        } else {
            node_val = minimax(depth + 1);
        }

        print_node(depth, player, num, node_val, is_terminal, depth_limited);

        if (!is_terminal) {
            if (depth_limited) {
                struct move_list next_optimal;
                struct move_list next_bad;

                collect_optimal(depth + 1, &next_optimal, &next_bad);
                if (next_bad.count > 0) {
                    print_avoid(depth + 1, &next_bad);
                }
            } else {
                print_tree(depth + 1);
            }
        }

        owner[num] = 0;
    }
}

int main(int argc, char **argv) {
    if (argc >= 3 && strcmp(argv[1], "--depth") == 0) {
        max_depth = atoi(argv[2]);
        if (max_depth < 1) {
            max_depth = 1;
        }
        if (max_depth > 9) {
            max_depth = 9;
        }
    }

    memset(owner, 0, sizeof(owner));
    memset(memo, 0, sizeof(memo));
    memset(is_last, 0, sizeof(is_last));

    printf("Game of 15 - Optimal Play Tree [%s]\n", value_label(minimax(1)));
    print_tree(1);

    return 0;
}
