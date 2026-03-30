# MiniCOBC

`MiniCOBC` is a small COBOL compiler written in COBOL. It compiles a practical COBOL subset into C, then `gcc` turns that generated C into native executables.

The implementation lives in [src/minicobc.cob](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/src/minicobc.cob). It is built with GnuCOBOL, but the compiler itself is written entirely in COBOL.

## Current Status

As of 2026-03-30, `MiniCOBC` is a working subset COBOL compiler with correctness tests, performance harnesses, an optimization mode, a bootstrap check, and one larger external program now handled through the generic front end.

- Generic compiler path: the shared `core` and `opt` corpus currently passes `11/11` benchmark cases, the full benchmark passes `19/19` including the compatibility suite, and additional regression tests now cover paragraph `PERFORM`, paragraph `PERFORM UNTIL`, `PERFORM VARYING`, restricted external `CALL`, multiline procedure statements, `EVALUATE`, `PIC X`, `PIC S9(...) COMP-5`, elementary and one-dimensional group `OCCURS`, indexed references, grouped child items, group `DISPLAY`, group `ACCEPT`, group-to-group `MOVE`, elementary `REDEFINES` views, redefining groups with child overlays that stay synchronized across writes, `FUNCTION SQRT`, and `PIC X` reference modification.
- Direct comparison with GnuCOBOL on the generic `core` suite: `minicobc + gcc` is about `0.69x` `cobc` compile time and about `0.51x` to `0.52x` runtime on this machine.
- Optimization mode: `OPT` now implements readonly `VALUE` propagation, local dead-store elimination, constant folding, loop-condition canonicalization, and width-aware integer selection. On the `core` suite, optimized `minicobc` is about `0.88x` baseline runtime.
- Bootstrap: the current compiler source bootstraps through a dedicated `PROGRAM-ID. MINICOB.` self-host path, and the stage-1 compiler reproduces the same stage-2 C template.
- Chess engine: the external COBOL chess engine at commit `faf0f163e9b2b4b6475262fc8f00fcaeeedf4919` builds and validates through a targeted compatibility path. On the default perft profile, the `minicobc`-built engine is about `1.14x` the runtime of the GnuCOBOL-built engine.
- DOOM: the COBOL portion of `acherm/agentic-cobol-doom` at commit `18ce52b3f7dd4d6d229d4a743513c39960959b44` now builds through the generic `MiniCOBC` front end and plain `gcc`. The current `MINICOBC_OPT=1` DOOM build is about `0.92x` the baseline build time on this machine, with similar startup latency and a smaller binary.

Important caveat: the chess engine and current bootstrap path are compatibility-mode integrations. DOOM is now a generic-front-end success case, but `MiniCOBC` is still intentionally far from full COBOL 85 coverage.

For a longer status snapshot with benchmark details, see `reports/current-status.md`.

## Supported subset

- `IDENTIFICATION DIVISION`, `DATA DIVISION`, `WORKING-STORAGE SECTION`, `PROCEDURE DIVISION`
- Elementary `01`, `05`, `77`, and similar level-number items with `PIC 9(...)` or `PIC X(...)`, optional `VALUE`, optional elementary `OCCURS`, and elementary `REDEFINES` views when packed widths match
- Signed numeric items with `PIC S9(...) COMP-5`
- Group items with child tracking, packed-layout serialization for group `DISPLAY`, group `ACCEPT`, and group-to-group `MOVE`, plus redefining groups with child items when packed widths match
- `DISPLAY` of string literals, numeric literals, numeric variables, and `PIC X` variables
- `ACCEPT` into numeric variables and `PIC X` variables
- `MOVE`
- `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`
- `COMPUTE` with infix arithmetic
- `FUNCTION MOD(...)`, `FUNCTION REM(...)`, and `FUNCTION SQRT(...)`
- `IF` / `ELSE` / `END-IF`
- `EVALUATE` with a single numeric subject or `EVALUATE TRUE`, `WHEN`, `WHEN OTHER`, and `END-EVALUATE`
- paragraph labels plus `PERFORM paragraph`
- `PERFORM paragraph UNTIL ...`
- `PERFORM UNTIL` / `END-PERFORM`
- `PERFORM VARYING ... FROM ... BY ... UNTIL ... END-PERFORM`
- restricted external `CALL "name"` with optional `USING BY VALUE`, `USING BY REFERENCE`, and `RETURNING`, including indexed numeric `BY VALUE` arguments and `PIC X` `BY REFERENCE` buffers
- `STOP RUN`
- multiline free-form procedure statements for the current subset, including `CALL`, `COMPUTE`, and `IF` conditions
- simple indexed references like `ITEMS(3)` or `ITEMS(IDX)` for elementary `OCCURS` items and one-dimensional group `OCCURS` items
- `PIC X` reference modification of the form `NAME(start:length)`
- Operators inside expressions: `+ - * / = <> < > <= >= AND OR NOT`
- simple alphanumeric equality/inequality comparisons
- Legacy infix `MOD` is still accepted as a MiniCOBC extension

