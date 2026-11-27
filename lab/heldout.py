"""Run a paired review experiment on local C fixtures using a signed-in Codex CLI."""
import argparse
import difflib
import hashlib
import json
import random
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from .model_review import PROMPT, RULE, SCHEMA

FIXTURES = Path(__file__).resolve().parents[1] / "eval/heldout_v1/cases.json"
COMMON = (" Use only the supplied contract and C11 diff. Do not call tools or read files. "
          "Assess the proposed result for the specified input domain. Report a verdict and one concrete reason.")


def source(case, field):
    body = "\n".join("    " + line for line in case[field].splitlines())
    return "#include <stdint.h>\n" + case["signature"] + "\n{\n" + body + "\n}\n"


def validate(cases):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture.c"
        exe = path.with_suffix("")
        for case in cases:
            name = case["signature"].split("(")[0].split()[-1]
            checks = "\n".join(f"    if ({name}({args}) != ({expected})) return 1;"
                               for args, expected in case["tests"])
            for field in ("before", "after"):
                path.write_text(source(case, field) + "\nint main(void) {\n" + checks + "\n    return 0;\n}\n")
                subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", str(path), "-o", str(exe)],
                               check=True, timeout=15)
                actual = subprocess.run([exe], timeout=5).returncode
                expected = int(field == "after" and case["defect"] is not None)
                if actual != expected:
                    raise ValueError(f"{case['id']} {field}: expected {expected}, observed {actual}")


def prompt_for(case, mode):
    patch = "".join(difflib.unified_diff(source(case, "before").splitlines(True),
                                        source(case, "after").splitlines(True), "before.c", "after.c"))
    instructions = PROMPT + COMMON
    if mode == "with-rule":
        instructions += " " + RULE
    return instructions + "\n\nContract: " + case["contract"] + "\n\n" + patch


def trial(case, mode, model, effort):
    prompt = prompt_for(case, mode)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        schema = directory / "schema.json"
        answer = directory / "answer.json"
        schema.write_text(json.dumps(SCHEMA))
        command = ["codex", "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
                   "-s", "read-only", "--disable", "apps", "--disable", "shell_tool",
                   "-c", 'web_search="disabled"', "-c", "project_doc_max_bytes=0",
                   "-c", f'model_reasoning_effort="{effort}"', "-m", model,
                   "--output-schema", str(schema), "-o", str(answer), "--json", "-"]
        start = time.monotonic()
        try:
            run = subprocess.run(command, cwd=directory, input=prompt, capture_output=True, text=True, timeout=120)
            elapsed = time.monotonic() - start
            events = [json.loads(line) for line in run.stdout.splitlines() if line.strip()]
            if run.returncode or not answer.is_file():
                errors = [e.get("message") or e.get("error") for e in events if e.get("type") in ("turn.failed","error")]
                raise RuntimeError(str(errors[-1:] or run.stderr[-450:]))
            items = [e["item"]["type"] for e in events if isinstance(e.get("item"), dict)]
            if set(items) - {"agent_message", "reasoning", "plan"}:
                raise ValueError("Non-text reviewer activity: " + str(sorted(set(items))))
            result = json.loads(answer.read_text())
            if result["verdict"] not in ("flag","pass") or not isinstance(result["evidence"], str):
                raise ValueError("Invalid verdict")
            usage = next((e.get("usage") for e in events if e.get("type") == "turn.completed"), None)
            return dict(id=case["id"], mode=mode, **result, seconds=round(elapsed, 3), usage=usage,
                        prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Reviewer timed out at 120 seconds") from exc


def summarize(cases, rows):
    faulty = {c["id"] for c in cases if c["defect"]}
    summary = {}
    for mode in ("baseline", "with-rule"):
        arm = [r for r in rows if r["mode"] == mode]
        if len(arm) != len(cases):
            continue
        summary[mode] = {
            "faults": len(faulty), "controls": len(cases) - len(faulty),
            "misses": sum(r["id"] in faulty and r["verdict"] == "pass" for r in arm),
            "false_alarms": sum(r["id"] not in faulty and r["verdict"] == "flag" for r in arm),
            "median_seconds": round(statistics.median(r["seconds"] for r in arm), 3),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New result file; partial runs are retained")
    parser.add_argument("--model", default="gpt-6.2-sol")
    parser.add_argument("--effort", default="medium")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output path for each experiment")
    cases = json.loads(FIXTURES.read_text())
    validate(cases)
    ordered = list(cases)
    random.Random(31).shuffle(ordered)
    report = dict(model=args.model, effort=args.effort, fixture_sha256=hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),
                  cli=subprocess.check_output(["codex","--version"], text=True).strip(), seed=31, rows=[], summary={})
    print(f"Validated {len(cases)} reference and candidate pairs. Fixture SHA-256: {report['fixture_sha256']}", flush=True)
    for index, case in enumerate(ordered):
        modes = ("baseline","with-rule") if index % 2 == 0 else ("with-rule","baseline")
        for mode in modes:
            try:
                row = trial(case, mode, args.model, args.effort)
            except (ValueError, RuntimeError, OSError) as exc:
                report["stopped_at"] = {"id": case["id"], "mode": mode, "reason": str(exc)}
                args.output.write_text(json.dumps(report, indent=2) + "\n")
                raise SystemExit(str(exc))
            report["rows"].append(row)
            report["summary"] = summarize(cases, report["rows"])
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(case["id"], mode, row["verdict"], row["seconds"], flush=True)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
