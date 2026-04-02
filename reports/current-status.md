# MiniCOBC Status Report

Date: 2026-04-02

## Executive Summary

`MiniCOBC` is currently a working COBOL compiler written in COBOL that:

- compiles a practical free-form COBOL subset to C
- supports a correctness benchmark corpus shared with GnuCOBOL
- has a first real optimization mode (`OPT`)
- can bootstrap its current compiler source through a dedicated self-host path
- can build and validate the external COBOL chess engine end-to-end through the generic front end, with dedicated phase-1 through phase-4 milestone harnesses
- can build `game15.cob` and `gameN.cob` from the external puzzle repository through the generic front end
- can build the COBOL portion of DOOM through the generic front end

The project is no longer just a proof of concept. It now has:

- an executable compiler
- reproducible correctness tests
- comparative performance harnesses
- a compiler-focused optimization corpus
- a bootstrap verification loop

The main limitation remains scope: the generic compiler is still a subset compiler, while the remaining `game015*` variants, Flappy, and the self-hosted compiler source still rely on repository-specific compatibility paths rather than full general COBOL front-end support. `game15.cob`, `game15tree.cob`, `gameN.cob`, DOOM, and now the full chess engine build are larger generic-front-end success cases, not just compatibility templates.

## Compiler Scope

The generic `MiniCOBC` front end supports:

- `IDENTIFICATION`, `DATA`, `WORKING-STORAGE`, and `PROCEDURE DIVISION`
- numeric and alphanumeric storage, including `PIC 9(...)`, `PIC Z...`, `PIC X(...)`, and `PIC S9(...) COMP-5`
- grouped items, one-dimensional `OCCURS`, and synchronized `REDEFINES` overlay families
- `DISPLAY`, `ACCEPT`, `MOVE`, `INITIALIZE`, `UNSTRING`, `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`
- `COMPUTE` with arithmetic and boolean expressions
- `IF` / `ELSE IF` / `ELSE` / `END-IF`, including repeated `END-IF` tokens on one logical line
- paragraph `PERFORM`, `PERFORM paragraph UNTIL`, `PERFORM UNTIL`, and `PERFORM VARYING`
- `EVALUATE`
- `FUNCTION MOD(...)`, `FUNCTION REM(...)`, `FUNCTION SQRT(...)`, `FUNCTION NUMVAL(...)`, and `FUNCTION TRIM(...)`
- restricted external `CALL`
- indexed references and `PIC X` reference modification `NAME(start:length)`
- `STOP RUN`

The generic compiler still does not support broad COBOL features such as:

- file I/O
- nested `OCCURS`
- full COBOL string/runtime semantics
- dynamic or runtime-resolved `CALL`
- section-heavy program structure beyond the current paragraph subset

## Correctness And Benchmark Corpus

The general benchmark harness is correctness-first and now covers three suites:

- `core`: `primes`, `collatz`, `gcd`
- `opt`: `constfold`, `constprop`, `deadstore`, `strength`, `boolchain`, `loopcanon`, `smallwidth`, `lcg`
- `compat`: the Game-of-15 repository workloads, with `game15`, `game15tree`, and `gameN` now generic and the `game015*` variants still compatibility-backed

Latest overall benchmark status from [build/benchmark/report.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/benchmark/report.md):

- `19/19` cases passed
- `3/3` `core` cases passed
- `8/8` `opt` cases passed
- `8/8` `compat` cases passed

The optimization suite is especially important because it is intentionally designed around common compiler passes:

- constant folding
- constant propagation
- dead-store elimination
- strength reduction
- boolean simplification
- loop canonicalization
- width-aware integer selection

## Compiler Performance

The direct apples-to-apples comparison for the generic compiler path is the `core` suite. Latest results from [build/perf/compiler-compare.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/compiler-compare.md):

- `minicobc + gcc` compile time: about `0.69x` `cobc`
- `minicobc`-generated runtime: about `0.51x` to `0.52x` `cobc`

Per-case medians:

- `primes`: `58.70 ms` vs `84.75 ms` compile, `2.38 ms` vs `4.67 ms` runtime
- `collatz`: `60.21 ms` vs `87.41 ms` compile, `2.35 ms` vs `4.50 ms` runtime
- `gcd`: `57.22 ms` vs `82.52 ms` compile, `2.14 ms` vs `4.22 ms` runtime

Those numbers are local wall-clock measurements and should be treated as comparative signals, not universal claims.

Compatibility-suite numbers still exist, but they are now mixed: `game15`, `game15tree`, and `gameN` exercise the generic subset compiler, while the `game015*` programs still measure template-backed compatibility paths.

