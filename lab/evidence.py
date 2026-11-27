"""Import and read point-in-time snapshots of firmware review evidence."""
from hashlib import sha256
import json
from pathlib import Path

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

DB = Path(__file__).resolve().parents[1] / "db"


def migrate(conn):
    with conn.transaction():
        conn.execute((DB / "001_evidence.sql").read_text())


def ingest(conn, snapshot):
    """Retrying the identical capture is safe, including concurrent delivery."""
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    key = sha256(encoded).hexdigest()
    with conn.transaction():
        row = conn.execute(
            """INSERT INTO optic_snapshot (id, repo, pr, head_sha, captured_at, pr_author, origin)
               VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id""",
            (key, *(snapshot[k] for k in ("repo","pr","head_sha","captured_at","pr_author","origin"))),
        ).fetchone()
        if row is None:
            return key
        with conn.cursor() as cur:
            for run in snapshot["runs"]:
                args = tuple(run[k] for k in ("run_id","attempt","head_sha","status","conclusion","url"))
                cur.execute("INSERT INTO optic_run VALUES (%s,%s,%s,%s,%s,%s,%s)", (key, *args))
                for case in run.get("cases", []):
                    cur.execute("INSERT INTO optic_case_result VALUES (%s,%s,%s,%s,%s,%s)",
                                (key, run["run_id"], run["attempt"], case["id"], case["verdict"], Jsonb(case)))
            for review in snapshot["reviews"]:
                args = tuple(review[k] for k in ("review_id","reviewer","eligible","state","reviewed_sha","submitted_at"))
                cur.execute("INSERT INTO optic_review VALUES (%s,%s,%s,%s,%s,%s,%s)", (key, *args))
    return key


def review_status(conn, repo, pr, sha, origin="github"):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute((DB / "review_status.sql").read_text(), dict(repo=repo, pr=pr, sha=sha, origin=origin))
        return cur.fetchone() or {"decision": "unknown"}


def get_run(conn, run_id, origin="github"):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT r.*, s.repo, s.pr, s.captured_at, s.origin
                       FROM optic_run r JOIN optic_snapshot s ON s.id=r.snapshot_id
                       WHERE run_id=%s AND origin=%s ORDER BY s.captured_at DESC, s.id DESC, attempt DESC LIMIT 1""",
                    (run_id, origin))
        row = cur.fetchone()
        if row is None:
            return {"status": "unknown"}
        cur.execute("""SELECT details FROM optic_case_result WHERE snapshot_id=%s AND run_id=%s AND attempt=%s
                       ORDER BY case_id""", (row.pop("snapshot_id"), run_id, row["attempt"]))
        row["cases"] = [case["details"] for case in cur.fetchall()]
        return row
