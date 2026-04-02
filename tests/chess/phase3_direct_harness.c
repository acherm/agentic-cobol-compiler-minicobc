#include <stdio.h>
#include <string.h>

typedef struct minicobc_group_GAME_STATE {
    short *m_GS_PIECE;
    short *m_GS_SIDE_TO_MOVE;
    short *m_GS_CASTLING;
    short *m_GS_EP_SQ;
    short *m_GS_HALFMOVE;
    short *m_GS_FULLMOVE;
    short *m_GS_KSQ;
    short *m_GS_PLY;
    long long *m_GS_KEY;
    short *m_U_CAPTURED;
    short *m_U_MOVED;
    short *m_U_CASTLING;
    short *m_U_EP_SQ;
    short *m_U_HALFMOVE;
    short *m_U_FULLMOVE;
    short *m_U_KING_SQ;
    long long *m_U_KEY;
} minicobc_group_GAME_STATE;

typedef struct minicobc_group_MOVE_REC {
    short *m_M_FROM;
    short *m_M_TO;
    short *m_M_PROMO;
    short *m_M_FLAGS;
    int *m_M_SCORE;
} minicobc_group_MOVE_REC;

typedef struct minicobc_group_SEARCH_STATE {
    long long *m_SS_NODES;
    short *m_SS_STOP;
    long long *m_SS_START_CS;
    long long *m_SS_TIME_LIMIT_CS;
    int *m_SS_TIME_CHECK;
    short *m_SS_TT_INIT;
    short *m_K1_FROM;
    short *m_K1_TO;
    short *m_K1_PROMO;
    short *m_K1_FLAGS;
    short *m_K2_FROM;
    short *m_K2_TO;
    short *m_K2_PROMO;
    short *m_K2_FLAGS;
    int *m_SS_HIST;
    long long *m_TTE_KEY;
    short *m_TTE_DEPTH;
    short *m_TTE_FLAG;
    int *m_TTE_SCORE;
    short *m_TTE_FROM;
    short *m_TTE_TO;
    short *m_TTE_PROMO;
    short *m_TTE_FLAGS;
} minicobc_group_SEARCH_STATE;

void minicobc_program_BOARD(void **minicobc_args);
void minicobc_program_FEN(void **minicobc_args);
void minicobc_program_MAKEMOVE(void **minicobc_args);
void minicobc_program_ALPHABETA(void **minicobc_args);
void minicobc_program_QUIESCE(void **minicobc_args);
void minicobc_program_MOVEGEN(void **minicobc_args);
void minicobc_program_MOVE2UCI(void **minicobc_args);
void minicobc_program_UNMAKEMOVE(void **minicobc_args);

static short gs_piece[128];
static short gs_side_to_move;
static short gs_castling;
static short gs_ep_sq;
static short gs_halfmove;
static short gs_fullmove;
static short gs_ksq[2];
static short gs_ply;
static long long gs_key;
static short u_captured[256];
static short u_moved[256];
static short u_castling[256];
static short u_ep_sq[256];
static short u_halfmove[256];
static short u_fullmove[256];
static short u_king_sq[256];
static long long u_key[256];

static long long ss_nodes;
static short ss_stop;
static long long ss_start_cs;
static long long ss_time_limit_cs;
static int ss_time_check;
static short ss_tt_init;
static short k1_from[256];
static short k1_to[256];
static short k1_promo[256];
static short k1_flags[256];
static short k2_from[256];
static short k2_to[256];
static short k2_promo[256];
static short k2_flags[256];
static int ss_hist[16384];
static long long tte_key[1048576];
static short tte_depth[1048576];
static short tte_flag[1048576];
static int tte_score[1048576];
static short tte_from[1048576];
static short tte_to[1048576];
static short tte_promo[1048576];
static short tte_flags[1048576];

static void init_search_state(void) {
    int i;
    ss_nodes = 0;
    ss_stop = 0;
    ss_start_cs = 0;
    ss_time_limit_cs = 0;
    ss_time_check = 2048;
    ss_tt_init = 1;
    memset(k1_from, 0, sizeof(k1_from));
    memset(k1_to, 0, sizeof(k1_to));
    memset(k1_promo, 0, sizeof(k1_promo));
    memset(k1_flags, 0, sizeof(k1_flags));
    memset(k2_from, 0, sizeof(k2_from));
    memset(k2_to, 0, sizeof(k2_to));
    memset(k2_promo, 0, sizeof(k2_promo));
    memset(k2_flags, 0, sizeof(k2_flags));
    memset(ss_hist, 0, sizeof(ss_hist));
    for (i = 0; i < 1048576; ++i) {
        tte_key[i] = -1;
    }
    memset(tte_depth, 0, sizeof(tte_depth));
    memset(tte_flag, 0, sizeof(tte_flag));
    memset(tte_score, 0, sizeof(tte_score));
    memset(tte_from, 0, sizeof(tte_from));
    memset(tte_to, 0, sizeof(tte_to));
    memset(tte_promo, 0, sizeof(tte_promo));
    memset(tte_flags, 0, sizeof(tte_flags));
}

