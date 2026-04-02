#!/usr/bin/env python3
import argparse
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import chess


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = ROOT / "external" / "agentic-chessengine-cobol-codex"

TEST_CASES = [
    ("Starting position (white)", []),
    ("After e2e4 (black)", ["e2e4"]),
    ("After e2e4 e7e5 (white)", ["e2e4", "e7e5"]),
    ("After d2d4 d7d5 c2c4 (black)", ["d2d4", "d7d5", "c2c4"]),
    ("After e2e4 d7d5 (white)", ["e2e4", "d7d5"]),
    ("After g1f3 (black)", ["g1f3"]),
    ("After e2e4 e7e5 g1f3 b8c6 (white)", ["e2e4", "e7e5", "g1f3", "b8c6"]),
    ("Castling ready (white)", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"]),
    ("Castling ready (black)", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "d2d3"]),
    ("EP available (white)", ["e2e4", "d7d5", "e4e5", "f7f5"]),
    ("EP available (black)", ["d2d4", "e7e5", "d4d5", "a7a6", "a2a3", "c7c5"]),
]


def run_command(cmd, *, cwd=ROOT):
    started = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return completed, elapsed_ms


def median(values):
    return statistics.median(values) if values else 0.0


def build_minicobc_engine(repo):
    out_dir = ROOT / "build" / "perf" / "chess-depth1" / "minicobc"
    out_dir.mkdir(parents=True, exist_ok=True)
    completed, elapsed_ms = run_command(
        [str(ROOT / "scripts" / "build-chess-engine.sh"), str(repo), str(out_dir)]
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to build chess engine with minicobc\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return out_dir / "cobochess", elapsed_ms


def build_gnucobol_engine(repo):
    out_dir = ROOT / "build" / "perf" / "chess-depth1" / "gnucobol"
    out_dir.mkdir(parents=True, exist_ok=True)
    completed, elapsed_ms = run_command(["make", "-C", str(repo), "build"])
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to build chess engine with gnucobol\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    source = repo / "bin" / "cobochess"
    target = out_dir / "cobochess"
    shutil.copy2(source, target)
    return target, elapsed_ms


def run_depth1(engine, fen):
    completed, elapsed_ms = run_command([str(engine), "--perft", fen, "1"])
    if completed.returncode != 0:
        raise RuntimeError(
            "depth1 run failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    stdout = completed.stdout.strip()
    if not stdout.startswith("nodes="):
        raise RuntimeError(f"unexpected output: {stdout!r}")
    return int(stdout.split("=", 1)[1]), elapsed_ms


def evaluate_case(mini, gnu, name, moves, iterations):
    board = chess.Board()
    for move in moves:
        board.push(chess.Move.from_uci(move))
    fen = board.fen()
    expected = board.legal_moves.count()

    mini_times = []
    gnu_times = []
    for _ in range(iterations):
        mini_nodes, mini_ms = run_depth1(mini, fen)
        gnu_nodes, gnu_ms = run_depth1(gnu, fen)
        if mini_nodes != expected or gnu_nodes != expected:
            raise RuntimeError(
                f"count mismatch on {name}: python-chess={expected} minicobc={mini_nodes} gnucobol={gnu_nodes}"
            )
        mini_times.append(mini_ms)
        gnu_times.append(gnu_ms)

    return {
        "name": name,
        "moves": moves,
        "fen": fen,
        "expected_nodes": expected,
        "iterations": iterations,
        "minicobc_median_ms": median(mini_times),
        "gnucobol_median_ms": median(gnu_times),
        "runtime_ratio_vs_gnucobol": median(mini_times) / median(gnu_times) if median(gnu_times) else None,
    }


def render_markdown(repo, minicobc_build_ms, gnucobol_build_ms, iterations, results):
    lines = []
    lines.append("# Chess Depth-1 Position Suite")
    lines.append("")
    lines.append("- Source inspiration: `agentic-chessengine-brainfuck/test_perft.py`")
    lines.append("- Purpose: independent correctness sweep against `python-chess` on depth-1 legal-move counts")
    lines.append("- Important caveat: this is mainly a correctness suite, not a strong throughput benchmark")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- Timed iterations per case: `{iterations}`")
    lines.append(f"- `minicobc` build pipeline time: `{minicobc_build_ms:.2f} ms`")
    lines.append(f"- GnuCOBOL build pipeline time: `{gnucobol_build_ms:.2f} ms`")
    lines.append("")
    lines.append("| Case | Nodes | Mini ms | GNU ms | Ratio |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for item in results:
        lines.append(
            f"| {item['name']} | {item['expected_nodes']} | "
            f"{item['minicobc_median_ms']:.2f} | {item['gnucobol_median_ms']:.2f} | "
            f"{item['runtime_ratio_vs_gnucobol']:.2f}x |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    minicobc_binary, minicobc_build_ms = build_minicobc_engine(repo)
    gnucobol_binary, gnucobol_build_ms = build_gnucobol_engine(repo)

    results = [
        evaluate_case(minicobc_binary, gnucobol_binary, name, moves, args.iterations)
        for name, moves in TEST_CASES
    ]

    out_dir = ROOT / "build" / "perf"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "chess-depth1-suite.json"
    md_path = out_dir / "chess-depth1-suite.md"

    payload = {
        "repo": str(repo),
        "iterations": args.iterations,
        "minicobc_build_ms": minicobc_build_ms,
        "gnucobol_build_ms": gnucobol_build_ms,
        "results": results,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        render_markdown(repo, minicobc_build_ms, gnucobol_build_ms, args.iterations, results),
        encoding="utf-8",
    )

    print(md_path.read_text(encoding="utf-8"), end="")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
