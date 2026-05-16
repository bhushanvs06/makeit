import json
import os
import uuid
from typing import List, Dict, Optional

STORAGE_FILE = "workflows.json"

def load_workflows() -> List[Dict]:
    if not os.path.exists(STORAGE_FILE):
        return []
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def save_workflows(workflows: List[Dict]):
    with open(STORAGE_FILE, "w") as f:
        json.dump(workflows, f, indent=2)

def add_workflow(workflow_data: Dict) -> Dict:
    workflows = load_workflows()
    workflow = {
        "id": str(uuid.uuid4()),
        "goal": workflow_data.get("goal", ""),
        "workflow_graph": workflow_data["workflow_graph"],
        "required_credentials": workflow_data.get("required_credentials", []),
        "created_at": workflow_data.get("created_at", "")
    }
    workflows.append(workflow)
    save_workflows(workflows)
    return workflow

def get_workflow(workflow_id: str) -> Optional[Dict]:
    workflows = load_workflows()
    for wf in workflows:
        if wf["id"] == workflow_id:
            return wf
    return None

def list_workflows() -> List[Dict]:
    return load_workflows()