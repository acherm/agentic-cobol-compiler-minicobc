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

void minicobc_program_FEN(void **minicobc_args);
void minicobc_program_PERFT(void **minicobc_args);

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
    static long long nodes = 0;

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
    void *fen_args[3];
    void *perft_args[3];

    fen_args[0] = &game_state;
    fen_args[1] = &startpos;
    fen_args[2] = &status;
    minicobc_program_FEN(fen_args);

    perft_args[0] = &game_state;
    perft_args[1] = &depth;
    perft_args[2] = &nodes;
    minicobc_program_PERFT(perft_args);

    printf("STATUS %d\n", status);
    printf("NODES %lld\n", nodes);
    return 0;
}
