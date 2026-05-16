COMPONENTS = [
    {
    "id": "format_data",
    "name": "Data Formatter",
    "description": "Uses AI to extract and format structured data (e.g., a top‑N list) from raw text",
    "category": "ai",
    "required_credentials": [],   # uses whatever LLM service is configured
    "inputs": ["raw_text", "format_instructions"],
    "outputs": ["formatted_data"]
},
    {
    "id": "extract_details",
    "name": "Details Extractor",
    "description": "Parses a user goal to extract key entities (dates, times, emails, topics, locations) as a structured JSON object. Ideal as the first node in a workflow.",
    "category": "ai",
    "required_credentials": [],
    "inputs": ["goal"],
    "outputs": ["summary", "start_time", "end_time", "attendees", "topic"]
},
    {
        "id": "whatsapp_trigger",
        "name": "WhatsApp Inbound Trigger",
        "description": "Listens for incoming WhatsApp messages to start a workflow",
        "category": "trigger",
        "required_credentials": [],                     # no credentials needed to receive a webhook
        "inputs": ["webhook_event"],
        "outputs": ["message_text", "sender_id"]
    },
    {
        "id": "whatsapp_sender",
        "name": "WhatsApp Message Sender",
        "description": "Sends a WhatsApp message via Twilio",
        "category": "action",
        "required_credentials": [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_WHATSAPP_NUMBER"
        ],
        "inputs": ["recipient_id", "message_body"],
        "outputs": ["send_status"]
    },
    {
        "id": "whatsapp_reply",
        "name": "WhatsApp Reply",
        "description": "Sends a reply to an incoming WhatsApp message.",
        "category": "communication",
        "required_credentials": [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_WHATSAPP_NUMBER"
        ],
        "inputs": ["message_body"],
        "outputs": ["send_status"]
    },
    {
        "id": "whatsapp_ask",
        "name": "WhatsApp Ask (Pause)",
        "description": "Sends a question via WhatsApp and pauses the workflow until the user replies.",
        "category": "communication",
        "required_credentials": [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_WHATSAPP_NUMBER"
        ],
        "inputs": ["question", "input_field"],
        "outputs": ["paused", "question_sent", "user_reply"]
    },
    {
        "id": "gemini_llm",
        "name": "Gemini LLM",
        "description": "Processes text with Google Gemini (e.g., summarization, generation)",
        "category": "ai",
        "required_credentials": ["GEMINI_API_KEY"],
        "inputs": ["prompt"],
        "outputs": ["ai_response"]
    },
    {
        "id": "google_calendar",
        "name": "Google Calendar",
        "description": "Creates, reads, updates, or deletes calendar events",
        "category": "productivity",
        "required_credentials": [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN"
        ],
        "inputs": ["event_details"],
        "outputs": ["event_id", "event_link"]
    },
    {
        "id": "google_meet_creator",
        "name": "Google Meet Creator",
        "description": "Generates a Google Meet link for a meeting",
        "category": "communication",
        "required_credentials": [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN"
        ],
        "inputs": ["event_title", "start_time", "end_time"],
        "outputs": ["meet_link"]
    },
    {
        "id": "gmail_sender",
        "name": "Gmail Sender",
        "description": "Sends an email via Gmail",
        "category": "communication",
        "required_credentials": [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN"
        ],
        "inputs": ["to_address", "subject", "body"],
        "outputs": ["email_sent"]
    },
    {
        "id": "google_sheets",
        "name": "Google Sheets",
        "description": "Reads or writes data to Google Sheets",
        "category": "data",
        "required_credentials": [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN"
        ],
        "inputs": ["spreadsheet_id", "range", "data"],
        "outputs": ["updated_range"]
    },
    {
        "id": "google_docs",
        "name": "Google Docs",
        "description": "Creates or appends text to a Google Doc",
        "category": "documents",
        "required_credentials": [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN"
        ],
        "inputs": ["title", "text", "doc_id"],
        "outputs": ["doc_id", "url"]
    },
    {
        "id": "goal_planner",
        "name": "Goal Planner",
        "description": "Breaks a high-level goal into actionable steps and reminders",
        "category": "planning",
        "required_credentials": [],
        "inputs": ["goal_text", "preferences"],
        "outputs": ["plan"]
    },
    {
        "id": "reminder_scheduler",
        "name": "Reminder Scheduler",
        "description": "Sets timed reminders for tasks",
        "category": "utility",
        "required_credentials": [],
        "inputs": ["reminder_text", "schedule_time"],
        "outputs": ["reminder_id"]
    },
    {
        "id": "web_search",
        "name": "Web Search",
        "description": "Performs a web search via Tavily and returns results",
        "category": "research",
        "required_credentials": ["TAVILY_API_KEY"],
        "inputs": ["query"],
        "outputs": ["search_results"]
    },
    {
        "id": "delay_scheduler",
        "name": "Delay Scheduler",
        "description": "Pauses workflow execution for a specified duration",
        "category": "utility",
        "required_credentials": [],
        "inputs": ["delay_seconds"],
        "outputs": ["done"]
    },
    {
        "id": "condition_checker",
        "name": "Condition Checker",
        "description": "Evaluates a condition and routes workflow accordingly",
        "category": "logic",
        "required_credentials": [],
        "inputs": ["condition", "data"],
        "outputs": ["true_branch", "false_branch"]
    }
]

def get_components():
    return COMPONENTS