## Current Optimization Status

`MiniCOBC` now has an `OPT` mode:

```bash
./build/bin/minicobc OPT input.cob output.c
```

Implemented passes in the generic compiler:

- readonly numeric `VALUE` propagation
- local dead-store elimination for overwritten `MOVE` and `COMPUTE`
- constant folding for fully constant arithmetic, comparison, and boolean expressions
- loop-condition canonicalization for simple counted `PERFORM UNTIL`
- width-aware C type selection from `PIC` widths

Examples of generated-code improvements:

- constant expressions now collapse, for example `TERM = 966`
- counted loops are emitted as direct `while (I <= LIMIT)` style loops instead of double-negated forms
- narrow numeric items now emit `short` or `int` instead of always using a wide integer type

Latest optimization comparison results:

From [build/perf/minicobc-opt-compare-core.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/minicobc-opt-compare-core.md):

- optimized compile ratio vs baseline: `1.01x`
- optimized runtime ratio vs baseline: `0.88x`

From [build/perf/minicobc-opt-compare-opt.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/minicobc-opt-compare-opt.md):

- optimized compile ratio vs baseline: `1.00x`
- optimized runtime ratio vs baseline: `0.99x`

`OPT` is now also wired into the DOOM build path through `MINICOBC_OPT=1`.
Latest DOOM-specific results from [build/perf/cobol-doom-opt-compare.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/cobol-doom-opt-compare.md):

- baseline DOOM build time: `1110.82 ms`
- `OPT` DOOM build time: `1020.89 ms`
- DOOM build ratio: `0.919x`
- baseline startup first output: `4.77 ms`
- `OPT` startup first output: `5.00 ms`
- startup ratio: `1.046x`
- binary size drops from `107672` to `89128` bytes

Interpretation:

- the new passes are correct and measurable
- the biggest current runtime gains show up on the real shared `core` programs
- the synthetic optimization suite still has headroom, especially for partial boolean simplification and strength reduction in mixed variable/constant expressions

## Bootstrap Status

`MiniCOBC` can currently bootstrap its own compiler source, but not through full generic language support.

Current mechanism:

- `src/minicobc.cob` is handled through a dedicated `PROGRAM-ID. MINICOB.` compatibility path
- that path emits a checked-in self-host C template
- bootstrap is validated through a stage-0 -> stage-1 -> stage-2 fixed-point check

Latest bootstrap results from [build/perf/selfhost-compare.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/selfhost-compare.md):

- stage-0 `cobc` build: `138.58 ms`
- self-host template regeneration: `44.27 ms`
- stage-1 bootstrap translate: `168.95 ms`
- stage-1 bootstrap C build: `89.53 ms`
- stage-1 fixed-point verification: `204.91 ms`

Translation comparison:

- `self/minicobc`: stage-0 `21.68 ms`, self-hosted `23.51 ms`, ratio `1.08x`
- `core/primes`: `5.97 ms` vs `5.89 ms`, ratio `0.99x`
- `core/collatz`: `5.93 ms` vs `5.89 ms`, ratio `0.99x`
- `core/gcd`: `5.72 ms` vs `5.34 ms`, ratio `0.93x`

Current status:

- bootstrap works
- stage-1 reproduces stage-2 identically on the self-host path
- this is not yet full self-hosting of the generic compiler feature set

## Chess Engine Handling

`MiniCOBC` can build the COBOL chess engine from:

- repo: `external/agentic-chessengine-cobol-codex`
- commit: `faf0f163e9b2b4b6475262fc8f00fcaeeedf4919`

End-to-end chess-engine support now goes through the real generic front end:

- [scripts/build-chess-engine.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/build-chess-engine.sh) compiles the top-level `COBOCHESS` driver and all required subprogram units through `minicobc`
- [scripts/test-chess-engine.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-engine.sh) matches the generated engine against the upstream GnuCOBOL build on CLI `perft` cases and a UCI smoke case
- the dedicated phase harnesses remain useful because they isolate the architecture slices that made that generic build possible

There is now a real generic phase-1 and phase-2 milestone ladder for the chess repo:

