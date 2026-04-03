#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = ROOT / "external" / "agentic-chessengine-cobol-codex"
DEFAULT_OPENINGS = ROOT / "benchmark" / "chess" / "cutechess-openings.pgn"
MINICOBC_WRAPPER = ROOT / "scripts" / "run-minicobc-chess-uci.sh"


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


def build_minicobc_engine(repo):
    out_dir = ROOT / "build" / "perf" / "chess-elo" / "minicobc"
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


def detect_stockfish_binary(explicit_path):
    if explicit_path:
        binary = Path(explicit_path).resolve()
        if not binary.exists():
            raise FileNotFoundError(f"stockfish binary not found: {binary}")
        return binary
    located = shutil.which("stockfish")
    if not located:
        raise FileNotFoundError("could not find `stockfish` in PATH")
    return Path(located).resolve()


def detect_stockfish_banner(binary):
    completed = subprocess.run(
        [str(binary)],
        input="uci\nquit\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=10.0,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to query stockfish banner\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    for line in completed.stdout.splitlines():
        if line.strip():
            return line.strip()
    return binary.name


def parse_score(stdout):
    matches = re.findall(
        r"Score of (.+?) vs (.+?): ([0-9.]+) - ([0-9.]+) - ([0-9.]+)\s+\[([0-9.]+)\]\s+([0-9]+)",
        stdout,
    )
    if not matches:
        return None
    left, right, wins, losses, draws, pct, games = matches[-1]
    return {
        "left": left,
        "right": right,
        "wins": float(wins),
        "losses": float(losses),
        "draws": float(draws),
        "score_pct": float(pct),
        "games": int(games),
    }


def parse_elo(stdout):
    match = re.search(
        r"Elo difference: ([^ ]+) \+/- ([^,]+), LOS: ([0-9.]+) %, DrawRatio: ([0-9.]+) %",
        stdout,
    )
    if not match:
        return None
    return {
        "elo_diff": match.group(1),
        "error": match.group(2),
        "los_pct": float(match.group(3)),
        "draw_ratio_pct": float(match.group(4)),
    }


def parse_finished_games(stdout):
    results = []
    for line in stdout.splitlines():
        line = line.strip()
        match = re.match(
            r"Finished game ([0-9]+) \((.+?) vs (.+?)\): ([0-9/.-]+) \{(.+)\}",
            line,
        )
        if match:
            results.append(
                {
                    "game": int(match.group(1)),
                    "white": match.group(2),
                    "black": match.group(3),
                    "result": match.group(4),
                    "reason": match.group(5),
                }
            )
    return results


def render_markdown(repo, commit, stockfish_banner, stockfish_binary, openings_file, tc, rounds, games_per_round, build_ms, score, elo, finished_games, raw_log_path, pgn_path):
    lines = []
    lines.append("# Cutechess Elo Match")
    lines.append("")
    lines.append("- Format: real end-to-end UCI games via `cutechess-cli`")
    lines.append("- MiniCOBC engine: generic `COBOCHESS` build, run through an unbuffered UCI wrapper")
    lines.append("- Opponent: Stockfish skill 0")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- Commit: `{commit}`")
    lines.append(f"- Stockfish: `{stockfish_banner}`")
    lines.append(f"- Stockfish binary: `{stockfish_binary}`")
    lines.append(f"- Openings: `{openings_file}`")
    lines.append(f"- Time control: `{tc}`")
    lines.append(f"- Rounds: `{rounds}`")
    lines.append(f"- Games per round: `{games_per_round}`")
    lines.append(f"- MiniCOBC build pipeline time: `{build_ms:.2f} ms`")
    lines.append(f"- Raw cutechess log: `{raw_log_path}`")
    lines.append(f"- PGN output: `{pgn_path}`")
    lines.append("")
    if score:
        lines.append("## Match Summary")
        lines.append("")
        lines.append(f"- Score line: `{score['left']} vs {score['right']}`")
        lines.append(f"- Result: `{score['wins']} - {score['losses']} - {score['draws']}`")
        lines.append(f"- Games: `{score['games']}`")
        lines.append(f"- Score percentage: `{score['score_pct']}`")
        lines.append("")
    if elo:
        lines.append("## Elo Estimate")
        lines.append("")
        lines.append(f"- Elo difference: `{elo['elo_diff']}`")
        lines.append(f"- Error bar: `+/- {elo['error']}`")
        lines.append(f"- LOS: `{elo['los_pct']} %`")
        lines.append(f"- Draw ratio: `{elo['draw_ratio_pct']} %`")
        lines.append("")
    if finished_games:
        lines.append("## Game Results")
        lines.append("")
        lines.append("| # | White | Black | Result | Reason |")
        lines.append("| ---: | --- | --- | --- | --- |")
        for item in finished_games:
            lines.append(
                f"| {item['game']} | {item['white']} | {item['black']} | {item['result']} | {item['reason']} |"
            )
        lines.append("")
    lines.append("## Caveat")
    lines.append("")
    lines.append("- This is a pilot Elo-style match, not a statistically solid rating conclusion. A serious rating estimate still needs many more games and likely SPRT or a larger gauntlet.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Run a real cutechess Elo-style match for the MiniCOBC-built chess engine."
    )
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument("--stockfish")
    parser.add_argument("--tc", default="120+1")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--games-per-round", type=int, default=2)
    parser.add_argument("--skill", type=int, default=0)
    parser.add_argument("--openings", default=str(DEFAULT_OPENINGS))
    parser.add_argument("--draw-movenumber", type=int, default=50)
    parser.add_argument("--draw-movecount", type=int, default=8)
    parser.add_argument("--draw-score", type=int, default=10)
    parser.add_argument("--resign-movecount", type=int, default=4)
    parser.add_argument("--resign-score", type=int, default=700)
    parser.add_argument("--maxmoves", type=int, default=140)
    parser.add_argument("--timemargin", type=int, default=1000)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    openings_file = Path(args.openings).resolve()
    if not repo.exists():
        print(f"repo not found: {repo}", file=sys.stderr)
        return 2
    if not openings_file.exists():
        print(f"openings file not found: {openings_file}", file=sys.stderr)
        return 2

    try:
        commit_cp, _ = run_command(["git", "-C", str(repo), "rev-parse", "HEAD"])
        commit = commit_cp.stdout.strip()
        stockfish_binary = detect_stockfish_binary(args.stockfish)
        stockfish_banner = detect_stockfish_banner(stockfish_binary)
        mini_binary, build_ms = build_minicobc_engine(repo)
    except (RuntimeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out_dir = ROOT / "build" / "perf"
    out_dir.mkdir(parents=True, exist_ok=True)
    tc_slug = args.tc.replace("/", "_").replace("+", "p").replace(":", "_")
    run_id = f"skill{args.skill}-{tc_slug}-r{args.rounds}g{args.games_per_round}"
    raw_log_path = out_dir / f"chess-cutechess-elo-{run_id}.txt"
    pgn_path = out_dir / f"chess-cutechess-elo-{run_id}.pgn"
    json_path = out_dir / f"chess-cutechess-elo-{run_id}.json"
    md_path = out_dir / f"chess-cutechess-elo-{run_id}.md"

    env = os.environ.copy()
    env["MINICOBC_CHESS_BIN"] = str(mini_binary)

    cmd = [
        "cutechess-cli",
        "-engine",
        f"name=MiniCOBC",
        f"cmd={MINICOBC_WRAPPER}",
        "proto=uci",
        f"tc={args.tc}",
        f"timemargin={args.timemargin}",
        "option.Hash=16",
        "-engine",
        f"name=Stockfish-s{args.skill}",
        f"cmd={stockfish_binary}",
        "proto=uci",
        f"tc={args.tc}",
        f"timemargin={args.timemargin}",
        "option.Threads=1",
        "option.Hash=16",
        f"option.Skill Level={args.skill}",
        "-openings",
        f"file={openings_file}",
        "format=pgn",
        "order=sequential",
        "plies=6",
        "policy=encounter",
        "-repeat",
        "-games",
        str(args.games_per_round),
        "-rounds",
        str(args.rounds),
        "-draw",
        f"movenumber={args.draw_movenumber}",
        f"movecount={args.draw_movecount}",
        f"score={args.draw_score}",
        "-resign",
        f"movecount={args.resign_movecount}",
        f"score={args.resign_score}",
        "twosided=true",
        "-maxmoves",
        str(args.maxmoves),
        "-concurrency",
        "1",
        "-recover",
        "-ratinginterval",
        "2",
        "-outcomeinterval",
        "2",
        "-pgnout",
        str(pgn_path),
        "fi",
    ]

    started = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    raw_log_path.write_text(completed.stdout + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")

    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode

    score = parse_score(completed.stdout)
    elo = parse_elo(completed.stdout)
    finished_games = parse_finished_games(completed.stdout)

    payload = {
        "repo": str(repo),
        "commit": commit,
        "stockfish_binary": str(stockfish_binary),
        "stockfish_banner": stockfish_banner,
        "openings_file": str(openings_file),
        "tc": args.tc,
        "rounds": args.rounds,
        "games_per_round": args.games_per_round,
        "skill": args.skill,
        "minicobc_build_ms": build_ms,
        "match_elapsed_ms": elapsed_ms,
        "score": score,
        "elo": elo,
        "finished_games": finished_games,
        "command": cmd,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(
        repo,
        commit,
        stockfish_banner,
        stockfish_binary,
        openings_file,
        args.tc,
        args.rounds,
        args.games_per_round,
        build_ms,
        score,
        elo,
        finished_games,
        raw_log_path,
        pgn_path,
    )
    md_path.write_text(markdown, encoding="utf-8")

    print(markdown, end="")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"wrote {raw_log_path}")
    print(f"wrote {pgn_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