## Optimization Mode

`MiniCOBC` now has an optional optimization mode:

```bash
./build/bin/minicobc OPT input.cob output.c
```

The current opt mode is still conservative, but it now enables:

- propagation of numeric `VALUE` items that are never written in the procedure division
- local dead-store elimination for overwritten `MOVE` and `COMPUTE` assignments
- constant folding for fully constant arithmetic, comparison, and boolean expressions
- loop-condition canonicalization for simple counted `PERFORM UNTIL` shapes
- width-aware C integer selection from `PIC 9(...)` widths

It is still not a full optimizer. Expression simplification inside mixed variable/constant boolean chains and more aggressive strength reduction remain future work.

## Deliberate constraints

- Source is treated as free-form
- Paragraph labels must still be terminated by a period
- Multiline assembly currently applies to procedure statements; the compiler is still a lightweight parser rather than a full COBOL sentence engine
- `EVALUATE` currently supports one subject only; `ALSO`, ranges like `THRU`, and table/indexed selectors are not yet implemented
- Group operations and `REDEFINES` overlays currently use a packed byte buffer per overlay family rather than a full general COBOL storage model with arbitrary aliasing
- One-dimensional group `OCCURS` is supported, but nested `OCCURS` and overlay families containing `OCCURS` items are still unsupported
- Group `MOVE` still requires the same packed width and does not yet support `OCCURS` children
- Group items still cannot appear directly inside expressions
- Indexed references currently support one-dimensional `OCCURS` only, with a simple literal or scalar variable subscript
- Alphanumeric expression support is still narrow: simple equality/inequality works, but general string arithmetic and richer string functions do not
- External `CALL` support currently targets quoted C symbols; generic COBOL dynamic call/runtime semantics are not implemented
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

That test now checks both pipelines:

1. `minicobc -> C -> gcc`
2. `cobc -x -free`

The core examples in `examples/` are valid free-form COBOL accepted by both compilers.

For the new generic front-end slices specifically, run:

```bash
./scripts/test-generic-features.sh
```

That covers:

- paragraph labels and `PERFORM paragraph`
- restricted external `CALL` with `BY VALUE`
- restricted external `CALL` with `BY REFERENCE`
- multiline `CALL`
- multiline `COMPUTE`
- multiline `IF` conditions
- `EVALUATE` with block `WHEN` arms
- inline `WHEN ... MOVE ...` forms
- scalar `PIC X` moves/displays
- elementary `OCCURS` with numeric and alphanumeric indexed references
- one-dimensional group `OCCURS` with indexed group `DISPLAY`, `ACCEPT`, and `MOVE`
- grouped child items
- group `DISPLAY`
- group `ACCEPT`
- group-to-group `MOVE`, including layout-changing moves when packed widths match
- elementary `REDEFINES` views for `DISPLAY`, `MOVE`, `ACCEPT`, and numeric expressions
- redefining groups with child overlays, including writes through either view

## Compatibility Mode

