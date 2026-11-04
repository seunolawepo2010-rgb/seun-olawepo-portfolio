from fastapi import HTTPException
from core import action, kpi, SCHEMAS, ins, upd, get, find, bulk, validate, by_status, in_days, today, now
import engine
from engine import APPROVAL

# ---------------- LAB 6: AI Governance ----------------
SCHEMAS["aigov"] = {}
SENS = {"public": 0, "internal": 1, "confidential": 3, "regulated": 4}
AUTO = {"advisory": 0, "human-in-loop": 1, "autonomous": 3}
IMPACT = {"low": 0, "moderate": 2, "high": 4}


async def seed_aigov(s):
    await bulk(s, "aigov", "ai_system", [
        {"name": "Policy Q&A Assistant (fictional)", "purpose": "Answer employee policy questions", "owner": "HR & Compliance", "model_type": "LLM (third-party)", "data_sensitivity": "internal",
         "autonomy": "advisory", "decision_impact": "low", "third_party": True, "user_facing": True, "tier": "Moderate", "status": "Approved – Monitoring"},
        {"name": "Transaction Anomaly Scorer (fictional)", "purpose": "Flag suspicious transactions for analyst review", "owner": "Fraud Ops", "model_type": "ML classifier",
         "data_sensitivity": "regulated", "autonomy": "human-in-loop", "decision_impact": "high", "third_party": False, "user_facing": False, "tier": "High", "status": "Approved – Monitoring"}])


async def st_ai_classify(s, ctx):
    a = await get(s, ctx["system_id"])
    pts = SENS[a["data_sensitivity"]] + AUTO[a["autonomy"]] + IMPACT[a["decision_impact"]] + (1 if a["third_party"] else 0) + (1 if a["user_facing"] else 0)
    tier = "Critical" if pts >= 10 else "High" if pts >= 7 else "Moderate" if pts >= 3 else "Low"
    await upd(s, a["id"], tier=tier, risk_points=pts, status="Under Assessment")
    ctx.update(tier=tier, name=a["name"], sys=a)
    return {"points": pts, "tier": tier, "rule": "sensitivity + autonomy + impact + third-party + user-facing"}


def checklist(kind):
    return {"Privacy impact assessment": ["Data inventory documented", "Lawful basis / purpose limitation", "Retention defined", "Data minimization applied"],
            "Security assessment": ["Prompt injection testing", "Access controls on model endpoints", "Logging & monitoring", "Secrets management"],
            "Bias & fairness review": ["Protected attributes identified", "Disparity metrics defined", "Test results reviewed"],
            "Explainability review": ["Explanation method documented", "User-facing explanation available"],
            "Third-party AI assessment": ["Provider terms reviewed", "Data usage/training opt-out confirmed", "Provider security attestation"],
            "Human oversight plan": ["Escalation path defined", "Override capability", "Reviewer training"]}[kind]


async def st_ai_assess(s, ctx):
    a = ctx.pop("sys")
    kinds = ["Security assessment"]
    if SENS[a["data_sensitivity"]] >= 3:
        kinds.append("Privacy impact assessment")
    if IMPACT[a["decision_impact"]] >= 2:
        kinds.append("Bias & fairness review")
    if a["decision_impact"] == "high" or a["autonomy"] == "autonomous":
        kinds += ["Explainability review", "Human oversight plan"]
    if a["third_party"]:
        kinds.append("Third-party AI assessment")
    for k in kinds:
        await ins(s, "aigov", "ai_assessment", system_id=ctx["system_id"], system=ctx["name"], kind=k, items=[{"item": i, "status": "Open"} for i in checklist(k)],
                  framework_ref="NIST AI RMF (Map/Measure/Manage) · ISO/IEC 42001 (summary)", status="Open")
    ctx["assessments"] = kinds
    return {"required_assessments": kinds}


