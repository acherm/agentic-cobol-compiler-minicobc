# MiniCOBC Status Report

Date: 2026-03-30

## Executive Summary

`MiniCOBC` is currently a working COBOL compiler written in COBOL that:

- compiles a practical free-form COBOL subset to C
- supports a correctness benchmark corpus shared with GnuCOBOL
- has a first real optimization mode (`OPT`)
- can bootstrap its current compiler source through a dedicated self-host path
- can build and validate an external COBOL chess engine through a targeted compatibility path
- can build `game15.cob` and `gameN.cob` from the external puzzle repository through the generic front end
- can build the COBOL portion of DOOM through the generic front end

The project is no longer just a proof of concept. It now has:

- an executable compiler
- reproducible correctness tests
- comparative performance harnesses
- a compiler-focused optimization corpus
- a bootstrap verification loop

The main limitation remains scope: the generic compiler is still a subset compiler, while the chess engine, the remaining Game-of-15 tree and `game015*` variants, and the self-hosted compiler source are supported through repository-specific compatibility paths rather than full general COBOL front-end support. `game15.cob`, `gameN.cob`, and DOOM are now larger generic-front-end success cases, not just compatibility templates.

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
- `compat`: the Game-of-15 repository workloads, with `game15` and `gameN` now generic and the other variants still compatibility-backed

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

Compatibility-suite numbers still exist, but they are now mixed: `game15` and `gameN` exercise the generic subset compiler, while the tree and `game015*` programs still measure template-backed compatibility paths.

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

This support is implemented as a targeted multi-file compatibility path:

- the compiler recognizes the engine program IDs
- it emits matching generated C translation units and required sidecar headers
- it does not yet compile that chess engine through the generic subset front end

Validation is covered by [scripts/test-chess-engine.sh](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/scripts/test-chess-engine.sh), which checks:

- `--perft-startpos 2`
- a `kiwipete` perft case
- an en-passant legality perft case
- a simple UCI depth-1 interaction

The `minicobc`-built engine matches the GnuCOBOL-built reference engine on those checked cases.

## Chess Engine Performance Benchmark

The chess-specific performance benchmark uses deterministic `perft` workloads, which is the right way to compare engine execution without conflating search heuristics or I/O behavior.

Latest results from [build/perf/chess-perft-compare.md](/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/chess-perft-compare.md):

- profile: `default`
- timed iterations per case: `3`
- total benchmark nodes: `296707`

Build pipelines:

- `minicobc` build pipeline: `1108.77 ms`
- GnuCOBOL build pipeline: `1483.95 ms`

Runtime comparison:

- aggregate median runtime: `2305.54 ms` vs `2027.62 ms`
- aggregate ratio: `1.14x`
- aggregate nodes/sec: `128693` vs `146333`

Per-case runtime ratios:

- `startpos/d4`: `1.14x`
- `kiwipete/d3`: `1.14x`
- `ep_illegal_exposes_king/d3`: `1.03x`
- `promotions_and_capture_promotions/d3`: `1.05x`

Interpretation:

- the `minicobc`-built chess engine is currently about `14%` slower on the default perft profile
- this is a valid engine benchmark, but it measures the compatibility path output, not improvements from the generic `MiniCOBC` front end

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

- chess-engine support is compatibility-based, not generic COBOL support
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
- eventually replacing the chess/self-host compatibility paths with genuine front-end support

Highest-value next benchmarking tasks:

- larger arithmetic kernels that still stay within the shared subset
- table-style workloads once `OCCURS` is supported
- file and text processing benchmarks once those features exist
