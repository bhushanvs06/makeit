import os
import re
import json
import logging

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from models.workflow_models import GenerateWorkflowRequest, GenerateWorkflowResponse
from services.workflow_service import WorkflowService
from services.websocket_manager import manager
from registry.component_registry import get_components, COMPONENTS
from execution.engine import WorkflowEngine
from storage.workflow_store import load_workflows

logger = logging.getLogger("api")
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# CREDENTIALS INFO
# ═══════════════════════════════════════════════════════════════════
@router.get("/credentials-info")
async def credentials_info():
    info = {}
    for comp in COMPONENTS:
        for cred in comp.get("required_credentials", []):
            env_var = cred.upper()
            info[cred] = {
                "env_var": env_var,
                "set": bool(os.getenv(env_var)),
                "description": f"Required for {comp['name']}"
            }
    return info


# ═══════════════════════════════════════════════════════════════════
# HEALTH + COMPONENT LIST
# ═══════════════════════════════════════════════════════════════════
@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/components")
async def list_components():
    return get_components()


# ═══════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════
from pydantic import BaseModel

class SettingsUpdate(BaseModel):
    whatsapp_listener_enabled: bool

@router.get("/settings")
async def get_settings():
    from services.settings_manager import SettingsManager
    return {"whatsapp_listener_enabled": SettingsManager.get("whatsapp_listener_enabled", False)}

@router.post("/settings")
async def update_settings(req: SettingsUpdate):
    from services.settings_manager import SettingsManager
    SettingsManager.set("whatsapp_listener_enabled", req.whatsapp_listener_enabled)
    return {"status": "ok", "whatsapp_listener_enabled": req.whatsapp_listener_enabled}



# ═══════════════════════════════════════════════════════════════════
# GENERATE WORKFLOW (design only – does NOT execute)
# ═══════════════════════════════════════════════════════════════════
@router.post("/generate-workflow", response_model=GenerateWorkflowResponse)
async def generate_workflow(req: GenerateWorkflowRequest, request: Request):
    service = WorkflowService()

    async def log_callback(agent: str, message: str):
        await manager.broadcast({"agent": agent, "message": message})

    # ── Smart goal augmentation ────────────────────────────────────
    # Only auto-append "write to Google Sheet" for simple list/search goals
    # where the user clearly wants the results saved but didn't say so.
    original_goal = req.goal.strip()
    augmented_goal = original_goal
    goal_lower = original_goal.lower()

    # These patterns indicate a pure-data-fetch goal where storage makes sense
    list_patterns = [
        r"(create|make|generate|build|produce|give)\s+(a\s+)?list",
        r"(find|search|get|fetch|retrieve)\s+(the\s+)?(top|best|latest)",
        r"(search|look)\s+(for|up)",
        r"(what|who)\s+(are|is)\s+the\s+(top|best)",
    ]

    # Skip augmentation if the goal already mentions any real-world action
    _no_augment_words = [
        "sheet", "spreadsheet", "excel", "google doc", "doc ", "drive",
        "whatsapp", "send", "email", "gmail", "message", "sms", "notify", "mail",
        "calendar", "event", "schedule", "remind", "reminder", "meeting", "meet",
        "create a", "set up", "book a", "add to",
    ]
    already_specified = any(w in goal_lower for w in _no_augment_words)

    # Also skip if the goal contains 2+ action conjunctions (user is composing a full pipeline)
    action_conjunction_count = len(re.findall(r"\b(and|then|after|,)\b", goal_lower))

    should_augment = (
        not already_specified
        and action_conjunction_count < 2
        and any(re.search(p, original_goal, re.IGNORECASE) for p in list_patterns)
    )

    if should_augment:
        augmented_goal = original_goal + " and write the results to a Google Sheet"
        await log_callback("System", "📊 Automatically added sheet storage to goal")


    result = await service.generate(augmented_goal, log_callback)

    return GenerateWorkflowResponse(
        analysis=result.analysis,
        research=result.research,
        selected_components=result.selected_components,
        workflow=result.workflow_graph,
        required_credentials=result.required_credentials,
        validation=result.validation_result
    )


