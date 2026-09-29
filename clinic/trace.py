import json

class Recorder:
    def __init__(self, run_id):
        self.run_id = run_id
        self.steps = []
    
    def record(self, kind, name, inputs, outputs):
        self.steps.append({
            "index": len(self.steps),
            "kind": kind,
            "name": name,
            "inputs": json.loads(json.dumps(inputs)),
            "outputs": json.loads(json.dumps(outputs))
        })
    
    def save(self, path):
        trace = {
            "run_id": self.run_id,
            "agent": "auditable-front-desk",
            "steps": self.steps
        }

        with open(path, "w") as f:
            json.dump(trace, f, indent=2)