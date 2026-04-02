       IDENTIFICATION DIVISION.
       PROGRAM-ID. NUMVALIDX.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 I                      PIC 9(4) COMP-5 VALUE 1.
       01 TOKENS.
          05 TOK OCCURS 3        PIC X(8).
       01 OUT-N                  PIC 9(4) COMP-5.

       PROCEDURE DIVISION.
           MOVE "7" TO TOK(2)
           MOVE FUNCTION NUMVAL(TOK(I + 1)) TO OUT-N
           DISPLAY OUT-N
           STOP RUN.
