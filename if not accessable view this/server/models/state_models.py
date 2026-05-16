from typing import List, Dict, Any, Optional

class WorkflowState:
    def __init__(self, goal: str):
        self.goal = goal
        self.analysis: Dict[str, Any] = {}
        self.research: Dict[str, Any] = {}
        self.selected_components: List[str] = []
        self.workflow_graph: Dict[str, Any] = {
            "workflow_name": "generated_workflow",
            "nodes": [],
            "edges": []
        }
        self.required_credentials: List[str] = []
        self.validation_result: Optional[Dict[str, Any]] = None