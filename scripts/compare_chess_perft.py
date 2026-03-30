#!/usr/bin/env python3
import argparse
import json
import shlex
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = ROOT / "external" / "agentic-chessengine-cobol-codex"
PERFT_CASES = DEFAULT_REPO / "tests" / "perft_cases.json"

PROFILE_DEPTHS = {
    "fast": {
        "startpos": 3,
        "kiwipete": 2,
        "ep_illegal_exposes_king": 3,
        "promotions_and_capture_promotions": 3,
    },
    "default": {
        "startpos": 4,
        "kiwipete": 3,
        "ep_illegal_exposes_king": 3,
        "promotions_and_capture_promotions": 3,
    },
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


def cmd_string(cmd):
    return " ".join(shlex.quote(part) for part in cmd)


def median(values):
    return statistics.median(values) if values else 0.0


def ensure_dirs():
    for rel in (
        "build/perf/chess-perft/minicobc",
        "build/perf/chess-perft/gnucobol",
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def load_cases(repo, profile):
    manifest_path = repo / "tests" / "perft_cases.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    cases = []
    for item in manifest["cases"]:
        if profile == "full":
            depth = max(int(key) for key in item["depths"])
        else:
            depth = PROFILE_DEPTHS[profile][item["name"]]
        expected_nodes = item["depths"][str(depth)]
        case = {
            "id": f"{item['name']}/d{depth}",
            "name": item["name"],
            "fen": item["fen"],
            "depth": depth,
            "expected_nodes": expected_nodes,
        }
        if item["name"] == "startpos":
            case["args"] = ["--perft-startpos", str(depth)]
        else:
            case["args"] = ["--perft", item["fen"], str(depth)]
        cases.append(case)
    return cases


def build_minicobc_engine(repo):
    out_dir = ROOT / "build" / "perf" / "chess-perft" / "minicobc"
    cmd = [
        str(ROOT / "scripts" / "build-chess-engine.sh"),
        str(repo),
        str(out_dir),
    ]
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to build chess engine with minicobc\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return out_dir / "cobochess", elapsed_ms


def build_gnucobol_engine(repo):
    cmd = ["make", "-C", str(repo), "clean", "build"]
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to build chess engine with gnucobol\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    source_binary = repo / "bin" / "cobochess"
    target_binary = ROOT / "build" / "perf" / "chess-perft" / "gnucobol" / "cobochess"
    shutil.copy2(source_binary, target_binary)
    return target_binary, elapsed_ms


def run_perft(binary, case):
    cmd = [str(binary), *case["args"]]
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "perft run failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    stdout = completed.stdout.strip()
    expected_stdout = f"nodes={case['expected_nodes']}"
    if stdout != expected_stdout:
        raise RuntimeError(
            "unexpected perft output\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(cmd)}\n"
            f"got: {stdout}\n"
            f"expected: {expected_stdout}"
        )
    return stdout, elapsed_ms


def benchmark_case(case, minicobc_binary, gnucobol_binary, iterations, warmups):
    for _ in range(warmups):
        run_perft(minicobc_binary, case)
        run_perft(gnucobol_binary, case)

    minicobc_times = []
    gnucobol_times = []
    baseline_stdout = None
    for _ in range(iterations):
        mini_stdout, mini_ms = run_perft(minicobc_binary, case)
        gc_stdout, gc_ms = run_perft(gnucobol_binary, case)
        if mini_stdout != gc_stdout:
            raise RuntimeError(
                "runtime output mismatch during chess perft comparison\n"
                f"case: {case['id']}"
            )
        baseline_stdout = mini_stdout
        minicobc_times.append(mini_ms)
        gnucobol_times.append(gc_ms)

    mini_median = median(minicobc_times)
    gc_median = median(gnucobol_times)
    nodes = case["expected_nodes"]
    return {
        "id": case["id"],
        "name": case["name"],
        "depth": case["depth"],
        "args": case["args"],
        "expected_nodes": nodes,
        "status": "compared",
        "iterations": iterations,
        "warmups": warmups,
        "minicobc_median_ms": mini_median,
        "gnucobol_median_ms": gc_median,
        "runtime_ratio_vs_gnucobol": (
            mini_median / gc_median if gc_median else None
        ),
        "minicobc_nodes_per_sec": (
            nodes / (mini_median / 1000.0) if mini_median else None
        ),
        "gnucobol_nodes_per_sec": (
            nodes / (gc_median / 1000.0) if gc_median else None
        ),
        "output": baseline_stdout,
    }


def render_report(
    repo,
    repo_commit,
    profile,
    iterations,
    warmups,
    minicobc_build_ms,
    gnucobol_build_ms,
    results,
):
    total_nodes = sum(item["expected_nodes"] for item in results)
    total_minicobc_ms = sum(item["minicobc_median_ms"] for item in results)
    total_gnucobol_ms = sum(item["gnucobol_median_ms"] for item in results)

    lines = []
    lines.append("# Chess Engine Perft Comparison")
    lines.append("")
    lines.append("- Metric: median wall-clock runtime across repeated local runs")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- Commit: `{repo_commit}`")
    lines.append(f"- Profile: `{profile}`")
    lines.append(f"- Warmups per case: `{warmups}`")
    lines.append(f"- Timed iterations per case: `{iterations}`")
    lines.append(
        f"- `minicobc` build pipeline time: `{minicobc_build_ms:.2f} ms`"
    )
    lines.append(
        f"- GnuCOBOL build pipeline time: `{gnucobol_build_ms:.2f} ms`"
    )
    lines.append("")
    lines.append(
        "Build times are informational only. The runtime comparison below is the "
        "apples-to-apples perft measure."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(
        "| Case | Nodes | Mini ms | GNU ms | Ratio | Mini nodes/s | GNU nodes/s |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for item in results:
        lines.append(
            f"| {item['id']} | "
            f"{item['expected_nodes']} | "
            f"{item['minicobc_median_ms']:.2f} | "
            f"{item['gnucobol_median_ms']:.2f} | "
            f"{item['runtime_ratio_vs_gnucobol']:.2f}x | "
            f"{item['minicobc_nodes_per_sec']:.0f} | "
            f"{item['gnucobol_nodes_per_sec']:.0f} |"
        )
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Total benchmark nodes: `{total_nodes}`")
    lines.append(
        f"- Sum of median runtimes: `minicobc {total_minicobc_ms:.2f} ms`, "
        f"`gnucobol {total_gnucobol_ms:.2f} ms`"
    )
    if total_gnucobol_ms:
        lines.append(
            f"- Aggregate runtime ratio: `{(total_minicobc_ms / total_gnucobol_ms):.2f}x`"
        )
        lines.append(
            f"- Aggregate nodes/sec: `minicobc {(total_nodes / (total_minicobc_ms / 1000.0)):.0f}`, "
            f"`gnucobol {(total_nodes / (total_gnucobol_ms / 1000.0)):.0f}`"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Compare chess-engine perft performance for minicobc vs GnuCOBOL."
    )
    parser.add_argument(
        "--repo",
        default=str(DEFAULT_REPO),
        help="path to the chess engine repository checkout",
    )
    parser.add_argument(
        "--profile",
        choices=("fast", "default", "full"),
        default="default",
        help="which perft workload profile to run",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="number of timed iterations per case",
    )
    parser.add_argument(
        "--warmups",
        type=int,
        default=1,
        help="number of warmup iterations per case",
    )
    args = parser.parse_args()

    repo = Path(args.repo)
    if not repo.exists():
        print(f"repo not found: {repo}", file=sys.stderr)
        return 2

    ensure_dirs()

    try:
        repo_commit_cp, _ = run_command(
            ["git", "-C", str(repo), "rev-parse", "HEAD"]
        )
        repo_commit = repo_commit_cp.stdout.strip()

        minicobc_binary, minicobc_build_ms = build_minicobc_engine(repo)
        gnucobol_binary, gnucobol_build_ms = build_gnucobol_engine(repo)

        cases = load_cases(repo, args.profile)
        results = []
        for case in cases:
            results.append(
                benchmark_case(
                    case,
                    minicobc_binary,
                    gnucobol_binary,
                    args.iterations,
                    args.warmups,
                )
            )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report = render_report(
        repo,
        repo_commit,
        args.profile,
        args.iterations,
        args.warmups,
        minicobc_build_ms,
        gnucobol_build_ms,
        results,
    )
    payload = {
        "repo": str(repo),
        "commit": repo_commit,
        "profile": args.profile,
        "iterations": args.iterations,
        "warmups": args.warmups,
        "minicobc_build_ms": minicobc_build_ms,
        "gnucobol_build_ms": gnucobol_build_ms,
        "results": results,
    }

    out_dir = ROOT / "build" / "perf"
    (out_dir / "chess-perft-compare.md").write_text(report, encoding="utf-8")
    (out_dir / "chess-perft-compare.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(report, end="")
    print(f"wrote {out_dir / 'chess-perft-compare.json'}")
    print(f"wrote {out_dir / 'chess-perft-compare.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
