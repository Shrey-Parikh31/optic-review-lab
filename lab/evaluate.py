"""Compare a build-only reviewer to a type- and behavior-aware reviewer."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .analyze import check

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "eval/cases.json").read_text())
TASKS = {
    "range": ("int candidate(int16_t raw, int supported)",
              "Report whether a signed sample is the sentinel -1 in this lab fixture.",
              "candidate(-1,1)==1 && candidate(0,1)==0"),
    "availability": ("int candidate(int read_ok, int supported)",
                     "Report -1 for an unavailable read, 0 for unsupported and 1 for supported.",
                     "candidate(0,0)==-1 && candidate(0,1)==-1 && candidate(1,0)==0 && candidate(1,1)==1"),
    "millivolts": ("double candidate(uint16_t mv)",
                   "Convert millivolts into volts and preserve fractional volts.",
                   "candidate(1250)==1.25 && candidate(0)==0"),
}


def task(case):
    signature, contract, _ = TASKS[case["task"]]
    source = f"#include <stdint.h>\n{signature}\n{{\n    {case['body']}\n}}\n"
    return {"id": case["id"], "contract": contract, "candidate": source}


def evaluate(case, guarded):
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        source = directory / "candidate.c"
        source.write_text(task(case)["candidate"])
        if guarded:
            code, detail = check([source])
            if code:
                return ("flag" if code == 1 else "error"), detail
        # Both configurations build identical input. Only the guarded one runs the oracle.
        oracle = TASKS[case["task"]][2] if guarded else "1"
        test = directory / "test.c"
        test.write_text('#include "candidate.c"\nint main(void) { return (' + oracle + ') ? 0 : 1; }\n')
        exe = directory / "test"
        build = subprocess.run(["cc", "-std=c11", str(test), "-o", str(exe)], capture_output=True,
                               text=True, timeout=15)
        if build.returncode:
            return "error", build.stderr
        result = subprocess.run([exe], timeout=5)
        return ("pass", "") if result.returncode == 0 else ("flag", "Contract example failed")


def score(rows):
    by_id = {r["id"]: r for r in rows}
    if len(by_id) != len(rows) or set(by_id) != {c["id"] for c in CASES}:
        raise ValueError("Supply exactly one decision per case ID")
    counts = {"detected": 0, "faulty": 0, "false_alarms": 0, "clean": 0, "errors": 0}
    for case in CASES:
        row = by_id[case["id"]]
        verdict = row["verdict"]
        if verdict not in {"flag", "pass", "error", "timeout"}:
            raise ValueError("Unknown verdict for " + case["id"])
        counts["faulty" if case["faulty"] else "clean"] += 1
        if verdict == "flag":
            counts["detected" if case["faulty"] else "false_alarms"] += 1
        if verdict in {"timeout", "error"}:
            counts["errors"] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["compare", "export", "score"])
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "export":
        report = [task(c) for c in CASES]
    elif args.action == "score":
        if not args.predictions:
            parser.error("score requires --predictions")
        report = score(json.loads(args.predictions.read_text()))
    else:
        report = {}
        for mode in ("build-only", "guarded"):
            rows = []
            for case in CASES:
                start = time.monotonic()
                try:
                    verdict, evidence = evaluate(case, mode == "guarded")
                except subprocess.TimeoutExpired as exc:
                    verdict, evidence = "timeout", str(exc)
                except OSError as exc:
                    verdict, evidence = "error", str(exc)
                rows.append({"id": case["id"], "verdict": verdict, "evidence": evidence,
                             "elapsed_ms": round(1000 * (time.monotonic() - start))})
            report[mode] = {"counts": score(rows), "results": rows}
    payload = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(payload + "\n")
    else:
        print(payload)
    if args.action == "compare" and (report["guarded"]["counts"] !=
            {"detected": 3, "faulty": 3, "false_alarms": 0, "clean": 3, "errors": 0}
            or report["build-only"]["counts"]["errors"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