# ═══════════════════════════════════════════════════════════════════
# EXECUTE WORKFLOW (run a pre-designed graph immediately)
# ═══════════════════════════════════════════════════════════════════
@router.post("/execute-workflow")
async def execute_workflow(request: Request):
    """
    Execute a workflow graph directly (no agent pipeline).
    Body: { "workflow": { nodes, edges, goal }, "inputs": {} }
    """
    body = await request.json()
    graph  = body.get("workflow") or body.get("graph")
    inputs = body.get("inputs", {})

    if not graph:
        raise HTTPException(status_code=400, detail="'workflow' field is required")

    engine = WorkflowEngine()
    outputs = await engine.execute(graph, node_outputs=inputs, goal=graph.get("goal", ""))
    return {"status": "ok", "outputs": {k: v for k, v in outputs.items()}}


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# WHATSAPP WEBHOOK  ←  Twilio posts here for every incoming message
# ═══════════════════════════════════════════════════════════════════
@router.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Interactive WhatsApp listener.
    Handles:
      1. 'master' commands: Generates and executes a workflow on the fly.
      2. Ongoing sessions: Resumes a paused workflow using the user's reply.
      3. New messages: Checks for legacy triggers, else runs a basic chatbot.
    """
    form_data   = await request.form()
    from_number = str(form_data.get("From", "")).strip()   # e.g. "whatsapp:+919876543210"
    body_text   = str(form_data.get("Body", "")).strip()
    num_media   = int(form_data.get("NumMedia", 0))

    logger.info(f"📱 Incoming WhatsApp from {from_number}: {body_text!r}")

    from services.settings_manager import SettingsManager
    if not SettingsManager.get("whatsapp_listener_enabled", False):
        logger.info("WhatsApp listener is disabled. Ignoring message.")
        return PlainTextResponse("", media_type="text/xml")

    if not body_text and num_media == 0:
        return PlainTextResponse("", media_type="text/xml")

    # Strip the "whatsapp:" prefix
    sender_phone = from_number.replace("whatsapp:", "").replace("+", "").strip()

    twiml_ack = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        '<Message>✅ MakeIt is working on your request…</Message>'
        '</Response>'
    )

    # ── 1. Master Command ──
    if body_text.lower().startswith("master "):
        goal = body_text[7:].strip()
        background_tasks.add_task(_run_master_command, goal, sender_phone, from_number)
        return PlainTextResponse(twiml_ack, media_type="text/xml")

    # ── 2. Ongoing Session Resume ──
    from services.conversation_manager import ConversationManager
    session = ConversationManager.get_session(sender_phone)
    if session:
        background_tasks.add_task(_resume_workflow, session, body_text, sender_phone)
        # Twilio requires a TwiML response, but we might just want to be silent if resuming
        return PlainTextResponse("", media_type="text/xml")

    # ── 3. Check for saved trigger workflows (Legacy) ──
    matched_saved = False
    for wf in load_workflows():
        nodes = wf.get("workflow_graph", {}).get("nodes", [])
        if any(n.get("component_id") == "whatsapp_trigger" for n in nodes):
            initial = {
                "whatsapp_trigger": {
                    "message_text": body_text,
                    "sender_id":    from_number,
                    "to":           from_number,
                    "recipient_id": sender_phone,
                }
            }
            background_tasks.add_task(_run_saved_workflow, wf["workflow_graph"], initial, body_text)
            matched_saved = True
            break

    # ── 4. If no session, no master, no legacy trigger → Chatbot ──
    if not matched_saved:
        background_tasks.add_task(_run_chatbot, body_text, sender_phone, from_number)
        return PlainTextResponse("", media_type="text/xml")

    return PlainTextResponse(twiml_ack, media_type="text/xml")


# ── Helper: run a saved whatsapp_trigger workflow ──────────────────────────
async def _run_saved_workflow(graph: dict, initial_outputs: dict, goal: str):
    try:
        engine = WorkflowEngine()
        await engine.execute(graph, node_outputs=initial_outputs, goal=goal)
        logger.info("✅ Saved WhatsApp-trigger workflow completed")
    except Exception as e:
        logger.error(f"❌ Saved workflow error: {e}")


# ── Helper: Master Command (Generate + Execute) ────────────────────────────
async def _run_master_command(goal: str, sender_phone: str, sender_full: str):
    logger.info(f"🤖 Master command activated for: {goal!r}")
    
    # Send immediate direct feedback
    await _send_wa_reply(sender_phone, "Master mode activated. Generating your workflow…")

    async def _noop_log(agent, msg):
        pass

    try:
        service = WorkflowService()
        result  = await service.generate(goal, _noop_log)
        graph   = result.workflow_graph

        if not graph or not graph.get("nodes"):
            await _send_wa_reply(sender_phone, f"Sorry, I couldn't generate a workflow for: {goal}")
            return

        for node in graph.get("nodes", []):
            node.setdefault("inputs", {})
        
        initial = {
            "whatsapp_trigger": {
                "message_text": goal,
                "sender_id":    sender_full,
                "to":           sender_full,
                "recipient_id": sender_phone,
                "phone_number": sender_phone,
            }
        }

        engine  = WorkflowEngine()
        outputs = await engine.execute(graph, node_outputs=initial, goal=goal)

        final_content = _extract_final_content(outputs)
        if final_content:
            await _send_wa_reply(sender_phone, final_content)
        else:
            # Check if a whatsapp component successfully sent something
            sent = any(isinstance(v, dict) and v.get("send_status") == "sent" for v in outputs.values())
            if not sent:
                await _send_wa_reply(sender_phone, "Workflow execution completed successfully.")

    except Exception as e:
        logger.error(f"Master command error: {e}", exc_info=True)
        await _send_wa_reply(sender_phone, f"⚠️ Error: {str(e)[:200]}")


# ── Helper: Resume Paused Session ──────────────────────────────────────────
async def _resume_workflow(session: dict, user_reply: str, sender_phone: str):
    from services.conversation_manager import ConversationManager
    engine = WorkflowEngine()
    try:
        outputs = await engine.resume(session, user_reply)
        
        if isinstance(outputs, dict) and outputs.get("__status__") == "paused":
            # Workflow paused again (another question asked)
            ConversationManager.save_session(sender_phone, outputs)
        else:
            # Workflow completed, clear the session
            ConversationManager.clear_session(sender_phone)
            
            # Send final content if applicable
            final_content = _extract_final_content(outputs)
            if final_content:
                await _send_wa_reply(sender_phone, final_content)
                
    except Exception as e:
        logger.error(f"Error resuming workflow: {e}", exc_info=True)
        ConversationManager.clear_session(sender_phone)
        await _send_wa_reply(sender_phone, "⚠️ Sorry, an error occurred while resuming the workflow.")


# ── Helper: Basic Chatbot ──────────────────────────────────────────────────
async def _run_chatbot(message: str, sender_phone: str, sender_full: str):
    """A simple conversational response."""
    try:
        from services.gemini_service import GeminiService
        llm = GeminiService()
        prompt = (
            "You are MakeIt, a helpful AI assistant operating on WhatsApp. "
            "Respond naturally and concisely to the user's message. "
            "Do not include meta-commentary, just the reply.\n\n"
            f"User: {message}"
        )
        reply = await llm.generate(prompt)
        await _send_wa_reply(sender_phone, reply.strip())
    except Exception as e:
        logger.error(f"Chatbot error: {e}")



def _extract_final_content(outputs: dict) -> str:
    """
    Walk the node outputs and return the last substantial AI-generated content.
    Returns empty string if a whatsapp_sender already ran (it sent the reply itself).
    """
    # If whatsapp_sender already ran successfully, don't send a duplicate
    for out in outputs.values():
        if isinstance(out, dict) and out.get("send_status") == "sent":
            return ""

    # Otherwise find the last LLM output
    content = ""
    for out in outputs.values():
        if not isinstance(out, dict):
            continue
        candidate = (
            out.get("formatted_data") or
            out.get("ai_response") or
            out.get("message_body") or
            out.get("text") or
            ""
        )
        if candidate and len(candidate) > len(content):
            content = candidate
    return content.strip()


async def _send_wa_reply(phone: str, message: str):
    """Send a WhatsApp message via Twilio (used for auto-workflow replies)."""
    try:
        from twilio.rest import Client as TwilioClient
        account_sid  = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token   = os.getenv("TWILIO_AUTH_TOKEN")
        from_number  = os.getenv("TWILIO_WHATSAPP_NUMBER")
        if not all([account_sid, auth_token, from_number]):
            logger.warning("_send_wa_reply: Twilio credentials not configured")
            return
        client = TwilioClient(account_sid, auth_token)
        client.messages.create(
            body=message[:1500],          # WhatsApp 1600-char limit with buffer
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:+{phone}"
        )
    except Exception as e:
        logger.error(f"_send_wa_reply error: {e}")