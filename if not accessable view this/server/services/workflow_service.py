from agents.orchestrator_agent import OrchestratorAgent
from models.state_models import WorkflowState

class WorkflowService:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()

    async def generate(self, goal: str, log_callback) -> WorkflowState:
        return await self.orchestrator.run(goal, log_callback)