async def st_ai_reviewers(s, ctx):
    rv = ["AI Governance Lead (fictional)"] + (["Privacy Officer (fictional)"] if "Privacy impact assessment" in ctx["assessments"] else []) + (["Model Risk (fictional)"] if ctx["tier"] in ("High", "Critical") else [])
    await upd(s, ctx["system_id"], reviewers=rv)
    return {"reviewers": rv}


async def st_ai_agent_review(s, ctx):
    from agents import run_named_agent
    run = await run_named_agent(s, "AI Governance Agent", f"Review AI system '{ctx['name']}' (tier {ctx['tier']}). Required assessments: {', '.join(ctx['assessments'])}. Recommend conditions for approval.",
                                {"tier": ctx["tier"], "assessments": ctx["assessments"]})
    return {"agent_run_id": run["id"], "mode": run["mode"], "recommendation": run["output"][:600]}


async def st_ai_monitor(s, ctx):
    await upd(s, ctx["system_id"], status="Approved – Monitoring", monitoring=["Drift (monthly)", "Incident rate", "Human override rate"], next_review=in_days(90 if ctx["tier"] in ("High", "Critical") else 180))
    return {"status": "Approved – Monitoring"}


async def rej_ai(s, ctx):
    await upd(s, ctx["system_id"], status="Rejected")


engine.workflow("ai_registration", "WF3: AI System Registration → Governance Assessment → Agent Review → Human Approval → Monitoring", "aigov", "New AI system registered",
                "Classifies risk tier, creates required assessments & checklists, assigns reviewers, gets AI Agent Manager review, routes to AI Governance Board, enables monitoring.",
                [("Classify AI risk tier", st_ai_classify, {}), ("Create required assessments", st_ai_assess, {}), ("Assign reviewers", st_ai_reviewers, {}),
                 ("AI Agent Manager review", st_ai_agent_review, {}), ("AI Governance Board approval", APPROVAL, {"title": lambda c: f"Approve AI system {c['name']} ({c['tier']})", "role": "AI Governance Board", "on_reject": rej_ai}),
                 ("Enable monitoring", st_ai_monitor, {})], cross_lab=True)


@action("aigov", "register_ai_system")
async def a_reg(s, p):
    d = validate({"name": ("str", True, 120), "purpose": ("str", True, 300), "owner": ("str", True, 80), "model_type": ("str", True, 60),
                  "data_sensitivity": ("choice", True, list(SENS)), "autonomy": ("choice", True, list(AUTO)), "decision_impact": ("choice", True, list(IMPACT)),
                  "third_party": ("bool", False, None), "user_facing": ("bool", False, None)}, p)
    d.setdefault("third_party", False)
    d.setdefault("user_facing", False)
    a = await ins(s, "aigov", "ai_system", status="Registered", **d)
    return {"system": a, "execution": await engine.start(s, "ai_registration", {"system_id": a["id"], "_lab": "aigov"}, "ai_system_registered")}


@action("aigov", "complete_checklist")
async def a_chk(s, p):
    d = validate({"assessment_id": ("str", True, 40), "item": ("str", True, 200), "status": ("choice", True, ["Pass", "Fail", "N/A"])}, p)
    a = await get(s, d["assessment_id"], "ai_assessment")
    items = [{**i, "status": d["status"]} if i["item"] == d["item"] else i for i in a["items"]]
    done = all(i["status"] != "Open" for i in items)
    await upd(s, a["id"], items=items, status=("Completed – Issues" if any(i["status"] == "Fail" for i in items) else "Completed") if done else "In Progress")
    return {"message": f"{d['item']}: {d['status']}"}


