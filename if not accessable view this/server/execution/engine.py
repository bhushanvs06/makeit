import asyncio
import json
import re
import logging
from collections import defaultdict, deque
from execution.component_executors import get_executor

logger = logging.getLogger("engine")

# ── Column presets for common subjects ───────────────────────────────────────
_COLUMN_PRESETS = {
    "student":     "StudentID, FirstName, LastName, DateOfBirth, Email, PhoneNumber, GradeLevel, Major, GPA, EnrollmentDate",
    "employee":    "EmployeeID, FirstName, LastName, Department, JobTitle, Email, PhoneNumber, Salary, HireDate, Manager",
    "product":     "ProductID, ProductName, Category, Description, Price, StockQuantity, SKU, Supplier, Weight, LastUpdated",
    "user":        "UserID, Username, Email, FullName, PhoneNumber, Country, SignupDate, LastLogin, Status, Role",
    "customer":    "CustomerID, FirstName, LastName, Email, PhoneNumber, Address, City, Country, TotalOrders, LastPurchaseDate",
    "inventory":   "ItemID, ItemName, Category, Quantity, UnitPrice, Supplier, Location, MinStock, LastRestocked, ExpiryDate",
    "teacher":     "TeacherID, FirstName, LastName, Subject, Email, PhoneNumber, Department, YearsExperience, Qualification, JoiningDate",
    "book":        "BookID, Title, Author, ISBN, Genre, Publisher, Year, Price, Copies, Language",
    "patient":     "PatientID, FirstName, LastName, DateOfBirth, Gender, BloodGroup, Email, PhoneNumber, Diagnosis, AdmissionDate",
    "transaction": "TransactionID, Date, Amount, Type, Category, Description, Account, Merchant, Status, Reference",
}

_TIMETABLE_DAYS = "Monday, Tuesday, Wednesday, Thursday, Friday, Saturday"

# Keywords that indicate a multi-step orchestration goal, NOT a pure data-dump goal.
# When present, the engine should NOT auto-override the LLM prompt with a table builder.
_ORCHESTRATION_KEYWORDS = {
    "schedule", "meeting", "meet", "calendar", "event", "remind", "reminder",
    "send", "email", "gmail", "whatsapp", "sms", "notify", "mail",
    "create a", "set up", "book a", "arrange",
}


