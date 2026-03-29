#!/usr/bin/env python3
import argparse
import json
import shlex
import statistics
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "benchmark" / "cases.json"
DEFAULT_COMPAT_REPO = ROOT / "external" / "agentic-cobol-game15tictactoe"

SELF_CASE = {
    "id": "self/minicobc",
    "suite": "self",
    "source": "src/minicobc.cob",
    "stem": "minicob-self",
    "args": [],
    "stdin": "",
    "oracle": {"type": "self"},
    "compile_mode": "cob_runtime",
}


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


def ensure_dirs():
    for rel in (
        "build/bin",
        "build/generated",
        "build/perf/selfhost/stage0/generated",
        "build/perf/selfhost/stage1/generated",
        "build/perf/selfhost/check/bin",
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def read_manifest():
    with MANIFEST.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_cases(suite, compat_repo, include_self):
    manifest = read_manifest()
    cases = []
    if include_self:
        cases.append(dict(SELF_CASE))

    for suite_name in ("core", "compat"):
        if suite != "all" and suite != suite_name:
            continue
        for case in manifest[suite_name]:
            expanded = dict(case)
            expanded["suite"] = suite_name
            expanded["source"] = expanded["source"].format(
                compat_repo=str(compat_repo)
            )
            expanded["compile_mode"] = (
                "cob_runtime" if expanded["source"] == "src/minicobc.cob" else "c"
            )
            cases.append(expanded)
    return cases


def get_cob_config_args(flag):
    completed, _ = run_command(["cob-config", flag])
    if completed.returncode != 0:
        raise RuntimeError(
            f"failed to query cob-config {flag}\n"
            f"stderr:\n{completed.stderr}"
        )
    return shlex.split(completed.stdout.strip())


def build_stage0():
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
            "failed to build stage-0 minicobc\n"
            f"command: {cmd_string(cmd)}\n"
            f"stderr:\n{completed.stderr}"
        )
    return binary, elapsed_ms


def regenerate_selfhost_template():
    cmd = ["./scripts/regenerate-selfhost-template.sh"]
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to regenerate self-host template\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return elapsed_ms


def build_stage1(stage0_binary, cob_cflags, cob_libs):
    generated_c = ROOT / "build" / "generated" / "minicob-self.c"
    stage2_c = ROOT / "build" / "generated" / "minicob-self-stage2.c"
    binary = ROOT / "build" / "bin" / "minicobc-self"

    for path in (generated_c, stage2_c, binary):
        if path.exists():
            path.unlink()

    translate_cmd = [str(stage0_binary), "src/minicobc.cob", str(generated_c)]
    translate_cp, translate_ms = run_command(translate_cmd)
    if translate_cp.returncode != 0:
        raise RuntimeError(
            "failed to translate self-host source with stage-0 compiler\n"
            f"command: {cmd_string(translate_cmd)}\n"
            f"stdout:\n{translate_cp.stdout}\n"
            f"stderr:\n{translate_cp.stderr}"
        )

    cc_cmd = ["cc", str(generated_c), *cob_cflags, *cob_libs, "-o", str(binary)]
    cc_cp, cc_ms = run_command(cc_cmd)
    if cc_cp.returncode != 0:
        raise RuntimeError(
            "failed to build stage-1 self-hosted compiler\n"
            f"command: {cmd_string(cc_cmd)}\n"
            f"stdout:\n{cc_cp.stdout}\n"
            f"stderr:\n{cc_cp.stderr}"
        )

    verify_cmd = [str(binary), "src/minicobc.cob", str(stage2_c)]
    verify_cp, verify_ms = run_command(verify_cmd)
    if verify_cp.returncode != 0:
        raise RuntimeError(
            "stage-1 compiler failed to reproduce self-host C\n"
            f"command: {cmd_string(verify_cmd)}\n"
            f"stdout:\n{verify_cp.stdout}\n"
            f"stderr:\n{verify_cp.stderr}"
        )

    if generated_c.read_text(encoding="utf-8") != stage2_c.read_text(encoding="utf-8"):
        raise RuntimeError("stage-1 compiler did not reproduce the stage-1 self-host C")

    return {
        "binary": binary,
        "generated_c": generated_c,
        "stage2_c": stage2_c,
        "translate_ms": translate_ms,
        "cc_ms": cc_ms,
        "verify_ms": verify_ms,
    }