@action("aigov", "record_evaluation")
async def a_eval(s, p):
    d = validate({"system_id": ("str", True, 40), "metric": ("str", True, 60), "value": ("float", True, (0, 1e6)), "threshold": ("float", True, (0, 1e6)), "higher_is_better": ("bool", False, None)}, p)
    a = await get(s, d["system_id"], "ai_system")
    ok = d["value"] >= d["threshold"] if d.get("higher_is_better", True) else d["value"] <= d["threshold"]
    return {"evaluation": await ins(s, "aigov", "model_evaluation", system=a["name"], result="Within threshold" if ok else "Breach", label="SIMULATED evaluation record (not an actual model test)", **d)}


@action("aigov", "report_ai_incident")
async def a_inc(s, p):
    d = validate({"system_id": ("str", True, 40), "description": ("str", True, 500), "severity": ("choice", True, ["Low", "Medium", "High"])}, p)
    a = await get(s, d["system_id"], "ai_system")
    if d["severity"] == "High":
        await upd(s, a["id"], status="Suspended – Under Review")
    return {"incident": await ins(s, "aigov", "ai_incident", system=a["name"], status="Open", **{k: v for k, v in d.items() if k != "system_id"})}


@kpi("aigov")
async def k_ai(s):
    a = await find(s, "aigov", "ai_system")
    asm = await find(s, "aigov", "ai_assessment")
    return {"kpis": [{"label": "AI systems", "value": len(a)}, {"label": "High/Critical", "value": sum(1 for x in a if x.get("tier") in ("High", "Critical"))},
                     {"label": "Open assessments", "value": sum(1 for x in asm if not x["status"].startswith("Completed"))},
                     {"label": "AI incidents", "value": len(await find(s, "aigov", "ai_incident"))}],
            "charts": [{"title": "AI systems by tier", "data": by_status(a, "tier")}, {"title": "Assessments", "data": by_status(asm)}]}


# ---------------- LAB 8: Project / Product ----------------
SCHEMAS["pm"] = {
    "story": {"project_id": ("str", True, 40), "title": ("str", True, 200), "as_a": ("str", True, 100), "i_want": ("str", True, 300), "so_that": ("str", True, 300),
              "acceptance_criteria": ("str", True, 1000), "points": ("int", True, (1, 21)), "priority": ("choice", True, ["Must", "Should", "Could"])},
    "raid": {"project_id": ("str", True, 40), "kind": ("choice", True, ["Risk", "Assumption", "Issue", "Dependency"]), "description": ("str", True, 500), "owner": ("str", True, 80), "severity": ("choice", True, ["Low", "Medium", "High"])},
    "stakeholder": {"project_id": ("str", True, 40), "name": ("str", True, 80), "role": ("str", True, 80), "influence": ("choice", True, ["Low", "Medium", "High"]), "interest": ("choice", True, ["Low", "Medium", "High"])},
    "requirement": {"project_id": ("str", True, 40), "ref": ("str", True, 20), "kind": ("choice", True, ["Business", "Functional", "Non-functional"]), "text": ("str", True, 500)},
}
PROJECTS = [("ServiceNow IRM Migration (case study)", "Migrate legacy GRC spreadsheets into IRM modules", 420000),
            ("Audit Remediation Program (case study)", "Close prior-year audit findings with verified evidence", 180000),
            ("AI Governance Implementation (case study)", "Stand up AI inventory, intake and review board", 250000),
            ("Cybersecurity Controls Improvement (case study)", "Raise control effectiveness for priority NIST families", 310000),
            ("Enterprise Workflow Automation (case study)", "Automate approvals & notifications across GRC processes", 200000)]