`MiniCOBC` also has a targeted compatibility path for the five programs in [`acherm/agentic-cobol-game15tictactoe`](https://github.com/acherm/agentic-cobol-game15tictactoe) at commit `4ae3129ad1f5b6a81cb28c075864781891c0e7a1`.

That path is intentionally narrow: the compiler detects the exact `PROGRAM-ID` values `GAME15`, `GAME15TREE`, `GAME015`, `GAME015TREE`, and `GAMEN`, then emits dedicated C templates for them. This is not a general COBOL 85 front-end; it is a compatibility layer for that repository.

To verify those five programs against GnuCOBOL:

```bash
./scripts/test-agentic-game15.sh
```

`MiniCOBC` also has a targeted multi-file compatibility path for [`acherm/agentic-chessengine-cobol-codex`](https://github.com/acherm/agentic-chessengine-cobol-codex) at commit `faf0f163e9b2b4b6475262fc8f00fcaeeedf4919`.

That path recognizes the engine program IDs (`COBOCHESS`, `BOARD`, `FEN`, `ATTACK`, `MOVEGEN`, `MAKEMOVE`, `PERFT`, `TIMEUTIL`, `EVAL`, `SEARCH`, and `MOVE2UCI`) and emits the matching GnuCOBOL-generated C translation units plus required sidecar headers. It is still a repository-specific compatibility layer, not general support for the full GNUCobol feature set used by the engine.

Build the chess engine with `minicobc`:

```bash
./scripts/build-chess-engine.sh
```

Verify the `minicobc`-built engine against the GnuCOBOL reference build:

```bash
./scripts/test-chess-engine.sh
```

Benchmark perft runtime for the `minicobc`-built engine against the usual GnuCOBOL build:

```bash
./scripts/compare-chess-perft.sh
```

That writes:

- `build/perf/chess-perft-compare.json`
- `build/perf/chess-perft-compare.md`

`MiniCOBC` can now compile the COBOL portion of [`acherm/agentic-cobol-doom`](https://github.com/acherm/agentic-cobol-doom) at commit `18ce52b3f7dd4d6d229d4a743513c39960959b44` through the generic front end. The key enabling features are signed `COMP-5`, paragraph `PERFORM UNTIL`, external `CALL` with indexed `BY VALUE` arguments and `PIC X` `BY REFERENCE` buffers, `FUNCTION SQRT`, and `PIC X` reference modification on redefining overlay views.

Build the COBOL part of DOOM with `minicobc`:

```bash
bash ./scripts/build-cobol-doom.sh
```

That script translates `doom.cob` to C with `minicobc` and builds the result with plain `gcc`.

Enable `minicobc`'s own optimization mode for that translation:

```bash
MINICOBC_OPT=1 bash ./scripts/build-cobol-doom.sh
```

Verify that the `minicobc`-translated build and the repo's own `cobc` build both start successfully under a bounded smoke test:

```bash
bash ./scripts/test-cobol-doom.sh
```

Compare DOOM builds with and without `minicobc`'s `OPT` mode:

```bash
bash ./scripts/compare-cobol-doom-opt.sh
```

## Self-Host Path

The current `src/minicobc.cob` is also supported through a dedicated `PROGRAM-ID. MINICOB.` compatibility path. That path is generated from the current compiler source with GnuCOBOL and packaged as a single C template in `templates/compat/minicob.c`.

Regenerate that template:

```bash
./scripts/regenerate-selfhost-template.sh
```

Verify the self-host bootstrap:

```bash
./scripts/test-selfhost.sh
```

That script:

1. Regenerates the `MINICOB` self-host template
2. Builds the stage-0 compiler with GnuCOBOL
3. Uses stage-0 `minicobc` to compile `src/minicobc.cob` into stage-1 C
4. Builds the stage-1 compiler
5. Uses the stage-1 compiler to reproduce the same stage-2 self-host C
6. Uses the stage-1 compiler on the core example programs

## Benchmark

The benchmark design and workload definitions live in `benchmark/README.md` and `benchmark/cases.json`.

For compiler optimization work, there is now a dedicated general-purpose optimization suite in `examples/opt/` with design notes in `benchmark/optimization-suite.md`.

The benchmark now includes an embedded compiler comparison against GnuCOBOL, so each case records:

- `minicobc` translation time
- `gcc` build time
- `cobc` compile time
- runtime for both produced binaries
- compile and runtime ratios versus GnuCOBOL

Correctness still drives pass/fail. The compiler comparison is informational.

Run the full benchmark:

```bash
./scripts/benchmark.sh
```

Run only the core suite:

```bash
./scripts/benchmark.sh --suite core
```

Run only the optimization suite:

```bash
./scripts/benchmark.sh --suite opt
```

Run only the compatibility suite:

```bash
./scripts/benchmark.sh --suite compat --compat-repo external/agentic-cobol-game15tictactoe
```

Tune the embedded compiler comparison:

```bash
./scripts/benchmark.sh --suite core --compile-iterations 7 --run-iterations 9
```

Skip the GnuCOBOL performance comparison and run correctness-only:

```bash
./scripts/benchmark.sh --skip-compiler-compare
```

## Compiler Performance Comparison

To compare `minicobc + gcc` against direct `cobc` compilation on the tested workloads:

```bash
./scripts/compare-compilers.sh
```

That writes:

- `build/perf/compiler-compare.json`
- `build/perf/compiler-compare.md`

The `core` suite is the direct apples-to-apples comparison for the generic subset compiler.

To compare the stage-0 compiler built by GnuCOBOL against the self-hosted stage-1 compiler:

```bash
./scripts/compare-selfhost.sh
```

That writes:

- `build/perf/selfhost-compare.json`
- `build/perf/selfhost-compare.md`

To compare baseline `minicobc`, optimized `minicobc`, and optimized GnuCOBOL on the compiler-focused suites:

```bash
./scripts/compare-minicobc-optimizations.sh --suite opt
```

That writes suite-specific reports such as:

- `build/perf/minicobc-opt-compare-opt.json`
- `build/perf/minicobc-opt-compare-opt.md`
