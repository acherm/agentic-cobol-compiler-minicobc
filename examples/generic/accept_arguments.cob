       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCEPTARGS.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 ARG-COUNT              PIC 9(4) COMP-5.
       01 ARG1                   PIC X(16).
       01 ARG2                   PIC X(16).

       PROCEDURE DIVISION.
           ACCEPT ARG-COUNT FROM ARGUMENT-NUMBER
           DISPLAY "COUNT " ARG-COUNT
           IF ARG-COUNT > 0
               ACCEPT ARG1 FROM ARGUMENT-VALUE
               DISPLAY "ARG1 " ARG1
           END-IF
           IF ARG-COUNT > 1
               ACCEPT ARG2 FROM ARGUMENT-VALUE
               DISPLAY "ARG2 " ARG2
           END-IF
           STOP RUN.
