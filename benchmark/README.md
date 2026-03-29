# Benchmark Design

This benchmark is built from the COBOL programs already exercised in this workspace. It is intended to answer one practical question:

Can `MiniCOBC` translate COBOL programs that we have already validated, build the generated C, and reproduce the expected observable behavior?

How does that same workload perform when compiled with `MiniCOBC + gcc` versus direct GnuCOBOL compilation with `cobc`?

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

- Validate the targeted compatibility path in `MiniCOBC`
- Cover the larger workloads that were manually tested in this repository

## Cases

The benchmark currently runs 11 cases:

- `core/primes`
- `core/collatz`
- `core/gcd`
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
