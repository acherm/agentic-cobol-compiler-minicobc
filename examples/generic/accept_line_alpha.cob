       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCEPTLINE.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 INPUT-LINE PIC X(32).
       PROCEDURE DIVISION.
           ACCEPT INPUT-LINE
           IF INPUT-LINE = "go depth 1"
               DISPLAY "MATCH"
           ELSE
               DISPLAY "MISS"
           END-IF
           STOP RUN.