class WorkflowEngine:
    async def execute(self, graph, node_outputs=None, max_iterations=50, goal: str = ""):
        nodes = graph.get("nodes") if graph else []
        edges = graph.get("edges") if graph else []

        if not goal:
            goal = graph.get("goal", "")

        if not isinstance(nodes, list):
            nodes = []
        if not isinstance(edges, list):
            edges = []

        if not nodes:
            logger.warning("No nodes in workflow")
            return {}

        if node_outputs is None:
            node_outputs = {}

        node_map = {n["id"]: n for n in nodes if "id" in n}

        # Build adjacency and in-degree for topological ordering
        adj = defaultdict(list)
        in_degree = {n["id"]: 0 for n in nodes}
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src in node_map and tgt in node_map:
                adj[src].append(tgt)
                in_degree[tgt] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        if not queue and nodes:
            queue.append(nodes[0]["id"])

        return await self._run_loop(queue, graph, node_outputs, adj, node_map, edges, goal, max_iterations)

    async def _run_loop(self, queue, graph, node_outputs, adj, node_map, edges, goal, max_iterations):
        executed = set(node_outputs.keys())
        iteration = 0

        while queue and iteration < max_iterations:
            nid = queue.popleft()
            comp_id = node_map[nid].get("component_id", "default")

            # 1. Start with inputs hardcoded in the graph node
            inputs = node_map[nid].get("inputs", {}).copy()

            # 2. Merge outputs from ALL predecessor nodes (data flow)
            for edge in edges:
                if edge.get("target") == nid:
                    src = edge.get("source")
                    if src in node_outputs and node_outputs[src] is not None:
                        src_out = node_outputs[src]
                        if isinstance(src_out, dict):
                            # Node-level inputs take priority over predecessor outputs
                            # (predecessor fills in gaps, doesn't overwrite explicit config)
                            merged = {**src_out, **inputs}
                            inputs = merged

            # 3. Always inject the goal so every node has context
            if goal:
                inputs["goal"] = goal

            # 4. Auto-prompt for text-generation nodes that have no explicit prompt
            if comp_id in ("gemini_llm", "sarvam_llm", "deepseek_llm", "groq_llm"):
                has_prompt = bool(inputs.get("prompt", "").strip())

                if not has_prompt:
                    if self._is_orchestration_goal(goal):
                        # Multi-step goal: use goal directly, don't override with a table builder
                        inputs["prompt"] = goal
                        logger.info(f"[{nid}] Orchestration goal – using goal as prompt.")
                    elif self._is_pure_data_goal(goal):
                        # Pure data generation: force a structured output prompt
                        inputs["prompt"] = self._build_data_prompt(goal)
                        logger.info(f"[{nid}] Data goal – built direct prompt: {inputs['prompt'][:80]}...")
                    else:
                        inputs["prompt"] = goal
                else:
                    # Architect provided a prompt. If it's a pure-data goal, append anti-filler instruction.
                    if self._is_pure_data_goal(goal) and not self._is_orchestration_goal(goal):
                        inputs["prompt"] += (
                            "\n\nCRITICAL: Output ONLY the final data as a Markdown table or numbered list. "
                            "Do NOT include any explanation, steps, preamble, or meta-commentary. "
                            "Return raw structured output only."
                        )

            logger.info(f"[iter={iteration}] Node '{nid}' ({comp_id}) inputs keys: {list(inputs.keys())}")

            executor = get_executor(comp_id)
            try:
                output = await executor(inputs)
                if output is None:
                    output = {}
                node_outputs[nid] = output
                executed.add(nid)
                logger.info(f"[iter={iteration}] '{nid}' output: {json.dumps(output, default=str)[:300]}")

                # Intercept pause signal from interactive components (e.g. whatsapp_ask)
                if isinstance(output, dict) and output.get("paused") is True:
                    logger.info(f"⏸️ Workflow paused at node '{nid}'")
                    return {
                        "__status__": "paused",
                        "paused_node": nid,
                        "input_field": output.get("input_field", "user_reply"),
                        "node_outputs": node_outputs,
                        "graph": graph,
                        "goal": goal
                    }

            except Exception as e:
                logger.error(f"Node '{nid}' failed: {e}", exc_info=True)
                node_outputs[nid] = {"status": "error", "error": str(e)}
                # Continue executing other branches rather than crashing the whole workflow

            # Route to next nodes
            if nid in adj:
                targets = adj[nid]
                output = node_outputs.get(nid, {})
                # Handle condition_checker branching
                if (
                    isinstance(output, dict)
                    and "true_branch" in output
                    and "false_branch" in output
                    and len(targets) >= 2
                ):
                    if output.get("true_branch"):
                        queue.append(targets[0])
                    elif output.get("false_branch"):
                        queue.append(targets[1])
                else:
                    for t in targets:
                        if t not in executed:
                            queue.append(t)

            iteration += 1

        return node_outputs

    async def resume(self, session: dict, user_reply: str, max_iterations: int = 50):
        """Resume a paused workflow session."""
        graph       = session.get("graph", {})
        node_outputs = session.get("node_outputs", {})
        paused_node  = session.get("paused_node")
        input_field  = session.get("input_field", "user_reply")
        goal         = session.get("goal", "")

        logger.info(f"▶️ Resuming workflow at node '{paused_node}' with reply: {user_reply!r}")

        if paused_node and paused_node in node_outputs:
            node_outputs[paused_node][input_field] = user_reply
            node_outputs[paused_node]["paused"] = False

        nodes    = graph.get("nodes", [])
        edges    = graph.get("edges", [])
        node_map = {n["id"]: n for n in nodes if "id" in n}

        adj = defaultdict(list)
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src in node_map and tgt in node_map:
                adj[src].append(tgt)

        queue = deque()
        if paused_node:
            output  = node_outputs.get(paused_node, {})
            targets = adj.get(paused_node, [])
            if isinstance(output, dict) and "true_branch" in output and len(targets) >= 2:
                if output.get("true_branch"):
                    queue.append(targets[0])
                elif output.get("false_branch"):
                    queue.append(targets[1])
            else:
                for t in targets:
                    queue.append(t)

        return await self._run_loop(queue, graph, node_outputs, adj, node_map, edges, goal, max_iterations)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _is_orchestration_goal(self, goal: str) -> bool:
        """
        Return True if the goal implies multi-step real-world actions
        (scheduling, sending, emailing, etc.).
        These goals should NOT have their prompts hijacked by the data builder.
        """
        gl = goal.lower()
        return any(kw in gl for kw in _ORCHESTRATION_KEYWORDS)

    def _is_pure_data_goal(self, goal: str) -> bool:
        """
        Return True if the goal is exclusively about generating structured data:
        tables, databases, timetables, lists – with no real-world action side effects.
        """
        if self._is_orchestration_goal(goal):
            return False

        patterns = [
            r"\b(timetable|time[\s\-]table|class\s+schedule)\b",
            r"\b(database|spreadsheet|roster|dataset)\b",
            r"\b(list\s+of|top\s+\d+|give\s+me\s+\d+)\b",
            r"\d+\s+(records?|rows?|entries|items?|students?|employees?|products?)",
            r"(generate|create|make|build|produce)\s+(a\s+)?(student|employee|product|user|customer|inventory|teacher|book|patient|transaction)\s*(database|table|list|sheet|dataset)?",
        ]
        return any(re.search(p, goal, re.IGNORECASE) for p in patterns)

    # Backward-compat aliases
    def _is_simple_list_goal(self, goal: str) -> bool:
        return self._is_pure_data_goal(goal)

    def _is_data_creation_goal(self, goal: str) -> bool:
        return self._is_pure_data_goal(goal)

    def _build_data_prompt(self, goal: str) -> str:
        """
        Convert a pure-data-generation goal into a laser-focused instruction that
        demands ONLY the raw Markdown table or numbered list – no explanations.
        """
        gl = goal.lower()

        # ── Timetable ────────────────────────────────────────────────────────
        if re.search(r"\b(timetable|time[\s\-]table|class\s+schedule|weekly\s+schedule)\b", goal, re.IGNORECASE):
            m = re.search(r"(?:for|of)\s+(.+?)(?:\s+and\s+|\s*$)", goal, re.IGNORECASE)
            topic = m.group(1).strip() if m else "a college student"
            topic = re.sub(r"\s*(send|via|whatsapp|email).*", "", topic, flags=re.IGNORECASE).strip() or topic
            return (
                f"Generate a realistic weekly class timetable for {topic} as a Markdown table. "
                f"Use time slots (9:00–10:00 … 17:00–18:00) as rows and days ({_TIMETABLE_DAYS}) as columns. "
                f"Fill every cell with a subject/activity. "
                f"Output ONLY the Markdown table. No explanation, heading, or commentary."
            )

        # ── Named-entity database ────────────────────────────────────────────
        subj_match = re.search(
            r"\b(student|employee|product|user|customer|inventory|teacher|book|patient|transaction)\b",
            goal, re.IGNORECASE
        )
        if subj_match:
            subject = subj_match.group(1).lower()
            num_match = re.search(r"(\d+)\s*(records?|rows?|entries?|items?)?", goal, re.IGNORECASE)
            number = num_match.group(1) if num_match else "10"
            # Try to find user-specified columns
            col_match = re.search(
                r"(?:with\s+(?:columns?|fields?)\s*[:\-]?\s*)([a-zA-Z ,/]+?)(?:\s+and\s+write|\s*$|\.)",
                goal, re.IGNORECASE
            )
            columns = col_match.group(1).strip() if col_match else _COLUMN_PRESETS.get(subject, "ID, Name, Email, Status, CreatedAt")
            return (
                f"Generate a Markdown table of exactly {number} {subject}s with realistic, fictional data. "
                f"Columns: {columns}. Every row must have a unique ID and plausible values. "
                f"Output ONLY the Markdown table (header + separator + {number} data rows). "
                f"Do NOT include any explanation, steps, or text outside the table."
            )

        # ── Top-N list ───────────────────────────────────────────────────────
        list_match = re.search(
            r"(?:list|show|give\s+me|find|get)\s+(?:a\s+)?(?:list\s+of\s+)?(?:the\s+)?(?:top\s+)?(\d+)\s+(.*?)(?:\s+and\s+write|\s*$)",
            goal, re.IGNORECASE
        )
        if list_match:
            number = list_match.group(1)
            topic  = re.sub(r"\s*(and\s+)?(send|write|put|store|via|on|to|in)\s+.*", "", list_match.group(2).strip(), flags=re.IGNORECASE).strip()
            return (
                f"List the top {number} {topic}.\n"
                f"Format: numbered list — each entry as \"N. Name – one-line description\".\n"
                f"Output ONLY the {number} list items. No heading, no introduction, no summary."
            )

        # ── Generic fallback ─────────────────────────────────────────────────
        return (
            f"Analyze this goal: '{goal}'.\n"
            f"Generate the requested data as a well-structured Markdown table.\n"
            f"CRITICAL: Output ONLY the Markdown table. No conversational text, no instructions, no explanations."
        )

    # Keep old name for backward compatibility
    def _build_direct_prompt(self, goal: str) -> str:
        return self._build_data_prompt(goal)