def output_paths(label, case):
    stem = case["id"].replace("/", "__")
    generated = ROOT / "build" / "perf" / "selfhost" / label / "generated" / f"{stem}.c"
    binary = ROOT / "build" / "perf" / "selfhost" / "check" / "bin" / f"{label}__{stem}"
    return generated, binary


def translate_case(compiler_binary, label, case):
    generated, _ = output_paths(label, case)
    if generated.exists():
        generated.unlink()

    cmd = [str(compiler_binary), case["source"], str(generated)]
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "compiler translation failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return generated, elapsed_ms


def build_generated_binary(case, generated_c, cob_cflags, cob_libs, label):
    _, binary = output_paths(label, case)
    if binary.exists():
        binary.unlink()

    if case["compile_mode"] == "cob_runtime":
        cmd = ["cc", str(generated_c), *cob_cflags, *cob_libs, "-o", str(binary)]
    else:
        cmd = ["gcc", "-std=c11", str(generated_c), "-o", str(binary)]
    completed, elapsed_ms = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "generated C build failed\n"
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
            "generated binary failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout, elapsed_ms


def expected_output(case, compat_repo):
    oracle = case["oracle"]
    if oracle["type"] == "self":
        return None
    if oracle["type"] == "file":
        return (ROOT / oracle["path"]).read_text(encoding="utf-8")

    binary = ROOT / "build" / "perf" / "selfhost" / "check" / "bin" / (
        "reference__" + case["id"].replace("/", "__")
    )
    if binary.exists():
        binary.unlink()

    cmd = ["cobc", "-x"]
    if case["suite"] == "core":
        cmd.append("-free")
    cmd.extend([case["source"], "-o", str(binary)])
    completed, _ = run_command(cmd)
    if completed.returncode != 0:
        raise RuntimeError(
            "reference build failed\n"
            f"case: {case['id']}\n"
            f"command: {cmd_string(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    stdout, _ = run_binary(binary, case)
    return stdout


def validate_case(case, stage0_binary, stage1_binary, cob_cflags, cob_libs, compat_repo):
    stage0_c, _ = translate_case(stage0_binary, "stage0", case)
    stage1_c, _ = translate_case(stage1_binary, "stage1", case)

    stage0_text = stage0_c.read_text(encoding="utf-8")
    stage1_text = stage1_c.read_text(encoding="utf-8")
    if stage0_text != stage1_text:
        raise RuntimeError(
            "stage-0 and self-hosted compilers generated different C\n"
            f"case: {case['id']}"
        )

    binary, build_ms = build_generated_binary(
        case, stage0_c, cob_cflags, cob_libs, "stage0"
    )
    if case["oracle"]["type"] != "self":
        actual_stdout, run_ms = run_binary(binary, case)
        expected_stdout = expected_output(case, compat_repo)
        if actual_stdout != expected_stdout:
            raise RuntimeError(
                "generated program output mismatch\n"
                f"case: {case['id']}"
            )
    else:
        run_ms = None

    return {
        "generated_c_lines": sum(1 for _ in stage0_c.open("r", encoding="utf-8")),
        "generated_c_bytes": stage0_c.stat().st_size,
        "binary_bytes": binary.stat().st_size,
        "validation_build_ms": build_ms,
        "validation_run_ms": run_ms,
    }


def benchmark_case(case, stage0_binary, stage1_binary, iterations):
    stage0_times = []
    stage1_times = []

    for _ in range(iterations):
        _, stage0_ms = translate_case(stage0_binary, "stage0", case)
        _, stage1_ms = translate_case(stage1_binary, "stage1", case)
        stage0_times.append(stage0_ms)
        stage1_times.append(stage1_ms)

    return {
        "stage0_translate_median_ms": median(stage0_times),
        "stage1_translate_median_ms": median(stage1_times),
        "translate_ratio_stage1_vs_stage0": (
            median(stage1_times) / median(stage0_times) if median(stage0_times) else None
        ),
    }


def render_report(
    results,
    suite,
    iterations,
    stage0_build_ms,
    template_regen_ms,
    stage1_bootstrap,
    stage0_binary,
    stage1_binary,
):
    lines = []
    lines.append("# Self-Hosted MiniCOBC Comparison")
    lines.append("")
    lines.append("- Metric: median wall-clock translation time across repeated local runs")
    lines.append(f"- Suite: `{suite}` plus `self/minicobc`")
    lines.append(f"- Iterations per case: `{iterations}`")
    lines.append(f"- Stage-0 build (`cobc`) time: `{stage0_build_ms:.2f} ms`")
    lines.append(f"- Self-host template regeneration time: `{template_regen_ms:.2f} ms`")
    lines.append(
        f"- Stage-1 bootstrap translate time: `{stage1_bootstrap['translate_ms']:.2f} ms`"
    )
    lines.append(f"- Stage-1 bootstrap C build time: `{stage1_bootstrap['cc_ms']:.2f} ms`")
    lines.append(
        f"- Stage-1 fixed-point verification time: `{stage1_bootstrap['verify_ms']:.2f} ms`"
    )
    lines.append(f"- Stage-0 binary bytes: `{stage0_binary.stat().st_size}`")
    lines.append(f"- Stage-1 binary bytes: `{stage1_binary.stat().st_size}`")
    lines.append("")
    lines.append(
        "The `self/minicobc` case measures the dedicated self-host path for `PROGRAM-ID. MINICOB.`. "
        "The `core/*` cases measure the generic subset compiler path."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(
        "| Case | Suite | Stage-0 ms | Self-hosted ms | Ratio | C LOC | C bytes | Validation |"
    )
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for item in results:
        ratio = item["translate_ratio_stage1_vs_stage0"]
        ratio_text = f"{ratio:.2f}x" if ratio is not None else "-"
        lines.append(
            f"| {item['id']} | {item['suite']} | "
            f"{item['stage0_translate_median_ms']:.2f} | "
            f"{item['stage1_translate_median_ms']:.2f} | "
            f"{ratio_text} | "
            f"{item['generated_c_lines']} | "
            f"{item['generated_c_bytes']} | "
            f"{item['validation_status']} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Compare stage-0 and self-hosted MiniCOBC performance."
    )
    parser.add_argument(
        "--suite",
        choices=("core", "compat", "all"),
        default="core",
        help="which tested suite to benchmark alongside self/minicobc",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=7,
        help="number of translation measurements per compiler per case",
    )
    parser.add_argument(
        "--compat-repo",
        default=str(DEFAULT_COMPAT_REPO),
        help="path to the compatibility repository checkout",
    )
    parser.add_argument(
        "--no-self-case",
        action="store_true",
        help="omit the self/minicobc case",
    )
    args = parser.parse_args()

    ensure_dirs()

    cob_cflags = get_cob_config_args("--cflags")
    cob_libs = get_cob_config_args("--libs")

    stage0_binary, stage0_build_ms = build_stage0()
    template_regen_ms = regenerate_selfhost_template()
    stage1_bootstrap = build_stage1(stage0_binary, cob_cflags, cob_libs)
    stage1_binary = stage1_bootstrap["binary"]

    cases = load_cases(args.suite, Path(args.compat_repo), not args.no_self_case)

    results = []
    for case in cases:
        validation = validate_case(
            case,
            stage0_binary,
            stage1_binary,
            cob_cflags,
            cob_libs,
            Path(args.compat_repo),
        )
        benchmark = benchmark_case(
            case,
            stage0_binary,
            stage1_binary,
            args.iterations,
        )
        results.append(
            {
                "id": case["id"],
                "suite": case["suite"],
                "validation_status": "identical_c",
                **validation,
                **benchmark,
            }
        )

    report = render_report(
        results,
        args.suite,
        args.iterations,
        stage0_build_ms,
        template_regen_ms,
        stage1_bootstrap,
        stage0_binary,
        stage1_binary,
    )

    report_path = ROOT / "build" / "perf" / "selfhost-compare.md"
    json_path = ROOT / "build" / "perf" / "selfhost-compare.json"
    report_path.write_text(report, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "suite": args.suite,
                "iterations": args.iterations,
                "stage0_build_ms": stage0_build_ms,
                "template_regen_ms": template_regen_ms,
                "stage1_bootstrap": {
                    "translate_ms": stage1_bootstrap["translate_ms"],
                    "cc_ms": stage1_bootstrap["cc_ms"],
                    "verify_ms": stage1_bootstrap["verify_ms"],
                },
                "stage0_binary_bytes": stage0_binary.stat().st_size,
                "stage1_binary_bytes": stage1_binary.stat().st_size,
                "results": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(report, end="")
    print(f"wrote {json_path}")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
