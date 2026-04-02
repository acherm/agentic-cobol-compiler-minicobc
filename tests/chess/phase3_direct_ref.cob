       IDENTIFICATION DIVISION.
       PROGRAM-ID. SEARCHDIRECTREF.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY "copybooks/types.cpy".

       01 PHASE3-FEN             PIC X(80)
           VALUE "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPB1PPP/R3K2R w KQkq - 0 1".

       01 SS.
          COPY "copybooks/searchstate.cpy".

       01 WS-STATUS              PIC S9(4) COMP-5 VALUE 0.
       01 WS-DEPTH               PIC S9(4) COMP-5 VALUE 0.
       01 WS-ALPHA               PIC S9(9) COMP-5 VALUE -30000.
       01 WS-BETA                PIC S9(9) COMP-5 VALUE 30000.
       01 WS-NMP                 PIC S9(4) COMP-5 VALUE 1.
       01 WS-OUT                 PIC S9(9) COMP-5 VALUE 0.
       01 TT-I                   PIC S9(9) COMP-5 VALUE 0.
       01 I                      PIC S9(4) COMP-5 VALUE 0.
       01 CAP-ONLY               PIC S9(4) COMP-5 VALUE 1.
       01 UCI-BUF                PIC X(8).

       PROCEDURE DIVISION.
           PERFORM RUN-ROOT
           PERFORM RUN-AFTER-D5E6
           PERFORM TRACE-AFTER-D5E6
           STOP RUN.

       RUN-ROOT.
           DISPLAY "CASE ROOT"
           PERFORM SETUP-ROOT
           PERFORM INIT-SS
           MOVE -30000 TO WS-ALPHA
           MOVE 30000 TO WS-BETA
           MOVE 0 TO WS-OUT
           CALL "QUIESCE" USING GAME-STATE WS-ALPHA WS-BETA SS WS-OUT
           DISPLAY "QUIESCE-OUT " WS-OUT
           DISPLAY "QUIESCE-NODES " SS-NODES

           PERFORM SETUP-ROOT
           PERFORM INIT-SS
           MOVE -30000 TO WS-ALPHA
           MOVE 30000 TO WS-BETA
           MOVE 0 TO WS-OUT
           MOVE 0 TO WS-DEPTH
           MOVE 1 TO WS-NMP
           CALL "ALPHABETA"
               USING GAME-STATE WS-DEPTH WS-ALPHA WS-BETA SS WS-NMP WS-OUT
           DISPLAY "ALPHABETA-OUT " WS-OUT
           DISPLAY "ALPHABETA-NODES " SS-NODES
           EXIT.

       RUN-AFTER-D5E6.
           DISPLAY "CASE AFTER-D5E6"
           PERFORM SETUP-AFTER-D5E6
           PERFORM INIT-SS
           MOVE -30000 TO WS-ALPHA
           MOVE 30000 TO WS-BETA
           MOVE 0 TO WS-OUT
           CALL "QUIESCE" USING GAME-STATE WS-ALPHA WS-BETA SS WS-OUT
           DISPLAY "QUIESCE-OUT " WS-OUT
           DISPLAY "QUIESCE-NODES " SS-NODES

           PERFORM SETUP-AFTER-D5E6
           PERFORM INIT-SS
           MOVE -30000 TO WS-ALPHA
           MOVE 30000 TO WS-BETA
           MOVE 0 TO WS-OUT
           MOVE 0 TO WS-DEPTH
           MOVE 1 TO WS-NMP
           CALL "ALPHABETA"
               USING GAME-STATE WS-DEPTH WS-ALPHA WS-BETA SS WS-NMP WS-OUT
           DISPLAY "ALPHABETA-OUT " WS-OUT
           DISPLAY "ALPHABETA-NODES " SS-NODES
           EXIT.

       TRACE-AFTER-D5E6.
           DISPLAY "TRACE AFTER-D5E6"
           PERFORM SETUP-AFTER-D5E6
           MOVE 1 TO CAP-ONLY
           CALL "MOVEGEN" USING GAME-STATE MOVE-LIST CAP-ONLY
           PERFORM VARYING I FROM 1 BY 1 UNTIL I > ML-COUNT
               MOVE ML-FROM(I) TO M-FROM OF MOVE-REC
               MOVE ML-TO(I) TO M-TO OF MOVE-REC
               MOVE ML-PROMO(I) TO M-PROMO OF MOVE-REC
               MOVE ML-FLAGS(I) TO M-FLAGS OF MOVE-REC
               MOVE 0 TO M-SCORE OF MOVE-REC
               CALL "MOVE2UCI" USING MOVE-REC UCI-BUF
               CALL "MAKEMOVE" USING GAME-STATE MOVE-REC WS-STATUS
               IF WS-STATUS = 1
                   PERFORM INIT-SS
                   MOVE -30000 TO WS-ALPHA
                   MOVE 30000 TO WS-BETA
                   MOVE 0 TO WS-OUT
                   CALL "QUIESCE" USING GAME-STATE WS-ALPHA WS-BETA SS WS-OUT
                   DISPLAY "TRACE " FUNCTION TRIM(UCI-BUF)
                       " OUT " WS-OUT
                       " NODES " SS-NODES
                   CALL "UNMAKEMOVE" USING GAME-STATE MOVE-REC
               END-IF
           END-PERFORM
           EXIT.

       SETUP-ROOT.
           CALL "BOARD" USING GAME-STATE
           CALL "FEN" USING GAME-STATE PHASE3-FEN WS-STATUS
           EXIT.

       SETUP-AFTER-D5E6.
           PERFORM SETUP-ROOT
           MOVE 67 TO M-FROM OF MOVE-REC
           MOVE 84 TO M-TO OF MOVE-REC
           MOVE 0 TO M-PROMO OF MOVE-REC
           MOVE 1 TO M-FLAGS OF MOVE-REC
           MOVE 0 TO M-SCORE OF MOVE-REC
           CALL "MAKEMOVE" USING GAME-STATE MOVE-REC WS-STATUS
           EXIT.

       INIT-SS.
           MOVE 0 TO SS-NODES SS-STOP SS-START-CS SS-TIME-LIMIT-CS
           MOVE 2048 TO SS-TIME-CHECK
           MOVE 1 TO SS-TT-INIT
           MOVE LOW-VALUES TO SS-HEUR
           PERFORM VARYING TT-I FROM 1 BY 1 UNTIL TT-I > 1048576
               MOVE -1 TO TTE-KEY(TT-I)
           END-PERFORM
           MOVE 0 TO TTE-DEPTH(1)
           MOVE 0 TO TTE-FLAG(1)
           MOVE 0 TO TTE-SCORE(1)
           MOVE 0 TO TTE-FROM(1)
           MOVE 0 TO TTE-TO(1)
           MOVE 0 TO TTE-PROMO(1)
           MOVE 0 TO TTE-FLAGS(1)
           EXIT.
