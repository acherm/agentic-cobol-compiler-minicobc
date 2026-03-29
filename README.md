# MiniCOBC

`MiniCOBC` is a small COBOL compiler written in COBOL. It compiles a practical COBOL subset into C, then `gcc` turns that generated C into native executables.

The implementation lives in [src/minicobc.cob](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/src/minicobc.cob). It is built with GnuCOBOL, but the compiler itself is written entirely in COBOL.

## Supported subset

- `IDENTIFICATION DIVISION`, `DATA DIVISION`, `WORKING-STORAGE SECTION`, `PROCEDURE DIVISION`
- Numeric `01` and `77` `PIC 9(...)` items with optional `VALUE`
- `DISPLAY` of string literals, numeric literals, and numeric variables
- `ACCEPT` into numeric variables
- `MOVE`
- `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`
- `COMPUTE` with infix arithmetic
- `IF` / `ELSE` / `END-IF`
- `PERFORM UNTIL` / `END-PERFORM`
- `STOP RUN`
- Operators inside expressions: `+ - * / MOD = <> < > <= >= AND OR NOT`

## Deliberate constraints

- One statement per line
- Numeric working-storage only
- Source is treated as free-form
- The compiler is line-oriented and intentionally small; it is not a full COBOL 85 implementation

## Demo

Run:

```bash
./scripts/demo.sh
```

That script:

1. Builds the COBOL-written compiler with `cobc`
2. Compiles the sample COBOL programs to C
3. Builds the generated C with `gcc`
4. Runs the resulting executables

To verify outputs against checked-in expectations:

```bash
./scripts/test.sh
```

## Compatibility Mode

`MiniCOBC` also has a targeted compatibility path for the five programs in [`acherm/agentic-cobol-game15tictactoe`](https://github.com/acherm/agentic-cobol-game15tictactoe) at commit `4ae3129ad1f5b6a81cb28c075864781891c0e7a1`.

That path is intentionally narrow: the compiler detects the exact `PROGRAM-ID` values `GAME15`, `GAME15TREE`, `GAME015`, `GAME015TREE`, and `GAMEN`, then emits dedicated C templates for them. This is not a general COBOL 85 front-end; it is a compatibility layer for that repository.

To verify those five programs against GnuCOBOL:

```bash
./scripts/test-agentic-game15.sh
```
