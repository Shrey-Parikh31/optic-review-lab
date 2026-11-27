import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lab.analyze import check, RULE
from lab.evaluate import CASES, score, task
from lab.model_review import review

ROOT = Path(__file__).resolve().parents[1]


class ToolingTests(unittest.TestCase):
    def test_model_inputs_and_response(self):
        public = task(CASES[0])
        self.assertEqual(set(public), {"id", "candidate", "contract"})
        result = {"model":"test-model", "usage":{"input_tokens":9},
                  "output":[{"content":[{"type":"output_text",
                  "text":json.dumps({"verdict":"flag","evidence":"impossible comparison"})}]}]}
        from io import BytesIO
        with patch("lab.model_review.urlopen", return_value=BytesIO(json.dumps(result).encode())) as call:
            verdict = review(public, "Check the contract", "test-model", "test-only")
        self.assertEqual(verdict["verdict"], "flag")
        payload = json.loads(call.call_args.args[0].data)
        self.assertEqual(json.loads(payload["input"]), public)
        self.assertEqual(payload["tools"], [])
        with self.assertRaises(ValueError):
            score([])

    def test_type_range_and_reversed_operands(self):
        for ctype, expression, expected in [
            ("int16_t", "value == 65535", 1),
            ("int16_t", "65535 != value", 1),
            ("uint16_t", "value == 65535", 0),
            ("int16_t", "value == -1 /* value == 65535 */", 0),
        ]:
            with self.subTest(ctype=ctype, expression=expression), tempfile.TemporaryDirectory() as d:
                path = Path(d) / "sample.c"
                path.write_text(f"#include <stdint.h>\nint f({ctype} value) {{ return {expression}; }}\n")
                status, diag = check([path])
                self.assertEqual(status, expected, diag)
                if expected:
                    self.assertIn(RULE, diag)
                    self.assertIn("sample.c:2:", diag)

    def test_unavailable_compiler_is_a_tool_error(self):
        self.assertEqual(check(["sample.c"], compiler="/missing/clang")[0], 2)

    def test_hook_dispatch(self):
        for path, expected in (("README.md", 0), ("firmware/temperature.h", None)):
            event = {"cwd": str(ROOT), "tool_input": {"file_path": path}}
            result = subprocess.run([sys.executable, "scripts/post_edit.py"], input=json.dumps(event),
                                    cwd=ROOT, capture_output=True, text=True)
            if expected is None:
                # Hook feedback must follow the learner's current acceptance result.
                firmware = subprocess.run(["bash", "scripts/check.sh"], cwd=ROOT, capture_output=True)
                expected = 2 if firmware.returncode else 0
            self.assertEqual(result.returncode, expected, result.stderr)

    def test_read_failure_then_retry(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "capability"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", "-Ifirmware", "firmware/capability.c",
                            "tests/test_capability.c", "-o", exe], cwd=ROOT, check=True)
            subprocess.run([exe], check=True)
