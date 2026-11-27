"""Evaluate a tool-free model on the public case inputs using the Responses API."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .evaluate import CASES, score, task

PROMPT = "Review the C function against its stated contract. Flag a correctness defect or pass it. Give a short reason."
RULE = "Trace signed ranges, fractional units and failed reads. Check at least one boundary example before deciding."
SCHEMA = {"type":"object", "properties":{"verdict":{"type":"string","enum":["flag","pass"]},
          "evidence":{"type":"string"}}, "required":["verdict","evidence"],"additionalProperties":False}


def review(public_input, instructions, model, token):
    payload = dict(model=model, instructions=instructions, input=json.dumps(public_input), tools=[], store=False,
                   text={"format":{"type":"json_schema","name":"review","strict":True,"schema":SCHEMA}})
    request = Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(),
                      headers={"Content-Type":"application/json","Authorization":"Bearer " + token})
    with urlopen(request, timeout=60) as response:
        result = json.load(response)
    texts = [p["text"] for msg in result["output"] for p in msg.get("content",[]) if p.get("type")=="output_text"]
    verdict = json.loads("".join(texts))
    if verdict.get("verdict") not in ("flag","pass") or not isinstance(verdict.get("evidence"), str):
        raise ValueError("Invalid review result")
    return dict(verdict, model=result["model"], usage=result.get("usage"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    token = os.environ.get("OPENAI_API_KEY")
    if not token:
        parser.error("OPENAI_API_KEY is required for live model evaluation")
    public = [task(c) for c in CASES]
    report = {"case_hash":hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest(),
              "requested_model":args.model, "cost":None, "trials":{}}
    for mode, instructions in [("baseline",PROMPT),("with-rule",PROMPT+" "+RULE)]:
        rows = []
        for case in public:
            start = time.monotonic()
            try:
                outcome = review(case,instructions,args.model,token)
            except HTTPError as exc:
                outcome = {"verdict":"error","evidence":f"HTTP {exc.code}"}
            except (TimeoutError,socket.timeout):
                outcome = {"verdict":"timeout","evidence":"Request timed out"}
            except (OSError,KeyError,TypeError,ValueError) as exc:
                outcome = {"verdict":"error","evidence":type(exc).__name__}
            rows.append(dict(outcome,id=case["id"], elapsed_ms=round(1000*(time.monotonic()-start))))
        report["trials"][mode] = {"instructions":instructions, "counts":score(rows), "results":rows}
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    return int(any(t["counts"]["errors"] for t in report["trials"].values()))


if __name__=="__main__":
    sys.exit(main())
