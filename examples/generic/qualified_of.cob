       IDENTIFICATION DIVISION.
       PROGRAM-ID. QUALIFIEDOF.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 ONE-MOVE.
          05 M-FROM               PIC 9(4).
       01 MOVE-LIST.
          05 ML-COUNT             PIC 9(4).
          05 ML-MOVE OCCURS 2.
             10 ML-FROM           PIC 9(4).
       01 IDX                     PIC 9(4).

       PROCEDURE DIVISION.
           MOVE 1 TO IDX
           MOVE 2 TO ML-FROM OF MOVE-LIST(IDX)
           MOVE ML-FROM OF MOVE-LIST(IDX) TO M-FROM OF ONE-MOVE
           DISPLAY M-FROM OF ONE-MOVE
           STOP RUN.
