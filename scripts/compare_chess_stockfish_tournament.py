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
import chess.engine
import chess.pgn

from compare_chess_tournament import (
    DEFAULT_REPO,
    OPENING_CASES,
    TOURNAMENT_PROFILES,
    build_minicobc_engine,
    build_position_command,
    make_board,
    normalize_line,
)


ROOT = Path(__file__).resolve().parent.parent


def median(values):
    return statistics.median(values) if values else 0.0


def parse_skill_levels(text):
    values = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        level = int(chunk)
        if level < 0 or level > 20:
            raise ValueError(f"invalid Stockfish skill level: {level}")
        values.append(level)
    if not values:
        raise ValueError("at least one Stockfish skill level is required")
    return values


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
        line = line.strip()
        if line:
            return line
    return binary.name


class StatelessUciEngine:
    def __init__(
        self,
        binary,
        label,
        variant,
        search_mode,
        search_value,
        setup_lines=None,
        timeout_s=30.0,
    ):
        self.binary = Path(binary)
        self.label = label
        self.variant = variant
        self.search_mode = search_mode
        self.search_value = search_value
        self.setup_lines = list(setup_lines or [])
        self.timeout_s = timeout_s

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def new_game(self):
        return None

    def search(self, case, played_moves, clock_state=None):
        if self.search_mode == "depth":
            search_command = f"go depth {self.search_value}"
        elif self.search_mode == "movetime":
            search_command = f"go movetime {self.search_value}"
        else:
            if clock_state is None:
                raise RuntimeError(f"{self.variant}: missing clock state for clock search mode")
            search_command = (
                f"go wtime {clock_state['white_ms']} "
                f"btime {clock_state['black_ms']} "
                f"winc {clock_state['white_inc_ms']} "
                f"binc {clock_state['black_inc_ms']}"
            )
            if clock_state.get("side_moves_to_go") is not None:
                search_command += f" movestogo {clock_state['side_moves_to_go']}"
        stdin_lines = ["uci"]
        stdin_lines.extend(self.setup_lines)
        stdin_lines.extend(
            [
                "isready",
                build_position_command(case, played_moves),
                search_command,
                "quit",
            ]
        )
        started = time.perf_counter()
        completed = subprocess.run(
            [str(self.binary)],
            input="\n".join(stdin_lines) + "\n",
            text=True,
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


class PersistentStockfishEngine:
    def __init__(self, binary, label, variant, skill, search_mode, search_value):
        self.binary = Path(binary)
        self.label = label
        self.variant = variant
        self.skill = skill
        self.search_mode = search_mode
        self.search_value = search_value
        self.engine = None
        self.game_token = None

    def __enter__(self):
        self.engine = chess.engine.SimpleEngine.popen_uci(str(self.binary))
        self.engine.configure(
            {
                "Threads": 1,
                "Hash": 16,
                "UCI_LimitStrength": False,
                "Skill Level": self.skill,
            }
        )
        self.game_token = object()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.engine is not None:
            self.engine.quit()
        return False

    def new_game(self):
        self.game_token = object()

    def search(self, case, played_moves, clock_state=None):
        board = make_board(case)
        for move in played_moves:
            board.push(chess.Move.from_uci(move))
        if self.search_mode == "depth":
            limit = chess.engine.Limit(depth=self.search_value)
        elif self.search_mode == "movetime":
            limit = chess.engine.Limit(time=self.search_value / 1000.0)
        else:
            if clock_state is None:
                raise RuntimeError(f"{self.variant}: missing clock state for clock search mode")
            limit = chess.engine.Limit(
                white_clock=clock_state["white_ms"] / 1000.0,
                black_clock=clock_state["black_ms"] / 1000.0,
                white_inc=clock_state["white_inc_ms"] / 1000.0,
                black_inc=clock_state["black_inc_ms"] / 1000.0,
                remaining_moves=clock_state.get("side_moves_to_go"),
            )
        started = time.perf_counter()
        result = self.engine.play(
            board,
            limit,
            info=chess.engine.INFO_ALL,
            game=self.game_token,
        )
        wall_ms = (time.perf_counter() - started) * 1000.0
        info = result.info
        return {
            "bestmove": result.move.uci() if result.move is not None else "(none)",
            "lines": [],
            "wall_ms": wall_ms,
            "depth": info.get("depth"),
            "nodes": info.get("nodes"),
        }


def build_game_header(case, white_name, black_name, result, search_mode, search_value, max_plies, initial_fen, skill):
    headers = {
        "Event": "MiniCOBC vs Stockfish Tournament",
        "Site": str(ROOT),
        "White": white_name,
        "Black": black_name,
        "Result": result,
        "OpeningCase": case["label"],
        "SearchMode": search_mode,
        "SearchValue": str(search_value),
        "MaxPlies": str(max_plies),
        "StockfishSkill": str(skill),
    }
    if "fen" in case or case.get("moves"):
        headers["FEN"] = initial_fen
        headers["SetUp"] = "1"
    return headers


def initial_clock_state(search_mode, search_value):
    if search_mode != "clock":
        return None
    base_ms = search_value["base_ms"]
    increment_ms = search_value["increment_ms"]
    moves_to_go = search_value.get("moves_to_go")
    return {
        "white_ms": base_ms,
        "black_ms": base_ms,
        "white_inc_ms": increment_ms,
        "black_inc_ms": increment_ms,
        "white_moves_to_go": moves_to_go,
        "black_moves_to_go": moves_to_go,
    }


def side_clock_view(clock_state, is_white_turn):
    if clock_state is None:
        return None
    return {
        "white_ms": int(max(0, round(clock_state["white_ms"]))),
        "black_ms": int(max(0, round(clock_state["black_ms"]))),
        "white_inc_ms": int(max(0, round(clock_state["white_inc_ms"]))),
        "black_inc_ms": int(max(0, round(clock_state["black_inc_ms"]))),
        "side_moves_to_go": clock_state["white_moves_to_go"] if is_white_turn else clock_state["black_moves_to_go"],
    }


def update_clock_state(clock_state, is_white_turn, elapsed_ms):
    if clock_state is None:
        return
    if is_white_turn:
        clock_state["white_ms"] = max(0.0, clock_state["white_ms"] - elapsed_ms)
        clock_state["white_ms"] += clock_state["white_inc_ms"]
        if clock_state["white_moves_to_go"] is not None and clock_state["white_moves_to_go"] > 0:
            clock_state["white_moves_to_go"] -= 1
    else:
        clock_state["black_ms"] = max(0.0, clock_state["black_ms"] - elapsed_ms)
        clock_state["black_ms"] += clock_state["black_inc_ms"]
        if clock_state["black_moves_to_go"] is not None and clock_state["black_moves_to_go"] > 0:
            clock_state["black_moves_to_go"] -= 1


def numeric_score(outcome, white_variant, black_variant):
    score = {white_variant: 0.0, black_variant: 0.0}
    if outcome is None or outcome.winner is None:
        score[white_variant] = 0.5
        score[black_variant] = 0.5
        return score
    winner_variant = white_variant if outcome.winner == chess.WHITE else black_variant
    loser_variant = black_variant if outcome.winner == chess.WHITE else white_variant
    score[winner_variant] = 1.0
    score[loser_variant] = 0.0
    return score


def aggregate_variant_stats(games, variants):
    data = {}
    for variant in variants:
        data[variant] = {
            "score": 0.0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "illegal_moves": 0,
            "moves": 0,
            "wall_ms": [],
            "depth": [],
            "nodes": [],
        }

    for game in games:
        for variant in variants:
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
            loser = game["termination"].split("_", 1)[1]
            if loser in data:
                data[loser]["illegal_moves"] += 1

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


def illegal_result(side_engine_variant, white_variant, black_variant):
    result_text = "0-1" if side_engine_variant == white_variant else "1-0"
    scores = {
        white_variant: 0.0,
        black_variant: 0.0,
    }
    winner = black_variant if side_engine_variant == white_variant else white_variant
    scores[winner] = 1.0
    return result_text, scores


def play_tournament_game(case, game_index, white_engine, black_engine, search_mode, search_value, max_plies, skill):
    board = make_board(case)
    played_moves = []
    clock_state = initial_clock_state(search_mode, search_value)
    game = chess.pgn.Game()
    game.headers.update(
        build_game_header(
            case,
            white_engine.label,
            black_engine.label,
            "*",
            search_mode,
            search_value,
            max_plies,
            board.fen(),
            skill,
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
        is_white_turn = board.turn == chess.WHITE
        side_engine = white_engine if is_white_turn else black_engine
        result = side_engine.search(case, played_moves, side_clock_view(clock_state, is_white_turn))
        move_text = result["bestmove"]
        if move_text in {"0000", "(none)"}:
            outcome = board.outcome(claim_draw=True)
            termination = "engine_no_move"
            break
        try:
            move = chess.Move.from_uci(move_text)
        except ValueError:
            termination = f"illegal_{side_engine.variant}"
            result_text, scores = illegal_result(
                side_engine.variant, white_engine.variant, black_engine.variant
            )
            game.headers["Result"] = result_text
            game.headers["Termination"] = termination
            return {
                "game_index": game_index,
                "skill": skill,
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
                "illegal_move": move_text,
            }
        if not board.is_legal(move):
            termination = f"illegal_{side_engine.variant}"
            result_text, scores = illegal_result(
                side_engine.variant, white_engine.variant, black_engine.variant
            )
            game.headers["Result"] = result_text
            game.headers["Termination"] = termination
            return {
                "game_index": game_index,
                "skill": skill,
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
        update_clock_state(clock_state, is_white_turn, result["wall_ms"])

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
        "skill": skill,
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


def render_markdown(repo, commit, stockfish_binary, stockfish_banner, profile, search_mode, search_value, max_plies, mini_build_ms, skill_results):
    lines = []
    lines.append("# MiniCOBC vs Stockfish Tournament")
    lines.append("")
    lines.append("- Purpose: compare the `minicobc`-built chess engine against Stockfish across multiple `Skill Level` settings")
    lines.append("- Format: paired games from a diversified opening/FEN suite, colors swapped for each starting position")
    lines.append("- Equality signal: illegal moves are treated as immediate losses")
    if search_mode == "depth":
        lines.append("- Search mode: fixed depth per move for both engines")
    else:
        if search_mode == "movetime":
            lines.append("- Search mode: fixed movetime per move for both engines")
        else:
            lines.append("- Search mode: clocked game with increment/moves-to-go")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- Commit: `{commit}`")
    lines.append(f"- Stockfish: `{stockfish_banner}`")
    lines.append(f"- Stockfish binary: `{stockfish_binary}`")
    lines.append(f"- Profile: `{profile}`")
    if search_mode == "depth":
        lines.append(f"- Fixed depth per move: `{search_value}`")
    elif search_mode == "movetime":
        lines.append(f"- Fixed movetime per move: `{search_value} ms`")
    else:
        lines.append(f"- Base time per side: `{search_value['base_ms']} ms`")
        lines.append(f"- Increment per move: `{search_value['increment_ms']} ms`")
        if search_value.get("moves_to_go") is not None:
            lines.append(f"- Moves to go hint: `{search_value['moves_to_go']}`")
    lines.append(f"- Max plies per game: `{max_plies}`")
    lines.append(f"- `minicobc` build pipeline time: `{mini_build_ms:.2f} ms`")
    lines.append("")
    lines.append("## Skill Summary")
    lines.append("")
    lines.append("| Skill | Games | MiniCOBC score | Stockfish score | MiniCOBC W-D-L | Stockfish W-D-L | MiniCOBC avg ms/move | Stockfish avg ms/move |")
    lines.append("| ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |")
    for item in skill_results:
        mini = item["summary"]["minicobc"]
        stockfish_variant = item["stockfish_variant"]
        sf = item["summary"][stockfish_variant]
        lines.append(
            f"| {item['skill']} | {len(item['games'])} | {mini['score']:.1f} | {sf['score']:.1f} | "
            f"{mini['wins']}-{mini['draws']}-{mini['losses']} | "
            f"{sf['wins']}-{sf['draws']}-{sf['losses']} | "
            f"{mini['avg_wall_ms']:.2f} | {sf['avg_wall_ms']:.2f} |"
        )

    for item in skill_results:
        stockfish_variant = item["stockfish_variant"]
        mini = item["summary"]["minicobc"]
        sf = item["summary"][stockfish_variant]
        lines.append("")
        lines.append(f"## Skill {item['skill']}")
        lines.append("")
        lines.append("| Engine | Score | W-D-L | Illegal moves | Avg wall ms/move | Median wall ms/move | Avg depth | Avg nodes/move |")
        lines.append("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |")
        lines.append(
            f"| minicobc | {mini['score']:.1f} | {mini['wins']}-{mini['draws']}-{mini['losses']} | "
            f"{mini['illegal_moves']} | {mini['avg_wall_ms']:.2f} | {mini['median_wall_ms']:.2f} | "
            f"{mini['avg_depth']:.2f} | {mini['avg_nodes']:.0f} |"
        )
        lines.append(
            f"| {stockfish_variant} | {sf['score']:.1f} | {sf['wins']}-{sf['draws']}-{sf['losses']} | "
            f"{sf['illegal_moves']} | {sf['avg_wall_ms']:.2f} | {sf['median_wall_ms']:.2f} | "
            f"{sf['avg_depth']:.2f} | {sf['avg_nodes']:.0f} |"
        )
        lines.append("")
        lines.append("| # | Case | White | Black | Result | Termination | Plies |")
        lines.append("| ---: | --- | --- | --- | --- | --- | ---: |")
        for game in item["games"]:
            lines.append(
                f"| {game['game_index']} | {game['case_label']} | {game['white']} | {game['black']} | "
                f"{game['result']} | {game['termination']} | {game['plies']} |"
            )

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Run a MiniCOBC-vs-Stockfish chess tournament across multiple skill levels."
    )
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument("--stockfish")
    parser.add_argument(
        "--profile",
        choices=tuple(TOURNAMENT_PROFILES.keys()),
        default="default",
    )
    parser.add_argument("--search-mode", choices=("depth", "movetime", "clock"), default="depth")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--movetime-ms", type=int, default=50)
    parser.add_argument("--base-ms", type=int, default=120000)
    parser.add_argument("--increment-ms", type=int, default=1000)
    parser.add_argument("--moves-to-go", type=int)
    parser.add_argument("--max-plies", type=int, default=12)
    parser.add_argument("--skills", default="0,5,10,15,20")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"repo not found: {repo}", file=sys.stderr)
        return 2

    if args.search_mode == "depth":
        search_value = args.depth
    elif args.search_mode == "movetime":
        search_value = args.movetime_ms
    else:
        search_value = {
            "base_ms": args.base_ms,
            "increment_ms": args.increment_ms,
            "moves_to_go": args.moves_to_go,
        }

    try:
        skill_levels = parse_skill_levels(args.skills)
        stockfish_binary = detect_stockfish_binary(args.stockfish)
        stockfish_banner = detect_stockfish_banner(stockfish_binary)
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        mini_binary, mini_build_ms = build_minicobc_engine(repo)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    all_games = []
    skill_results = []
    game_index = 1

    try:
        for skill in skill_levels:
            stockfish_variant = f"stockfish-s{skill}"
            with StatelessUciEngine(
                mini_binary,
                "MiniCOBC",
                "minicobc",
                args.search_mode,
                search_value,
            ) as mini_engine, PersistentStockfishEngine(
                stockfish_binary,
                f"Stockfish skill {skill}",
                stockfish_variant,
                skill,
                args.search_mode,
                search_value,
            ) as stockfish_engine:
                games = []
                for opening_id in TOURNAMENT_PROFILES[args.profile]:
                    case = dict(OPENING_CASES[opening_id])
                    case["id"] = opening_id
                    for swap in (False, True):
                        if not swap:
                            white = mini_engine
                            black = stockfish_engine
                        else:
                            white = stockfish_engine
                            black = mini_engine
                        game = play_tournament_game(
                            case,
                            game_index,
                            white,
                            black,
                            args.search_mode,
                            search_value,
                            args.max_plies,
                            skill,
                        )
                        games.append(game)
                        all_games.append(game)
                        game_index += 1
                summary = aggregate_variant_stats(games, ["minicobc", stockfish_variant])
                skill_results.append(
                    {
                        "skill": skill,
                        "stockfish_variant": stockfish_variant,
                        "games": games,
                        "summary": summary,
                    }
                )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "repo": str(repo),
        "commit": commit,
        "stockfish_binary": str(stockfish_binary),
        "stockfish_banner": stockfish_banner,
        "profile": args.profile,
        "search_mode": args.search_mode,
        "search_value": search_value,
        "max_plies": args.max_plies,
        "skills": skill_levels,
        "minicobc_build_ms": mini_build_ms,
        "results": skill_results,
        "games": all_games,
    }

    out_dir = ROOT / "build" / "perf"
    out_dir.mkdir(parents=True, exist_ok=True)
    skills_slug = "-".join(str(skill) for skill in skill_levels)
    if args.search_mode == "depth":
        mode_slug = f"d{args.depth}"
    elif args.search_mode == "movetime":
        mode_slug = f"mt{args.movetime_ms}"
    else:
        mode_slug = f"tc{args.base_ms}+{args.increment_ms}"
        if args.moves_to_go is not None:
            mode_slug += f"-m{args.moves_to_go}"
    run_id = f"{args.profile}-{mode_slug}-p{args.max_plies}-s{skills_slug}"
    json_path = out_dir / f"chess-stockfish-tournament-{run_id}.json"
    md_path = out_dir / f"chess-stockfish-tournament-{run_id}.md"
    pgn_path = out_dir / f"chess-stockfish-tournament-{run_id}.pgn"
    latest_json_path = out_dir / "chess-stockfish-tournament.json"
    latest_md_path = out_dir / "chess-stockfish-tournament.md"
    latest_pgn_path = out_dir / "chess-stockfish-tournament.pgn"

    markdown = render_markdown(
        repo,
        commit,
        stockfish_binary,
        stockfish_banner,
        args.profile,
        args.search_mode,
        search_value,
        args.max_plies,
        mini_build_ms,
        skill_results,
    )
    pgn_text = "\n\n".join(game["pgn"] for game in all_games) + "\n"

    json_text = json.dumps(payload, indent=2) + "\n"
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    pgn_path.write_text(pgn_text, encoding="utf-8")
    latest_json_path.write_text(json_text, encoding="utf-8")
    latest_md_path.write_text(markdown, encoding="utf-8")
    latest_pgn_path.write_text(pgn_text, encoding="utf-8")

    print(markdown, end="")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"wrote {pgn_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
