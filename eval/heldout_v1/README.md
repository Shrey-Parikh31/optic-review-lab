# Does the firmware review rule help?

On eight new synthetic C patches, GPT-6.2-Sol found the same four defects and accepted the same four clean changes with either prompt. The rule added no correct verdicts in this run. It did prompt the reviewer to explain boundary inputs even for several clean patches. [Per-patch answers, latency and token usage](results.json)

| Reviewer setting | Defects found | Misses | False alarms on clean patches | Median wall time per patch |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 4/4 | 0 | 0/4 | 4.76 s |
| With firmware rule | 4/4 | 0 | 0/4 | 5.91 s |

For example, both prompts flagged the latch change at exactly 75 °C. An active alarm must stay active there, but the proposed comparison cleared it. Both prompts also accepted the wraparound counter change. The extra rule elicited an explicit example of the counter moving from 65535 to 0.

## How the comparison was run

- Eight synthetic patches were prepared separately from the original six calibration cases. The contracts cover offset-binary counts, wrapping counters, signed rounding, retry limits, hysteresis, bit-field updates, valid zero samples and unsigned averages.
- Before review, a C11 compiler built each reference and proposed function. Executable examples checked the expected result. All eight references passed. Four candidate implementations failed at least one example, and the four clean controls passed. The fixture digest is in the measured result.
- Each patch went through two independent, ephemeral CLI sessions using the same model and medium reasoning effort. The model received a contract and unified diff. The fixture labels, case IDs, executable tests, the other response and the answer key were excluded. Sessions ran in an empty temporary directory. The runner checked the event stream for tool activity.
- Both prompts used the same review request. The treatment appended the pre-existing instruction: “Trace signed ranges, fractional units and failed reads. Check at least one boundary example before deciding.” The patch order was seeded and the first prompt alternated between patches.
- A miss means a faulty patch was passed. A false alarm means a clean patch was flagged. The written reasons for all eight flags identified the expected defects. Time includes CLI startup, network and inference. There were 16 successful reviews and no missing responses in the measured run.

One pair per patch and eight short patches give limited power to detect a difference. Both arms reached the maximum score. The timings describe this run and include service variability. A future independent assessment would need fresh, more difficult patches, with repeated trials for timing or reliability claims. The results here describe a model review of synthetic firmware code.

## Reproduce the run

Use Python 3, a C11 compiler named `cc` on your path, and a signed-in Codex CLI that offers the selected model. The measured CLI version is recorded in the JSON. From the repository root:

```bash
mkdir -p .lab
python3 -m lab.heldout --output .lab/heldout-rerun.json
```

This makes 16 model calls through your Codex account. Use a fresh output filename for each experiment. The runner validates the labels first and records the verdict, explanation, latency, available token usage and prompt hash after each call. The repository CI verifies the C fixtures and paired prompts offline.

[Fixture definitions and answer key](cases.json) · [Experiment runner](../../lab/heldout.py)