static void setup_position(const char *fen_text, int apply_d5e6) {
    char fen_buf[257];
    short status = 0;
    short ok = 0;
    short move_from = 67;
    short move_to = 84;
    short move_promo = 0;
    short move_flags = 1;
    int move_score = 0;
    void *board_args[1];
    void *fen_args[3];
    void *makemove_args[3];
    minicobc_group_GAME_STATE game_state = {
        gs_piece,
        &gs_side_to_move,
        &gs_castling,
        &gs_ep_sq,
        &gs_halfmove,
        &gs_fullmove,
        gs_ksq,
        &gs_ply,
        &gs_key,
        u_captured,
        u_moved,
        u_castling,
        u_ep_sq,
        u_halfmove,
        u_fullmove,
        u_king_sq,
        u_key
    };
    minicobc_group_MOVE_REC move_rec = {
        &move_from,
        &move_to,
        &move_promo,
        &move_flags,
        &move_score
    };

    memset(gs_piece, 0, sizeof(gs_piece));
    memset(gs_ksq, 0, sizeof(gs_ksq));
    memset(u_captured, 0, sizeof(u_captured));
    memset(u_moved, 0, sizeof(u_moved));
    memset(u_castling, 0, sizeof(u_castling));
    memset(u_ep_sq, 0, sizeof(u_ep_sq));
    memset(u_halfmove, 0, sizeof(u_halfmove));
    memset(u_fullmove, 0, sizeof(u_fullmove));
    memset(u_king_sq, 0, sizeof(u_king_sq));
    memset(u_key, 0, sizeof(u_key));
    gs_side_to_move = 0;
    gs_castling = 0;
    gs_ep_sq = 0;
    gs_halfmove = 0;
    gs_fullmove = 0;
    gs_ply = 0;
    gs_key = 0;

    snprintf(fen_buf, sizeof(fen_buf), "%s", fen_text);

    board_args[0] = &game_state;
    minicobc_program_BOARD(board_args);

    fen_args[0] = &game_state;
    fen_args[1] = &fen_buf;
    fen_args[2] = &status;
    minicobc_program_FEN(fen_args);

    if (apply_d5e6) {
        makemove_args[0] = &game_state;
        makemove_args[1] = &move_rec;
        makemove_args[2] = &ok;
        minicobc_program_MAKEMOVE(makemove_args);
    }
}

static void run_case(const char *label, int apply_d5e6) {
    static const char *fen_text =
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPB1PPP/R3K2R w KQkq - 0 1";
    short depth = 0;
    int alpha = -30000;
    int beta = 30000;
    short nmp = 1;
    int out = 0;
    void *quiesce_args[5];
    void *alphabeta_args[7];
    minicobc_group_GAME_STATE game_state = {
        gs_piece,
        &gs_side_to_move,
        &gs_castling,
        &gs_ep_sq,
        &gs_halfmove,
        &gs_fullmove,
        gs_ksq,
        &gs_ply,
        &gs_key,
        u_captured,
        u_moved,
        u_castling,
        u_ep_sq,
        u_halfmove,
        u_fullmove,
        u_king_sq,
        u_key
    };
    minicobc_group_SEARCH_STATE ss = {
        &ss_nodes,
        &ss_stop,
        &ss_start_cs,
        &ss_time_limit_cs,
        &ss_time_check,
        &ss_tt_init,
        k1_from,
        k1_to,
        k1_promo,
        k1_flags,
        k2_from,
        k2_to,
        k2_promo,
        k2_flags,
        ss_hist,
        tte_key,
        tte_depth,
        tte_flag,
        tte_score,
        tte_from,
        tte_to,
        tte_promo,
        tte_flags
    };

    printf("CASE %s\n", label);

    setup_position(fen_text, apply_d5e6);
    init_search_state();
    alpha = -30000;
    beta = 30000;
    out = 0;
    quiesce_args[0] = &game_state;
    quiesce_args[1] = &alpha;
    quiesce_args[2] = &beta;
    quiesce_args[3] = &ss;
    quiesce_args[4] = &out;
    minicobc_program_QUIESCE(quiesce_args);
    printf("QUIESCE-OUT %d\n", out);
    printf("QUIESCE-NODES %lld\n", ss_nodes);

    setup_position(fen_text, apply_d5e6);
    init_search_state();
    alpha = -30000;
    beta = 30000;
    out = 0;
    alphabeta_args[0] = &game_state;
    alphabeta_args[1] = &depth;
    alphabeta_args[2] = &alpha;
    alphabeta_args[3] = &beta;
    alphabeta_args[4] = &ss;
    alphabeta_args[5] = &nmp;
    alphabeta_args[6] = &out;
    minicobc_program_ALPHABETA(alphabeta_args);
    printf("ALPHABETA-OUT %d\n", out);
    printf("ALPHABETA-NODES %lld\n", ss_nodes);
}

