import asyncio
import hashlib
import os
import re
import time
from fastapi import HTTPException
from core import db, action, kpi, SCHEMAS, ins, upd, get, find, bulk, validate, audit, by_status, today, now, new_id, P, log
import engine
from engine import APPROVAL

LAB = "agents"
SCHEMAS[LAB] = {}
TOOLS = ["read_controls", "read_evidence", "calc_risk", "map_obligations", "create_finding", "create_task", "generate_report", "read_vendors",
         "read_ai_inventory", "sn_table_api", "read_projects", "read_pi_board", "read_incidents", "send_external_email", "delete_records", "export_pii"]
SENSITIVE_TOOLS = {"send_external_email", "delete_records", "export_pii"}
PRICING = {  # illustrative list prices per 1M tokens (USD); configurable, verify with provider before budgeting
    "claude-haiku-5-5": {"provider": "anthropic", "in": 1.0, "out": 5.0, "base_ms": 900, "ms_per_tok": 6, "verbosity": 0.8, "quality": 0.82},
    "claude-sonnet-5-5": {"provider": "anthropic", "in": 3.0, "out": 15.0, "base_ms": 1800, "ms_per_tok": 11, "verbosity": 1.0, "quality": 0.93},
    "gpt-5.4-mini": {"provider": "openai", "in": 0.4, "out": 1.6, "base_ms": 700, "ms_per_tok": 5, "verbosity": 0.9, "quality": 0.80},
    "gpt-5.4": {"provider": "openai", "in": 2.5, "out": 10.0, "base_ms": 1600, "ms_per_tok": 9, "verbosity": 1.1, "quality": 0.92},
    "gemini-3-flash-preview": {"provider": "gemini", "in": 0.3, "out": 2.5, "base_ms": 650, "ms_per_tok": 4, "verbosity": 0.9, "quality": 0.81},
}
INJECTION = [r"ignore (all |any )?(previous|prior) instructions", r"system prompt", r"reveal .*(key|secret|password)", r"disable .*(guard|safety|logging)",
             r"you are now", r"exfiltrat", r"bypass", r"act as (an )?admin"]
PII = [r"\b\d{3}-\d{2}-\d{4}\b", r"\b(?:\d[ -]?){13,16}\b"]

AGENTS = [
    ("GRC Assessment Agent", "Assess control design & operating effectiveness", ["read_controls", "read_evidence", "calc_risk", "create_finding"], "Control set, evidence", "Control assessment summary"),
    ("IT Audit Agent", "Plan tests and summarize audit exceptions", ["read_controls", "read_evidence", "generate_report"], "Audit scope, test results", "Exception summary"),
    ("Vendor Risk Agent", "Summarize vendor risk posture", ["read_vendors", "calc_risk"], "Vendor profile, questionnaire", "Vendor risk summary"),
    ("AI Governance Agent", "Recommend AI approval conditions", ["read_ai_inventory", "map_obligations"], "AI system profile", "Governance recommendation"),
    ("ServiceNow Workflow Agent", "Propose ServiceNow-style flow configurations", ["sn_table_api", "create_task"], "Process description", "Flow design"),
    ("Project Delivery Agent", "Summarize project health & risks", ["read_projects", "generate_report"], "Project data", "Status summary"),
    ("SAFe RTE Coordination Agent", "Prepare ART Sync agenda from dependencies", ["read_pi_board", "create_task"], "Program board", "ART Sync agenda"),
    ("Incident Response Agent", "Recommend containment actions", ["read_incidents", "create_task"], "Incident record", "Response recommendations"),
    ("Reporting Agent", "Compile executive reports", ["generate_report"], "Workflow outputs", "Executive report"),
    ("Intake Agent", "Triage assessment requests (workflow helper)", ["read_controls"], "Request", "Scoped request"),
    ("Evidence Agent", "Identify missing documentation (workflow helper)", ["read_evidence"], "Evidence packages", "Missing evidence list"),
    ("Risk Agent", "Calculate preliminary risk (workflow helper)", ["calc_risk"], "Gaps", "Preliminary risk"),
    ("Compliance Agent", "Map applicable obligations (workflow helper)", ["map_obligations"], "Scope", "Obligation mapping"),
]
BOUNDARY = "Use only the provided fictional data. Never request credentials, never take external actions, never output personal data. Flag uncertainty. Max 120 words."


