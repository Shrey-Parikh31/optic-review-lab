"""Collect authenticated GitHub evidence for one PR and import it atomically."""
import argparse
from datetime import datetime, timezone
import json
import os
import re
from urllib.request import Request, urlopen

import psycopg
from .evidence import ingest, migrate, review_status


def api(path):
    request = Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def pages(path, key=None):
    join = "&" if "?" in path else "?"
    page = 1
    while True:
        data = api(f"{path}{join}per_page=100&page={page}")
        rows = data[key] if key else data
        yield from rows
        if len(rows) < 100:
            return
        page += 1


def capture(repo, pr):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or pr < 1:
        raise ValueError("Expected owner/repository and a positive PR number")
    start = datetime.now(timezone.utc).isoformat()
    base = f"/repos/{repo}"
    path = f"{base}/pulls/{pr}"
    pull = api(path)
    sha = pull["head"]["sha"]
    run_path = f"{base}/actions/workflows/check.yml/runs?event=pull_request&head_sha={sha}"
    runs = []
    for run in pages(run_path, "workflow_runs"):
        if not any(p["number"] == pr for p in run["pull_requests"]):
            continue
        runs.append(dict(run_id=run["id"], attempt=run["run_attempt"], head_sha=run["head_sha"],
                         status=run["status"], conclusion=run["conclusion"], url=run["html_url"]))
    reviews = []
    for r in pages(path + "/reviews"):
        if r.get("submitted_at") and r.get("user") and r.get("commit_id"):
            reviews.append(dict(review_id=r["id"], reviewer=r["user"]["login"], state=r["state"],
                                eligible=r["user"]["type"] == "User" and
                                r["author_association"] in {"OWNER","MEMBER","COLLABORATOR"},
                                reviewed_sha=r["commit_id"], submitted_at=r["submitted_at"]))
    if api(path)["head"]["sha"] != sha:
        raise RuntimeError("PR head changed during collection. Retry for the new revision.")
    return dict(repo=repo, pr=pr, head_sha=sha, captured_at=start, pr_author=pull["user"]["login"],
                origin="github", runs=runs, reviews=reviews)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo")
    parser.add_argument("pr", type=int)
    args = parser.parse_args()
    snapshot = capture(args.repo, args.pr)
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        migrate(conn)
        key = ingest(conn, snapshot)
        status = review_status(conn, args.repo, args.pr, snapshot["head_sha"])
        print(json.dumps({"snapshot": key, **status}, default=str))


if __name__ == "__main__":
    main()