static void trace_after_d5e6_children(void) {
    short ml_count = 0;
    short ml_from[256];
    short ml_to[256];
    short ml_promo[256];
    short ml_flags[256];
    int ml_score[256];
    short cap_only = 1;
    short ok = 0;
    short move_from = 0;
    short move_to = 0;
    short move_promo = 0;
    short move_flags = 0;
    int move_score = 0;
    int alpha = -30000;
    int beta = 30000;
    int out = 0;
    char uci_buf[9];
    int i;
    void *movegen_args[3];
    void *uci_args[2];
    void *makemove_args[3];
    void *unmake_args[2];
    void *quiesce_args[5];
    minicobc_group_GAME_STATE game_state = {
        gs_piece,
        &gs_side_to_move,
        &gs_castling,
        &gs_ep_sq,
        &gs_halfmove,
        &gs_fullmove,
        gs_ksq,
        &gs_ply,
        &gs_key,
        u_captured,
        u_moved,
        u_castling,
        u_ep_sq,
        u_halfmove,
        u_fullmove,
        u_king_sq,
        u_key
    };
    minicobc_group_MOVE_REC move_rec = {
        &move_from,
        &move_to,
        &move_promo,
        &move_flags,
        &move_score
    };
    minicobc_group_SEARCH_STATE ss = {
        &ss_nodes,
        &ss_stop,
        &ss_start_cs,
        &ss_time_limit_cs,
        &ss_time_check,
        &ss_tt_init,
        k1_from,
        k1_to,
        k1_promo,
        k1_flags,
        k2_from,
        k2_to,
        k2_promo,
        k2_flags,
        ss_hist,
        tte_key,
        tte_depth,
        tte_flag,
        tte_score,
        tte_from,
        tte_to,
        tte_promo,
        tte_flags
    };
    struct {
        short *m_ML_COUNT;
        short *m_ML_FROM;
        short *m_ML_TO;
        short *m_ML_PROMO;
        short *m_ML_FLAGS;
        int *m_ML_SCORE;
    } move_list = {
        &ml_count,
        ml_from,
        ml_to,
        ml_promo,
        ml_flags,
        ml_score
    };

    printf("TRACE AFTER-D5E6\n");
    setup_position(
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPB1PPP/R3K2R w KQkq - 0 1",
        1
    );
    memset(ml_from, 0, sizeof(ml_from));
    memset(ml_to, 0, sizeof(ml_to));
    memset(ml_promo, 0, sizeof(ml_promo));
    memset(ml_flags, 0, sizeof(ml_flags));
    memset(ml_score, 0, sizeof(ml_score));
    movegen_args[0] = &game_state;
    movegen_args[1] = &move_list;
    movegen_args[2] = &cap_only;
    minicobc_program_MOVEGEN(movegen_args);

    for (i = 0; i < ml_count; ++i) {
        move_from = ml_from[i];
        move_to = ml_to[i];
        move_promo = ml_promo[i];
        move_flags = ml_flags[i];
        move_score = 0;
        memset(uci_buf, 0, sizeof(uci_buf));
        uci_args[0] = &move_rec;
        uci_args[1] = &uci_buf;
        minicobc_program_MOVE2UCI(uci_args);

        makemove_args[0] = &game_state;
        makemove_args[1] = &move_rec;
        makemove_args[2] = &ok;
        minicobc_program_MAKEMOVE(makemove_args);
        if (ok == 1) {
            init_search_state();
            alpha = -30000;
            beta = 30000;
            out = 0;
            quiesce_args[0] = &game_state;
            quiesce_args[1] = &alpha;
            quiesce_args[2] = &beta;
            quiesce_args[3] = &ss;
            quiesce_args[4] = &out;
            minicobc_program_QUIESCE(quiesce_args);
            printf(
                "TRACE %.*s OUT %d NODES %lld\n",
                8,
                uci_buf,
                out,
                ss_nodes
            );
            unmake_args[0] = &game_state;
            unmake_args[1] = &move_rec;
            minicobc_program_UNMAKEMOVE(unmake_args);
        }
    }
}

int main(void) {
    run_case("ROOT", 0);
    run_case("AFTER-D5E6", 1);
    trace_after_d5e6_children();
    return 0;
}
