from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from storage.workflow_store import add_workflow, list_workflows, get_workflow
from execution.engine import WorkflowEngine
from datetime import datetime

router = APIRouter(prefix="/workflows", tags=["workflows"])

class SaveWorkflowRequest(BaseModel):
    goal: str
    workflow_graph: Dict[str, Any]
    required_credentials: List[str] = []

class WorkflowResponse(BaseModel):
    id: str
    goal: str
    workflow_graph: Dict[str, Any]
    required_credentials: List[str]
    created_at: str

@router.post("/save", response_model=WorkflowResponse)
async def save_workflow(req: SaveWorkflowRequest):
    workflow = add_workflow({
        "goal": req.goal,
        "workflow_graph": req.workflow_graph,
        "required_credentials": req.required_credentials,
        "created_at": datetime.now().isoformat()
    })
    return workflow

@router.get("/", response_model=List[WorkflowResponse])
async def get_workflows():
    return list_workflows()

@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str):
    wf = get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    graph = wf["workflow_graph"]
    goal = wf.get("goal") or graph.get("goal", "")   # <-- THIS READS THE GOAL

    engine = WorkflowEngine()
    outputs = await engine.execute(graph, goal=goal)   # <-- THIS SENDS IT
    return {"status": "success", "outputs": outputs}

@router.get("/{workflow_id}/required-credentials", response_model=List[str])
async def get_required_credentials(workflow_id: str):
    import os
    wf = get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    missing = []
    for cred in wf.get("required_credentials", []):
        env_var = cred.upper()
        if not os.getenv(env_var):
            missing.append(env_var)
    return missing