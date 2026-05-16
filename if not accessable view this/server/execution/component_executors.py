"""
Complete component_executors.py – production‑ready implementations for all
MakeIt components.  Uses official Google APIs (Sheets, Docs, Calendar, Gmail,
Meet) when credentials are available, falls back to simulation otherwise.
"""

import os
import asyncio
import logging
import json
import re
from datetime import datetime, timedelta

logger = logging.getLogger("executor")

# ── Optional Twilio ──────────────────────────────────────────────
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None  # type: ignore

# ── Optional Google API clients (lazy import inside functions) ───
# We'll build them on first use to avoid slowing startup.

# ── Helpers ──────────────────────────────────────────────────────

# ── All Google API scopes needed across all executors ─────────────────────
_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
]

def _get_google_creds():
    """Return credentials from a service account JSON file or OAuth refresh token."""
    # 1. Service account (preferred for server-to-server)
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_file and os.path.exists(sa_file):
        from google.oauth2.service_account import Credentials
        return Credentials.from_service_account_file(sa_file, scopes=_GOOGLE_SCOPES)
    
    # 2. OAuth user credentials (requires refresh token)
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if client_id and client_secret and refresh_token:
        from google.oauth2.credentials import Credentials
        return Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=_GOOGLE_SCOPES,
        )
    return None

def _pick(inputs: dict, keys: list, exclude: list = None) -> str:
    """Helper to pick the first non-empty, non-placeholder value from inputs."""
    if exclude is None:
        exclude = ["", None, "Hello from MakeIt!", "No prompt provided"]
    for k in keys:
        val = inputs.get(k)
        if val and str(val).strip() not in exclude:
            return str(val).strip()
    return ""

# ═════════════════════════════════════════════════════════════════
# WHATSAPP SENDER
# ═════════════════════════════════════════════════════════════════
async def whatsapp_sender(inputs: dict) -> dict:
    if not TWILIO_AVAILABLE:
        return {"send_status": "error", "error": "Twilio not installed. Run: pip install twilio"}

    # Normalise recipient: strip whatsapp: prefix, then ensure there is exactly one leading +
    raw_recipient = (
        inputs.get("recipient_id") or inputs.get("to") or
        inputs.get("phone_number") or inputs.get("sender_id") or
        os.getenv("TEST_WHATSAPP_NUMBER", "")
    ).strip().replace("whatsapp:", "").strip()
    # Remove any existing + so we can add exactly one back
    recipient_digits = raw_recipient.lstrip("+")

    if not recipient_digits:
        return {"send_status": "error", "error": "No recipient phone number"}

    # Check all possible content fields in priority order; skip placeholder/empty values
    PLACEHOLDER_PHRASES = {"Hello from MakeIt!", "No prompt provided", ""}
    message_body = ""
    for field in ["formatted_data", "ai_response", "message_body", "body", "text", "meet_link", "event_link", "message_text"]:
        candidate = str(inputs.get(field, "")).strip()
        if candidate and candidate not in PLACEHOLDER_PHRASES:
            message_body = candidate
            break

    if not message_body:
        return {
            "send_status": "error",
            "error": "No valid message content – check that a content-generating node runs before whatsapp_sender"
        }

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "").strip().lstrip("+")
    if not all([account_sid, auth_token, from_number]):
        return {"send_status": "error", "error": "Twilio credentials missing (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_NUMBER)"}

    try:
        client = TwilioClient(account_sid, auth_token)
        msg = client.messages.create(
            body=message_body[:1500],          # WhatsApp 1600-char limit with buffer
            from_=f"whatsapp:+{from_number}",
            to=f"whatsapp:+{recipient_digits}"
        )
        logger.info(f"✅ WhatsApp sent to +{recipient_digits}: {message_body[:80]}")
        return {"send_status": "sent", "message_sid": msg.sid, "to": recipient_digits, "body": message_body}
    except Exception as e:
        logger.error(f"Twilio error: {e}")
        return {"send_status": "error", "error": str(e)}

