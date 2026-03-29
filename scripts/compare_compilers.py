#!/usr/bin/env python3
import argparse
import json
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "benchmark" / "cases.json"
DEFAULT_COMPAT_REPO = ROOT / "external" / "agentic-cobol-game15tictactoe"


def run_command(cmd, *, stdin_text=None, cwd=ROOT):
    started = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return completed, elapsed_ms


def cmd_string(cmd):
    return " ".join(shlex.quote(part) for part in cmd)


def ensure_dirs():
    for rel in (
        "build/bin",
        "build/perf/minicobc/generated",
        "build/perf/minicobc/bin",
        "build/perf/gnucobol/bin",
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def load_cases(suite, compat_repo):
    with MANIFEST.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    cases = []
    for suite_name in ("core", "compat"):
        if suite != "all" and suite != suite_name:
            continue
        for case in manifest[suite_name]:
            expanded = dict(case)
            expanded["suite"] = suite_name
            expanded["source"] = expanded["source"].format(
                compat_repo=str(compat_repo)
            )
            cases.append(expanded)
    return cases


def build_minicobc():
    binary = ROOT / "build" / "bin" / "minicobc"
    cmd = [
        "cobc",
        "-x",
        "-free",
        "-Wall",
        "src/minicobc.cob",
        "-o",
        str(binary),
    ]
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to build minicobc\n"
            f"command: {cmd_string(cmd)}\n"
            f"stderr:\n{completed.stderr}"
        )
    return binary, elapsed_ms


def build_with_minicobc(case, minicobc_binary):
    generated_c = ROOT / "build" / "perf" / "minicobc" / "generated" / (
        case["id"].replace("/", "__") + ".c"
    )
    binary = ROOT / "build" / "perf" / "minicobc" / "bin" / (
        case["id"].replace("/", "__")
    )

    if generated_c.exists():
        generated_c.unlink()
    if binary.exists():
        binary.unlink()

    translate_cmd = [str(minicobc_binary), case["source"], str(generated_c)]
    translate_cp, translate_ms = run_command(translate_cmd)
    if translate_cp.returncode != 0:
        raise RuntimeError(
            "minicobc translation failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(translate_cmd)}\n"
            f"stdout:\n{translate_cp.stdout}\n"
            f"stderr:\n{translate_cp.stderr}"
        )

    gcc_cmd = ["gcc", "-std=c11", str(generated_c), "-o", str(binary)]
    gcc_cp, gcc_ms = run_command(gcc_cmd)
    if gcc_cp.returncode != 0:
        raise RuntimeError(
            "gcc build failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(gcc_cmd)}\n"
            f"stdout:\n{gcc_cp.stdout}\n"
            f"stderr:\n{gcc_cp.stderr}"
        )

    return binary, generated_c, translate_ms, gcc_ms


def build_with_gnucobol(case):
    binary = ROOT / "build" / "perf" / "gnucobol" / "bin" / (
        case["id"].replace("/", "__")
    )
    if binary.exists():
        binary.unlink()

    cmd = ["cobc", "-x"]
    if case["suite"] == "core":
        cmd.append("-free")
    cmd.extend([case["source"], "-o", str(binary)])
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "gnucobol build failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return binary, elapsed_ms