async def seed_agents(s):
    rows = [{"name": n, "role": n.replace(" Agent", ""), "objective": o, "instructions": f"You are the {n}. {o}. Be concise and evidence-based.", "tools": t,
             "inputs": i, "outputs": out, "boundaries": BOUNDARY, "model": "claude-haiku-5-5", "status": "active", "version": 1} for n, o, t, i, out in AGENTS]
    docs = await bulk(s, LAB, "agent", rows)
    await bulk(s, LAB, "agent_version", [{"agent_id": d["id"], "agent": d["name"], "version": 1, "snapshot": {k: d[k] for k in ("instructions", "tools", "model", "objective")}, "note": "Initial"} for d in docs])


async def ai_settings():
    st = await db.settings.find_one({"key": "ai"}, P)
    return st or {"key": "ai", "live_enabled": True, "provider": "anthropic", "model": "claude-haiku-5-5",
                  "daily_limit_global": int(os.environ["LIVE_AI_DAILY_LIMIT"]), "daily_limit_session": int(os.environ["LIVE_AI_SESSION_LIMIT"])}


async def quota(s):
    st = await ai_settings()
    day = today()
    g = await db.ai_usage.count_documents({"day": day})
    m = await db.ai_usage.count_documents({"day": day, "session": s})
    return st, max(0, st["daily_limit_global"] - g), max(0, st["daily_limit_session"] - m)


def modeled_latency(model, out_tokens, seed):
    pr = PRICING.get(model, PRICING["claude-haiku-5-5"])
    jitter = int(hashlib.md5(seed.encode()).hexdigest()[:4], 16) % 300
    return pr["base_ms"] + pr["ms_per_tok"] * out_tokens + jitter


def cost(model, tin, tout):
    pr = PRICING.get(model, PRICING["claude-haiku-5-5"])
    return round(tin / 1e6 * pr["in"] + tout / 1e6 * pr["out"], 6)


def simulate(agent, task, ctx):
    facts = "; ".join(f"{k}: {v}" for k, v in (ctx or {}).items() if not isinstance(v, (dict,)))[:500]
    return (f"[SIMULATION – deterministic rule-based output, not live AI] {agent['name']} processed the task. "
            f"Objective: {agent['objective']}. Facts considered: {facts or 'none'}. Recommendation: prioritize items with the highest computed risk, "
            f"assign accountable owners, and require human review before any record is created.")


def guard(text):
    hits = [p for p in INJECTION if re.search(p, text, re.I)]
    pii = [p for p in PII if re.search(p, text)]
    return hits, pii


