# Optimization Benchmark Suite

This suite is the first compiler-oriented corpus in this repository.

It is deliberately built from valid free-form COBOL that both `MiniCOBC` and GnuCOBOL accept today, so performance comparisons stay apples-to-apples while `MiniCOBC` grows.

## Design Principles

- Keep every case deterministic and use checked-in stdout oracles.
- Use small, readable programs rather than generated stress tests.
- Make each microbenchmark expose one dominant optimization opportunity.
- Keep at least one arithmetic kernel so the suite does not overfit to synthetic microbenches.
- Stay within the current common denominator of both compilers for now.
- Avoid `PIC` overflow in the benchmark definitions so results reflect compiler behavior rather than dialect-specific truncation rules.

## Cases

| Case | Kind | Primary signal | Why it exists |
| --- | --- | --- | --- |
| `opt/constfold` | micro | constant folding | Repeats a pure constant expression inside a hot loop. |
| `opt/constprop` | micro | constant propagation | Uses values set once in procedure code and then consumed in an affine recurrence. |
| `opt/deadstore` | micro | dead-store elimination | Overwrites a temporary before its first value is ever observed. |
| `opt/strength` | micro | strength reduction | Repeats multiplications by small powers of two in a tight counted loop. |
| `opt/boolchain` | micro | boolean simplification | Carries constant flags through a branch condition that collapses to a single hot path. |
| `opt/loopcanon` | micro | loop canonicalization | Uses counted nested loops written as `PERFORM UNTIL NOT ( ... )` to expose normalization opportunities. |
| `opt/smallwidth` | micro | width-aware integer selection | Uses several narrow `PIC` items in a long-running cyclic counter workload. |
| `opt/lcg` | kernel | end-to-end arithmetic | Exercises recurrence, modulo arithmetic, and loop-carried state so optimization work does not overfit to only toy loops. |

## Reading the Results

Use the suite in three ways:

- Runtime trend: measure whether a compiler change makes the generated executables faster.
- Code quality trend: watch generated C size and final binary size alongside runtime.
- Front-end stability: keep exact outputs fixed while changing optimization logic.

No single case should be over-interpreted. The useful signal is the shape across the suite:

- `constfold`, `constprop`, and `deadstore` should move first once a basic IR/dataflow layer exists.
- `strength`, `boolchain`, and `loopcanon` should move once expressions and loops are normalized.
- `smallwidth` should move once `PIC` widths start influencing chosen C integer types.
- `lcg` should confirm that local wins still matter on a more realistic arithmetic kernel.

## Current MiniCOBC Opt Mode

The current `MiniCOBC OPT` mode implements these source-level optimizations:

- readonly numeric `VALUE` propagation
- local dead-store elimination for overwritten `MOVE` and `COMPUTE` statements
- constant folding for fully constant arithmetic, comparison, and boolean expressions
- canonicalization of simple counted `PERFORM UNTIL` loop conditions
- width-aware C integer selection from `PIC 9(...)` widths

That means the suite is still slightly ahead of the implementation, but no longer by much. The remaining obvious gaps are partial boolean simplification inside mixed expressions and stronger strength reduction.

## Current Scope And Next Tiers

This first suite intentionally avoids features that `MiniCOBC` does not compile generically yet, such as:

- `OCCURS` tables
- string-heavy workloads
- file I/O
- `CALL`
- section/paragraph-heavy control flow

Once the front end grows, the next benchmark tier should add:

- table scans and reductions
- histogram-style counting
- text/token scanning
- record-oriented file transforms
- multi-procedure workloads with more realistic control flow
