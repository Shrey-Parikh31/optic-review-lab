"""Load the measured deterministic evaluation into an explicitly synthetic review."""
import argparse
import json
import os
from pathlib import Path

import psycopg
from .evidence import ingest, migrate, review_status


def fixture(results):
    sha = "a" * 40
    return dict(repo="example/optics", pr=1, head_sha=sha,
                captured_at="2026-01-01T12:00:00Z", pr_author="fixture-author", origin="fixture",
                runs=[dict(run_id=101, attempt=1, head_sha=sha, status="completed", conclusion="success",
                           url="fixture:run/101", cases=results)],
                reviews=[dict(review_id=201, reviewer="fixture-reviewer", eligible=True, state="APPROVED",
                              reviewed_sha=sha, submitted_at="2026-01-01T11:00:00Z")])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    row = fixture(report["guarded"]["results"])
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        migrate(conn)
        ingest(conn, row)
        print(json.dumps(review_status(conn, row["repo"], 1, row["head_sha"], "fixture"), default=str))


if __name__ == "__main__":
    main()
