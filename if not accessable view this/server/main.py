import signal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from api.websocket_routes import router as ws_router
from api.workflow_execution_routes import router as workflow_router
from services.scheduler_service import start_scheduler, scheduler
import logging

logger = logging.getLogger("main")

app = FastAPI(title="MakeIt Architect Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(api_router)
app.include_router(ws_router)
app.include_router(workflow_router)


@app.on_event("startup")
async def startup_event():
    """Start the background scheduler when the server starts."""
    start_scheduler()
    logger.info("✅ Scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("✅ Scheduler shut down")


# Optional: catch SIGINT/SIGTERM for cleaner exit
def handle_sigterm(signum, frame):
    logger.info("Received signal to stop. Shutting down gracefully.")
    if scheduler.running:
        scheduler.shutdown(wait=False)

signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)