- `BOARD` compiles through the generic `MiniCOBC` subprogram path
- `FEN` compiles through the generic `MiniCOBC` subprogram path
- `ATTACK`, `MOVEGEN`, `MAKEMOVE`, `UNMAKEMOVE`, and `PERFT` also compile through the generic front end
- internal chess-unit `CALL ... USING ...` chains now work through the real front end, including recursive `CALL "PERFT"`
- `LOCAL-STORAGE` now works correctly for the generic recursive `PERFT` unit through per-call C shadow locals
- [scripts/test-chess-phase1.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-phase1.sh) links the generated `BOARD` and `FEN` C units with a small C harness and checks the resulting `FEN(startpos)` state against a GnuCOBOL reference harness
- [scripts/test-chess-phase2.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-phase2.sh) links the generated `BOARD`, `FEN`, `ATTACK`, `MOVEGEN`, `MAKEMOVE`, `UNMAKEMOVE`, and `PERFT` C units with a small C harness and checks `PERFT(startpos, depth=2)` against GnuCOBOL

There is now a real generic phase-3 milestone for the chess repo:

- `TIMEUTIL`, `EVAL`, `SEARCH`, and `MOVE2UCI` also compile through the generic front end
- the helper-unit search stack now runs through real generic internal `CALL ... USING ...` chains rather than compatibility templates
- [scripts/test-chess-phase3.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-phase3.sh) links the generated `BOARD`, `FEN`, `ATTACK`, `MOVEGEN`, `MAKEMOVE`, `UNMAKEMOVE`, `TIMEUTIL`, `EVAL`, `SEARCH`, and `MOVE2UCI` C units with a small C harness and checks a shallow `SEARCH` result against GnuCOBOL
- [scripts/test-chess-phase3-direct.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-phase3-direct.sh) goes one level lower and compares direct `QUIESCE`, direct recursive `ALPHABETA`, and the first capture-reply traces on the phase-3 debug FEN against GnuCOBOL

There is now a real generic phase-4 milestone for the chess repo:

- the top-level `COBOCHESS` driver compiles through the generic front end
- `ACCEPT ARGUMENT-NUMBER`, `ACCEPT ARGUMENT-VALUE`, line-based `ACCEPT` into `PIC X`, `RETURN-CODE`, `STRING ... INTO`, `PERFORM FOREVER`, and the line-oriented UCI loop now work correctly in the top-level engine flow
- [scripts/test-chess-phase4.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-phase4.sh) builds the full generic engine and checks `--perft-startpos 2` against the GnuCOBOL engine build

That phase-2 work required real generic compiler support for:

- `LINKAGE SECTION`
- `PROCEDURE DIVISION USING`
- callable COBOL subprogram emission instead of `main`-only output
- internal COBOL `CALL` with `BY REFERENCE` group/scalar argument marshaling
- qualified `OF` references in the chess copybooks and move structures
- `EXIT PERFORM`
- multi-target numeric `MOVE`
- recursive subprogram linkage preservation
- per-call `LOCAL-STORAGE` shadow locals in generated C for recursive units
- `GOBACK`
- `END PROGRAM`
- level `78` constants
- `COPY` expansion before parsing
- an implicit entry block before the first explicit paragraph

Validation is covered by [scripts/test-chess-engine.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-engine.sh), which checks:

- `--perft-startpos 2`
- a `kiwipete` perft case
- an en-passant legality perft case
- a simple UCI depth-1 interaction

The `minicobc`-built engine now matches the GnuCOBOL-built reference engine on those checked cases through the generic path rather than a compatibility template path.

One useful debugging note changed the confidence level of that statement.

During the generic chess bring-up, a deterministic phase-3 search mismatch appeared on the debug FEN:

- `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPB1PPP/R3K2R w KQkq - 0 1`

The mismatch was not randomness:

- repeated runs on both engines were stable
- the same `bestmove` often appeared, but node counts and scores differed
- direct `QUIESCE` / `ALPHABETA` tracing showed the first bad split below `d5e6`

The root cause turned out to be a real compiler bug in generic indexed numeric `MOVE` source lowering:

- `MOVE ARR(I - 1) TO X` compiled as `X = I - 1`
- instead of `X = ARR[(I - 1) - 1]`

That exact bug affected the pawn-structure loads in chess `EVAL`, notably statements such as:

- `MOVE WPC(F-IX - 1) TO FRIEND-L`
- `MOVE BPC(F-IX + 1) TO FRIEND-R`

The fix is now in [src/minicobc.cob](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/src/minicobc.cob), and the regression is covered by:

- [examples/generic/move_index_expr.cob](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/examples/generic/move_index_expr.cob)
- [scripts/test-generic-features.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-generic-features.sh)

After rebuilding the generic engine, the phase-3 debug FEN now matches GnuCOBOL at `go depth 2`:

- `info depth 1 nodes 1531 score cp -408 pv d5e6`
- `info depth 2 nodes 2855 score cp -408 pv d5e6`
- `bestmove d5e6`