async def seed_pm(s):
    for i, (n, bc, b) in enumerate(PROJECTS):
        p = await ins(s, "pm", "project", name=n, sponsor="Executive Sponsor (fictional)", business_case=bc, budget=b, spent=round(b * (0.35 + 0.1 * i)),
                      health="Green", status="In Flight", methodology="Hybrid Agile", charter=f"Objective: {bc}. Scope, success measures and governance defined in charter (fictional).")
        await bulk(s, "pm", "milestone", [{"project_id": p["id"], "project": n, "name": "Requirements sign-off", "due_date": in_days(-20), "critical": True, "status": "Complete"},
                                          {"project_id": p["id"], "project": n, "name": "UAT complete", "due_date": in_days(-2 if i == 0 else 25), "critical": True, "status": "In Progress", "escalated": False},
                                          {"project_id": p["id"], "project": n, "name": "Go-live", "due_date": in_days(60), "critical": True, "status": "Not Started", "escalated": False}])
        await bulk(s, "pm", "story", [{"project_id": p["id"], "title": t, "as_a": "GRC analyst", "i_want": t.lower(), "so_that": "work is traceable and auditable",
                                       "acceptance_criteria": "Given valid input, when saved, then the record is created and audit-logged", "points": pt, "priority": pr, "status": "Backlog", "sprint": None}
                                      for t, pt, pr in [("Import risk register", 5, "Must"), ("Configure approval routing", 8, "Must"), ("Build exec dashboard", 5, "Should"), ("Policy attestation reminders", 3, "Could")]])
        if i == 0:
            await bulk(s, "pm", "raid", [{"project_id": p["id"], "kind": "Dependency", "description": "Data owner availability for UAT", "owner": "PMO", "severity": "Medium", "status": "Open"}])
            await bulk(s, "pm", "stakeholder", [{"project_id": p["id"], "name": "CISO (fictional)", "role": "Sponsor", "influence": "High", "interest": "High"}])
            await bulk(s, "pm", "requirement", [{"project_id": p["id"], "ref": "BR-01", "kind": "Business", "text": "Single source of truth for enterprise risks"},
                                                {"project_id": p["id"], "ref": "FR-01", "kind": "Functional", "text": "System shall route remediation plans for approval"}])


async def st_pm_risk(s, ctx):
    m = await get(s, ctx["milestone_id"])
    r = await ins(s, "pm", "raid", project_id=m["project_id"], kind="Risk", description=f"Critical milestone '{m['name']}' overdue (due {m['due_date']})", owner="Project Manager", severity="High", status="Open")
    ctx.update(project_id=m["project_id"], milestone=m["name"], project=m["project"])
    return {"raid_id": r["id"]}


async def st_pm_health(s, ctx):
    await upd(s, ctx["project_id"], health="Red", health_reason=f"{ctx['milestone']} overdue")
    return {"health": "Red"}


async def st_pm_escalate(s, ctx):
    e = await ins(s, "pm", "escalation", project_id=ctx["project_id"], project=ctx["project"], title=f"Escalation: {ctx['milestone']} overdue", to="Steering Committee (fictional)", status="Open")
    await upd(s, ctx["milestone_id"], escalated=True)
    return {"escalation_id": e["id"]}


async def st_pm_report(s, ctx):
    p = await get(s, ctx["project_id"])
    ms = await find(s, "pm", "milestone", project_id=p["id"])
    r = await ins(s, "pm", "status_report", project_id=p["id"], project=p["name"], health=p["health"], revision="Revised (automated)",
                  summary=f"Health RED: '{ctx['milestone']}' overdue. Budget {round(100 * p['spent'] / p['budget'])}% consumed. {sum(1 for m in ms if m['status'] == 'Complete')}/{len(ms)} milestones complete. Escalated to steering committee.")
    return {"status_report_id": r["id"]}


engine.workflow("project_delay", "WF4: Milestone Delay → Project Risk → Escalation → Executive Status", "pm", "Critical milestone overdue (scheduler)",
                "Overdue critical milestones create a project risk, set health Red, escalate and publish a revised executive status report.",
                [("Log project risk (RAID)", st_pm_risk, {}), ("Update project health", st_pm_health, {}), ("Create escalation", st_pm_escalate, {}), ("Revise executive status report", st_pm_report, {})], cross_lab=True)


