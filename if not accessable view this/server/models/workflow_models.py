from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class GenerateWorkflowRequest(BaseModel):
    goal: str

class ComponentSchema(BaseModel):
    id: str
    name: str
    description: str
    category: str
    required_credentials: List[str]
    inputs: List[str]
    outputs: List[str]

class WorkflowNode(BaseModel):
    id: str
    label: str
    component_id: str

class WorkflowEdge(BaseModel):
    source: str
    target: str

class WorkflowGraph(BaseModel):
    workflow_name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str]

class GenerateWorkflowResponse(BaseModel):
    analysis: Optional[Dict[str, Any]] = {}
    research: Optional[Dict[str, Any]] = {}
    selected_components: List[str] = []
    workflow: Optional[WorkflowGraph] = None
    required_credentials: List[str] = []
    validation: Optional[ValidationResult] = None