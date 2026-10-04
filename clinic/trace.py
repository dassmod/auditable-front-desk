"""Records a run step by step and saves it as a trace file."""

import json

class Recorder:
    """Collects the steps of one run, in order."""

    def __init__(self, run_id):
        self.run_id = run_id
        self.steps = []
    
    def record(self, kind, name, inputs, outputs):
        """
        Append one step. `kind` is "deterministic" if it can be re-run from
        its inputs, else "nondeterministic".

        Inputs and outputs are copied through JSON, so later changes to the
        originals cannot alter the record.
        """
        self.steps.append({
            "index": len(self.steps),
            "kind": kind,
            "name": name,
            "inputs": json.loads(json.dumps(inputs)),
            "outputs": json.loads(json.dumps(outputs))
        })
    
    def save(self, path):
        """Write the run to `path` as JSON."""
        trace = {
            "run_id": self.run_id,
            "agent": "auditable-front-desk",
            "steps": self.steps
        }

        with open(path, "w") as f:
            json.dump(trace, f, indent=2)