async def whatsapp_reply(inputs: dict) -> dict:
    """Send a reply back to the user without pausing the workflow.
    This is effectively identical to whatsapp_sender but explicitly expects a message_body 
    and uses the injected phone number.
    """
    return await whatsapp_sender(inputs)

async def whatsapp_ask(inputs: dict) -> dict:
    """Send a question to the user and pause the workflow until they reply."""
    question = _pick(inputs, ["question", "message_body", "text"], exclude=["", None])
    if not question:
        question = "Please provide more information:"
        
    input_field = inputs.get("input_field", "user_reply")
    
    # We use whatsapp_sender to actually send the message
    send_inputs = dict(inputs)
    send_inputs["message_body"] = question
    result = await whatsapp_sender(send_inputs)
    
    # Return a special pause indicator for the engine
    return {
        "paused": True,
        "input_field": input_field,
        "question_sent": question,
        "send_status": result.get("send_status")
    }


# ═════════════════════════════════════════════════════════════════
# WHATSAPP TRIGGER
# ═════════════════════════════════════════════════════════════════
async def whatsapp_trigger(inputs: dict) -> dict:
    return {
        "message_text": inputs.get("message_text", ""),
        "sender_id": inputs.get("sender_id", ""),
        "recipient_id": inputs.get("sender_id", ""),
        "to": inputs.get("sender_id", "")
    }

# ═════════════════════════════════════════════════════════════════
# GEMINI LLM
# ═════════════════════════════════════════════════════════════════
async def gemini_llm(inputs: dict) -> dict:
    from services.sarvam_service import SarvamService

    prompt = (
        inputs.get("prompt") or inputs.get("goal") or
        inputs.get("message_text") or inputs.get("instruction") or ""
    )
    iteration = inputs.get("iteration", 0)
    previous = inputs.get("previous_responses", [])

    if not prompt:
        return {"ai_response": "No prompt or goal provided", "message_body": "No prompt or goal provided"}

    if iteration > 0 and previous:
        prompt += f"\n\nGenerate variation #{iteration+1}. Avoid repeating: {json.dumps(previous[-3:])}"

    try:
        gemini = SarvamService() 
        response = await gemini.generate(prompt)
        text = response.strip()
        return {
            "ai_response": text,
            "message_body": text,
            "iteration": iteration + 1,
            "previous_responses": previous + [text]
        }
    except Exception as e:
        fallback = f"Generated message #{iteration+1}"
        return {
            "ai_response": fallback,
            "message_body": fallback,
            "iteration": iteration + 1,
            "previous_responses": previous + [fallback]
        }

# ═════════════════════════════════════════════════════════════════
# DELAY SCHEDULER
# ═════════════════════════════════════════════════════════════════
async def delay_scheduler(inputs: dict) -> dict:
    delay = float(inputs.get("delay_seconds") or inputs.get("delay") or inputs.get("wait_seconds", 1))
    logger.info(f"⏳ Waiting {delay}s...")
    await asyncio.sleep(delay)
    output = dict(inputs)
    output["done"] = True
    output["delay_seconds"] = delay
    return output

# ═════════════════════════════════════════════════════════════════
# CONDITION CHECKER
# ═════════════════════════════════════════════════════════════════
async def condition_checker(inputs: dict) -> dict:
    iteration = inputs.get("iteration", 0)
    max_iter = int(inputs.get("max_iterations") or inputs.get("count") or inputs.get("times", 5))
    next_iter = iteration + 1
    should_continue = next_iter < max_iter
    logger.info(f"🔍 Condition: {next_iter}/{max_iter} → continue={should_continue}")
    output = dict(inputs)
    output.update({
        "true_branch": should_continue,
        "false_branch": not should_continue,
        "iteration": next_iter,
        "max_iterations": max_iter
    })
    return output

# ═════════════════════════════════════════════════════════════════
# GOAL PLANNER
# ═════════════════════════════════════════════════════════════════
async def goal_planner(inputs: dict) -> dict:
    from services.gemini_service import GeminiService
    goal = inputs.get("goal_text") or inputs.get("goal", "")
    if not goal:
        return {"plan": ["No goal provided"]}
    try:
        gemini = GeminiService()
        res = await gemini.generate(f"Break this goal into steps: {goal}\nReturn JSON: {{\"plan\": [...]}}")
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', res)
        data = json.loads(match.group(1) if match else res)
        return {"plan": data.get("plan", [res]), "goal_text": goal}
    except Exception as e:
        return {"plan": [f"Error: {e}"], "goal_text": goal}

