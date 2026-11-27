"""Ask Clang whether an integer constant falls outside its operand's range."""
import argparse
from pathlib import Path
import subprocess
import sys

WARNING = "-Wtautological-constant-out-of-range-compare"
RULE = "OPTIC-RANGE-01"


def check(files, compiler="clang"):
    try:
        result = subprocess.run(
            [compiler, "-std=c11", "-fsyntax-only", "-fno-color-diagnostics",
             "-Werror=tautological-constant-out-of-range-compare",
             *[str(Path(f).resolve()) for f in files]],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 2, str(exc)
    diagnostics = result.stderr.strip()
    if result.returncode == 0:
        return 0, diagnostics
    lines = diagnostics.splitlines()
    findings = [line for line in lines if "error:" in line and WARNING in line]
    other = any("error:" in line and WARNING not in line for line in lines)
    if findings and not other:
        return 1, "\n".join(f"{RULE} {line}" for line in findings)
    return 2, diagnostics or "Clang failed to analyze this input"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    code, message = check(parser.parse_args().files)
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
