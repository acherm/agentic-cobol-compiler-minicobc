# Cutechess Elo Match

- Format: real end-to-end UCI games via `cutechess-cli`
- MiniCOBC engine: generic `COBOCHESS` build, run through an unbuffered UCI wrapper
- Opponent: Stockfish skill 0
- Repo: `/Users/mathieuacher/SANDBOX/cobol-compiler-codex/external/agentic-chessengine-cobol-codex`
- Commit: `faf0f163e9b2b4b6475262fc8f00fcaeeedf4919`
- Stockfish: `Stockfish 18 by the Stockfish developers (see AUTHORS file)`
- Stockfish binary: `/opt/homebrew/Cellar/stockfish/18/bin/stockfish`
- Openings: `/Users/mathieuacher/SANDBOX/cobol-compiler-codex/benchmark/chess/cutechess-openings.pgn`
- Time control: `120+1`
- Rounds: `1`
- Games per round: `2`
- MiniCOBC build pipeline time: `3651.29 ms`
- Raw cutechess log: `/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/chess-cutechess-elo-skill0-120p1-r1g2.txt`
- PGN output: `/Users/mathieuacher/SANDBOX/cobol-compiler-codex/build/perf/chess-cutechess-elo-skill0-120p1-r1g2.pgn`

## Match Summary

- Score line: `MiniCOBC vs Stockfish-s0`
- Result: `2.0 - 0.0 - 0.0`
- Games: `2`
- Score percentage: `1.0`

## Elo Estimate

- Elo difference: `inf`
- Error bar: `+/- nan`
- LOS: `92.1 %`
- Draw ratio: `0.0 %`

## Game Results

| # | White | Black | Result | Reason |
| ---: | --- | --- | --- | --- |
| 1 | MiniCOBC | Stockfish-s0 | 1-0 | White wins by adjudication |
| 2 | Stockfish-s0 | MiniCOBC | 0-1 | Black wins by adjudication |

## Caveat

- This is a pilot Elo-style match, not a statistically solid rating conclusion. A serious rating estimate still needs many more games and likely SPRT or a larger gauntlet.
