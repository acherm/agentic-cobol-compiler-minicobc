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

import chess
import chess.pgn


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = ROOT / "external" / "agentic-chessengine-cobol-codex"

OPENING_CASES = {
    "startpos": {
        "label": "Start position",
        "start": "startpos",
        "moves": [],
    },
    "open_game": {
        "label": "Open game",
        "start": "startpos",
        "moves": ["e2e4", "e7e5", "g1f3", "b8c6"],
    },
    "queens_gambit": {
        "label": "Queen's gambit",
        "start": "startpos",
        "moves": ["d2d4", "d7d5", "c2c4"],
    },
    "phase3_fen": {
        "label": "Phase-3 debug FEN",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPB1PPP/R3K2R w KQkq - 0 1",
    },
    "kiwipete_fen": {
        "label": "Kiwipete perft FEN",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    },
    "ep_fen": {
        "label": "EP legality FEN",
        "fen": "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    },
    "promo_fen": {
        "label": "Promotion race FEN",
        "fen": "1r5k/P7/8/8/8/8/8/7K w - - 0 1",
    },
}

TOURNAMENT_PROFILES = {
    "quick": ["startpos", "open_game", "phase3_fen"],
    "default": ["startpos", "open_game", "queens_gambit", "phase3_fen", "kiwipete_fen"],
    "extended": [
        "startpos",
        "open_game",
        "queens_gambit",
        "phase3_fen",
        "kiwipete_fen",
        "ep_fen",
        "promo_fen",
    ],
}


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
    out_dir = ROOT / "build" / "perf" / "chess-tournament" / "minicobc"
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
    out_dir = ROOT / "build" / "perf" / "chess-tournament" / "gnucobol"
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


def make_board(case):
    if "fen" in case:
        return chess.Board(case["fen"])
    board = chess.Board()
    for uci in case["moves"]:
        board.push(chess.Move.from_uci(uci))
    return board


def build_position_command(case, played_moves):
    all_moves = list(case.get("moves", [])) + list(played_moves)
    if "fen" in case:
        command = f"position fen {case['fen']}"
    else:
        command = "position startpos"
    if all_moves:
        command += " moves " + " ".join(all_moves)
    return command


def build_game_header(case, white_name, black_name, result, depth, max_plies, initial_fen):
    headers = {
        "Event": "MiniCOBC vs GnuCOBOL Tournament",
        "Site": str(ROOT),
        "White": white_name,
        "Black": black_name,
        "Result": result,
        "OpeningCase": case["label"],
        "Depth": str(depth),
        "MaxPlies": str(max_plies),
    }
    if "fen" in case or case.get("moves"):
        headers["FEN"] = initial_fen
        headers["SetUp"] = "1"
    return headers


def numeric_score(outcome, white_variant, black_variant):
    score = {"minicobc": 0.0, "gnucobol": 0.0}
    if outcome is None or outcome.winner is None:
        score["minicobc"] = 0.5
        score["gnucobol"] = 0.5
        return score
    winner_variant = white_variant if outcome.winner == chess.WHITE else black_variant
    loser_variant = black_variant if outcome.winner == chess.WHITE else white_variant
    score[winner_variant] = 1.0
    score[loser_variant] = 0.0
    return score


def aggregate_variant_stats(games):
    data = {
        "minicobc": {
            "score": 0.0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "illegal_moves": 0,
            "moves": 0,
            "wall_ms": [],
            "depth": [],
            "nodes": [],
        },
        "gnucobol": {
            "score": 0.0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "illegal_moves": 0,
            "moves": 0,
            "wall_ms": [],
            "depth": [],
            "nodes": [],
        },
    }

    for game in games:
        for variant in ("minicobc", "gnucobol"):
            entry = data[variant]
            game_score = game["scores"][variant]
            entry["score"] += game_score
            if game_score == 1.0:
                entry["wins"] += 1
            elif game_score == 0.5:
                entry["draws"] += 1
            else:
                entry["losses"] += 1

        if game["termination"].startswith("illegal_"):
            data[game["termination"].split("_", 1)[1]]["illegal_moves"] += 1

        for move in game["moves"]:
            entry = data[move["variant"]]
            entry["moves"] += 1
            entry["wall_ms"].append(move["wall_ms"])
            if move["depth"] is not None:
                entry["depth"].append(move["depth"])
            if move["nodes"] is not None:
                entry["nodes"].append(move["nodes"])

    for variant in data.values():
        variant["avg_wall_ms"] = (
            sum(variant["wall_ms"]) / len(variant["wall_ms"]) if variant["wall_ms"] else 0.0
        )
        variant["avg_depth"] = (
            sum(variant["depth"]) / len(variant["depth"]) if variant["depth"] else 0.0
        )
        variant["avg_nodes"] = (
            sum(variant["nodes"]) / len(variant["nodes"]) if variant["nodes"] else 0.0
        )
        variant["median_wall_ms"] = median(variant["wall_ms"])
    return data


class UciEngine:
    def __init__(self, binary, label, variant, timeout_s=30.0):
        self.binary = Path(binary)
        self.label = label
        self.variant = variant
        self.timeout_s = timeout_s

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def new_game(self):
        return None

    def search(self, case, played_moves, depth):
        stdin_text = "\n".join(
            [
                "uci",
                "isready",
                build_position_command(case, played_moves),
                f"go depth {depth}",
                "quit",
            ]
        ) + "\n"
        started = time.perf_counter()
        completed = subprocess.run(
            [str(self.binary)],
            text=True,
            input=stdin_text,
            capture_output=True,
            check=False,
            timeout=self.timeout_s,
        )
        wall_ms = (time.perf_counter() - started) * 1000.0
        if completed.returncode != 0:
            raise RuntimeError(
                f"{self.variant}: engine run failed with code {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        lines = [normalize_line(line) for line in completed.stdout.splitlines()]
        lines = [line for line in lines if line]
        bestmove_lines = [line for line in lines if line.startswith("bestmove ")]
        if not bestmove_lines:
            raise RuntimeError(f"{self.variant}: search returned without a bestmove line")
        bestmove = bestmove_lines[-1].split()[1]
        info_lines = [line for line in lines if line.startswith("info depth ")]
        last_info = info_lines[-1].split() if info_lines else []
        depth_value = None
        nodes_value = None
        if last_info:
            for index, token in enumerate(last_info):
                if token == "depth" and index + 1 < len(last_info):
                    try:
                        depth_value = int(last_info[index + 1])
                    except ValueError:
                        depth_value = None
                if token == "nodes" and index + 1 < len(last_info):
                    try:
                        nodes_value = int(last_info[index + 1])
                    except ValueError:
                        nodes_value = None
        return {
            "bestmove": bestmove,
            "lines": lines,
            "wall_ms": wall_ms,
            "depth": depth_value,
            "nodes": nodes_value,
        }


def play_tournament_game(case, game_index, white_engine, black_engine, depth, max_plies):
    board = make_board(case)
    played_moves = []
    game = chess.pgn.Game()
    game.headers.update(
        build_game_header(
            case,
            white_engine.label,
            black_engine.label,
            "*",
            depth,
            max_plies,
            board.fen(),
        )
    )
    node = game
    moves = []
    outcome = None
    termination = "max_plies"

    white_engine.new_game()
    black_engine.new_game()

    for ply in range(max_plies):
        if board.is_game_over(claim_draw=True):
            outcome = board.outcome(claim_draw=True)
            termination = outcome.termination.name
            break
        side_engine = white_engine if board.turn == chess.WHITE else black_engine
        result = side_engine.search(case, played_moves, depth)
        move_text = result["bestmove"]
        if move_text in {"0000", "(none)"}:
            outcome = board.outcome(claim_draw=True)
            termination = "engine_no_move"
            break
        try:
            move = chess.Move.from_uci(move_text)
        except ValueError:
            termination = f"illegal_{side_engine.variant}"
            scores = {
                "minicobc": 0.0 if side_engine.variant == "minicobc" else 1.0,
                "gnucobol": 0.0 if side_engine.variant == "gnucobol" else 1.0,
            }
            game.headers["Result"] = "0-1" if side_engine.variant == "minicobc" else "1-0"
            game.headers["Termination"] = termination
            return {
                "game_index": game_index,
                "case_id": case["id"],
                "case_label": case["label"],
                "white": white_engine.variant,
                "black": black_engine.variant,
                "result": game.headers["Result"],
                "termination": termination,
                "plies": len(moves),
                "scores": scores,
                "moves": moves,
                "pgn": str(game),
                "final_fen": board.fen(),
            }
        if not board.is_legal(move):
            termination = f"illegal_{side_engine.variant}"
            scores = {
                "minicobc": 0.0 if side_engine.variant == "minicobc" else 1.0,
                "gnucobol": 0.0 if side_engine.variant == "gnucobol" else 1.0,
            }
            game.headers["Result"] = "0-1" if side_engine.variant == "minicobc" else "1-0"
            game.headers["Termination"] = termination
            return {
                "game_index": game_index,
                "case_id": case["id"],
                "case_label": case["label"],
                "white": white_engine.variant,
                "black": black_engine.variant,
                "result": game.headers["Result"],
                "termination": termination,
                "plies": len(moves),
                "scores": scores,
                "moves": moves,
                "pgn": str(game),
                "final_fen": board.fen(),
                "illegal_move": move_text,
            }

        san = board.san(move)
        moves.append(
            {
                "ply": ply + 1,
                "variant": side_engine.variant,
                "color": "white" if board.turn == chess.WHITE else "black",
                "uci": move.uci(),
                "san": san,
                "wall_ms": result["wall_ms"],
                "depth": result["depth"],
                "nodes": result["nodes"],
            }
        )
        node = node.add_variation(move)
        board.push(move)
        played_moves.append(move.uci())

    if outcome is None:
        outcome = board.outcome(claim_draw=True)
    if outcome is None:
        result_text = "1/2-1/2"
    else:
        result_text = outcome.result()
        termination = outcome.termination.name

    game.headers["Result"] = result_text
    game.headers["Termination"] = termination
    scores = numeric_score(outcome, white_engine.variant, black_engine.variant)

    return {
        "game_index": game_index,
        "case_id": case["id"],
        "case_label": case["label"],
        "white": white_engine.variant,
        "black": black_engine.variant,
        "result": result_text,
        "termination": termination,
        "plies": len(moves),
        "scores": scores,
        "moves": moves,
        "pgn": str(game),
        "final_fen": board.fen(),
    }


def render_markdown(repo, commit, profile, depth, max_plies, mini_build_ms, gnu_build_ms, games, summary):
    lines = []
    lines.append("# Chess Tournament Benchmark")
    lines.append("")
    lines.append("- Purpose: compare practical play under equal fixed-depth search, not only perft or one-position search")
    lines.append("- Format: paired games from a diversified opening/FEN suite, colors swapped for each starting position")
    lines.append("- Equality signal: illegal moves are treated as immediate losses and the transcript records per-move depth/nodes")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- Commit: `{commit}`")
    lines.append(f"- Profile: `{profile}`")
    lines.append(f"- Fixed depth per move: `{depth}`")
    lines.append(f"- Max plies per game: `{max_plies}`")
    lines.append(f"- `minicobc` build pipeline time: `{mini_build_ms:.2f} ms`")
    lines.append(f"- GnuCOBOL build pipeline time: `{gnu_build_ms:.2f} ms`")
    lines.append("")
    lines.append("## Match Score")
    lines.append("")
    lines.append("| Engine | Score | W-D-L | Illegal moves | Avg wall ms/move | Median wall ms/move | Avg depth | Avg nodes/move |")
    lines.append("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |")
    for variant in ("minicobc", "gnucobol"):
        item = summary[variant]
        lines.append(
            f"| {variant} | {item['score']:.1f} | "
            f"{item['wins']}-{item['draws']}-{item['losses']} | "
            f"{item['illegal_moves']} | "
            f"{item['avg_wall_ms']:.2f} | {item['median_wall_ms']:.2f} | "
            f"{item['avg_depth']:.2f} | {item['avg_nodes']:.0f} |"
        )
    lines.append("")
    lines.append("## Games")
    lines.append("")
    lines.append("| # | Case | White | Black | Result | Termination | Plies |")
    lines.append("| ---: | --- | --- | --- | --- | --- | ---: |")
    for game in games:
        lines.append(
            f"| {game['game_index']} | {game['case_label']} | {game['white']} | {game['black']} | "
            f"{game['result']} | {game['termination']} | {game['plies']} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Run a MiniCOBC vs GnuCOBOL chess-engine tournament."
    )
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument(
        "--profile",
        choices=tuple(TOURNAMENT_PROFILES.keys()),
        default="default",
    )
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--max-plies", type=int, default=60)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo not found: {repo}", file=sys.stderr)
        return 2

    try:
        commit_cp, _ = run_command(["git", "-C", str(repo), "rev-parse", "HEAD"])
        commit = commit_cp.stdout.strip()
        mini_binary, mini_build_ms = build_minicobc_engine(repo)
        gnu_binary, gnu_build_ms = build_gnucobol_engine(repo)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out_dir = ROOT / "build" / "perf"
    out_dir.mkdir(parents=True, exist_ok=True)
    games = []

    try:
        with UciEngine(mini_binary, "MiniCOBC", "minicobc") as mini_engine, UciEngine(
            gnu_binary, "GnuCOBOL", "gnucobol"
        ) as gnu_engine:
            opening_ids = TOURNAMENT_PROFILES[args.profile]
            game_index = 1
            for opening_id in opening_ids:
                case = dict(OPENING_CASES[opening_id])
                case["id"] = opening_id
                for swap in (False, True):
                    if not swap:
                        white = mini_engine
                        black = gnu_engine
                    else:
                        white = gnu_engine
                        black = mini_engine
                    games.append(
                        play_tournament_game(
                            case,
                            game_index,
                            white,
                            black,
                            args.depth,
                            args.max_plies,
                        )
                    )
                    game_index += 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    summary = aggregate_variant_stats(games)
    payload = {
        "repo": str(repo),
        "commit": commit,
        "profile": args.profile,
        "depth": args.depth,
        "max_plies": args.max_plies,
        "minicobc_build_ms": mini_build_ms,
        "gnucobol_build_ms": gnu_build_ms,
        "games": games,
        "summary": summary,
    }

    run_id = f"{args.profile}-d{args.depth}-p{args.max_plies}"
    json_path = out_dir / f"chess-tournament-{run_id}.json"
    md_path = out_dir / f"chess-tournament-{run_id}.md"
    pgn_path = out_dir / f"chess-tournament-{run_id}.pgn"
    latest_json_path = out_dir / "chess-tournament.json"
    latest_md_path = out_dir / "chess-tournament.md"
    latest_pgn_path = out_dir / "chess-tournament.pgn"

    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(
        repo,
        commit,
        args.profile,
        args.depth,
        args.max_plies,
        mini_build_ms,
        gnu_build_ms,
        games,
        summary,
    )
    md_path.write_text(markdown, encoding="utf-8")
    pgn_path.write_text("\n\n".join(game["pgn"] for game in games) + "\n", encoding="utf-8")
    latest_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    latest_md_path.write_text(markdown, encoding="utf-8")
    latest_pgn_path.write_text("\n\n".join(game["pgn"] for game in games) + "\n", encoding="utf-8")

    print(markdown, end="")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"wrote {pgn_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
