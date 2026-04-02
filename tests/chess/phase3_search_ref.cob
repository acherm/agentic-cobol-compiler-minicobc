       IDENTIFICATION DIVISION.
       PROGRAM-ID. SEARCHPHASE3.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY "copybooks/types.cpy".

       01 STARTPOS               PIC X(80)
           VALUE "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1".
       01 WS-STATUS              PIC S9(4) COMP-5 VALUE 0.
       01 WS-DEPTH               PIC S9(4) COMP-5 VALUE 2.
       01 WS-TIME-LIMIT-CS       PIC S9(18) COMP-5 VALUE 0.
       01 WS-OUT-SCORE           PIC S9(9) COMP-5 VALUE 0.
       01 WS-OUT-NODES           PIC S9(18) COMP-5 VALUE 0.
       01 UCI-BUF                PIC X(8).
       01 OUT-S                  PIC -Z(8)9.
       01 OUT-N                  PIC -Z(17)9.

       PROCEDURE DIVISION.
           CALL "FEN" USING GAME-STATE STARTPOS WS-STATUS
           CALL "SEARCH"
               USING GAME-STATE WS-DEPTH WS-TIME-LIMIT-CS
                     MOVE-REC WS-OUT-SCORE WS-OUT-NODES
           CALL "MOVE2UCI" USING MOVE-REC UCI-BUF

           MOVE WS-STATUS TO OUT-N
           DISPLAY "STATUS " FUNCTION TRIM(OUT-N)
           DISPLAY "BESTMOVE " FUNCTION TRIM(UCI-BUF)
           MOVE WS-OUT-SCORE TO OUT-S
           DISPLAY "SCORE " FUNCTION TRIM(OUT-S)
           MOVE WS-OUT-NODES TO OUT-N
           DISPLAY "NODES " FUNCTION TRIM(OUT-N)

           STOP RUN.
