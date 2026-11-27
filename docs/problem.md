# Reviewing changes to optical module telemetry

A firmware reviewer receives an AI-assisted change to a temperature decoder. It compiles, and the example in the pull request reads 25.5 °C. What happens below freezing? This lab starts with a check the reviewer can verify by hand. Later exercises connect that check to a particular commit and record who approved it, so the next engineer can recover the basis for the decision.

## Two handoff problems shaped the design

Razorpay's Fix My Itch catalog describes businesses struggling to verify unfamiliar suppliers before a purchase and manufacturers struggling to hold someone accountable for a missed pickup. The lab borrows one question from each. What evidence is available before a decision? Who owns the handoff? In a code review, that translates into a test result attached to the exact revision under review and a separate record of the engineer's decision. The firmware application is this project's interpretation of those entries. [Razorpay, Fix My Itch](https://razorpay.com/m/fix-my-itch/#all-problems)

## Two bytes can expose a plausible error

The Common Management Interface Specification (CMIS) defines a module temperature field at bytes 14 and 15 for paged-memory modules. It encodes a signed value in steps of 1/256 °C, with the most significant byte first. An unsigned decoder gives the right answer for `19 80` (25.5 °C), yet reports 255.5 °C for `FF 80` (−0.5 °C). One negative sample exposes the error. A host test establishes how the program interprets those bytes. Measuring a sensor's physical accuracy requires hardware. [OIF CMIS 5.3, §§8.1.3.5 and 8.2.5](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf)

## An upstream report gives the evaluation a second case

A SONiC contributor reported that a failed capability read could be presented as a definite answer about sensor support. An independent lab case can simulate a failed read followed by a successful retry. The expected result moves from “reading unavailable” to a valid sample, which could be 0 °C. A separate control covers a successful capability read that confirms an unsupported sensor. Label these cases as adaptations of a contributor report and the unsigned conversion as a deliberately planted mistake. [SONiC platform-common PR #756](https://github.com/sonic-net/sonic-platform-common/pull/756)

## What this adds to a portfolio

Tool Picker tests tool selection, an RBAC retrieval assistant checks access to retrieved material, and a CPU scheduling simulator explores scheduling policies. Here the learner's work is a reviewable C patch, a Bash command that reproduces the result, and evidence that a rule catches a specific defect while accepting a correct patch. A PostgreSQL exercise can then answer a practical release question: which revision passed these cases, and did the engineer approve that same revision? Counts from these fixtures apply to the published case set. Claims about optical link performance or production releases would need separate evidence.