async def pm_health_check(s):
    out = []
    for m in await find(s, "pm", "milestone"):
        if m.get("critical") and m["status"] != "Complete" and m["due_date"] < today() and not m.get("escalated"):
            out.append((await engine.start(s, "project_delay", {"milestone_id": m["id"], "_lab": "pm"}, "scheduler:overdue_milestone"))["id"])
    return out


@action("pm", "create_project")
async def a_proj(s, p):
    d = validate({"name": ("str", True, 150), "sponsor": ("str", True, 80), "business_case": ("str", True, 1000), "budget": ("float", True, (0, 1e9)), "methodology": ("choice", True, ["Agile", "Waterfall", "Hybrid Agile"])}, p)
    pr = await ins(s, "pm", "project", spent=0, health="Green", status="Intake", charter=f"Objective: {d['business_case']}", **d)
    await ins(s, "pm", "milestone", project_id=pr["id"], project=pr["name"], name="Charter approved", due_date=in_days(14), critical=True, status="Not Started", escalated=False)
    return {"project": pr}


@action("pm", "health_check")
async def a_health(s, p):
    ids = await pm_health_check(s)
    return {"executions": ids, "message": f"{len(ids)} overdue critical milestone(s) escalated" if ids else "No new overdue critical milestones"}


@action("pm", "simulate_delay")
async def a_delay(s, p):
    d = validate({"milestone_id": ("str", True, 40)}, p)
    m = await get(s, d["milestone_id"], "milestone")
    if m["status"] == "Complete":
        raise HTTPException(409, "Milestone already complete")
    await upd(s, m["id"], due_date=in_days(-1), critical=True, escalated=False)
    return {"executions": await pm_health_check(s)}


@action("pm", "complete_milestone")
async def a_ms(s, p):
    d = validate({"milestone_id": ("str", True, 40)}, p)
    m = await upd(s, (await get(s, d["milestone_id"], "milestone"))["id"], status="Complete")
    left = [x for x in await find(s, "pm", "milestone", project_id=m["project_id"]) if x["status"] != "Complete" and x["due_date"] < today()]
    if not left:
        await upd(s, m["project_id"], health="Green")
    return {"message": "Milestone complete" + ("; project health restored to Green" if not left else "")}


@action("pm", "move_story")
async def a_move(s, p):
    d = validate({"story_id": ("str", True, 40), "status": ("choice", True, ["Backlog", "To Do", "In Progress", "Done"])}, p)
    return {"story": await upd(s, (await get(s, d["story_id"], "story"))["id"], status=d["status"])}


@action("pm", "plan_sprint")
async def a_sprint(s, p):
    d = validate({"project_id": ("str", True, 40), "sprint": ("str", True, 30), "capacity": ("int", True, (1, 200))}, p)
    order = {"Must": 0, "Should": 1, "Could": 2}
    backlog = sorted([x for x in await find(s, "pm", "story", project_id=d["project_id"]) if x["status"] == "Backlog"], key=lambda x: order[x["priority"]])
    used, picked = 0, []
    for st in backlog:
        if used + st["points"] <= d["capacity"]:
            used += st["points"]
            picked.append(st["title"])
            await upd(s, st["id"], status="To Do", sprint=d["sprint"])
    await ins(s, "pm", "sprint", project_id=d["project_id"], name=d["sprint"], capacity=d["capacity"], committed=used, status="Active")
    return {"committed_points": used, "stories": picked}


@action("pm", "close_sprint")
async def a_close(s, p):
    d = validate({"project_id": ("str", True, 40), "sprint": ("str", True, 30), "went_well": ("str", True, 500), "improve": ("str", True, 500)}, p)
    sp = await find(s, "pm", "sprint", project_id=d["project_id"], name=d["sprint"])
    if not sp:
        raise HTTPException(404, "Sprint not found")
    stories = await find(s, "pm", "story", project_id=d["project_id"], sprint=d["sprint"])
    done = sum(x["points"] for x in stories if x["status"] == "Done")
    for x in stories:
        if x["status"] != "Done":
            await upd(s, x["id"], status="Backlog", sprint=None)
    await upd(s, sp[0]["id"], status="Closed", velocity=done)
    await ins(s, "pm", "retrospective", project_id=d["project_id"], sprint=d["sprint"], went_well=d["went_well"], improve=d["improve"], velocity=done)
    return {"velocity": done, "carried_over": sum(1 for x in stories if x["status"] != "Done")}


