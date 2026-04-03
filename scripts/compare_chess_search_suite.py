#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = ROOT / "external" / "agentic-chessengine-cobol-codex"

SEARCH_PROFILES = {
    "default": [
        {
            "id": "startpos_d2",
            "label": "Startpos depth 2",
            "commands": [
                "position startpos",
                "go depth 2",
                "quit",
            ],
        },
        {
            "id": "opening_knights_d2",
            "label": "Open game depth 2",
            "commands": [
                "position startpos moves e2e4 e7e5 g1f3 b8c6",
                "go depth 2",
                "quit",
            ],
        },
        {
            "id": "qg_d2",
            "label": "Queen's gambit depth 2",
            "commands": [
                "position startpos moves d2d4 d7d5 c2c4",
                "go depth 2",
                "quit",
            ],
        },
        {
            "id": "phase3_fen_d2",
            "label": "Phase-3 debug FEN depth 2",
            "commands": [
                "position fen r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPB1PPP/R3K2R w KQkq - 0 1",
                "go depth 2",
                "quit",
            ],
        },
    ],
    "extended": [
        {
            "id": "startpos_d3",
            "label": "Startpos depth 3",
            "commands": [
                "position startpos",
                "go depth 3",
                "quit",
            ],
        },
        {
            "id": "opening_knights_d3",
            "label": "Open game depth 3",
            "commands": [
                "position startpos moves e2e4 e7e5 g1f3 b8c6",
                "go depth 3",
                "quit",
            ],
        },
        {
            "id": "qg_d3",
            "label": "Queen's gambit depth 3",
            "commands": [
                "position startpos moves d2d4 d7d5 c2c4",
                "go depth 3",
                "quit",
            ],
        },
        {
            "id": "phase3_fen_d3",
            "label": "Phase-3 debug FEN depth 3",
            "commands": [
                "position fen r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPB1PPP/R3K2R w KQkq - 0 1",
                "go depth 3",
                "quit",
            ],
        },
        {
            "id": "kiwipete_perft_fen_d2",
            "label": "Kiwipete perft FEN depth 2",
            "commands": [
                "position fen r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
                "go depth 2",
                "quit",
            ],
        },
        {
            "id": "ep_fen_d2",
            "label": "EP legality FEN depth 2",
            "commands": [
                "position fen k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
                "go depth 2",
                "quit",
            ],
        },
        {
            "id": "promo_fen_d2",
            "label": "Promotion race FEN depth 2",
            "commands": [
                "position fen 1r5k/P7/8/8/8/8/8/7K w - - 0 1",
                "go depth 2",
                "quit",
            ],
        },
    ],
}


def run_command(cmd, *, cwd=ROOT, stdin_text=None):
    started = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        input=stdin_text,
        capture_output=True,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return completed, elapsed_ms


def median(values):
    return statistics.median(values) if values else 0.0


def build_minicobc_engine(repo):
    out_dir = ROOT / "build" / "perf" / "chess-search" / "minicobc"
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
    out_dir = ROOT / "build" / "perf" / "chess-search" / "gnucobol"
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


def normalize_line(line):
    tokens = line.strip().split()
    if not tokens:
        return ""
    merged = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"-", "+"} and index + 1 < len(tokens):
            next_token = tokens[index + 1]
            if next_token.isdigit():
                merged.append(f"{token}{next_token}")
                index += 2
                continue
        merged.append(token)
        index += 1
    normalized = " ".join(merged)
    normalized = re.sub(r"\bcp \+(\d+)\b", r"cp \1", normalized)
    return normalized


def normalize_transcript(stdout):
    lines = [normalize_line(line) for line in stdout.splitlines()]
    return [line for line in lines if line]


def extract_summary(lines):
    info_lines = [line for line in lines if line.startswith("info depth ")]
    bestmove_lines = [line for line in lines if line.startswith("bestmove ")]
    if not bestmove_lines:
        raise RuntimeError("search transcript did not contain a bestmove line")
    return {
        "info_lines": info_lines,
        "bestmove": bestmove_lines[-1],
    }


