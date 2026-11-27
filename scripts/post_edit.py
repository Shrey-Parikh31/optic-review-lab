"""PostToolUse hook for edits to this repository's firmware."""
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    event = json.load(sys.stdin)
    raw = event.get("tool_input", {}).get("file_path")
    if not isinstance(raw, str):
        return 0
    file = (Path(event.get("cwd") or os.getcwd()) / raw).resolve()
    if root / "firmware" not in file.parents or file.suffix not in {".c", ".h"}:
        return 0
    sources = sorted((root / "firmware").glob("*.c"))
    analyze = subprocess.run([sys.executable, "-m", "lab.analyze", *sources], cwd=root)
    if analyze.returncode:
        print("Review the Clang diagnostic before continuing.", file=sys.stderr)
        return 2
    result = subprocess.run(["bash", "scripts/check.sh"], cwd=root, capture_output=True, text=True)
    if result.returncode:
        print(result.stderr + result.stdout, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
