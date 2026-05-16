# MakeIt — Autonomous AI Workflow Operating System

> **MakeIt** is an AI-native autonomous workflow synthesis engine that converts natural-language goals into dynamically generated executable workflows using a collaborative team of AI architect agents and reusable workflow components.

---

# Vision

Modern automation tools require users to:
- manually connect nodes
- understand APIs
- configure workflows
- design logic systems themselves

MakeIt changes this completely.

Instead of manually building workflows, users simply describe a problem in natural language:

```txt
"Schedule a meeting tomorrow with Rahul and Priya"
```

or

```txt
"Help me stay consistent with DSA preparation"
```

The system autonomously:
- understands the problem
- researches required integrations
- selects workflow components
- creates a DAG execution graph
- identifies required credentials
- validates workflow correctness
- returns an executable workflow

---

# Core Concept

MakeIt is NOT:
- a chatbot
- a static automation builder
- a hardcoded workflow engine

MakeIt IS:
# an autonomous AI workflow architecture system.

The platform behaves like:
# a team of AI solution architects collaborating in real time.

---

# High-Level System Flow

```txt
User Goal
   ↓
Architect Agent Team
   ↓
Goal Analysis
   ↓
Web Research
   ↓
Component Selection
   ↓
Workflow DAG Construction
   ↓
Credential Detection
   ↓
Validation
   ↓
Executable Workflow JSON
```

---

# Dynamic Workflow Generation

The most important design principle:

# Workflows are NEVER hardcoded.

The system does NOT use:
- predefined templates
- fixed execution chains
- static graphs

Instead:
- workflows emerge dynamically through reasoning
- agents synthesize workflows from reusable components

---

# Architect Agent Team

## 1. ProblemAnalyzerAgent

Responsibilities:
- Understand user intent
- Break goals into subtasks
- Extract entities
- Infer workflow requirements

Uses:
# Sarvam AI API

---

## 2. WebResearchAgent

Responsibilities:
- Research APIs
- Discover integration methods
- Find workflow patterns

---

## 3. ComponentSelectorAgent

Responsibilities:
- Match tasks to reusable components
- Select workflow blocks dynamically

---

## 4. WorkflowArchitectAgent

Responsibilities:
- Construct DAG workflows
- Connect workflow nodes logically
- Generate workflow JSON

---

## 5. CredentialManagerAgent

Responsibilities:
- Detect required credentials
- Map credentials to components

---

## 6. ValidationAgent

Responsibilities:
- Validate graph correctness
- Detect invalid execution order

---

## 7. OrchestratorAgent

Responsibilities:
- Coordinate all agents
- Maintain shared workflow state
- Stream live reasoning logs

---

# Current Components

```txt
1. whatsapp_trigger
2. whatsapp_sender
3. sarvam_llm
4. google_calendar
5. google_meet_creator
6. gmail_sender
7. goal_planner
8. reminder_scheduler
9. google_sheets
10. web_search
11. delay_scheduler
12. condition_checker
```

---

# Backend Stack

- Python
- FastAPI
- asyncio
- Pydantic
- WebSockets
- LangChain
- LangGraph

---

# Frontend Stack

- React
- Vite
- TailwindCSS
- React Flow
- Framer Motion
- WebSockets

---

# FastAPI APIs

## Health Check

```http
GET /health
```

## Component Registry

```http
GET /components
```

## Workflow Generation

```http
POST /generate-workflow
```

---

# WebSocket Endpoint

```txt
/ws/logs
```

Streams:
- agent actions
- workflow generation steps
- reasoning updates
- validation logs

---

# Environment Variables

Create a `.env` file:

```env
SARVAM_API_KEY=your_sarvam_api_key

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

WHATSAPP_API_KEY=your_whatsapp_api_key
```

---

# Run Backend

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

---

# Run Frontend

```bash
npm install
npm run dev
```

---

# Final Idea Summary

# MakeIt is an AI-native autonomous workflow operating system where a team of AI architect agents dynamically designs executable workflows from reusable components using reasoning, orchestration, and live collaboration powered by Sarvam AI.
