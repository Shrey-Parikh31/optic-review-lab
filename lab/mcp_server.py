"""Read-only MCP tools over stored review evidence."""
import os
import psycopg
from mcp.server.fastmcp import FastMCP
from . import evidence

server = FastMCP("optic-review-lab")


def read(query, *args):
    with psycopg.connect(os.environ["OPTIC_READ_DSN"], options="-c default_transaction_read_only=on") as conn:
        return query(conn, *args, origin=os.environ.get("OPTIC_SOURCE", "github"))


@server.tool()
def get_run(run_id: int) -> dict:
    """Read the latest captured attempt and any imported case details."""
    return read(evidence.get_run, run_id)


@server.tool()
def review_status(repo: str, pr: int, sha: str) -> dict:
    """Read the last captured review decision for a repository, PR and full head SHA."""
    return read(evidence.review_status, repo, pr, sha)


if __name__ == "__main__":
    server.run(transport="stdio")