async def st_cr_impact(s, ctx):
    return {"cost_impact": ctx["impact_cost"], "schedule_impact_days": ctx["impact_days"], "approver": "Sponsor" if ctx["impact_cost"] > 25000 else "Project Manager"}


async def st_cr_apply(s, ctx):
    p = await get(s, ctx["project_id"])
    await upd(s, p["id"], budget=p["budget"] + ctx["impact_cost"])
    await upd(s, ctx["cr_id"], status="Approved")
    return {"new_budget": p["budget"] + ctx["impact_cost"]}


async def rej_cr(s, ctx):
    await upd(s, ctx["cr_id"], status="Rejected")


engine.workflow("pm_change", "Project Change Request", "pm", "Change request submitted", "Impact analysis, approval, apply to baseline.",
                [("Impact analysis", st_cr_impact, {}), ("Change control approval", APPROVAL, {"title": lambda c: f"Change request: {c['title']}", "role": "Sponsor / CCB", "on_reject": rej_cr}),
                 ("Update baseline", st_cr_apply, {})])


@action("pm", "submit_change_request")
async def a_cr(s, p):
    d = validate({"project_id": ("str", True, 40), "title": ("str", True, 150), "impact_cost": ("float", True, (0, 1e8)), "impact_days": ("int", True, (0, 365))}, p)
    await get(s, d["project_id"], "project")
    cr = await ins(s, "pm", "change_request", status="Submitted", **d)
    return {"execution": await engine.start(s, "pm_change", {"cr_id": cr["id"], **d, "_lab": "pm"}, "change_request")}


@action("pm", "record_uat")
async def a_uat(s, p):
    d = validate({"story_id": ("str", True, 40), "result": ("choice", True, ["Pass", "Fail"]), "tester": ("str", True, 80)}, p)
    st = await get(s, d["story_id"], "story")
    await ins(s, "pm", "uat", story=st["title"], project_id=st["project_id"], result=d["result"], tester=d["tester"])
    if d["result"] == "Fail":
        await upd(s, st["id"], status="In Progress")
    return {"message": f"UAT {d['result']} recorded"}


@kpi("pm")
async def k_pm(s):
    p = await find(s, "pm", "project")
    st = await find(s, "pm", "story")
    return {"kpis": [{"label": "Projects", "value": len(p)}, {"label": "Red health", "value": sum(1 for x in p if x["health"] == "Red")},
                     {"label": "Budget consumed", "value": f"{round(100 * sum(x['spent'] for x in p) / max(sum(x['budget'] for x in p), 1))}%"},
                     {"label": "Open escalations", "value": sum(1 for x in await find(s, "pm", "escalation") if x["status"] == "Open")}],
            "charts": [{"title": "Project health", "data": by_status(p, "health")}, {"title": "Stories by status", "data": by_status(st)}]}


# ---------------- LAB 10: Incident Response & BCDR ----------------
SCHEMAS["ir"] = {}
PLAYBOOK = {"Ransomware": ["Isolate affected hosts", "Disable compromised accounts", "Preserve forensic images", "Validate backup integrity", "Restore from clean backups"],
            "Data Breach": ["Contain data egress path", "Identify affected records", "Engage legal & privacy (fictional)", "Prepare regulator notification assessment"],
            "Phishing": ["Purge malicious emails", "Reset affected credentials", "Block sender/domain"],
            "DDoS": ["Engage upstream scrubbing", "Rate-limit edge", "Monitor service health"],
            "Insider Threat": ["Suspend access", "Preserve logs", "HR & legal coordination (fictional)"]}


