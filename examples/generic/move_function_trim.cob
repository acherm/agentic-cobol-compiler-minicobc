       IDENTIFICATION DIVISION.
       PROGRAM-ID. MOVETRIM.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 SRC                    PIC X(8) VALUE "ABCD    ".
       01 DST                    PIC X(8).

       PROCEDURE DIVISION.
           MOVE FUNCTION TRIM(SRC) TO DST
           DISPLAY DST
           STOP RUN.