def run_binary(binary, case):
    cmd = [str(binary), *case["args"]]
    completed, elapsed_ms = run_command(cmd, stdin_text=case["stdin"])
    if completed.returncode != 0:
        raise RuntimeError(
            "binary run failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout, elapsed_ms


def median(values):
    return statistics.median(values) if values else 0.0


def compare_case(case, minicobc_binary, compile_iterations, run_iterations):
    mini_translate = []
    mini_gcc = []
    mini_total = []
    gc_compile = []
    output_baseline = None

    last_mini_binary = None
    last_gc_binary = None
    last_generated_c = None

    try:
        for _ in range(compile_iterations):
            mini_binary, generated_c, translate_ms, gcc_ms = build_with_minicobc(
                case, minicobc_binary
            )
            gc_binary, gc_ms = build_with_gnucobol(case)

            mini_translate.append(translate_ms)
            mini_gcc.append(gcc_ms)
            mini_total.append(translate_ms + gcc_ms)
            gc_compile.append(gc_ms)

            last_mini_binary = mini_binary
            last_gc_binary = gc_binary
            last_generated_c = generated_c
    except RuntimeError as exc:
        return {
            "id": case["id"],
            "suite": case["suite"],
            "source": case["source"],
            "args": case["args"],
            "status": "unsupported_by_gnucobol",
            "reason": str(exc),
        }

    mini_runs = []
    gc_runs = []
    for _ in range(run_iterations):
        mini_stdout, mini_run_ms = run_binary(last_mini_binary, case)
        gc_stdout, gc_run_ms = run_binary(last_gc_binary, case)
        if mini_stdout != gc_stdout:
            raise RuntimeError(
                "runtime output mismatch during compiler comparison\n"
                f"case: {case['id']}"
            )
        output_baseline = mini_stdout
        mini_runs.append(mini_run_ms)
        gc_runs.append(gc_run_ms)

    return {
        "id": case["id"],
        "suite": case["suite"],
        "source": case["source"],
        "args": case["args"],
        "status": "compared",
        "compile_iterations": compile_iterations,
        "run_iterations": run_iterations,
        "minicobc_translate_median_ms": median(mini_translate),
        "minicobc_gcc_median_ms": median(mini_gcc),
        "minicobc_end_to_end_median_ms": median(mini_total),
        "gnucobol_compile_median_ms": median(gc_compile),
        "minicobc_run_median_ms": median(mini_runs),
        "gnucobol_run_median_ms": median(gc_runs),
        "compile_ratio_vs_gnucobol": (
            median(mini_total) / median(gc_compile) if median(gc_compile) else None
        ),
        "runtime_ratio_vs_gnucobol": (
            median(mini_runs) / median(gc_runs) if median(gc_runs) else None
        ),
        "generated_c_lines": sum(1 for _ in last_generated_c.open("r", encoding="utf-8")),
        "generated_c_bytes": last_generated_c.stat().st_size,
        "minicobc_binary_bytes": last_mini_binary.stat().st_size,
        "gnucobol_binary_bytes": last_gc_binary.stat().st_size,
        "output_bytes": len(output_baseline.encode("utf-8")),
    }


def render_report(results, minicobc_build_ms, compat_repo, compile_iterations, run_iterations):
    lines = []
    lines.append("# Compiler Performance Comparison")
    lines.append("")
    lines.append(
        "- Metric: median wall-clock time across repeated local runs"
    )
    lines.append(f"- `minicobc` build time: `{minicobc_build_ms:.2f} ms`")
    lines.append(f"- Compile iterations per case: `{compile_iterations}`")
    lines.append(f"- Runtime iterations per case: `{run_iterations}`")
    lines.append(f"- Compatibility repo: `{compat_repo}`")
    lines.append("")
    lines.append(
        "Compatibility cases measure the targeted template path in `minicobc`, "
        "so only the core suite represents the generic subset compiler."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(
        "| Case | Suite | Mini translate ms | Mini gcc ms | Mini total ms | "
        "cobc ms | Compile ratio | Mini run ms | cobc run ms | Runtime ratio |"
    )
    lines.append(
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for item in results:
        if item["status"] != "compared":
            lines.append(
                f"| {item['id']} | {item['suite']} | - | - | - | - | - | - | - | - |"
            )
            continue
        lines.append(
            f"| {item['id']} | {item['suite']} | "
            f"{item['minicobc_translate_median_ms']:.2f} | "
            f"{item['minicobc_gcc_median_ms']:.2f} | "
            f"{item['minicobc_end_to_end_median_ms']:.2f} | "
            f"{item['gnucobol_compile_median_ms']:.2f} | "
            f"{item['compile_ratio_vs_gnucobol']:.2f}x | "
            f"{item['minicobc_run_median_ms']:.2f} | "
            f"{item['gnucobol_run_median_ms']:.2f} | "
            f"{item['runtime_ratio_vs_gnucobol']:.2f}x |"
        )
    unsupported = [item for item in results if item["status"] != "compared"]
    if unsupported:
        lines.append("")
        lines.append("## Unsupported Cases")
        lines.append("")
        for item in unsupported:
            lines.append(f"- `{item['id']}`: {item['status']}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Compare MiniCOBC performance against GnuCOBOL."
    )
    parser.add_argument(
        "--suite",
        choices=("all", "core", "compat"),
        default="all",
        help="which suite to compare",
    )
    parser.add_argument(
        "--compile-iterations",
        type=int,
        default=5,
        help="number of repeated compile measurements per case",
    )
    parser.add_argument(
        "--run-iterations",
        type=int,
        default=7,
        help="number of repeated runtime measurements per case",
    )
    parser.add_argument(
        "--compat-repo",
        default=str(DEFAULT_COMPAT_REPO),
        help="path to the compatibility repository checkout",
    )
    args = parser.parse_args()

    compat_repo = Path(args.compat_repo)
    if args.suite in ("all", "compat") and not compat_repo.exists():
        print(f"compatibility repo not found: {compat_repo}", file=sys.stderr)
        return 2

    ensure_dirs()
    cases = load_cases(args.suite, compat_repo)
    minicobc_binary, minicobc_build_ms = build_minicobc()

    results = []
    for case in cases:
        results.append(
            compare_case(
                case,
                minicobc_binary,
                args.compile_iterations,
                args.run_iterations,
            )
        )

    report = render_report(
        results,
        minicobc_build_ms,
        compat_repo,
        args.compile_iterations,
        args.run_iterations,
    )
    output = {
        "minicobc_build_ms": minicobc_build_ms,
        "compile_iterations": args.compile_iterations,
        "run_iterations": args.run_iterations,
        "results": results,
    }

    out_dir = ROOT / "build" / "perf"
    (out_dir / "compiler-compare.json").write_text(
        json.dumps(output, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "compiler-compare.md").write_text(report, encoding="utf-8")

    print(report, end="")
    print(f"wrote {out_dir / 'compiler-compare.json'}")
    print(f"wrote {out_dir / 'compiler-compare.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
