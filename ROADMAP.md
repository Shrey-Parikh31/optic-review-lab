# From two bytes to a review decision

Make one small pull request per milestone. Before coding, predict a failure. Afterward, retain the command that demonstrates it, the passing control and one sentence about your design decision. Ask the agent for critique after your first attempt.

| Phase | What you learn and implement | Test that closes the phase |
| --- | --- | --- |
| 1. Decode a sample | Implement the C11 decoder in the README. Explain byte order, integer promotion, signed range and the fractional unit. Read the Bash script and trace its exit status from the test program to the CI job. | All five original vectors and your new vector pass. Show one failing test for a deliberate byte swap. |
| 2. Model a failed read | Define a small C result type for a simulated capability read and temperature sample. Choose how callers distinguish unavailable, unsupported and valid. Cite the upstream scenario and explain when to retry. | A failed read followed by a supported, ready read recovers. An unsupported sensor stays unsupported. Zero degrees is a valid reading. |
| 3. Check a patch from Bash and Python | Extend the script with an analysis stage. Write a Python check using Clang's syntax tree and type information to flag an impossible comparison between a signed 16-bit sample and 65535. Return a rule ID, file and line. Link that rule to its type-range rationale. | An out-of-range comparison triggers the rule, the same comparison on an unsigned 16-bit field is valid, and a comment containing the expression stays silent. A missing analyzer fails the check explicitly. Run in Linux CI and repeat the Bash entry point on Windows with WSL. |
| 4. Add an agent rule and hook | Turn the signedness finding into a short rule with one example. Wire the Bash check into a coding agent's post-edit hook for C files. Keep a CI check that runs when a contributor works without the hook. | Edit a fixture and capture the diagnostic in the agent session. A docs-only edit skips local compilation. A branch with the hook disabled still fails CI on the planted fault. |
| 5. Evaluate the reviewer | Write a Python runner that presents a labeled patch to the reviewer and records its verdict, the cited defect and elapsed time. Use both the SONiC-derived case and independent planted faults, paired with correct changes. | Freeze the case set. Compare the same patches with and without the rule, then change one model or workflow setting at a time. Report detected defects / faulty patches and false alarms / clean patches. Record failures and timeouts separately. |
| 6. Store review evidence in PostgreSQL | Write the schema migration, importer and release query described below. Learn keys, joins, transactions and retry behavior against a disposable PostgreSQL database. | Import the same delivery twice, trigger a partial import failure, and look up a commit before and after a new push. Each produces the expected history. |
| 7. Let an agent retrieve evidence | Implement two read-only Model Context Protocol (MCP) tools in Python: `get_run(run_id)` and `review_status(repo, pr, sha)`. Make an adoption example another engineer can follow from a clean checkout. | Query a known run, unknown ID and superseded commit. Tool results match SQL, including pending status. Demonstrate a human review against the current SHA before a release decision. |

## The first useful demo

After phase 4, open a practice PR with a faulty decoding change. Reproduce a diagnostic locally, inspect the CI result, fix the patch and explain the evidence in the PR. A plain compiler can accept an unsigned decoder that returns a plausible number. The behavioral tests and the type-aware rule cover different kinds of mistakes. The type-range rule is inspired by a separate QSFP ethtool report involving SFF-8636. Its sentinel convention belongs to that context. [Upstream ethtool patch](https://lists.openwall.net/netdev/2019/03/14/108)

For phase 5, start with a signedness error, byte swap, loss of fractional precision and a failed-read recovery case. Label each with its source, expected finding and clean counterpart. Keep expected answers out of the reviewer's context. Pin the patch, prompt, rules revision and tool versions. For model comparisons, repeat trials and record model ID, time, token use and cost when available. Show counts alongside rates and report missing usage as unknown. Use one held-out patch pair to check whether a rule generalizes. [SONiC capability-read report](https://github.com/sonic-net/sonic-platform-common/pull/756)

## Why PostgreSQL belongs here

Start with one question: **Which exact revision passed the required checks and received a still-current human approval?** A rerun on the same SHA is a different attempt. A new push creates a new revision. A reviewer can dismiss an approval. Preserving those distinctions is the database exercise.

Sketch these relationships before writing SQL:

- A revision belongs to one repository and PR. Store the full head SHA and track changes to the PR head.
- A run belongs to a revision and records workflow ID, run ID, attempt, rule version and model configuration. Each case result references its run and case version. Keep check outcomes and reviewer verdicts in separate columns.
- A review event records its GitHub source ID, reviewer identity, reviewed SHA, decision and time. Preserve dismissals and requested changes. Derive human approval from authenticated GitHub review events. An agent response or checkbox cannot create one.
- Give each import a unique delivery key. Write a run and its results in a transaction. Replaying the same delivery should leave the row counts unchanged, while a new attempt should get its own row.

Test the acceptance query against PostgreSQL itself. Passing checks and approval on A should produce a positive result for A while it is current. After pushing B, show A in the history and B pending. A dismissed review, missing result or failed latest required check should keep the current change pending or blocked. Test two concurrent imports of one delivery. Keep a saved SQL query and its result as your database portfolio artifact.

PostgreSQL covers the joins, constraints and transactions in that workflow. Small scanner payloads can use JSONB when their shape varies. Revisit Redis only if measured queue delays justify a separate worker. The planned data and access patterns give MongoDB and Cassandra no distinct job.

## Finish with evidence

Pick one change and trace it from the agent's suggestion to the C diff, a local command, CI run, PostgreSQL result and GitHub review on the same head SHA. Record both the PR head SHA and the tested SHA when CI tests a synthetic merge commit. If no second engineer reviews the work, report self-review and leave independent approval pending. Describe a merge gate as enforced only after verifying repository rules and attempting a blocked merge.

A portfolio demo can report the actual count of faulty patches detected, clean patches flagged, and median review time for the frozen suite. Keep the raw counts and commands alongside the conclusion. The lab measures review behavior on host-run cases.
