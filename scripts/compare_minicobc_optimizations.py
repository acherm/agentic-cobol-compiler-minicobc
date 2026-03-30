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


def median(values):
    return statistics.median(values) if values else 0.0


def format_ms(value):
    return f"{value:.2f}"


def format_ratio(value):
    return "-" if value is None else f"{value:.2f}x"


def ensure_dirs():
    for rel in (
        "build/bin",
        "build/perf/optcompare/base/generated",
        "build/perf/optcompare/base/bin",
        "build/perf/optcompare/opt/generated",
        "build/perf/optcompare/opt/bin",
        "build/perf/optcompare/gnucobol/bin",
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def load_cases(suite):
    with MANIFEST.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    suite_names = []
    if suite == "all":
        suite_names = ["core", "opt"]
    else:
        suite_names = [suite]

    cases = []
    for suite_name in suite_names:
        for case in manifest.get(suite_name, []):
            expanded = dict(case)
            expanded["suite"] = suite_name
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


def build_with_minicobc(case, minicobc_binary, opt_mode):
    variant = "opt" if opt_mode else "base"
    generated_c = ROOT / "build" / "perf" / "optcompare" / variant / "generated" / (
        case["id"].replace("/", "__") + ".c"
    )
    binary = ROOT / "build" / "perf" / "optcompare" / variant / "bin" / (
        case["id"].replace("/", "__")
    )

    if generated_c.exists():
        generated_c.unlink()
    if binary.exists():
        binary.unlink()

    translate_cmd = [str(minicobc_binary)]
    if opt_mode:
        translate_cmd.append("OPT")
    translate_cmd.extend([case["source"], str(generated_c)])
    translate_cp, translate_ms = run_command(translate_cmd)
    if translate_cp.returncode != 0:
        raise RuntimeError(
            "minicobc translation failed\n"
            f"variant: {variant}\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(translate_cmd)}\n"
            f"stdout:\n{translate_cp.stdout}\n"
            f"stderr:\n{translate_cp.stderr}"
        )

    gcc_cmd = ["gcc", "-std=c11", "-O0", str(generated_c), "-o", str(binary)]
    gcc_cp, gcc_ms = run_command(gcc_cmd)
    if gcc_cp.returncode != 0:
        raise RuntimeError(
            "gcc build failed\n"
            f"variant: {variant}\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(gcc_cmd)}\n"
            f"stdout:\n{gcc_cp.stdout}\n"
            f"stderr:\n{gcc_cp.stderr}"
        )

    return binary, generated_c, translate_ms, gcc_ms


def build_with_gnucobol(case):
    binary = ROOT / "build" / "perf" / "optcompare" / "gnucobol" / "bin" / (
        case["id"].replace("/", "__")
    )
    if binary.exists():
        binary.unlink()

    cmd = ["cobc", "-x", "-A", "-O2"]
    if case.get("free_form", False):
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


def expected_stdout(case):
    oracle = case["oracle"]
    if oracle["type"] != "file":
        raise RuntimeError(
            f"three-way comparison only supports file-backed oracles: {case['id']}"
        )
    return (ROOT / oracle["path"]).read_text(encoding="utf-8")


def compare_case(case, minicobc_binary, compile_iterations, run_iterations):
    base_translate = []
    base_gcc = []
    base_total = []
    opt_translate = []
    opt_gcc = []
    opt_total = []
    gc_compile = []

    last_base_binary = None
    last_opt_binary = None
    last_gc_binary = None
    last_base_generated_c = None
    last_opt_generated_c = None

    try:
        for _ in range(compile_iterations):
            (
                base_binary,
                base_generated_c,
                base_translate_ms,
                base_gcc_ms,
            ) = build_with_minicobc(case, minicobc_binary, opt_mode=False)
            (
                opt_binary,
                opt_generated_c,
                opt_translate_ms,
                opt_gcc_ms,
            ) = build_with_minicobc(case, minicobc_binary, opt_mode=True)
            gc_binary, gc_ms = build_with_gnucobol(case)

            base_translate.append(base_translate_ms)
            base_gcc.append(base_gcc_ms)
            base_total.append(base_translate_ms + base_gcc_ms)
            opt_translate.append(opt_translate_ms)
            opt_gcc.append(opt_gcc_ms)
            opt_total.append(opt_translate_ms + opt_gcc_ms)
            gc_compile.append(gc_ms)

            last_base_binary = base_binary
            last_opt_binary = opt_binary
            last_gc_binary = gc_binary
            last_base_generated_c = base_generated_c
            last_opt_generated_c = opt_generated_c
    except RuntimeError as exc:
        return {
            "id": case["id"],
            "suite": case["suite"],
            "source": case["source"],
            "args": case["args"],
            "status": "build_failed",
            "reason": str(exc),
        }

    expected = expected_stdout(case)
    base_runs = []
    opt_runs = []
    gc_runs = []
    try:
        for _ in range(run_iterations):
            base_stdout, base_run_ms = run_binary(last_base_binary, case)
            opt_stdout, opt_run_ms = run_binary(last_opt_binary, case)
            gc_stdout, gc_run_ms = run_binary(last_gc_binary, case)

            if base_stdout != expected:
                raise RuntimeError("baseline minicobc output mismatch")
            if opt_stdout != expected:
                raise RuntimeError("optimized minicobc output mismatch")
            if gc_stdout != expected:
                raise RuntimeError("gnucobol output mismatch")
            if base_stdout != opt_stdout or base_stdout != gc_stdout:
                raise RuntimeError("variant output mismatch")

            base_runs.append(base_run_ms)
            opt_runs.append(opt_run_ms)
            gc_runs.append(gc_run_ms)
    except RuntimeError as exc:
        return {
            "id": case["id"],
            "suite": case["suite"],
            "source": case["source"],
            "args": case["args"],
            "status": "runtime_failed",
            "reason": str(exc),
        }

    base_compile_ms = median(base_total)
    opt_compile_ms = median(opt_total)
    gc_compile_ms = median(gc_compile)
    base_run_ms = median(base_runs)
    opt_run_ms = median(opt_runs)
    gc_run_ms = median(gc_runs)

    return {
        "id": case["id"],
        "suite": case["suite"],
        "source": case["source"],
        "args": case["args"],
        "status": "compared",
        "compile_iterations": compile_iterations,
        "run_iterations": run_iterations,
        "baseline_translate_median_ms": median(base_translate),
        "baseline_gcc_median_ms": median(base_gcc),
        "baseline_compile_median_ms": base_compile_ms,
        "optimized_translate_median_ms": median(opt_translate),
        "optimized_gcc_median_ms": median(opt_gcc),
        "optimized_compile_median_ms": opt_compile_ms,
        "gnucobol_compile_median_ms": gc_compile_ms,
        "baseline_run_median_ms": base_run_ms,
        "optimized_run_median_ms": opt_run_ms,
        "gnucobol_run_median_ms": gc_run_ms,
        "optimized_compile_ratio_vs_baseline": (
            opt_compile_ms / base_compile_ms if base_compile_ms else None
        ),
        "optimized_runtime_ratio_vs_baseline": (
            opt_run_ms / base_run_ms if base_run_ms else None
        ),
        "gnucobol_compile_ratio_vs_baseline": (
            gc_compile_ms / base_compile_ms if base_compile_ms else None
        ),
        "gnucobol_runtime_ratio_vs_baseline": (
            gc_run_ms / base_run_ms if base_run_ms else None
        ),
        "baseline_generated_c_lines": sum(
            1 for _ in last_base_generated_c.open("r", encoding="utf-8")
        ),
        "optimized_generated_c_lines": sum(
            1 for _ in last_opt_generated_c.open("r", encoding="utf-8")
        ),
        "baseline_generated_c_bytes": last_base_generated_c.stat().st_size,
        "optimized_generated_c_bytes": last_opt_generated_c.stat().st_size,
        "baseline_binary_bytes": last_base_binary.stat().st_size,
        "optimized_binary_bytes": last_opt_binary.stat().st_size,
        "gnucobol_binary_bytes": last_gc_binary.stat().st_size,
    }


def suite_summary(results, suite_name):
    suite_items = [item for item in results if item["suite"] == suite_name]
    compared = [item for item in suite_items if item["status"] == "compared"]
    if not compared:
        return {
            "total_cases": len(suite_items),
            "compared_cases": 0,
            "failed_cases": len(suite_items),
        }

    baseline_compile = sum(item["baseline_compile_median_ms"] for item in compared)
    optimized_compile = sum(item["optimized_compile_median_ms"] for item in compared)
    gnucobol_compile = sum(item["gnucobol_compile_median_ms"] for item in compared)
    baseline_run = sum(item["baseline_run_median_ms"] for item in compared)
    optimized_run = sum(item["optimized_run_median_ms"] for item in compared)
    gnucobol_run = sum(item["gnucobol_run_median_ms"] for item in compared)

    return {
        "total_cases": len(suite_items),
        "compared_cases": len(compared),
        "failed_cases": len(suite_items) - len(compared),
        "baseline_compile_sum_ms": baseline_compile,
        "optimized_compile_sum_ms": optimized_compile,
        "gnucobol_compile_sum_ms": gnucobol_compile,
        "baseline_run_sum_ms": baseline_run,
        "optimized_run_sum_ms": optimized_run,
        "gnucobol_run_sum_ms": gnucobol_run,
        "optimized_compile_ratio_vs_baseline": (
            optimized_compile / baseline_compile if baseline_compile else None
        ),
        "optimized_runtime_ratio_vs_baseline": (
            optimized_run / baseline_run if baseline_run else None
        ),
        "gnucobol_compile_ratio_vs_baseline": (
            gnucobol_compile / baseline_compile if baseline_compile else None
        ),
        "gnucobol_runtime_ratio_vs_baseline": (
            gnucobol_run / baseline_run if baseline_run else None
        ),
    }


def overall_summary(results):
    suites = sorted({item["suite"] for item in results})
    by_suite = {suite: suite_summary(results, suite) for suite in suites}
    compared = [item for item in results if item["status"] == "compared"]
    if not compared:
        return {
            "total_cases": len(results),
            "compared_cases": 0,
            "failed_cases": len(results),
            "by_suite": by_suite,
        }

    baseline_compile = sum(item["baseline_compile_median_ms"] for item in compared)
    optimized_compile = sum(item["optimized_compile_median_ms"] for item in compared)
    gnucobol_compile = sum(item["gnucobol_compile_median_ms"] for item in compared)
    baseline_run = sum(item["baseline_run_median_ms"] for item in compared)
    optimized_run = sum(item["optimized_run_median_ms"] for item in compared)
    gnucobol_run = sum(item["gnucobol_run_median_ms"] for item in compared)

    return {
        "total_cases": len(results),
        "compared_cases": len(compared),
        "failed_cases": len(results) - len(compared),
        "baseline_compile_sum_ms": baseline_compile,
        "optimized_compile_sum_ms": optimized_compile,
        "gnucobol_compile_sum_ms": gnucobol_compile,
        "baseline_run_sum_ms": baseline_run,
        "optimized_run_sum_ms": optimized_run,
        "gnucobol_run_sum_ms": gnucobol_run,
        "optimized_compile_ratio_vs_baseline": (
            optimized_compile / baseline_compile if baseline_compile else None
        ),
        "optimized_runtime_ratio_vs_baseline": (
            optimized_run / baseline_run if baseline_run else None
        ),
        "gnucobol_compile_ratio_vs_baseline": (
            gnucobol_compile / baseline_compile if baseline_compile else None
        ),
        "gnucobol_runtime_ratio_vs_baseline": (
            gnucobol_run / baseline_run if baseline_run else None
        ),
        "by_suite": by_suite,
    }


def render_report(results, summary, minicobc_build_ms, compile_iterations, run_iterations):
    lines = []
    lines.append("# MiniCOBC Optimization Comparison")
    lines.append("")
    lines.append(
        "- Configurations: `minicobc + gcc -O0`, `minicobc OPT + gcc -O0`, `cobc -A -O2`"
    )
    lines.append(f"- `minicobc` build time: `{minicobc_build_ms:.2f} ms`")
    lines.append(f"- Compile iterations per case: `{compile_iterations}`")
    lines.append(f"- Runtime iterations per case: `{run_iterations}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"- Cases compared: `{summary['compared_cases']}/{summary['total_cases']}`"
    )
    if summary["compared_cases"] > 0:
        lines.append(
            f"- Optimized compile ratio vs baseline: "
            f"`{format_ratio(summary['optimized_compile_ratio_vs_baseline'])}`"
        )
        lines.append(
            f"- Optimized runtime ratio vs baseline: "
            f"`{format_ratio(summary['optimized_runtime_ratio_vs_baseline'])}`"
        )
        lines.append(
            f"- GnuCOBOL compile ratio vs baseline: "
            f"`{format_ratio(summary['gnucobol_compile_ratio_vs_baseline'])}`"
        )
        lines.append(
            f"- GnuCOBOL runtime ratio vs baseline: "
            f"`{format_ratio(summary['gnucobol_runtime_ratio_vs_baseline'])}`"
        )

    lines.append("")
    lines.append("## By Suite")
    lines.append("")
    lines.append(
        "| Suite | Compared | Failed | Base compile ms | Opt compile ms | GNU compile ms | "
        "Opt compile ratio | Base run ms | Opt run ms | GNU run ms | Opt runtime ratio |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for suite_name, suite in summary["by_suite"].items():
        lines.append(
            f"| {suite_name} | {suite['compared_cases']} | {suite['failed_cases']} | "
            f"{format_ms(suite.get('baseline_compile_sum_ms', 0.0))} | "
            f"{format_ms(suite.get('optimized_compile_sum_ms', 0.0))} | "
            f"{format_ms(suite.get('gnucobol_compile_sum_ms', 0.0))} | "
            f"{format_ratio(suite.get('optimized_compile_ratio_vs_baseline'))} | "
            f"{format_ms(suite.get('baseline_run_sum_ms', 0.0))} | "
            f"{format_ms(suite.get('optimized_run_sum_ms', 0.0))} | "
            f"{format_ms(suite.get('gnucobol_run_sum_ms', 0.0))} | "
            f"{format_ratio(suite.get('optimized_runtime_ratio_vs_baseline'))} |"
        )

    lines.append("")
    lines.append("## Cases")
    lines.append("")
    lines.append(
        "| Case | Status | Base compile ms | Opt compile ms | GNU compile ms | "
        "Opt compile ratio | Base run ms | Opt run ms | GNU run ms | Opt runtime ratio |"
    )
    lines.append(
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for item in results:
        if item["status"] != "compared":
            lines.append(
                f"| {item['id']} | {item['status']} | - | - | - | - | - | - | - | - |"
            )
            continue
        lines.append(
            f"| {item['id']} | {item['status']} | "
            f"{format_ms(item['baseline_compile_median_ms'])} | "
            f"{format_ms(item['optimized_compile_median_ms'])} | "
            f"{format_ms(item['gnucobol_compile_median_ms'])} | "
            f"{format_ratio(item['optimized_compile_ratio_vs_baseline'])} | "
            f"{format_ms(item['baseline_run_median_ms'])} | "
            f"{format_ms(item['optimized_run_median_ms'])} | "
            f"{format_ms(item['gnucobol_run_median_ms'])} | "
            f"{format_ratio(item['optimized_runtime_ratio_vs_baseline'])} |"
        )

    failures = [item for item in results if item["status"] != "compared"]
    if failures:
        lines.append("")
        lines.append("## Failures")
        lines.append("")
        for item in failures:
            lines.append(f"- `{item['id']}`: {item['reason']}")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Compare baseline MiniCOBC, optimized MiniCOBC, and GnuCOBOL."
    )
    parser.add_argument(
        "--suite",
        choices=("opt", "core", "all"),
        default="opt",
        help="which benchmark suite to compare; all means core + opt",
    )
    parser.add_argument(
        "--compile-iterations",
        type=int,
        default=3,
        help="number of repeated compile measurements per case",
    )
    parser.add_argument(
        "--run-iterations",
        type=int,
        default=5,
        help="number of repeated runtime measurements per case",
    )
    args = parser.parse_args()

    ensure_dirs()
    cases = load_cases(args.suite)
    minicobc_binary, minicobc_build_ms = build_minicobc()

    results = [
        compare_case(case, minicobc_binary, args.compile_iterations, args.run_iterations)
        for case in cases
    ]
    summary = overall_summary(results)
    report = render_report(
        results,
        summary,
        minicobc_build_ms,
        args.compile_iterations,
        args.run_iterations,
    )

    suffix = args.suite
    results_path = ROOT / "build" / "perf" / f"minicobc-opt-compare-{suffix}.json"
    report_path = ROOT / "build" / "perf" / f"minicobc-opt-compare-{suffix}.md"
    payload = {
        "summary": summary,
        "minicobc_build_ms": minicobc_build_ms,
        "results": results,
    }
    results_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")

    print(report, end="")
    print(f"wrote {results_path}")
    print(f"wrote {report_path}")

    return 0 if summary["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
