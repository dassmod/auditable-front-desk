"""
Replay a saved trace through the proof-of-agent-run engine and print one
line per step: its index, its name and the engine's verdict (match,
divergence, skipped, or a could-not-check reason such as unknown_guard).

The engine is the sibling repo proof-of-agent-run, installed in this repo's
virtual environment with `pip install -e ../proof-of-agent-run`. TABLE, in
clinic/table.py, is the whitelist of what the engine may re-run.

Usage: python verify.py [traces/conv-0001.json]
"""

import json
import sys

from replay.engine import replay_trace
from clinic.table import TABLE

path = sys.argv[1] if len(sys.argv) > 1 else "traces/conv-0001.json"

with open(path) as f:
    trace = json.load(f)

print(trace["run_id"])

for verdict in replay_trace(trace, TABLE):
    detail = ""
    if "recorded" in verdict:
        detail = (
            f"  recorded={verdict['recorded']}"
            f" rederived={verdict['rederived']}"
        )
    print(f"  {verdict['index']:>2}  {verdict['name']:<22} {verdict['status']}{detail}")