async def seed_ir(s):
    await bulk(s, "ir", "bia_process", [{"process": p, "systems": sy, "rto_hours": rto, "rpo_hours": rpo, "priority": pr} for p, sy, rto, rpo, pr in [
        ("Customer Payments Processing", ["Payments Gateway", "Core Ledger DB"], 4, 1, 1), ("Online Customer Portal", ["Customer Portal"], 8, 4, 2),
        ("Payroll", ["HR SaaS"], 48, 24, 3), ("Internal Email & Collaboration", ["Email"], 24, 12, 3)]])


async def st_ir_tasks(s, ctx):
    inc = await get(s, ctx["incident_id"])
    steps = PLAYBOOK[inc["category"]]
    for t in steps:
        await ins(s, "ir", "ir_task", incident_id=inc["id"], title=t, status="Open", owner="IR Team (fictional)")
    ctx.update(category=inc["category"], systems=inc["affected_systems"], title=inc["title"])
    return {"tasks_created": len(steps), "playbook": inc["category"]}


async def st_ir_escalate(s, ctx):
    e = await ins(s, "ir", "escalation", incident_id=ctx["incident_id"], to=["CISO (fictional)", "Legal (fictional)", "Communications (fictional)"], delivery="In-app record only – no real notifications sent", status="Open")
    return {"escalation_id": e["id"]}


async def st_ir_timeline(s, ctx):
    await ins(s, "ir", "timeline", incident_id=ctx["incident_id"], event="Critical severity confirmed; response playbook initiated", at=now())
    return {"timeline": "updated"}


async def st_ir_bcdr(s, ctx):
    hit = [b for b in await find(s, "ir", "bia_process") if set(b["systems"]) & set(ctx["systems"])]
    for b in hit:
        await ins(s, "ir", "recovery_item", incident_id=ctx["incident_id"], process=b["process"], rto_hours=b["rto_hours"], rpo_hours=b["rpo_hours"], priority=b["priority"], status="Not Recovered")
    await upd(s, ctx["incident_id"], bcdr_review="Completed", impacted_processes=[b["process"] for b in hit])
    return {"impacted_processes": [b["process"] for b in hit], "min_rto_hours": min([b["rto_hours"] for b in hit], default=None)}


engine.workflow("critical_incident", "WF6: Critical Incident → Response → BCDR Assessment → Recovery Tracking", "ir", "Incident classified Critical",
                "Creates playbook tasks, escalation record, timeline entry, BCDR impact review from the BIA and recovery tracking items.",
                [("Create response tasks", st_ir_tasks, {}), ("Escalate", st_ir_escalate, {}), ("Update incident timeline", st_ir_timeline, {}), ("BCDR impact review & recovery tracking", st_ir_bcdr, {})], cross_lab=True)


@action("ir", "create_incident")
async def a_incident(s, p):
    d = validate({"title": ("str", True, 150), "category": ("choice", True, list(PLAYBOOK)), "affected_systems": ("list", True, None),
                  "data_involved": ("choice", True, ["none", "internal", "pii", "regulated"]), "users_affected": ("int", True, (0, 10_000_000)), "description": ("str", False, 1000)}, p)
    pts = {"none": 0, "internal": 1, "pii": 3, "regulated": 4}[d["data_involved"]] + (3 if d["users_affected"] > 1000 else 1 if d["users_affected"] > 50 else 0) + (3 if d["category"] == "Ransomware" else 1)
    sev = "Critical" if pts >= 6 else "High" if pts >= 4 else "Medium" if pts >= 2 else "Low"
    inc = await ins(s, "ir", "incident", severity=sev, severity_points=pts, phase="Triage", status="Open", **d)
    await ins(s, "ir", "timeline", incident_id=inc["id"], event=f"Incident reported; classified {sev} ({pts} pts)", at=now())
    exe = await engine.start(s, "critical_incident", {"incident_id": inc["id"], "_lab": "ir"}, "critical_incident") if sev == "Critical" else None
    return {"incident": inc, "execution": exe}


