# How to help in this lab

Implement and verify requested changes. Explain the reasoning briefly. Preserve an exercise for the learner when they specifically request hands-on practice.

State the C units and the CMIS section behind each behavioral change. Keep the
host simulation deterministic. Run `bash scripts/check.sh` and report its exit
status and failing input. Preserve the existing acceptance cases.

Record agent assistance in the pull request. An agent suggestion, a passing CI
run and a human review each supply different evidence. Identify each explicitly.

OPTIC-RANGE-01 flags comparisons to constants outside an operand’s representable range. For a signed 16-bit sample, compare a signed sentinel only when its field contract specifies one. Preserve the difference between a failed capability read and a known unsupported sensor. Run `bash scripts/tooling.sh` for changes to these guardrails.
