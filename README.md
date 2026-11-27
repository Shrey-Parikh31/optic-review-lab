# Optic Review Lab

An engineer reviewing an AI-assisted change to optical module firmware needs to know whether the code still interprets telemetry correctly. This lab starts with a two-byte temperature reading from the Common Management Interface Specification (CMIS). The eventual review record should let a second engineer reproduce the failure, see which revision fixed it and find the human decision on that revision.

## Start here

You need Bash, Git and a C11 compiler such as Clang or GCC. On Windows, use WSL with GCC or Clang. Run these commands inside the repository:

```bash
git switch -c lab/temperature-decoder
bash scripts/check.sh
```

The starter compiles and prints `0/5 temperature cases passed`. Exit status 1 is the expected starting point. The decoder currently returns `NAN` for every input.

1. Open [the five test cases](tests/test_temperature.c). Work out `19 80` and `FF 80` on paper. The first byte is the most significant. One signed count represents 1/256 °C.
2. Implement [temperature_c](firmware/temperature.c) in about five lines. Choose the intermediate integer type yourself. Explain where the sign comes from and when the fractional part enters the calculation. Aim for portable C11 on a host machine.
3. Run the same Bash command. The original five cases should pass. Add one case of your own, predict the output, then briefly swap the two input bytes in your local implementation. Check which tests notice, undo that change and rerun.
4. Commit your fix and open a pull request. Include one failing input from the experiment and the CI run for the corrected patch. An agent reviewing your work should follow [the lab instructions](AGENTS.md).

The exercise assumes a supported temperature field on a ready module. A later exercise introduces a read failure and a retry. The byte fixtures run on your computer. Testing sensor accuracy, electrical behavior or link throughput requires a physical setup. [OIF CMIS 5.3, sections 8.1.3.5 and 8.2.5](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf)

## Run the working review tools

Run `bash scripts/tooling.sh` for the analyzer, hook tests, simulated capability reads and the six-case evaluation. It runs independently of the unfinished temperature decoder. The tooling CI job also starts PostgreSQL 16 and exercises both read-only MCP tools over stdio.

The review database records the PR head, workflow attempt, reviewer identity and reviewed SHA. The release query reports whether the last captured GitHub evidence supports that exact revision. The fixture demo imports measured evaluation results alongside synthetic review history.

See the [setup and commands](docs/run-the-lab.md), [learning roadmap](ROADMAP.md) and [problem research](docs/problem.md).