@action("ir", "advance_phase")
async def a_phase(s, p):
    d = validate({"incident_id": ("str", True, 40), "phase": ("choice", True, ["Triage", "Investigation", "Containment", "Eradication", "Recovery", "Closed"]), "note": ("str", True, 500)}, p)
    await get(s, d["incident_id"], "incident")
    await upd(s, d["incident_id"], phase=d["phase"], status="Closed" if d["phase"] == "Closed" else "Open")
    await ins(s, "ir", "timeline", incident_id=d["incident_id"], event=f"{d['phase']}: {d['note']}", at=now())
    return {"message": f"Phase → {d['phase']}"}


@action("ir", "update_task")
async def a_task(s, p):
    d = validate({"task_id": ("str", True, 40), "status": ("choice", True, ["Open", "In Progress", "Done"])}, p)
    t = await upd(s, (await get(s, d["task_id"], "ir_task"))["id"], status=d["status"])
    await ins(s, "ir", "timeline", incident_id=t["incident_id"], event=f"Task '{t['title']}' → {d['status']}", at=now())
    return {"task": t}


@action("ir", "recovery_update")
async def a_recover(s, p):
    d = validate({"item_id": ("str", True, 40), "hours_to_recover": ("float", True, (0, 1000))}, p)
    it = await get(s, d["item_id"], "recovery_item")
    met = d["hours_to_recover"] <= it["rto_hours"]
    await upd(s, it["id"], status="Recovered", hours_to_recover=d["hours_to_recover"], rto_met=met)
    await ins(s, "ir", "timeline", incident_id=it["incident_id"], event=f"{it['process']} recovered in {d['hours_to_recover']}h (RTO {it['rto_hours']}h {'met' if met else 'MISSED'})", at=now())
    return {"rto_met": met}


@action("ir", "record_rca")
async def a_rca(s, p):
    d = validate({"incident_id": ("str", True, 40), "root_cause": ("str", True, 1000), "lessons_learned": ("str", True, 1000)}, p)
    await get(s, d["incident_id"], "incident")
    return {"incident": await upd(s, d["incident_id"], root_cause=d["root_cause"], lessons_learned=d["lessons_learned"])}


@action("ir", "run_bcdr_exercise")
async def a_ex(s, p):
    d = validate({"process_id": ("str", True, 40), "scenario": ("str", True, 300), "actual_recovery_hours": ("float", True, (0, 1000))}, p)
    b = await get(s, d["process_id"], "bia_process")
    met = d["actual_recovery_hours"] <= b["rto_hours"]
    return {"exercise": await ins(s, "ir", "bcdr_exercise", process=b["process"], scenario=d["scenario"], actual_recovery_hours=d["actual_recovery_hours"], rto_hours=b["rto_hours"], result="Pass" if met else "Fail")}


@kpi("ir")
async def k_ir(s):
    i = await find(s, "ir", "incident")
    rec = await find(s, "ir", "recovery_item")
    done = [x for x in rec if x["status"] == "Recovered"]
    return {"kpis": [{"label": "Open incidents", "value": sum(1 for x in i if x["status"] == "Open")}, {"label": "Critical", "value": sum(1 for x in i if x["severity"] == "Critical")},
                     {"label": "Recovery items", "value": f"{len(done)}/{len(rec)}"}, {"label": "RTO compliance", "value": f"{round(100 * sum(1 for x in done if x['rto_met']) / len(done))}%" if done else "n/a"}],
            "charts": [{"title": "Incidents by severity", "data": by_status(i, "severity")}, {"title": "Incidents by phase", "data": by_status(i, "phase")}]}
