# Benchmark Design

This benchmark is built from the COBOL programs already exercised in this workspace. It is intended to answer two practical questions:

Can `MiniCOBC` translate COBOL programs that we have already validated, build the generated C, and reproduce the expected observable behavior?

How does that same workload perform when compiled with `MiniCOBC + gcc` versus direct GnuCOBOL compilation with `cobc`?

For compiler-improvement work, the most useful suite is now the optimization corpus described in `benchmark/optimization-suite.md`.

## Suites

### Core suite

These are the three local example programs already used for the subset compiler smoke tests:

- `primes.cob`
- `collatz.cob`
- `gcd.cob`

Oracle:

- Exact stdout match against checked-in expected files in `expected/`

Purpose:

- Validate the generic subset compiler path
- Cover arithmetic, loops, conditionals, `DISPLAY`, `ACCEPT`, and `COMPUTE`

### Optimization suite

These are valid free-form COBOL programs designed specifically to expose optimization opportunities while staying in the current common subset shared by `MiniCOBC` and GnuCOBOL:

- `examples/opt/constfold.cob`
- `examples/opt/constprop.cob`
- `examples/opt/deadstore.cob`
- `examples/opt/strength.cob`
- `examples/opt/boolchain.cob`
- `examples/opt/loopcanon.cob`
- `examples/opt/smallwidth.cob`
- `examples/opt/lcg.cob`

Oracle:

- Exact stdout match against checked-in expected files in `expected/opt/`

Purpose:

- Provide a stable microbenchmark/kernel corpus for compiler optimization work
- Map concrete programs to constant folding, constant propagation, dead-store elimination, strength reduction, boolean simplification, loop canonicalization, and width-aware integer selection
- Keep the benchmark apples-to-apples across `MiniCOBC` and GnuCOBOL

The detailed design notes live in `benchmark/optimization-suite.md`.

### Compatibility suite

These are the five richer programs from `acherm/agentic-cobol-game15tictactoe` at commit `4ae3129ad1f5b6a81cb28c075864781891c0e7a1`:

- `game15.cob`
- `game15tree.cob`
- `game015.cob`
- `game015tree.cob`
- `gameN.cob`

Oracle:

- Exact stdout match against GnuCOBOL output for the same source and invocation

Purpose:

- Validate the pinned external Game-of-15 workloads
- Cover three programs that now go through the generic front end (`game15.cob`, `game15tree.cob`, and `gameN.cob`) plus the remaining variants that still use targeted compatibility paths

## Cases

The benchmark currently runs 19 cases:

- `core/primes`
- `core/collatz`
- `core/gcd`
- `opt/constfold`
- `opt/constprop`
- `opt/deadstore`
- `opt/strength`
- `opt/boolchain`
- `opt/loopcanon`
- `opt/smallwidth`
- `opt/lcg`
- `compat/game15`
- `compat/game15_unique`
- `compat/game15tree_depth2`
- `compat/game015`
- `compat/game015tree_depth2`
- `compat/gameN_15_9`
- `compat/gameN_12_8`
- `compat/gameN_10`

The manifest lives in `benchmark/cases.json`.

## Metrics

For each case, the runner records:

- Translation time from COBOL to generated C
- C build time with `gcc`
- Program run time
- Generated C line count
- Generated C file size
- Final binary size
- Output hash
- Exact pass/fail result
- Median repeated compile time for `MiniCOBC + gcc`
- Median repeated compile time for GnuCOBOL `cobc`
- Median repeated runtime for both produced binaries
- Compile and runtime ratios versus GnuCOBOL

## Pass criteria

This benchmark is correctness-first.

- A case passes only if translation succeeds, C compilation succeeds, the program exits successfully, and stdout matches the oracle exactly.
- Timing and size metrics, including the embedded GnuCOBOL comparison, are tracked for trend analysis, but they are not used as pass/fail thresholds.

This is deliberate: a single weighted score would hide the distinction between semantic correctness and performance drift.

## Running

Run all suites:

```bash
./scripts/benchmark.sh
```

Run only the core subset benchmark:

```bash
./scripts/benchmark.sh --suite core
```

Run only the optimization benchmark:

```bash
./scripts/benchmark.sh --suite opt
```

Run only the compatibility benchmark with an explicit repo path:

```bash
./scripts/benchmark.sh --suite compat --compat-repo /path/to/agentic-cobol-game15tictactoe
```

Tune the embedded compiler comparison:

```bash
./scripts/benchmark.sh --suite core --compile-iterations 7 --run-iterations 9
```

Skip the embedded GnuCOBOL performance comparison and run correctness-only:

```bash
./scripts/benchmark.sh --skip-compiler-compare
```

The runner writes:

- `build/benchmark/results.json`
- `build/benchmark/report.md`
