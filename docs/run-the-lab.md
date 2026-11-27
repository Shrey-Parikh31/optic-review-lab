# Run the review lab

## See a defect that compiles

From the repository root, run `bash scripts/tooling.sh` with Bash, Python 3 and Clang on your path. It checks the firmware with Clang's type-aware diagnostic, tests the review hook and capability state, and compares two deterministic reviewers. The six candidates contain three defects and three clean controls. The range case is adapted from the ethtool report, the read-failure case from SONiC, and the voltage conversion error is planted. The range sentinel is specific to its fixture.

```bash
mkdir -p .lab
python3 -m lab.evaluate compare --output .lab/evaluation.json
python3 -m lab.evaluate export --output .lab/inputs.json
```

The exported file contains contracts and candidate code. A reviewer can return a JSON array with one object per ID, such as `{"id":"m01","verdict":"flag","evidence":"reason"}`. Run `python3 -m lab.evaluate score --predictions .lab/predictions.json`. Inspect the reason as well as each verdict. This small suite is for calibration. A future held-out case should come from an unfamiliar change.

For an optional live comparison, set your own `OPENAI_API_KEY` and run `python3 -m lab.model_review --model YOUR_MODEL_ID --output .lab/model.json`. It sends the six exported examples twice to the Responses API, once with the base instructions and once with a review rule. It records the returned model ID, usage, elapsed time, verdicts and errors. This uses the API account's billing. The deterministic command runs offline.

## Use the hook

Claude Code reads `.claude/settings.json` when the project hooks are trusted. The post-edit hook checks C source and headers in `firmware/`. A compiler diagnostic or failing temperature test returns feedback to the agent. Replay the same event without starting a model session:

```bash
printf '%s\n' '{"tool_input":{"file_path":"firmware/temperature.c"}}' | python3 scripts/post_edit.py
```

The unfinished decoder produces exit 2 from this hook. Changing a Markdown file skips the build. CI invokes the underlying checks independently of the editor.

## Query the database and MCP tools

Use Python 3.12 and a disposable PostgreSQL instance. The Compose file binds port 55432 to localhost and uses a development-only password. If PostgreSQL already runs elsewhere, use a dedicated lab database and its own connection string.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
docker compose up -d --wait
export DATABASE_URL=postgresql://optic:lab-only@localhost:55432/optics
OPTIC_TEST_DSN="$DATABASE_URL" python -m unittest discover -s tests -p test_evidence.py -v
python -m lab.demo .lab/evaluation.json
```

The demo stores your six measured results with a synthetic run and named fixture reviewer. It labels both as fixtures. To collect real evidence, set a GitHub token with read access to Actions and pull requests in your shell and run `python -m lab.sync OWNER/REPO PR_NUMBER` with `GITHUB_TOKEN` set. The importer reads the named repository's `check.yml` PR runs and GitHub reviews, rechecks the head, and commits a complete snapshot in one transaction. A later capture preserves earlier observations. The API capture stores workflow conclusions; detailed case rows are available for imported local evaluation reports.

Run the MCP server through a stdio-capable client with program `.venv/bin/python`, arguments `-m lab.mcp_server`, and the repository root as its working directory. Set `OPTIC_READ_DSN` in the server environment. A dedicated PostgreSQL login with SELECT on the four optic tables is suitable for real data. The server also opens its connection in read-only transaction mode. The server needs no GitHub token. For the local demo use `OPTIC_READ_DSN=$DATABASE_URL` and `OPTIC_SOURCE=fixture`. For collected records the default source is `github`.

Ask for `get_run(101)` to see the synthetic run and case details, then `review_status("example/optics", 1, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")` to see the decision. The integration test performs the actual MCP handshake, lists the tools and calls them.

The release query evaluates the latest captured state. It requires a successful firmware workflow for that PR/head and an eligible independent GitHub review. Changes requested, dismissed approvals, a newer failing attempt or a new head change that answer. The scope is advisory: repository branch protection, optical hardware validation and physical release authority are outside this demo. Stop the local database with `docker compose stop`.