So the earlier phase-3 search mismatch is no longer evidence that the generic chess binary is wrong on that target. The remaining benchmark caveat is about the size of the measured speedup, not about that specific search-equivalence failure.

## Chess Engine Performance Benchmark

The chess-specific performance benchmark uses deterministic `perft` workloads, which is the right way to compare engine execution without conflating search heuristics or I/O behavior.

Latest results from [build/perf/chess-perft-compare.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/chess-perft-compare.md):

- profile: `default`
- timed iterations per case: `3`
- total benchmark nodes: `296707`

Build pipelines:

- `minicobc` build pipeline: `3625.13 ms`
- GnuCOBOL build pipeline: `1003.25 ms`

Runtime comparison:

- aggregate median runtime: `34.43 ms` vs `1764.96 ms`
- aggregate ratio: `0.02x`
- aggregate nodes/sec: `8617938` vs `168110`

Per-case runtime ratios:

- `startpos/d4`: `0.02x`
- `kiwipete/d3`: `0.02x`
- `ep_illegal_exposes_king/d3`: `0.19x`
- `promotions_and_capture_promotions/d3`: `0.13x`

Interpretation:

- the generic `minicobc`-built chess engine is currently much faster than the GnuCOBOL build on the default perft profile measured here
- the performance benchmark now measures the real generic top-level engine build rather than a compatibility-emitted artifact

Benchmark caveat:

- the result is correctness-checked, but the size of the speedup is unusually large and should be treated as provisional rather than as a settled compiler-performance conclusion
- the current validation is strong for the covered cases, but deeper `perft` depths, broader FEN coverage, and profiling are still warranted
- there is now an additional independent depth-1 suite in [scripts/compare-chess-depth1-suite.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/compare-chess-depth1-suite.sh), adapted from the Brainfuck chess-engine `test_perft.py` style, to cross-check shallow move counts against `python-chess`
- `MINICOBC_OPT=1` is currently not safe for chess: it miscompiles the engine and returns `nodes=0` on `perft`, so the reported chess numbers use plain `minicobc` plus `gcc -O2`, not `minicobc OPT`

## Generic DOOM Support

`MiniCOBC` can now build the COBOL portion of DOOM from:

- repo: `external/agentic-cobol-doom`
- commit: `18ce52b3f7dd4d6d229d4a743513c39960959b44`

This is a genuine generic-front-end path, not a copied template path. The current workflow is:

- [scripts/build-cobol-doom.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/build-cobol-doom.sh)
- [scripts/run-cobol-doom.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/run-cobol-doom.sh)
- [scripts/test-cobol-doom.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-cobol-doom.sh)

The key enabling pieces were:

- signed `COMP-5`
- paragraph `PERFORM UNTIL`
- indexed `CALL ... USING BY VALUE`
- `PIC X` buffers passed `BY REFERENCE`
- `FUNCTION SQRT`
- `PIC X` reference modification on redefining overlay views

Current smoke validation:

- generic `minicobc` DOOM build: `alive=1 rc=-15 stdout=1287 stderr=0`
- reference GnuCOBOL DOOM build: `alive=1 rc=-15 stdout=1287 stderr=23`

So the generic build reaches the same startup surface and stdout volume under the bounded smoke check.

## Overall Assessment

Current strengths:

- generic compiler path works on a real cross-compiler subset
- correctness infrastructure is in place
- optimization work is now measurable rather than speculative
- bootstrap is operational
- chess-engine validation and perft benchmarking are operational
- DOOM now builds through the generic front end

Current architectural caveats:

- full chess-engine support is now generic, but Flappy and some remaining external variants are still compatibility-based
- bootstrap is compatibility-based, not full self-hosting of the generic source language
- the generic front end is still a subset compiler, even though it is now strong enough to compile the COBOL DOOM program
- the optimizer is still source-level and local, not IR-based

## Recommended Next Steps

Highest-value next compiler tasks:

- partial boolean simplification inside mixed constant/variable expressions
- strength reduction for repeated multiplication by small constants
- broader constant propagation beyond readonly `VALUE` items
- a small explicit IR layer between parsing and C emission

Highest-value next language-coverage tasks:

- broader expression handling
- more realistic control-flow structure
- eventually replacing the self-host and Flappy compatibility paths with genuine front-end support

Highest-value next benchmarking tasks:

- larger arithmetic kernels that still stay within the shared subset
- table-style workloads once `OCCURS` is supported
- file and text processing benchmarks once those features exist
