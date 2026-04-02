#include <stdio.h>

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

void minicobc_program_FEN(void **minicobc_args);
void minicobc_program_SEARCH(void **minicobc_args);
void minicobc_program_MOVE2UCI(void **minicobc_args);

int main(void) {
    static short gs_piece[128] = {0};
    static short gs_side_to_move = 0;
    static short gs_castling = 0;
    static short gs_ep_sq = 0;
    static short gs_halfmove = 0;
    static short gs_fullmove = 0;
    static short gs_ksq[2] = {0};
    static short gs_ply = 0;
    static long long gs_key = 0;
    static short u_captured[256] = {0};
    static short u_moved[256] = {0};
    static short u_castling[256] = {0};
    static short u_ep_sq[256] = {0};
    static short u_halfmove[256] = {0};
    static short u_fullmove[256] = {0};
    static short u_king_sq[256] = {0};
    static long long u_key[256] = {0};
    static char startpos[257] =
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    static short status = 0;
    static short depth = 2;
    static long long time_limit_cs = 0;
    static short move_from = 0;
    static short move_to = 0;
    static short move_promo = 0;
    static short move_flags = 0;
    static int move_score = 0;
    static int out_score = 0;
    static long long out_nodes = 0;
    static char uci_buf[9] = {0};

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
    minicobc_group_MOVE_REC bestmove = {
        &move_from,
        &move_to,
        &move_promo,
        &move_flags,
        &move_score
    };
    void *fen_args[3];
    void *search_args[6];
    void *uci_args[2];

    fen_args[0] = &game_state;
    fen_args[1] = &startpos;
    fen_args[2] = &status;
    minicobc_program_FEN(fen_args);

    search_args[0] = &game_state;
    search_args[1] = &depth;
    search_args[2] = &time_limit_cs;
    search_args[3] = &bestmove;
    search_args[4] = &out_score;
    search_args[5] = &out_nodes;
    minicobc_program_SEARCH(search_args);

    uci_args[0] = &bestmove;
    uci_args[1] = &uci_buf;
    minicobc_program_MOVE2UCI(uci_args);

    printf("STATUS %d\n", status);
    printf("BESTMOVE %s\n", uci_buf);
    printf("SCORE %d\n", out_score);
    printf("NODES %lld\n", out_nodes);
    return 0;
}
