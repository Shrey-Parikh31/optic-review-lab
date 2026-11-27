import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
import sys
import unittest
from unittest.mock import patch
import uuid

import psycopg
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from lab.demo import fixture
from lab.evidence import get_run, ingest, migrate, review_status
from lab.sync import capture


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.dsn = os.environ["OPTIC_TEST_DSN"]
        self.conn = psycopg.connect(self.dsn, autocommit=True)
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        self.row = fixture([{"id":"m01","verdict":"flag"}])
        self.row["repo"] = "fixture/" + uuid.uuid4().hex
        self.row["runs"][0]["run_id"] = uuid.uuid4().int % 2**60

    def status(self):
        return review_status(self.conn, self.row["repo"], 1, "a" * 40, "fixture")["decision"]

    def test_atomic_replay(self):
        def insert(_):
            with psycopg.connect(self.dsn, autocommit=True) as conn:
                return ingest(conn, self.row)
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(insert, range(2)))
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM optic_case_result WHERE snapshot_id=%s",
                                           (ids[0],)).fetchone()[0], 1)
        broken = deepcopy(self.row)
        broken["captured_at"] = "2026-01-01T14:00:00Z"
        broken["runs"][0]["cases"] += [{"id":"x", "verdict":"invalid"}]
        with self.assertRaises(psycopg.errors.CheckViolation):
            ingest(self.conn, broken)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM optic_snapshot WHERE repo=%s",
                                           (self.row["repo"],)).fetchone()[0], 1)

    def test_decisions(self):
        for hour, state, reviewer, eligible, status in [
            (12,"APPROVED","peer",True,"reviewed"),
            (13,"DISMISSED","peer",True,"review_pending"),
            (14,"APPROVED","fixture-author",True,"review_pending"),
            (15,"APPROVED","bot",False,"review_pending"),
            (16,"CHANGES_REQUESTED","peer",True,"changes_requested"),
        ]:
            with self.subTest(state=state, reviewer=reviewer):
                self.row["captured_at"] = f"2026-01-01T{hour}:00:00Z"
                self.row["reviews"][0].update(state=state, reviewer=reviewer, eligible=eligible)
                ingest(self.conn, self.row)
                self.assertEqual(self.status(), status)
        self.row["head_sha"] = "b" * 40
        self.row["captured_at"] = "2026-01-01T17:00:00Z"
        self.row["reviews"] = []
        ingest(self.conn, self.row)
        self.assertEqual(self.status(), "superseded")
        self.assertEqual(review_status(self.conn,self.row["repo"],1,"b"*40,"fixture")["decision"], "checks_pending")

    def test_attempts_and_provenance(self):
        self.row["runs"].append(dict(self.row["runs"][0], attempt=2, conclusion="failure"))
        ingest(self.conn, self.row)
        self.assertEqual(self.status(), "checks_failed")
        self.assertEqual(get_run(self.conn,self.row["runs"][0]["run_id"],"fixture")["attempt"], 2)
        self.assertEqual(review_status(self.conn,self.row["repo"],1,"a"*40)["decision"], "unknown")

    def test_mcp_over_stdio(self):
        ingest(self.conn, self.row)
        async def exercise():
            params = StdioServerParameters(command=sys.executable, args=["-m","lab.mcp_server"],
                          env={"OPTIC_READ_DSN":self.dsn,"OPTIC_SOURCE":"fixture"})
            async with stdio_client(params) as streams, ClientSession(*streams) as session:
                await session.initialize()
                tools = await session.list_tools()
                self.assertEqual({t.name for t in tools.tools},{"get_run","review_status"})
                for tool,args,field,expected in [
                    ("get_run",{"run_id":self.row["runs"][0]["run_id"]},"attempt",1),
                    ("get_run",{"run_id":-1},"status","unknown"),
                    ("review_status",{"repo":self.row["repo"],"pr":1,"sha":"a"*40},"decision","reviewed"),
                    ("review_status",{"repo":self.row["repo"],"pr":1,"sha":"b"*40},"decision","unknown"),
                ]:
                    response = await session.call_tool(tool,args)
                    self.assertFalse(response.isError, response.content)
                    self.assertEqual(json.loads(response.content[0].text)[field],expected)
        asyncio.run(exercise())

    def test_collection_filters_and_racing_push(self):
        pull = {"head":{"sha":"a"*40},"user":{"login":"author"}}
        runs = [{"pull_requests":[{"number":2}],"id":1,"run_attempt":1,"head_sha":"a"*40,
                 "status":"completed","conclusion":"success","html_url":"fixture:run/1"}]
        with patch("lab.sync.api",side_effect=[pull,{"workflow_runs":runs},[],pull]):
            self.assertEqual(capture("example/optics",1)["runs"],[])
        changed = dict(pull, head={"sha":"b"*40})
        with patch("lab.sync.api",side_effect=[pull,{"workflow_runs":[]},[],changed]):
            with self.assertRaises(RuntimeError):
                capture("example/optics",1)
