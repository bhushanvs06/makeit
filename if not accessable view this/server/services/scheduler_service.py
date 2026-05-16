from apscheduler.schedulers.asyncio import AsyncIOScheduler
from storage.workflow_store import load_workflows
from execution.engine import WorkflowEngine
import logging

logger = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler()

async def execute_saved_workflow(workflow):
    engine = WorkflowEngine()
    logger.info(f"Scheduler running workflow: {workflow['id']}")
    try:
        outputs = await engine.execute(workflow["workflow_graph"])
        logger.info(f"Workflow {workflow['id']} finished: {outputs}")
    except Exception as e:
        logger.error(f"Workflow {workflow['id']} failed: {e}")

def load_and_schedule_all():
    """Schedule all saved workflows to run every 5 minutes (example)."""
    workflows = load_workflows()
    for wf in workflows:
        job_id = f"wf_{wf['id']}"
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                execute_saved_workflow,
                'interval',
                minutes=5,               # change as needed
                args=[wf],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled workflow {wf['id']} every 5 minutes")

def start_scheduler():
    scheduler.start()
    load_and_schedule_all()