# ═════════════════════════════════════════════════════════════════
# WEB SEARCH (Tavily, cached)
# ═════════════════════════════════════════════════════════════════
async def web_search(inputs: dict) -> dict:
    from tavily import TavilyClient
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"search_results": [], "error": "TAVILY_API_KEY not set"}
    query = inputs.get("query") or inputs.get("search_query", "")
    if not query:
        return {"search_results": []}
    client = TavilyClient(api_key=api_key)
    results = client.search(query=query, max_results=3, include_answer=True)
    notes = []
    if results.get("answer"):
        notes.append(results["answer"])
    for r in results.get("results", []):
        notes.append(f"{r['title']}: {r['content']}")
    return {"search_results": notes, "query": query}

# ═════════════════════════════════════════════════════════════════
# GOOGLE SHEETS (real API with fallback)
# ═════════════════════════════════════════════════════════════════
async def google_sheets(inputs: dict) -> dict:
    from googleapiclient.discovery import build
    import re

    creds = _get_google_creds()
    if not creds:
        return {"status": "simulated", "updated_range": "Sheet1!A1"}

    service = build("sheets", "v4", credentials=creds)

    # 1. Determine spreadsheet ID
    spreadsheet_id = (
        inputs.get("spreadsheet_id")
        or os.getenv("TEST_SPREADSHEET_ID")
        or inputs.get("sheet_id")
    )
    if not spreadsheet_id:
        # Only try to create a new sheet if no fallback exists
        try:
            drive_service = build("drive", "v3", credentials=creds)
            file_metadata = {
                "name": inputs.get("title", "MakeIt Sheet"),
                "mimeType": "application/vnd.google-apps.spreadsheet",
            }
            file = drive_service.files().create(body=file_metadata, fields="id").execute()
            spreadsheet_id = file.get("id")
        except Exception as e:
            return {"status": "error", "error": f"Could not create spreadsheet: {e}"}

    # 2. Extract raw data from any AI output field (priority order)
    raw_text = (
        inputs.get("formatted_data")
        or inputs.get("ai_response")
        or inputs.get("message_body")
        or inputs.get("text")
        or inputs.get("data")   # could already be a list
        or ""
    )

    # 3. Convert raw_text to list[list] (grid)
    values = []

    if isinstance(raw_text, list):
        # Already a grid or list of strings
        if raw_text and isinstance(raw_text[0], list):
            values = raw_text
        else:
            values = [[str(item)] for item in raw_text]

    elif isinstance(raw_text, str) and raw_text.strip():
        # ── Priority 1: Markdown table ────────────────────────────────────
        # Extract ONLY lines that look like table rows (contain |).
        # This discards any surrounding prose/instructions the LLM might have added.
        all_lines  = raw_text.splitlines()
        table_lines = [ln.strip() for ln in all_lines if "|" in ln]

        if len(table_lines) >= 2:
            # Drop separator lines like |---|---|
            data_lines = [ln for ln in table_lines if not re.match(r'^[\|\-\s\:]+$', ln)]
            for ln in data_lines:
                cells = [c.strip() for c in ln.split("|")]
                # split("|") on "| A | B |" gives ['', 'A', 'B', ''] – drop empties at edges
                cells = [c for c in cells if c]  
                if cells:
                    values.append(cells)
            if not values:
                values = [["No table data found"]]

        else:
            # ── Priority 2: Numbered list ──────────────────────────────────
            list_items = []
            for ln in all_lines:
                m = re.match(r'^\s*(\d+)[\.)\-]\s+(.*)', ln)
                if m:
                    list_items.append([m.group(1), m.group(2).strip()])
                elif ln.strip():
                    list_items.append([ln.strip()])
            values = list_items if list_items else [[raw_text]]

    if not values:
        values = [["No data provided"]]

    # 4. Write to sheet
    range_name = inputs.get("range", "Sheet1!A1")
    body = {"values": values}
    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        return {
            "updated_range": result.get("updatedRange"),
            "spreadsheet_id": spreadsheet_id,
            "status": "ok"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
# ═════════════════════════════════════════════════════════════════
# GOOGLE DOCS
# ═════════════════════════════════════════════════════════════════
async def google_docs(inputs: dict) -> dict:
    """Create a new Google Doc or append text to an existing one.

    Expected inputs:
      - doc_id     : str (optional, if empty a new doc is created)
      - title      : str (for new doc)
      - text       : str (text to insert)
      - action     : 'create' | 'append' (default 'append')
    """
    from googleapiclient.discovery import build
    creds = _get_google_creds()
    if not creds:
        return {"status": "simulated", "doc_id": "simulated-doc-id"}

    service = build("docs", "v1", credentials=creds)
    action = inputs.get("action", "append")

    if action == "create" or not inputs.get("doc_id"):
        title = inputs.get("title", "MakeIt Document")
        try:
            doc = service.documents().create(body={"title": title}).execute()
            doc_id = doc.get("documentId")
            # Insert initial text if provided
            text = inputs.get("text", "")
            if text:
                requests = [{
                    "insertText": {
                        "location": {"index": 1},
                        "text": text
                    }
                }]
                service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
            return {"status": "ok", "doc_id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    else:
        doc_id = inputs.get("doc_id")
        text = inputs.get("text", "")
        if not text:
            return {"status": "error", "error": "No text provided"}
        try:
            # Append at end: find document length
            doc_info = service.documents().get(documentId=doc_id).execute()
            end_index = doc_info.get("body", {}).get("content", [{}])[-1].get("endIndex", 1) - 1
            requests = [{
                "insertText": {
                    "location": {"index": end_index},
                    "text": f"\n{text}"
                }
            }]
            service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
            return {"status": "ok", "doc_id": doc_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# ═════════════════════════════════════════════════════════════════
# GOOGLE CALENDAR
# ═════════════════════════════════════════════════════════════════
async def google_calendar(inputs: dict) -> dict:
    """Create a Google Calendar event. Must be provided explicit fields."""
    from googleapiclient.discovery import build
    
    creds = _get_google_creds()
    if not creds:
        return {"status": "error", "error": "Google Service Account credentials missing."}

    summary = inputs.get("summary") or inputs.get("event_title")
    start_time = inputs.get("start_time")
    
    if not summary or not start_time:
        return {"status": "error", "error": f"Missing required fields for calendar: summary='{summary}', start_time='{start_time}'"}
        
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')[:19])
        end_time = inputs.get("end_time") or (start_dt + timedelta(hours=1)).isoformat()
    except ValueError:
        return {"status": "error", "error": "Invalid start_time format. Must be ISO 8601."}

    description = inputs.get("description", _pick(inputs, ["formatted_data", "ai_response", "message_body", "text", "goal"]))
    attendees = inputs.get("attendees", [])
    if isinstance(attendees, str):
        attendees = [a.strip() for a in attendees.split(",") if a.strip()]

    event = {
        "summary": summary,
        "description": description or "Created by MakeIt",
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }
    
    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]

    try:
        service = build("calendar", "v3", credentials=creds)
        created = service.events().insert(calendarId="primary", body=event).execute()
        link = created.get("htmlLink")
        return {
            "status": "ok", 
            "event_id": created.get("id"), 
            "event_link": link,
            "formatted_data": f"Successfully created calendar event: '{summary}'. Link: {link}"
        }
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        return {"status": "error", "error": str(e)}

# ═════════════════════════════════════════════════════════════════
# GMAIL SENDER
# ═════════════════════════════════════════════════════════════════
async def gmail_sender(inputs: dict) -> dict:
    """Send an email via Gmail API.

    Expected inputs:
      - to        : str (email address)
      - subject   : str
      - body      : str (plain text)
    """
    from googleapiclient.discovery import build
    import base64
    from email.mime.text import MIMEText

    creds = _get_google_creds()
    if not creds:
        return {"status": "error", "error": "Google Service Account credentials missing."}

    service = build("gmail", "v1", credentials=creds)
    to = inputs.get("to", inputs.get("to_address", ""))
    subject = inputs.get("subject", "MakeIt Message")
    body = _pick(inputs, ["formatted_data", "ai_response", "message_body", "body", "text", "goal"])
    if not body:
        return {"status": "error", "error": "No valid email body content provided."}

    if not to:
        return {"status": "error", "error": "No recipient email"}

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"status": "ok", "email_sent": True, "message_id": sent.get("id")}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ═════════════════════════════════════════════════════════════════
# GOOGLE MEET CREATOR
# ═════════════════════════════════════════════════════════════════
async def google_meet_creator(inputs: dict) -> dict:
    """Create a Google Meet link by adding conference data to a calendar event."""
    from googleapiclient.discovery import build
    
    creds = _get_google_creds()
    if not creds:
        return {"status": "error", "error": "Google Service Account credentials missing."}

    summary = inputs.get("summary", inputs.get("event_title"))
    start_time = inputs.get("start_time")
    
    if not summary or not start_time:
        return {"status": "error", "error": f"Missing required fields for meet: summary='{summary}', start_time='{start_time}'"}

    attendees = inputs.get("attendees", [])
    if isinstance(attendees, str):
        attendees = [a.strip() for a in attendees.split(",") if a.strip()]

    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')[:19])
        end_time = inputs.get("end_time") or (start_dt + timedelta(hours=1)).isoformat()
    except ValueError:
        return {"status": "error", "error": "Invalid start_time format. Must be ISO 8601."}

    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
        "conferenceData": {
            "createRequest": {
                "requestId": f"makeit-{datetime.now().timestamp()}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }
    }
    
    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]

    try:
        service = build("calendar", "v3", credentials=creds)
        created = service.events().insert(
            calendarId="primary", 
            body=event, 
            conferenceDataVersion=1
        ).execute()
        
        meet_link = None
        conf_data = created.get("conferenceData", {})
        for entry in conf_data.get("entryPoints", []):
            if entry.get("entryPointType") == "video":
                meet_link = entry.get("uri")
                
        if not meet_link:
            meet_link = created.get("htmlLink") # Fallback to calendar link
            
        return {
            "status": "ok", 
            "event_id": created.get("id"), 
            "meet_link": meet_link,
            "summary": summary,
            "formatted_data": f"Google Meet '{summary}' scheduled successfully. Join link: {meet_link}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ═════════════════════════════════════════════════════════════════
# REMINDER SCHEDULER (placeholder – can be extended later)
# ═════════════════════════════════════════════════════════════════
async def reminder_scheduler(inputs: dict) -> dict:
    logger.info(f"Reminder: {inputs}")
    return {"reminder_id": f"rem_{datetime.now().timestamp()}"}

# ═════════════════════════════════════════════════════════════════
# DEFAULT EXECUTOR
# ═════════════════════════════════════════════════════════════════
async def default_executor(inputs: dict) -> dict:
    logger.info(f"Default executor: {inputs}")
    return {"output": "ok", "inputs_received": inputs}

# ═════════════════════════════════════════════════════════════════
# EXTRACT DETAILS
# ═════════════════════════════════════════════════════════════════
async def extract_details(inputs: dict) -> dict:
    """Parse a user goal and extract key entities as a JSON object."""
    from services.gemini_service import GeminiService
    import json
    
    goal = inputs.get("goal") or inputs.get("text") or _pick(inputs, ["formatted_data", "ai_response", "message_body"])
    if not goal:
        return {"status": "error", "error": "No goal or text provided to extract details from."}
        
    llm = GeminiService()
    now_str = datetime.now().isoformat()
    prompt = f"""
    Analyze the following user goal and extract all relevant entities (dates, times, emails, topics, locations).
    The current date/time is {now_str}.
    
    Return a flat JSON object where keys are descriptive names (e.g. "summary", "start_time", "end_time", "attendees", "topic", "recipient_email").
    Format times as ISO 8601 strings. If multiple attendees/emails are found, return them as a comma-separated string or a JSON array.
    
    Return ONLY the raw JSON object. Do not include markdown formatting or backticks.
    
    Goal:
    {goal}
    """
    
    try:
        response = await llm.generate(prompt)
        response_clean = response.strip()
        if response_clean.startswith("```"):
            response_clean = response_clean.split("\n", 1)[1]
        if response_clean.endswith("```"):
            response_clean = response_clean.rsplit("\n", 1)[0]
            
        details = json.loads(response_clean)
        details["status"] = "ok"
        return details
    except Exception as e:
        logger.error(f"Extract details failed: {e}")
        # Try to return at least the raw text
        return {"status": "error", "error": str(e)}

# ═════════════════════════════════════════════════════════════════
# FORMAT DATA
# Smart pass-through + LLM formatter for structured data.
# Always defined BEFORE EXECUTOR_MAP so it can be referenced in it.
# ═════════════════════════════════════════════════════════════════
async def format_data(inputs: dict) -> dict:
    """
    Two-phase formatter:
      1. If upstream already produced real structured content, apply the
         format_instructions via LLM to reshape it (e.g. "format as WhatsApp message").
      2. If there is no upstream content at all, call LLM with just the instructions.
    This ensures senders always get a human-readable, correctly-shaped message.
    """
    from services.gemini_service import GeminiService

    # Gather all upstream content in priority order
    upstream_keys = ["formatted_data", "ai_response", "meet_link", "event_link",
                     "message_body", "text", "doc_url", "updated_range"]
    # Build a combined context string from all available upstream fields
    context_parts = []
    for k in upstream_keys:
        v = inputs.get(k, "")
        if v and str(v).strip() and str(v).strip() not in ("", "No content to format"):
            context_parts.append(f"{k}: {v}")
    upstream_context = "\n".join(context_parts)

    instruction = inputs.get(
        "format_instructions",
        "Reformat the provided information clearly and concisely. "
        "Do NOT include any preamble or meta-commentary."
    )
    goal = inputs.get("goal", "")

    if not upstream_context.strip():
        # Nothing from upstream nodes at all
        raw = inputs.get("raw_text") or goal
        if not raw:
            return {"formatted_data": "No content to format"}
        upstream_context = raw

    prompt = (
        f"{instruction}\n\n"
        f"Available information:\n{upstream_context}\n\n"
        f"CRITICAL: Output ONLY the formatted result. No preamble, no meta-commentary."
    )
    if goal:
        prompt = f"Overall goal context: {goal}\n\n" + prompt

    try:
        llm = GeminiService()
        result = await llm.generate(prompt)
        return {"formatted_data": result.strip(), "message_body": result.strip()}
    except Exception as e:
        logger.error(f"format_data LLM error: {e}")
        return {"formatted_data": upstream_context, "message_body": upstream_context, "error": str(e)}


# ═════════════════════════════════════════════════════════════════
# EXECUTOR MAP
# ═════════════════════════════════════════════════════════════════
EXECUTOR_MAP = {
    "whatsapp_sender":    whatsapp_sender,
    "whatsapp_trigger":   whatsapp_trigger,
    "whatsapp_reply":     whatsapp_reply,
    "whatsapp_ask":       whatsapp_ask,
    "reminder_scheduler": reminder_scheduler,
    "google_calendar":    google_calendar,
    "gmail_sender":       gmail_sender,
    "google_meet_creator": google_meet_creator,
    "google_sheets":      google_sheets,
    "google_docs":        google_docs,
    "goal_planner":       goal_planner,
    "web_search":         web_search,
    "delay_scheduler":    delay_scheduler,
    "condition_checker":  condition_checker,
    "gemini_llm":         gemini_llm,
    "extract_details":    extract_details,
    "format_data":        format_data,   # defined above
}


def get_executor(component_id: str):
    """Return the executor function for a component ID, defaulting to default_executor."""
    return EXECUTOR_MAP.get(component_id, default_executor)