def run_case(engine, case):
    stdin_text = "\n".join(case["commands"]) + "\n"
    completed, elapsed_ms = run_command([str(engine)], stdin_text=stdin_text)
    if completed.returncode != 0:
        raise RuntimeError(
            "search run failed\n"
            f"case: {case['id']}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    normalized = normalize_transcript(completed.stdout)
    return extract_summary(normalized), elapsed_ms


def benchmark_case(mini, gnu, case, iterations):
    mini_times = []
    gnu_times = []
    baseline_summary = None
    for _ in range(iterations):
        mini_summary, mini_ms = run_case(mini, case)
        gnu_summary, gnu_ms = run_case(gnu, case)
        if mini_summary != gnu_summary:
            raise RuntimeError(
                "search transcript mismatch\n"
                f"case: {case['id']}\n"
                f"minicobc: {mini_summary}\n"
                f"gnucobol: {gnu_summary}"
            )
        baseline_summary = mini_summary
        mini_times.append(mini_ms)
        gnu_times.append(gnu_ms)

    return {
        "id": case["id"],
        "label": case["label"],
        "commands": case["commands"],
        "iterations": iterations,
        "minicobc_median_ms": median(mini_times),
        "gnucobol_median_ms": median(gnu_times),
        "runtime_ratio_vs_gnucobol": (
            median(mini_times) / median(gnu_times) if median(gnu_times) else None
        ),
        "summary": baseline_summary,
    }


def render_markdown(repo, commit, profile, iterations, mini_build_ms, gnu_build_ms, results):
    lines = []
    lines.append("# Chess Fixed-Depth Search Suite")
    lines.append("")
    lines.append("- Purpose: compare real search transcripts, not only perft counts")
    lines.append("- Equality criterion: normalized `info depth ...` lines plus `bestmove` must match GnuCOBOL exactly")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- Commit: `{commit}`")
    lines.append(f"- Profile: `{profile}`")
    lines.append(f"- Timed iterations per case: `{iterations}`")
    lines.append(f"- `minicobc` build pipeline time: `{mini_build_ms:.2f} ms`")
    lines.append(f"- GnuCOBOL build pipeline time: `{gnu_build_ms:.2f} ms`")
    lines.append("")
    lines.append("| Case | Mini ms | GNU ms | Ratio | Bestmove | Final info |")
    lines.append("| --- | ---: | ---: | ---: | --- | --- |")
    for item in results:
        final_info = item["summary"]["info_lines"][-1] if item["summary"]["info_lines"] else "(none)"
        lines.append(
            f"| {item['label']} | "
            f"{item['minicobc_median_ms']:.2f} | "
            f"{item['gnucobol_median_ms']:.2f} | "
            f"{item['runtime_ratio_vs_gnucobol']:.2f}x | "
            f"`{item['summary']['bestmove']}` | "
            f"`{final_info}` |"
        )
    total_mini = sum(item["minicobc_median_ms"] for item in results)
    total_gnu = sum(item["gnucobol_median_ms"] for item in results)
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append(
        f"- Sum of median runtimes: `minicobc {total_mini:.2f} ms`, `gnucobol {total_gnu:.2f} ms`"
    )
    if total_gnu:
        lines.append(f"- Aggregate runtime ratio: `{(total_mini / total_gnu):.2f}x`")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Compare fixed-depth search transcripts for minicobc vs GnuCOBOL."
    )
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument(
        "--profile",
        choices=tuple(SEARCH_PROFILES.keys()),
        default="default",
    )
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo not found: {repo}", file=sys.stderr)
        return 2

    try:
        commit_cp, _ = run_command(["git", "-C", str(repo), "rev-parse", "HEAD"])
        commit = commit_cp.stdout.strip()
        mini, mini_build_ms = build_minicobc_engine(repo)
        gnu, gnu_build_ms = build_gnucobol_engine(repo)
        cases = SEARCH_PROFILES[args.profile]
        results = [benchmark_case(mini, gnu, case, args.iterations) for case in cases]
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out_dir = ROOT / "build" / "perf"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "chess-search-suite.json"
    md_path = out_dir / "chess-search-suite.md"

    payload = {
        "repo": str(repo),
        "commit": commit,
        "profile": args.profile,
        "iterations": args.iterations,
        "minicobc_build_ms": mini_build_ms,
        "gnucobol_build_ms": gnu_build_ms,
        "results": results,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        render_markdown(
            repo,
            commit,
            args.profile,
            args.iterations,
            mini_build_ms,
            gnu_build_ms,
            results,
        ),
        encoding="utf-8",
    )

    print(md_path.read_text(encoding="utf-8"), end="")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
