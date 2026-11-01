"""
Replay each deterministic step and print clinic-specific checks across
pending-state and confirmed-booking events.

The engine is the sibling repo proof-of-agent-run, installed in this repo's
virtual environment with `pip install -e ../proof-of-agent-run`. TABLE, in
clinic/table.py, is the whitelist of what the engine may re-run.

Usage: python verify.py [traces/conv-0001.json]
"""

import json
import sys

from clinic.verification import verify_trace

path = sys.argv[1] if len(sys.argv) > 1 else "traces/conv-0001.json"

with open(path) as f:
    trace = json.load(f)

print(trace["run_id"])

for verdict in verify_trace(trace):
    detail = ""
    if "recorded" in verdict:
        detail = (
            f"  recorded={verdict['recorded']}"
            f" rederived={verdict['rederived']}"
        )
    if verdict.get("issues"):
        detail += "  " + "; ".join(verdict["issues"])
    print(
        f"  {verdict['index']:>2}  {verdict['name']:<22} "
        f"{verdict['status']}{detail}"
    )
