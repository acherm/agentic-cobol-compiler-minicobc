       IDENTIFICATION DIVISION.
       PROGRAM-ID. PERFTPHASE2.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY "copybooks/types.cpy".

       01 STARTPOS               PIC X(80)
           VALUE "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1".
       01 WS-STATUS              PIC S9(4) COMP-5 VALUE 0.
       01 WS-DEPTH               PIC S9(4) COMP-5 VALUE 2.
       01 WS-NODES               PIC S9(18) COMP-5 VALUE 0.
       01 OUT-N                  PIC -Z(17)9.

       PROCEDURE DIVISION.
           CALL "FEN" USING GAME-STATE STARTPOS WS-STATUS
           CALL "PERFT" USING GAME-STATE WS-DEPTH WS-NODES

           MOVE WS-STATUS TO OUT-N
           DISPLAY "STATUS " FUNCTION TRIM(OUT-N)
           MOVE WS-NODES TO OUT-N
           DISPLAY "NODES " FUNCTION TRIM(OUT-N)

           STOP RUN.
