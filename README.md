# Optic Review Lab

Optic Review Lab checks AI-assisted C changes to optical-module telemetry. It runs a Clang diagnostic and behavioral tests in GitHub Actions, records review evidence for each commit in PostgreSQL, and exposes the results through two read-only MCP tools.

## See a review in one minute

1. Open the [original failing firmware run](https://github.com/Shrey-Parikh31/optic-review-lab/actions/runs/45927535041). The unimplemented decoder passed 0 of 5 temperature cases.
2. Read [the fix and its sixth test](https://github.com/Shrey-Parikh31/optic-review-lab/pull/1). The smallest negative reading is −1/256 °C. Integer division turns it into zero. [All six cases passed on the corrected revision.](https://github.com/Shrey-Parikh31/optic-review-lab/actions/runs/45956301996)
3. Inspect the [review-tooling run](https://github.com/Shrey-Parikh31/optic-review-lab/actions/runs/45956301962). On six fixed C examples, compilation alone missed all three defects. The guarded checks caught all three and accepted all three clean controls. The same run imported the PR into PostgreSQL and reported `review_pending` because no independent engineer had approved that revision.

## Run the firmware tests

From the repository root, run `bash scripts/check.sh` with Bash and a C11 compiler such as Clang or GCC. The expected result is `6/6 temperature cases passed`. On Windows, use WSL.

The [decoder](firmware/temperature.c) combines the two bytes in a 32-bit integer. Values with bit 15 set represent negative counts. Each count is 1/256 °C, so `19 80` gives +25.5 °C, `FF 80` gives −0.5 °C and `FF FF` gives −0.00390625 °C. Integer division would turn the last reading into zero. The [six test vectors](tests/test_temperature.c) include both ends of the range.

The inputs represent a supported sensor on a ready module. A separate [capability check](firmware/capability.c) distinguishes a failed read from an unsupported sensor. These host-side fixtures test the software interpretation of the bytes. Physical accuracy and link performance require hardware measurements. [CMIS 5.3, §§8.1.3.5 and 8.2.5](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf)

## Run the working review tools

Run `bash scripts/tooling.sh` for the analyzer, hook tests, simulated capability reads and the six-case evaluation. It runs independently of the six decoder assertions. The tooling CI job also starts PostgreSQL 16 and exercises both read-only MCP tools over stdio.

The review database records the PR head, workflow attempt, reviewer identity and reviewed SHA. The release query reports whether the last captured GitHub evidence supports that exact revision. The fixture demo imports measured evaluation results alongside synthetic review history.

See the [setup and commands](docs/run-the-lab.md), [learning roadmap](ROADMAP.md) and [problem research](docs/problem.md).
