#!/usr/bin/env python3
import argparse
import hashlib
import json
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "benchmark" / "cases.json"
DEFAULT_COMPAT_REPO = ROOT / "external" / "agentic-cobol-game15tictactoe"


def run_command(cmd, *, cwd=ROOT, stdin_text=None):
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


def load_manifest(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def expand_cases(manifest, suite, compat_repo):
    selected = []
    for suite_name in ("core", "compat"):
        if suite != "all" and suite != suite_name:
            continue
        for case in manifest.get(suite_name, []):
            expanded = dict(case)
            expanded["suite"] = suite_name
            expanded["source"] = expanded["source"].format(
                compat_repo=str(compat_repo)
            )
            selected.append(expanded)
    return selected


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def line_count(path):
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def command_string(cmd):
    return " ".join(shlex.quote(part) for part in cmd)


def median(values):
    return statistics.median(values) if values else 0.0


def ensure_dirs():
    for rel in (
        "build/bin",
        "build/benchmark/generated",
        "build/benchmark/binaries",
        "build/benchmark/reference",
        "build/benchmark/oracles",
        "build/benchmark/perf/minicobc/generated",
        "build/benchmark/perf/minicobc/binaries",
        "build/benchmark/perf/gnucobol/binaries",
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def gnucobol_compile_command(source, binary, suite):
    cmd = ["cobc", "-x"]
    if suite == "core":
        cmd.append("-free")
    cmd.extend([source, "-o", str(binary)])
    return cmd


def compile_minicobc():
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
            f"command: {command_string(cmd)}\n"
            f"stderr:\n{completed.stderr}"
        )
    return {"path": binary, "build_ms": elapsed_ms}


def compile_generated(source, stem, minicobc_path, cache):
    if source in cache:
        return cache[source]

    generated_c = ROOT / "build" / "benchmark" / "generated" / f"{stem}.c"
    binary = ROOT / "build" / "benchmark" / "binaries" / stem

    if generated_c.exists():
        generated_c.unlink()
    if binary.exists():
        binary.unlink()

    translate_cmd = [str(minicobc_path), source, str(generated_c)]
    translate_cp, translate_ms = run_command(translate_cmd)
    if translate_cp.returncode != 0:
        result = {
            "ok": False,
            "phase": "translate",
            "command": command_string(translate_cmd),
            "stdout": translate_cp.stdout,
            "stderr": translate_cp.stderr,
            "translate_ms": translate_ms,
        }
        cache[source] = result
        return result

    gcc_cmd = ["gcc", "-std=c11", str(generated_c), "-o", str(binary)]
    gcc_cp, gcc_ms = run_command(gcc_cmd)
    if gcc_cp.returncode != 0:
        result = {
            "ok": False,
            "phase": "gcc",
            "command": command_string(gcc_cmd),
            "stdout": gcc_cp.stdout,
            "stderr": gcc_cp.stderr,
            "translate_ms": translate_ms,
            "gcc_ms": gcc_ms,
        }
        cache[source] = result
        return result

    result = {
        "ok": True,
        "generated_c": str(generated_c),
        "binary": str(binary),
        "translate_ms": translate_ms,
        "gcc_ms": gcc_ms,
        "generated_c_lines": line_count(generated_c),
        "generated_c_bytes": generated_c.stat().st_size,
        "binary_bytes": binary.stat().st_size,
    }
    cache[source] = result
    return result


def compile_reference(source, stem, suite, cache):
    cache_key = (source, suite)
    if cache_key in cache:
        return cache[cache_key]

    binary = ROOT / "build" / "benchmark" / "reference" / stem
    if binary.exists():
        binary.unlink()

    cmd = gnucobol_compile_command(source, binary, suite)
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        result = {
            "ok": False,
            "command": command_string(cmd),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "build_ms": elapsed_ms,
        }
        cache[cache_key] = result
        return result

    result = {
        "ok": True,
        "binary": str(binary),
        "build_ms": elapsed_ms,
    }
    cache[cache_key] = result
    return result


def run_binary(binary, args, stdin_text):
    cmd = [str(binary), *args]
    completed, elapsed_ms = run_command(cmd, stdin_text=stdin_text)
    return {
        "command": command_string(cmd),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "run_ms": elapsed_ms,
    }


def run_case(case, generated_cache, reference_cache, minicobc_path):
    compiled = compile_generated(
        case["source"], case["stem"], minicobc_path, generated_cache
    )
    result = {
        "id": case["id"],
        "suite": case["suite"],
        "source": case["source"],
        "args": case["args"],
    }

    if not compiled["ok"]:
        result.update(
            {
                "status": "fail",
                "reason": f"generated {compiled['phase']} failed",
                "translate_ms": compiled.get("translate_ms"),
                "gcc_ms": compiled.get("gcc_ms"),
                "details": compiled,
            }
        )
        return result

    mine = run_binary(compiled["binary"], case["args"], case["stdin"])
    result.update(
        {
            "translate_ms": compiled["translate_ms"],
            "gcc_ms": compiled["gcc_ms"],
            "run_ms": mine["run_ms"],
            "generated_c_lines": compiled["generated_c_lines"],
            "generated_c_bytes": compiled["generated_c_bytes"],
            "binary_bytes": compiled["binary_bytes"],
            "output_sha256": sha256_text(mine["stdout"]),
        }
    )

    if mine["returncode"] != 0:
        result.update(
            {
                "status": "fail",
                "reason": f"generated binary exited {mine['returncode']}",
                "details": mine,
            }
        )
        return result

    oracle = case["oracle"]
    if oracle["type"] == "file":
        expected_path = ROOT / oracle["path"]
        expected_stdout = expected_path.read_text(encoding="utf-8")
        reference_meta = {"oracle": str(expected_path)}
    else:
        reference = compile_reference(
            case["source"], case["stem"], case["suite"], reference_cache
        )
        if not reference["ok"]:
            result.update(
                {
                    "status": "fail",
                    "reason": "reference compile failed",
                    "details": reference,
                }
            )
            return result
        ref_run = run_binary(reference["binary"], case["args"], case["stdin"])
        if ref_run["returncode"] != 0:
            result.update(
                {
                    "status": "fail",
                    "reason": f"reference binary exited {ref_run['returncode']}",
                    "details": ref_run,
                }
            )
            return result
        expected_stdout = ref_run["stdout"]
        reference_meta = {
            "oracle": "gnucobol",
            "reference_build_ms": reference["build_ms"],
            "reference_run_ms": ref_run["run_ms"],
        }

    if mine["stdout"] != expected_stdout:
        result.update(
            {
                "status": "fail",
                "reason": "stdout mismatch",
                "details": {
                    "generated_stdout": mine["stdout"],
                    "expected_stdout": expected_stdout,
                },
            }
        )
        result.update(reference_meta)
        return result

    result.update({"status": "pass"})
    result.update(reference_meta)
    return result


def perf_build_with_minicobc(case, minicobc_path):
    stem = case["id"].replace("/", "__")
    generated_c = (
        ROOT / "build" / "benchmark" / "perf" / "minicobc" / "generated" / f"{stem}.c"
    )
    binary = (
        ROOT / "build" / "benchmark" / "perf" / "minicobc" / "binaries" / stem
    )

    if generated_c.exists():
        generated_c.unlink()
    if binary.exists():
        binary.unlink()

    translate_cmd = [str(minicobc_path), case["source"], str(generated_c)]
    translate_cp, translate_ms = run_command(translate_cmd)
    if translate_cp.returncode != 0:
        return {
            "ok": False,
            "phase": "translate",
            "command": command_string(translate_cmd),
            "stdout": translate_cp.stdout,
            "stderr": translate_cp.stderr,
            "translate_ms": translate_ms,
        }

    gcc_cmd = ["gcc", "-std=c11", str(generated_c), "-o", str(binary)]
    gcc_cp, gcc_ms = run_command(gcc_cmd)
    if gcc_cp.returncode != 0:
        return {
            "ok": False,
            "phase": "gcc",
            "command": command_string(gcc_cmd),
            "stdout": gcc_cp.stdout,
            "stderr": gcc_cp.stderr,
            "translate_ms": translate_ms,
            "gcc_ms": gcc_ms,
        }

    return {
        "ok": True,
        "generated_c": generated_c,
        "binary": binary,
        "translate_ms": translate_ms,
        "gcc_ms": gcc_ms,
    }


def perf_build_with_gnucobol(case):
    stem = case["id"].replace("/", "__")
    binary = ROOT / "build" / "benchmark" / "perf" / "gnucobol" / "binaries" / stem
    if binary.exists():
        binary.unlink()

    cmd = gnucobol_compile_command(case["source"], binary, case["suite"])
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        return {
            "ok": False,
            "command": command_string(cmd),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "build_ms": elapsed_ms,
        }

    return {
        "ok": True,
        "binary": binary,
        "build_ms": elapsed_ms,
    }


def compare_case(case, minicobc_path, compile_iterations, run_iterations):
    mini_translate = []
    mini_gcc = []
    mini_total = []
    gnucobol_compile = []
    mini_runs = []
    gnucobol_runs = []
    output_baseline = None

    last_minicobc = None
    last_gnucobol = None
    last_generated_c = None

    for _ in range(compile_iterations):
        built_minicobc = perf_build_with_minicobc(case, minicobc_path)
        if not built_minicobc["ok"]:
            return {
                "status": "minicobc_failed",
                "reason": (
                    f"minicobc {built_minicobc['phase']} failed: "
                    f"{built_minicobc.get('stderr', '').strip()}"
                ).strip(),
                "details": built_minicobc,
            }

        built_gnucobol = perf_build_with_gnucobol(case)
        if not built_gnucobol["ok"]:
            return {
                "status": "unsupported_by_gnucobol",
                "reason": built_gnucobol.get("stderr", "").strip() or "build failed",
                "details": built_gnucobol,
            }

        mini_translate.append(built_minicobc["translate_ms"])
        mini_gcc.append(built_minicobc["gcc_ms"])
        mini_total.append(
            built_minicobc["translate_ms"] + built_minicobc["gcc_ms"]
        )
        gnucobol_compile.append(built_gnucobol["build_ms"])

        last_minicobc = built_minicobc["binary"]
        last_gnucobol = built_gnucobol["binary"]
        last_generated_c = built_minicobc["generated_c"]

    for _ in range(run_iterations):
        minicobc_run = run_binary(last_minicobc, case["args"], case["stdin"])
        if minicobc_run["returncode"] != 0:
            return {
                "status": "minicobc_runtime_failed",
                "reason": f"minicobc binary exited {minicobc_run['returncode']}",
                "details": minicobc_run,
            }

        gnucobol_run = run_binary(last_gnucobol, case["args"], case["stdin"])
        if gnucobol_run["returncode"] != 0:
            return {
                "status": "gnucobol_runtime_failed",
                "reason": f"gnucobol binary exited {gnucobol_run['returncode']}",
                "details": gnucobol_run,
            }

        if minicobc_run["stdout"] != gnucobol_run["stdout"]:
            return {
                "status": "runtime_output_mismatch",
                "reason": "minicobc and gnucobol produced different stdout",
                "details": {
                    "minicobc_stdout": minicobc_run["stdout"],
                    "gnucobol_stdout": gnucobol_run["stdout"],
                },
            }

        output_baseline = minicobc_run["stdout"]
        mini_runs.append(minicobc_run["run_ms"])
        gnucobol_runs.append(gnucobol_run["run_ms"])

    gnucobol_compile_median_ms = median(gnucobol_compile)
    gnucobol_run_median_ms = median(gnucobol_runs)
    minicobc_end_to_end_median_ms = median(mini_total)
    minicobc_run_median_ms = median(mini_runs)

    return {
        "status": "compared",
        "compile_iterations": compile_iterations,
        "run_iterations": run_iterations,
        "minicobc_translate_median_ms": median(mini_translate),
        "minicobc_gcc_median_ms": median(mini_gcc),
        "minicobc_end_to_end_median_ms": minicobc_end_to_end_median_ms,
        "gnucobol_compile_median_ms": gnucobol_compile_median_ms,
        "minicobc_run_median_ms": minicobc_run_median_ms,
        "gnucobol_run_median_ms": gnucobol_run_median_ms,
        "compile_ratio_vs_gnucobol": (
            minicobc_end_to_end_median_ms / gnucobol_compile_median_ms
            if gnucobol_compile_median_ms
            else None
        ),
        "runtime_ratio_vs_gnucobol": (
            minicobc_run_median_ms / gnucobol_run_median_ms
            if gnucobol_run_median_ms
            else None
        ),
        "generated_c_lines": line_count(last_generated_c),
        "generated_c_bytes": last_generated_c.stat().st_size,
        "minicobc_binary_bytes": last_minicobc.stat().st_size,
        "gnucobol_binary_bytes": last_gnucobol.stat().st_size,
        "output_bytes": len(output_baseline.encode("utf-8")),
    }


def add_performance(results, cases, minicobc_path, compile_iterations, run_iterations):
    cases_by_id = {case["id"]: case for case in cases}
    performance_results = {}
    for item in results:
        performance_results[item["id"]] = compare_case(
            cases_by_id[item["id"]],
            minicobc_path,
            compile_iterations,
            run_iterations,
        )

    enriched = []
    for item in results:
        updated = dict(item)
        updated["performance"] = performance_results[item["id"]]
        enriched.append(updated)
    return enriched


def summarise(results):
    summary = {
        "total_cases": len(results),
        "passed_cases": sum(1 for item in results if item["status"] == "pass"),
        "failed_cases": sum(1 for item in results if item["status"] != "pass"),
        "by_suite": {},
    }
    for suite_name in sorted({item["suite"] for item in results}):
        suite_items = [item for item in results if item["suite"] == suite_name]
        summary["by_suite"][suite_name] = {
            "total_cases": len(suite_items),
            "passed_cases": sum(
                1 for item in suite_items if item["status"] == "pass"
            ),
            "failed_cases": sum(
                1 for item in suite_items if item["status"] != "pass"
            ),
        }
    return summary


def summarise_performance(results):
    summary = {
        "total_cases": len(results),
        "compared_cases": 0,
        "unsupported_cases": 0,
        "failed_cases": 0,
        "by_suite": {},
    }

    for suite_name in sorted({item["suite"] for item in results}):
        suite_items = [item for item in results if item["suite"] == suite_name]
        suite_summary = {
            "total_cases": len(suite_items),
            "compared_cases": 0,
            "unsupported_cases": 0,
            "failed_cases": 0,
        }
        for item in suite_items:
            perf = item.get("performance", {})
            if perf.get("status") == "compared":
                suite_summary["compared_cases"] += 1
                summary["compared_cases"] += 1
            elif perf.get("status") == "unsupported_by_gnucobol":
                suite_summary["unsupported_cases"] += 1
                summary["unsupported_cases"] += 1
            elif perf:
                suite_summary["failed_cases"] += 1
                summary["failed_cases"] += 1
        summary["by_suite"][suite_name] = suite_summary

    return summary


def format_ratio(value):
    if value is None:
        return "-"
    return f"{value:.2f}x"


def render_report(
    summary,
    performance_summary,
    results,
    compat_repo,
    minicobc_build_ms,
    compiler_compare_enabled,
    compile_iterations,
    run_iterations,
):
    lines = []
    lines.append("# Benchmark Report")
    lines.append("")
    lines.append(f"- Compatibility repo: `{compat_repo}`")
    lines.append(f"- `minicobc` build time: `{minicobc_build_ms:.2f} ms`")
    lines.append(
        f"- Cases: `{summary['passed_cases']}/{summary['total_cases']}` passed"
    )
    if compiler_compare_enabled:
        lines.append("- Compiler comparison: `enabled`")
        lines.append(f"- Compile iterations per case: `{compile_iterations}`")
        lines.append(f"- Runtime iterations per case: `{run_iterations}`")
    else:
        lines.append("- Compiler comparison: `disabled`")
    lines.append("")
    lines.append("## Suite Summary")
    lines.append("")
    lines.append("| Suite | Passed | Failed | Total |")
    lines.append("| --- | ---: | ---: | ---: |")
    for suite_name, suite_summary in summary["by_suite"].items():
        lines.append(
            f"| {suite_name} | {suite_summary['passed_cases']} | "
            f"{suite_summary['failed_cases']} | {suite_summary['total_cases']} |"
        )

    if compiler_compare_enabled:
        lines.append("")
        lines.append("## Compiler Comparison Summary")
        lines.append("")
        lines.append("| Suite | Compared | Unsupported | Failed | Total |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for suite_name, suite_summary in performance_summary["by_suite"].items():
            lines.append(
                f"| {suite_name} | {suite_summary['compared_cases']} | "
                f"{suite_summary['unsupported_cases']} | "
                f"{suite_summary['failed_cases']} | "
                f"{suite_summary['total_cases']} |"
            )

    lines.append("")
    lines.append("## Case Metrics")
    lines.append("")
    lines.append(
        "| Case | Status | Translate ms | GCC ms | Run ms | C LOC | C bytes | "
        "Binary bytes | Oracle |"
    )
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for item in results:
        lines.append(
            f"| {item['id']} | {item['status']} | "
            f"{item.get('translate_ms', 0):.2f} | "
            f"{item.get('gcc_ms', 0):.2f} | "
            f"{item.get('run_ms', 0):.2f} | "
            f"{item.get('generated_c_lines', 0)} | "
            f"{item.get('generated_c_bytes', 0)} | "
            f"{item.get('binary_bytes', 0)} | "
            f"{item.get('oracle', '-')} |"
        )

    if compiler_compare_enabled:
        lines.append("")
        lines.append("## Compiler Performance")
        lines.append("")
        lines.append(
            "Performance is informational only. Pass/fail still comes from exact "
            "observable behavior."
        )
        lines.append("")
        lines.append(
            "| Case | Perf status | Mini translate ms | Mini gcc ms | Mini total ms | "
            "cobc ms | Compile ratio | Mini run ms | cobc run ms | Runtime ratio |"
        )
        lines.append(
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
        )
        for item in results:
            perf = item.get("performance", {})
            if perf.get("status") != "compared":
                lines.append(
                    f"| {item['id']} | {perf.get('status', '-')} | - | - | - | - | - | - | - | - |"
                )
                continue
            lines.append(
                f"| {item['id']} | {perf['status']} | "
                f"{perf['minicobc_translate_median_ms']:.2f} | "
                f"{perf['minicobc_gcc_median_ms']:.2f} | "
                f"{perf['minicobc_end_to_end_median_ms']:.2f} | "
                f"{perf['gnucobol_compile_median_ms']:.2f} | "
                f"{format_ratio(perf['compile_ratio_vs_gnucobol'])} | "
                f"{perf['minicobc_run_median_ms']:.2f} | "
                f"{perf['gnucobol_run_median_ms']:.2f} | "
                f"{format_ratio(perf['runtime_ratio_vs_gnucobol'])} |"
            )

        performance_issues = [
            item
            for item in results
            if item.get("performance", {}).get("status") != "compared"
        ]
        if performance_issues:
            lines.append("")
            lines.append("## Compiler Comparison Issues")
            lines.append("")
            for item in performance_issues:
                perf = item.get("performance", {})
                lines.append(
                    f"- `{item['id']}`: {perf.get('status', 'unknown')} "
                    f"({perf.get('reason', 'no detail')})"
                )

    failures = [item for item in results if item["status"] != "pass"]
    if failures:
        lines.append("")
        lines.append("## Failures")
        lines.append("")
        for item in failures:
            lines.append(f"- `{item['id']}`: {item['reason']}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Run the MiniCOBC benchmark suite."
    )
    parser.add_argument(
        "--suite",
        choices=("all", "core", "compat"),
        default="all",
        help="which suite to run",
    )
    parser.add_argument(
        "--compat-repo",
        default=str(DEFAULT_COMPAT_REPO),
        help="path to the acherm/agentic-cobol-game15tictactoe checkout",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="path to the benchmark manifest",
    )
    parser.add_argument(
        "--compile-iterations",
        type=int,
        default=5,
        help="number of repeated compile measurements per case for compiler comparison",
    )
    parser.add_argument(
        "--run-iterations",
        type=int,
        default=7,
        help="number of repeated runtime measurements per case for compiler comparison",
    )
    parser.add_argument(
        "--skip-compiler-compare",
        action="store_true",
        help="skip the embedded GnuCOBOL performance comparison",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    compat_repo = Path(args.compat_repo)

    if args.suite in ("all", "compat") and not compat_repo.exists():
        print(
            f"compatibility repo not found: {compat_repo}",
            file=sys.stderr,
        )
        return 2

    ensure_dirs()
    manifest = load_manifest(manifest_path)
    cases = expand_cases(manifest, args.suite, compat_repo)
    minicobc = compile_minicobc()

    generated_cache = {}
    reference_cache = {}
    results = []
    for case in cases:
        results.append(
            run_case(case, generated_cache, reference_cache, minicobc["path"])
        )

    compiler_compare_enabled = not args.skip_compiler_compare
    if compiler_compare_enabled:
        results = add_performance(
            results,
            cases,
            minicobc["path"],
            args.compile_iterations,
            args.run_iterations,
        )

    summary = summarise(results)
    performance_summary = (
        summarise_performance(results) if compiler_compare_enabled else None
    )
    report = render_report(
        summary,
        performance_summary,
        results,
        compat_repo,
        minicobc["build_ms"],
        compiler_compare_enabled,
        args.compile_iterations,
        args.run_iterations,
    )

    results_path = ROOT / "build" / "benchmark" / "results.json"
    report_path = ROOT / "build" / "benchmark" / "report.md"
    payload = {
        "summary": summary,
        "minicobc_build_ms": minicobc["build_ms"],
        "compiler_compare": {
            "enabled": compiler_compare_enabled,
            "compile_iterations": args.compile_iterations,
            "run_iterations": args.run_iterations,
            "summary": performance_summary,
        },
        "results": results,
    }
    results_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report, encoding="utf-8")

    print(report, end="")
    print(f"wrote {results_path}")
    print(f"wrote {report_path}")

    return 0 if summary["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