async def execute_agent(s, agent, task, ctx=None, mode="auto", tools_needed=None, workflow=None):
    tools_needed = tools_needed or []
    base = {"agent_id": agent["id"], "agent_name": agent["name"], "version": agent["version"], "model": agent["model"], "input": task[:1500], "workflow": workflow,
            "tool_calls": tools_needed, "retries": 0}
    if agent["status"] != "active":
        return await ins(s, LAB, "agent_run", **base, mode="blocked", status="blocked", output="Agent is deactivated – execution refused.", latency_ms=0, tokens_in=0, tokens_out=0, cost_usd=0, error="inactive")
    denied = [t for t in tools_needed if t not in agent["tools"]]
    inj, pii = guard(task)
    if denied or inj or pii:
        reason = (f"Tool(s) not in allowlist: {denied}. " if denied else "") + (f"Prompt-injection pattern detected. " if inj else "") + ("Sensitive data pattern detected (redacted). " if pii else "")
        ev = await ins(s, LAB, "security_event", agent_id=agent["id"], agent=agent["name"], kind="unauthorized_tool" if denied else "prompt_injection" if inj else "sensitive_data",
                       detail=reason, decision="BLOCKED", tools=denied, escalated=bool(denied and set(denied) & SENSITIVE_TOOLS))
        if ev["escalated"]:
            await ins(s, "ir", "incident", title=f"AI agent security event: {agent['name']} requested {', '.join(denied)}", category="Insider Threat", affected_systems=["AI Agent Platform"],
                      data_involved="internal", users_affected=0, severity="Medium", phase="Triage", status="Open", source="Agent Command Center")
        violations = len(await find(s, LAB, "security_event", agent_id=agent["id"]))
        if violations >= 3:
            await upd(s, agent["id"], status="inactive", deactivated_reason="Auto-deactivated after 3 security violations")
        return await ins(s, LAB, "agent_run", **base, mode="blocked", status="blocked", output=f"Request blocked by policy. {reason}", latency_ms=0, tokens_in=0, tokens_out=0,
                         cost_usd=0, error="policy_violation", security_event_id=ev["id"])
    st, g_left, s_left = await quota(s)
    use_live = mode in ("auto", "live") and st["live_enabled"] and g_left > 0 and s_left > 0 and bool(os.environ.get("EMERGENT_LLM_KEY"))
    fallback = None if use_live else ("Live AI disabled by administrator" if not st["live_enabled"] else "Daily live-AI limit reached" if (g_left == 0 or s_left == 0) else "No AI provider configured") if mode != "simulation" else "Simulation requested"
    sys_msg = f"{agent['instructions']}\nSafety boundaries: {agent['boundaries']}"
    prompt = f"Task: {task}\nContext (fictional data): {ctx or {}}"
    tin = (len(sys_msg) + len(prompt)) // 4
    t0 = time.perf_counter()
    if use_live:
        model = st["model"]
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id("agent-"), system_message=sys_msg).with_model(st["provider"], model)
            await db.ai_usage.insert_one({"day": today(), "session": s, "agent": agent["name"], "at": now()})
            out = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), 45)
            ms = round((time.perf_counter() - t0) * 1000)
            tout = len(out) // 4
            return await ins(s, LAB, "agent_run", **{**base, "model": model}, mode="live", status="success", output=out, latency_ms=ms, tokens_in=tin, tokens_out=tout,
                             cost_usd=cost(model, tin, tout), token_basis="estimated (chars/4)", latency_basis="measured")
        except Exception as e:  # noqa: BLE001 - fall back to simulation and record the error
            log.warning("live agent call failed: %s", e)
            fallback = f"Live call failed ({type(e).__name__}); fell back to simulation"
    out = simulate(agent, task, ctx)
    tout = int(len(out) // 4 * PRICING.get(agent["model"], PRICING["claude-haiku-5-5"])["verbosity"])
    return await ins(s, LAB, "agent_run", **base, mode="simulation", status="success", output=out, latency_ms=modeled_latency(agent["model"], tout, task),
                     tokens_in=tin, tokens_out=tout, cost_usd=cost(agent["model"], tin, tout), fallback_reason=fallback, token_basis="estimated", latency_basis="modeled (simulation)",
                     retries=1 if fallback and "failed" in fallback else 0)


async def agent_by_name(s, name):
    a = await find(s, LAB, "agent", name=name)
    if not a:
        raise HTTPException(404, f"Agent {name} not found")
    return a[0]


async def run_named_agent(s, name, task, ctx=None, tools=None, workflow=None):
    return await execute_agent(s, await agent_by_name(s, name), task, ctx, tools_needed=tools, workflow=workflow)


# ---- Multi-agent enterprise risk assessment ----
GAP_WORDS = ["still active", "lacking", "11 months", "not", "missing"]


async def st_intake(s, ctx):
    controls = [c for c in await find(s, "irm", "control") if c["status"] in ("Not Tested", "Ineffective")][:6]
    ctx["controls"] = [{"id": c["id"], "ref": c["ref"], "evidence": c["evidence"], "owner": c["owner"]} for c in controls]
    r = await run_named_agent(s, "Intake Agent", f"Scope request: {ctx['request']}", {"controls_in_scope": [c["ref"] for c in controls]}, ["read_controls"], "agent_grc_assessment")
    return {"agent_run": r["id"], "mode": r["mode"], "controls_in_scope": [c["ref"] for c in controls]}


async def st_grc(s, ctx):
    r = await run_named_agent(s, "GRC Assessment Agent", "Review in-scope controls for design adequacy", {"controls": [c["ref"] for c in ctx["controls"]]}, ["read_controls"], "agent_grc_assessment")
    return {"agent_run": r["id"], "mode": r["mode"], "summary": r["output"][:400]}


async def st_evidence(s, ctx):
    missing = [c for c in ctx["controls"] if any(w in c["evidence"].lower() for w in GAP_WORDS)]
    ctx["missing"] = [{"ref": c["ref"], "id": c["id"], "owner": c["owner"], "gap": c["evidence"]} for c in missing]
    r = await run_named_agent(s, "Evidence Agent", "Identify missing or deficient documentation", {"gaps": [c["ref"] for c in missing]}, ["read_evidence"], "agent_grc_assessment")
    return {"agent_run": r["id"], "mode": r["mode"], "missing_evidence": [m["ref"] for m in ctx["missing"]]}


async def st_risk(s, ctx):
    n = len(ctx["missing"])
    ctx["rating"] = "High" if n >= 3 else "Medium" if n >= 1 else "Low"
    r = await run_named_agent(s, "Risk Agent", "Calculate preliminary risk", {"gaps": n, "rating": ctx["rating"]}, ["calc_risk"], "agent_grc_assessment")
    return {"agent_run": r["id"], "mode": r["mode"], "preliminary_rating": ctx["rating"], "rule": "≥3 gaps High, ≥1 Medium"}


async def st_compliance(s, ctx):
    ctx["obligations"] = ["NIST SP 800-53 (AC, CM, CP, RA families)", "SOX ITGC – access & change", "GLBA Safeguards (summary)"]
    r = await run_named_agent(s, "Compliance Agent", "Map applicable obligations", {"scope": ctx["scope"]}, ["map_obligations"], "agent_grc_assessment")
    return {"agent_run": r["id"], "mode": r["mode"], "obligations": ctx["obligations"]}


async def st_report(s, ctx):
    r = await run_named_agent(s, "Reporting Agent", "Write the executive assessment report", {"rating": ctx["rating"], "gaps": [m["ref"] for m in ctx["missing"]], "obligations": ctx["obligations"]},
                              ["generate_report"], "agent_grc_assessment")
    ctx["report"] = f"Enterprise Risk Assessment – {ctx['request']}\nPreliminary rating: {ctx['rating']}\nEvidence gaps: {', '.join(m['ref'] for m in ctx['missing']) or 'none'}\nObligations: {'; '.join(ctx['obligations'])}\n\nAgent narrative ({r['mode']}): {r['output']}"
    return {"agent_run": r["id"], "mode": r["mode"], "report_chars": len(ctx["report"])}


async def st_tasks(s, ctx):
    ids = []
    for m in ctx["missing"]:
        f = await ins(s, "irm", "finding", title=f"Evidence gap: {m['ref']} (agent-identified, human-approved)", control_id=m["id"], control_ref=m["ref"], source="AI Agent workflow", status="Remediation In Progress", severity=ctx["rating"])
        r = await ins(s, "irm", "remediation", title=f"Provide/repair evidence for {m['ref']}", finding_id=f["id"], control_id=m["id"], owner=m["owner"], due_date=today(), severity=ctx["rating"], status="In Progress")
        await upd(s, m["id"], status="Remediation In Progress")
        ids.append(r["id"])
    return {"remediation_tasks": ids}


engine.workflow("agent_grc_assessment", "Multi-Agent Enterprise Risk Assessment", LAB, "Assessment request submitted",
                "Intake → GRC → Evidence → Risk → Compliance agents → Human reviewer → Reporting agent → approved remediation tasks.",
                [("Intake Agent: scope request", st_intake, {}), ("GRC Agent: review controls", st_grc, {}), ("Evidence Agent: missing documentation", st_evidence, {}),
                 ("Risk Agent: preliminary risk", st_risk, {}), ("Compliance Agent: map obligations", st_compliance, {}),
                 ("Human reviewer", APPROVAL, {"title": lambda c: f"Review agent recommendations ({c['rating']}, {len(c['missing'])} gaps)", "role": "GRC Manager"}),
                 ("Reporting Agent: generate report", st_report, {}), ("Create approved remediation tasks", st_tasks, {})], cross_lab=True)


async def st_scan(s, ctx):
    controls = await find(s, "irm", "control")
    cands = [c for c in controls if c["status"] != "Remediation In Progress" and any(w in c["evidence"].lower() for w in GAP_WORDS[:3])]
    r = await run_named_agent(s, "GRC Assessment Agent", "Scan control library for potential control issues",
                              {"controls": [f"{c['ref']} ({c['status']}): {c['evidence']}" for c in controls]}, ["read_controls"], "agent_control_issue")
    if cands:
        c = cands[0]
        ctx.update(control_id=c["id"], control_ref=c["ref"], owner=c["owner"], issue=c["evidence"])
    ctx["found"] = bool(cands)
    return {"agent_run": r["id"], "mode": r["mode"], "issue_found": ctx.get("control_ref", "none")}


async def st_wf7_finding(s, ctx):
    f = await ins(s, "irm", "finding", title=f"Agent-identified issue: {ctx['control_ref']}", control_id=ctx["control_id"], control_ref=ctx["control_ref"], source="AI Agent (human approved)", status="Open", severity="High")
    ctx["finding_id"] = f["id"]
    return {"finding_id": f["id"]}


async def st_wf7_task(s, ctx):
    r = await ins(s, "irm", "remediation", title=f"Remediate {ctx['control_ref']} (agent-identified)", finding_id=ctx["finding_id"], control_id=ctx["control_id"], owner=ctx["owner"], due_date=today(), severity="High", status="In Progress")
    await upd(s, ctx["control_id"], status="Remediation In Progress")
    return {"remediation_id": r["id"]}


NOT_FOUND = {"skip_if": lambda c: not c.get("found"), "skip_reason": "No issue identified"}
engine.workflow("agent_control_issue", "WF7: Agent-Identified Control Issue → Human Review → GRC Finding → Remediation", LAB, "Agent control scan",
                "An agent flags a potential control issue; a human must approve before a GRC finding and remediation task are created.",
                [("Agent scans controls", st_scan, {}), ("Human review", APPROVAL, {**NOT_FOUND, "title": lambda c: f"Agent flagged {c.get('control_ref')}: approve GRC finding?", "role": "GRC Manager"}),
                 ("Create approved GRC finding", st_wf7_finding, NOT_FOUND), ("Create remediation task", st_wf7_task, NOT_FOUND)], cross_lab=True)


async def st_chg_assess(s, ctx):
    added = set(ctx["changes"].get("tools", [])) - set(ctx["old_tools"])
    ctx["sensitive"] = sorted(added & SENSITIVE_TOOLS)
    return {"tools_added": sorted(added), "sensitive_tools_added": ctx["sensitive"], "risk": "High" if ctx["sensitive"] else "Low"}


async def st_chg_apply(s, ctx):
    a = await get(s, ctx["agent_id"])
    nv = a["version"] + 1
    new = {**a, **ctx["changes"], "version": nv}
    await upd(s, a["id"], **{k: new[k] for k in ("instructions", "tools", "model", "objective", "version")})
    await ins(s, LAB, "agent_version", agent_id=a["id"], agent=a["name"], version=nv, snapshot={k: new[k] for k in ("instructions", "tools", "model", "objective")}, note=ctx.get("note", "Change"))
    return {"new_version": nv}


engine.workflow("agent_change", "Agent Change Approval", LAB, "Agent configuration change", "Assess change risk, approve, publish new agent version.",
                [("Assess change risk", st_chg_assess, {}), ("Change approval", APPROVAL, {"title": lambda c: f"Approve change to {c['agent']} (sensitive tools: {c.get('sensitive') or 'none'})", "role": "AI Operations Manager"}),
                 ("Publish new version", st_chg_apply, {})])


async def st_sens_propose(s, ctx):
    r = await run_named_agent(s, ctx["agent"], f"Propose sensitive action: {ctx['sensitive_action']}", {}, None, "agent_sensitive_action")
    return {"agent_run": r["id"], "mode": r["mode"], "proposal": r["output"][:300]}


async def st_sens_exec(s, ctx):
    await ins(s, LAB, "action_log", agent=ctx["agent"], action=ctx["sensitive_action"], result="Executed in sandbox after human approval")
    return {"executed": ctx["sensitive_action"]}


engine.workflow("agent_sensitive_action", "Human-in-the-Loop Sensitive Action", LAB, "Agent requests sensitive action", "Workflow pauses for human approval before a sensitive action executes.",
                [("Agent proposes action", st_sens_propose, {}), ("Human approval gate", APPROVAL, {"title": lambda c: f"{c['agent']} wants to: {c['sensitive_action']}", "role": "Human Reviewer"}),
                 ("Execute approved action (sandbox)", st_sens_exec, {})])

EVAL_SET = [("Privileged admin accounts not reviewed for 12 months", "High"), ("Public-facing app missing MFA for admins", "High"), ("Backup restore test overdue by 2 months", "Medium"),
            ("Password policy documented and enforced", "Low"), ("Unencrypted laptop with customer data lost", "High"), ("Change tickets missing CAB approval in 2 of 25 samples", "Medium"),
            ("Security awareness training 97% completion", "Low"), ("Vendor SOC 2 report expired last quarter", "Medium")]


def sim_classify(text):
    t = text.lower()
    score = sum(w in t for w in ["privileged", "admin", "unencrypted", "customer data", "public-facing"]) * 2 + sum(w in t for w in ["overdue", "missing", "expired"])
    return "High" if score >= 3 else "Medium" if score >= 1 else "Low"


@action(LAB, "create_agent")
async def a_create(s, p):
    d = validate({"name": ("str", True, 80), "objective": ("str", True, 300), "instructions": ("str", True, 2000), "tools": ("list", True, None), "model": ("choice", True, list(PRICING)),
                  "inputs": ("str", False, 200), "outputs": ("str", False, 200)}, p)
    bad = [t for t in d["tools"] if t not in TOOLS]
    if bad:
        raise HTTPException(422, f"Unknown tools: {bad}")
    if await find(s, LAB, "agent", name=d["name"]):
        raise HTTPException(409, "Agent name exists")
    a = await ins(s, LAB, "agent", role=d["name"], boundaries=BOUNDARY, status="active", version=1, **d)
    await ins(s, LAB, "agent_version", agent_id=a["id"], agent=a["name"], version=1, snapshot={k: a[k] for k in ("instructions", "tools", "model", "objective")}, note="Created")
    await audit(s, "agent.created", LAB, {"agent": a["name"]})
    return {"agent": a}


@action(LAB, "test_agent")
async def a_test(s, p):
    d = validate({"agent_id": ("str", True, 40), "task": ("str", True, 1500), "mode": ("choice", False, ["auto", "simulation"])}, p)
    return {"run": await execute_agent(s, await get(s, d["agent_id"], "agent"), d["task"], {"dataset": "fictional"}, d.get("mode", "auto"))}


@action(LAB, "update_agent")
async def a_update(s, p):
    d = validate({"agent_id": ("str", True, 40), "instructions": ("str", False, 2000), "tools": ("list", False, None), "model": ("choice", False, list(PRICING)), "note": ("str", False, 200)}, p)
    a = await get(s, d.pop("agent_id"), "agent")
    note = d.pop("note", "Change")
    if any(t not in TOOLS for t in d.get("tools", [])):
        raise HTTPException(422, "Unknown tool")
    return {"execution": await engine.start(s, "agent_change", {"agent_id": a["id"], "agent": a["name"], "old_tools": a["tools"], "changes": d, "note": note, "_lab": LAB}, "agent_change")}


@action(LAB, "rollback_agent")
async def a_rollback(s, p):
    d = validate({"agent_id": ("str", True, 40), "version": ("int", True, (1, 1000))}, p)
    v = await find(s, LAB, "agent_version", agent_id=d["agent_id"], version=d["version"])
    if not v:
        raise HTTPException(404, "Version not found")
    await upd(s, d["agent_id"], **v[0]["snapshot"], version=d["version"])
    await audit(s, "agent.rollback", LAB, d)
    return {"message": f"Rolled back to v{d['version']}"}


@action(LAB, "set_status")
async def a_status(s, p):
    d = validate({"agent_id": ("str", True, 40), "status": ("choice", True, ["active", "inactive"])}, p)
    await audit(s, f"agent.{d['status']}", LAB, d)
    return {"agent": await upd(s, (await get(s, d["agent_id"], "agent"))["id"], status=d["status"])}


@action(LAB, "run_assessment")
async def a_multi(s, p):
    d = validate({"request": ("str", True, 300), "scope": ("str", True, 300)}, p)
    return {"execution": await engine.start(s, "agent_grc_assessment", {**d, "_lab": LAB}, "assessment_request")}


@action(LAB, "control_scan")
async def a_scan(s, p):
    return {"execution": await engine.start(s, "agent_control_issue", {"_lab": LAB}, "agent_scan")}


@action(LAB, "security_test")
async def a_sec(s, p):
    d = validate({"agent_id": ("str", True, 40), "tool": ("choice", True, TOOLS), "prompt": ("str", True, 1500)}, p)
    run = await execute_agent(s, await get(s, d["agent_id"], "agent"), d["prompt"], None, "simulation", [d["tool"]])
    return {"run": run, "enforced": run["status"] == "blocked"}


@action(LAB, "sensitive_action")
async def a_sens(s, p):
    d = validate({"agent_id": ("str", True, 40), "sensitive_action": ("str", True, 200)}, p)
    a = await get(s, d["agent_id"], "agent")
    return {"execution": await engine.start(s, "agent_sensitive_action", {"agent": a["name"], "sensitive_action": d["sensitive_action"], "_lab": LAB}, "sensitive_action")}


@action(LAB, "evaluate")
async def a_eval(s, p):
    d = validate({"agent_id": ("str", True, 40), "mode": ("choice", True, ["simulation", "live"])}, p)
    a = await get(s, d["agent_id"], "agent")
    cases = []
    for text, exp in EVAL_SET:
        pred, mode = sim_classify(text), "simulation"
        if d["mode"] == "live":
            r = await execute_agent(s, a, f"Classify this control issue risk. Reply with exactly one word: Low, Medium or High. Issue: {text}", None, "auto", workflow="evaluation")
            if r["mode"] == "live":
                m = re.search(r"\b(Low|Medium|High)\b", r["output"])
                pred, mode = (m.group(1) if m else "Unparseable"), "live"
        cases.append({"input": text, "expected": exp, "predicted": pred, "pass": pred == exp, "mode": mode})
    acc = round(100 * sum(c["pass"] for c in cases) / len(cases), 1)
    ev = await ins(s, LAB, "eval_run", agent_id=a["id"], agent=a["name"], version=a["version"], mode=d["mode"], accuracy=acc, cases=cases,
                   live_cases=sum(c["mode"] == "live" for c in cases), dataset="Control-risk classification v1 (8 fictional cases)")
    return {"evaluation": ev}


@action(LAB, "cost_compare")
async def a_cost(s, p):
    d = validate({"task": ("str", True, 1500), "models": ("list", True, None), "quality_floor": ("float", False, (0, 1))}, p)
    rows = []
    tin = (len(d["task"]) + 400) // 4
    for m in d["models"]:
        if m not in PRICING:
            raise HTTPException(422, f"Unknown model {m}")
        pr = PRICING[m]
        tout = int(220 * pr["verbosity"])
        rows.append({"model": m, "tokens_in": tin, "tokens_out": tout, "est_cost_usd": cost(m, tin, tout), "cost_per_1k_runs": round(cost(m, tin, tout) * 1000, 2),
                     "modeled_latency_ms": modeled_latency(m, tout, d["task"] + m), "quality_index": pr["quality"]})
    floor = d.get("quality_floor", 0.8)
    ok = [r for r in rows if r["quality_index"] >= floor]
    rec = min(ok, key=lambda r: r["est_cost_usd"])["model"] if ok else None
    return {"comparison": await ins(s, LAB, "cost_compare", task=d["task"][:200], rows=rows, quality_floor=floor, recommended=rec,
                                    basis="Illustrative list prices & modeled latency (simulation); quality index is an illustrative benchmark")}


@kpi(LAB)
async def k_agents(s):
    runs = await find(s, LAB, "agent_run")
    agents = await find(s, LAB, "agent")
    appr = await db.approvals.find({"session": s, "workflow": {"$in": ["agent_grc_assessment", "agent_control_issue", "agent_sensitive_action", "agent_change"]}, "status": {"$ne": "pending"}}, P).to_list(500)
    per = {}
    for r in runs:
        k = (r["agent_name"], r["version"])
        x = per.setdefault(k, {"agent": r["agent_name"], "version": r["version"], "runs": 0, "success": 0, "blocked": 0, "lat": 0, "tokens": 0, "cost": 0.0, "live": 0, "retries": 0})
        x["runs"] += 1
        x["success"] += r["status"] == "success"
        x["blocked"] += r["status"] == "blocked"
        x["lat"] += r["latency_ms"]
        x["tokens"] += r["tokens_in"] + r["tokens_out"]
        x["cost"] += r["cost_usd"]
        x["live"] += r["mode"] == "live"
        x["retries"] += r.get("retries", 0)
    table = [{"agent": x["agent"], "version": f"v{x['version']}", "runs": x["runs"], "success_rate": f"{round(100 * x['success'] / x['runs'])}%", "failures_blocked": x["blocked"],
              "avg_latency_ms": round(x["lat"] / max(x["success"], 1)), "tokens": x["tokens"], "est_cost_usd": round(x["cost"], 5), "live_runs": x["live"], "retries": x["retries"]} for x in per.values()]
    st, g_left, s_left = await quota(s)
    budget = float(os.environ["AGENT_DAILY_BUDGET_USD"])
    spent = round(sum(r["cost_usd"] for r in runs if r["mode"] == "live"), 5)
    n = max(len(runs), 1)
    return {"kpis": [{"label": "Agents active", "value": f"{sum(1 for a in agents if a['status'] == 'active')}/{len(agents)}"}, {"label": "Runs", "value": len(runs)},
                     {"label": "Success rate", "value": f"{round(100 * sum(r['status'] == 'success' for r in runs) / n)}%"},
                     {"label": "Avg latency", "value": f"{round(sum(r['latency_ms'] for r in runs) / n)} ms"}, {"label": "Tokens (est.)", "value": sum(r['tokens_in'] + r['tokens_out'] for r in runs)},
                     {"label": "Live cost / budget", "value": f"${spent} / ${budget}"}, {"label": "Human approval rate", "value": f"{round(100 * sum(a['status'] == 'approved' for a in appr) / len(appr))}%" if appr else "n/a"},
                     {"label": "Security blocks", "value": sum(r['status'] == 'blocked' for r in runs)}],
            "charts": [{"title": "Runs by mode", "data": by_status(runs, "mode")}, {"title": "Runs by status", "data": by_status(runs)}],
            "table": table, "live": {"enabled": st["live_enabled"], "model": st["model"], "remaining_global": g_left, "remaining_session": s_left}, "tools": TOOLS, "models": list(PRICING)}
