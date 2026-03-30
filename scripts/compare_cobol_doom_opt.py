#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import select
import statistics
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = ROOT / "external" / "agentic-cobol-doom"
DEFAULT_OUT = ROOT / "build" / "perf"


def run_build(repo: Path, out_dir: Path, opt: bool) -> dict[str, object]:
    env = os.environ.copy()
    env["MINICOBC_OPT"] = "1" if opt else "0"
    build_cmd = [
        "bash",
        "./scripts/build-cobol-doom.sh",
        str(repo),
        str(out_dir),
    ]
    start = time.perf_counter()
    subprocess.run(
        build_cmd,
        cwd=ROOT,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    binary = out_dir / "cobol-doom"
    return {
        "build_ms": elapsed_ms,
        "binary_size": binary.stat().st_size,
        "binary": str(binary),
    }


def measure_startup(binary: Path, warmups: int, iterations: int) -> dict[str, object]:
    first_output_samples: list[float] = []
    stdout_samples: list[int] = []
    stderr_samples: list[int] = []
    statuses: list[str] = []

    for sample_index in range(warmups + iterations):
        started = time.perf_counter()
        proc = subprocess.Popen(
            [str(binary)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        first_output_ms: float | None = None
        stdout_collected = bytearray()
        stderr_collected = bytearray()

        try:
            deadline = time.perf_counter() + 0.25
            while time.perf_counter() < deadline:
                ready, _, _ = select.select(
                    [stream for stream in (proc.stdout, proc.stderr) if stream is not None],
                    [],
                    [],
                    0.005,
                )
                for stream in ready:
                    if stream is proc.stdout:
                        chunk = os.read(stream.fileno(), 4096)
                        if chunk and first_output_ms is None:
                            first_output_ms = (time.perf_counter() - started) * 1000.0
                        if chunk:
                            stdout_collected.extend(chunk)
                    elif stream is proc.stderr:
                        err_chunk = os.read(stream.fileno(), 4096)
                        if err_chunk:
                            stderr_collected.extend(err_chunk)
                if proc.poll() is not None:
                    break
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                out_tail, err_tail = proc.communicate(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                out_tail, err_tail = proc.communicate()

        stdout_collected.extend(out_tail)
        stderr_collected.extend(err_tail)
        if first_output_ms is None and stdout_collected:
            first_output_ms = (time.perf_counter() - started) * 1000.0

        status = f"alive={int(proc.returncode in (-15, -9) or proc.returncode is None)} rc={proc.returncode}"
        statuses.append(status)
        if sample_index >= warmups:
            first_output_samples.append(first_output_ms or 250.0)
            stdout_samples.append(len(stdout_collected))
            stderr_samples.append(len(stderr_collected))

    return {
        "startup_first_output_ms": statistics.median(first_output_samples),
        "startup_stdout_bytes": statistics.median(stdout_samples),
        "startup_stderr_bytes": statistics.median(stderr_samples),
        "statuses": statuses,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    perf_dir = Path(args.out_dir).resolve()
    perf_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, object] = {
        "repo": str(repo),
        "iterations": args.iterations,
        "warmups": args.warmups,
        "modes": {},
    }

    for mode_name, opt_flag in (("baseline", False), ("opt", True)):
        mode_dir = ROOT / "build" / "doom" / mode_name
        mode_dir.mkdir(parents=True, exist_ok=True)
        build_samples: list[float] = []
        binary_size = 0
        binary_path = mode_dir / "cobol-doom"

        for _ in range(args.warmups + args.iterations):
            build_info = run_build(repo, mode_dir, opt_flag)
            binary_size = int(build_info["binary_size"])
            build_samples.append(float(build_info["build_ms"]))
        build_median = statistics.median(build_samples[args.warmups :])
        startup_info = measure_startup(binary_path, args.warmups, args.iterations)
        results["modes"][mode_name] = {
            "build_ms": build_median,
            "binary_size": binary_size,
            **startup_info,
        }

    baseline = results["modes"]["baseline"]
    opt = results["modes"]["opt"]
    results["ratios"] = {
        "build_ms": opt["build_ms"] / baseline["build_ms"],
        "startup_first_output_ms": (
            opt["startup_first_output_ms"] / baseline["startup_first_output_ms"]
        ),
    }

    json_path = perf_dir / "cobol-doom-opt-compare.json"
    md_path = perf_dir / "cobol-doom-opt-compare.md"
    json_path.write_text(json.dumps(results, indent=2) + "\n")
    md_path.write_text(
        "\n".join(
            [
                "# COBOL DOOM OPT Comparison",
                "",
                f"- repo: `{repo}`",
                f"- iterations: `{args.iterations}`",
                f"- warmups: `{args.warmups}`",
                "",
                "## Baseline",
                f"- build ms: `{baseline['build_ms']:.2f}`",
                f"- startup first output ms: `{baseline['startup_first_output_ms']:.2f}`",
                f"- startup stdout bytes: `{int(baseline['startup_stdout_bytes'])}`",
                f"- startup stderr bytes: `{int(baseline['startup_stderr_bytes'])}`",
                f"- binary size: `{baseline['binary_size']}`",
                "",
                "## OPT",
                f"- build ms: `{opt['build_ms']:.2f}`",
                f"- startup first output ms: `{opt['startup_first_output_ms']:.2f}`",
                f"- startup stdout bytes: `{int(opt['startup_stdout_bytes'])}`",
                f"- startup stderr bytes: `{int(opt['startup_stderr_bytes'])}`",
                f"- binary size: `{opt['binary_size']}`",
                "",
                "## Ratios",
                f"- build ms ratio: `{results['ratios']['build_ms']:.3f}x`",
                f"- startup first output ratio: `{results['ratios']['startup_first_output_ms']:.3f}x`",
                "",
            ]
        )
        + "\n"
    )

    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
