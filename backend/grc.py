from fastapi import HTTPException
from core import action, kpi, SCHEMAS, ins, upd, get, find, validate, by_status, in_days, today, now, audit
import engine

LAB = "grc"
SCHEMAS[LAB] = {}
ROLES = ["grc_admin", "policy_owner", "policy_reviewer", "approver", "risk_analyst", "control_owner", "issue_owner", "remediation_owner", "auditor", "employee", "executive", "compliance_owner"]
PREFIX = {"policy": "POL", "control": "CTL", "assessment": "CAS", "campaign": "ACM", "ack": "ACK", "exception": "EXC", "risk": "RSK", "issue": "ISS", "task": "RTK", "notification": "NTF"}
EMPLOYEES = {"Finance": ["Avery Brooks", "Jordan Lee", "Priya Nair"], "IT": ["Marcus Hall", "Elena Ruiz", "Tom Becker"], "HR": ["Grace Kim", "Samuel Ortiz"], "Operations": ["Nina Patel", "Owen Carter"]}
REGS = ["NIST SP 800-53", "NIST CSF", "ISO 27001", "SOC 2", "SOX ITGC", "PCI DSS", "HIPAA", "GLBA", "NYDFS", "GDPR", "CCPA"]
THRESHOLD = 12


def H(by, kind, text, days=0):
    return {"at": now() if not days else f"{in_days(days)}T10:00:00+00:00", "by": by, "kind": kind, "text": text}


async def num(s, t):
    return f"{PREFIX[t]}{1001 + len(await find(s, LAB, t)):07d}"


async def new(s, t, by, text, days=0, **f):
    return await ins(s, LAB, t, number=await num(s, t), history=[H(by, "created", text, days)], **f)


async def log(s, rec, by, kind, text, **f):
    rec = await get(s, rec["id"])
    return await upd(s, rec["id"], history=rec.get("history", []) + [H(by, kind, text)], **f)


async def notify(s, to, subject, rec, days=0):
    await ins(s, LAB, "notification", number=await num(s, "notification"), to=to, subject=subject, related=rec.get("number"), related_id=rec["id"],
              channel="In-app (simulated – no email sent)", read=False, history=[H("system", "created", subject, days)])


def need(cond, msg):
    if not cond:
        raise HTTPException(409, msg)


# ---------- transition hooks ----------
async def g_submit(s, r, d):
    need(r.get("reviewers") and r.get("regulations"), "Assign reviewers and applicable regulations before submitting for review")


async def a_submit(s, r, d):
    for rv in r["reviewers"]:
        await notify(s, rv, f"Review requested: {r['number']} {r['title']}", r)


async def e_review(s, r, d):
    return {"reviewed": True, "review_comments": r.get("review_comments", []) + [{"by": "Policy Reviewer", "at": now(), "comment": d["comment"]}]}


async def g_approve_pol(s, r, d):
    need(r.get("reviewed"), "Policy review must be completed before approval")


async def e_approve_pol(s, r, d):
    return {"approval_history": r.get("approval_history", []) + [{"by": "Approver", "decision": "Approved", "at": now(), "comment": d.get("comment", "")}]}


async def e_publish(s, r, d):
    return {"effective_date": today(), "review_date": in_days(365)}


async def g_retire(s, r, d):
    need(not await find(s, LAB, "campaign", policy_id=r["id"], state="Active"), "Close active acknowledgment campaigns before retiring")


async def a_launch(s, r, d):
    pol = await get(s, r["policy_id"])
    need(pol["state"] == "Published", "Only Published policies can be campaigned")
    await engine.start(s, "grc_campaign_launch", {"campaign_id": r["id"], "_lab": LAB}, "campaign_launched")


async def e_close_camp(s, r, d):
    acks = await find(s, LAB, "ack", campaign_id=r["id"])
    done = sum(a["state"] == "Acknowledged" for a in acks)
    for a in acks:
        if a["state"] != "Acknowledged":
            await log(s, a, "system", "state", f"{a['state']} → Not Completed (campaign closed)", state="Not Completed")
    return {"final_total": len(acks), "final_acknowledged": done, "final_completion_pct": round(100 * done / max(len(acks), 1), 1), "closed_at": now()}


async def g_ack(s, r, d):
    need(d.get("employee") == r["employee"], f"Only {r['employee']} can acknowledge this task (select that employee)")
    c = await get(s, r["campaign_id"])
    need(c["state"] == "Active", "Campaign is not active")


async def e_ack(s, r, d):
    return {"acknowledged_at": now()}


async def e_exc_assess(s, r, d):
    score = int(d["likelihood"]) * int(d["impact"])
    res = round(score * (1 - int(d["compensating_effectiveness"]) / 100), 1)
    rating = "High" if res >= 12 else "Medium" if res >= 6 else "Low"
    return {"inherent_score": score, "risk_score": res, "risk_rating": rating, "compensating_controls": d.get("compensating_controls", r.get("compensating_controls")),
            "approver": "CISO (fictional)" if rating == "High" else "Policy Owner (fictional)"}


async def e_exc_approve(s, r, d):
    return {"expires": in_days(int(r["duration_days"])), "approved_at": now(), "approval_history": r.get("approval_history", []) + [{"decision": "Approved", "by": r.get("approver"), "at": now(), "comment": d.get("comment", "")}]}


async def e_exc_reject(s, r, d):
    return {"approval_history": r.get("approval_history", []) + [{"decision": "Rejected", "by": r.get("approver"), "at": now(), "comment": d["comment"]}]}


async def e_renew(s, r, d):
    return {"duration_days": int(r["duration_days"]) + int(d["extra_days"]), "renewal_requested": True}


async def e_risk_assess(s, r, d):
    L, I, ce = int(d["likelihood"]), int(d["impact"]), int(d["control_effectiveness"])
    q = d.get("questionnaire") or {}
    L = min(5, L + sum(1 for v in q.values() if v == "no") // 2)
    inh, res = L * I, round(L * I * (1 - ce / 100), 1)
    rating = "Critical" if res >= 20 else "High" if res >= THRESHOLD else "Medium" if res >= 6 else "Low"
    return {"likelihood": L, "impact": I, "control_effectiveness": ce, "inherent": inh, "residual": res, "rating": rating, "questionnaire": q, "review_date": in_days(90)}


async def a_risk_assess(s, r, d):
    r = await get(s, r["id"])
    await new(s, "risk_assessment", "risk_analyst", f"Assessment of {r['number']} recorded", risk_id=r["id"], risk=r["number"], likelihood=r["likelihood"], impact=r["impact"],
              control_effectiveness=r["control_effectiveness"], inherent=r["inherent"], residual=r["residual"], rating=r["rating"], questionnaire=r.get("questionnaire"), assessor="Risk Analyst (fictional)", state="Completed")
    if r["residual"] >= THRESHOLD:
        await engine.start(s, "grc_risk_threshold", {"risk_id": r["id"], "_lab": LAB}, "risk_threshold_exceeded")


async def e_risk_approve(s, r, d):
    return {"approved_at": now(), "next_review": in_days(90)}


async def g_risk_close(s, r, d):
    open_iss = [i for i in await find(s, LAB, "issue", risk_id=r["id"]) if i["state"] != "Closed"]
    need(not open_iss, f"{len(open_iss)} linked issue(s) still open")


async def a_issue_assign(s, r, d):
    t = await new(s, "task", "issue_owner", f"Remediation task created from {r['number']}", issue_id=r["id"], issue=r["number"], title=f"Remediate: {r['title']}",
                  assignment_group="GRC Remediation", assigned_to=None, priority="1 - Critical" if r["severity"] in ("Critical", "High") else "3 - Moderate",
                  sla_due=d["due_date"], due_date=d["due_date"], action_plan=d["action_plan"], evidence=[], state="Open")
    await notify(s, "GRC Remediation group", f"New remediation task {t['number']} for {r['number']}", t)


async def g_issue_validate(s, r, d):
    tasks = await find(s, LAB, "task", issue_id=r["id"])
    need(tasks and all(t["state"] == "Closed" for t in tasks), "All remediation tasks must be Closed before issue validation")


async def a_issue_validate(s, r, d):
    r = await get(s, r["id"])
    if r["state"] == "Remediation in Progress":
        t = await new(s, "task", "auditor", f"Rework task created after failed validation of {r['number']}", issue_id=r["id"], issue=r["number"], title=f"Rework: {r['title']}",
                      assignment_group="GRC Remediation", assigned_to=None, priority="2 - High", sla_due=in_days(14), due_date=in_days(14), action_plan="Address validation gaps", evidence=[], state="Open")
        await notify(s, "Issue Owner", f"Validation failed for {r['number']}; rework task {t['number']} created", t)
        return
    if r["state"] != "Closed":
        return
    if r.get("control_id"):
        c = await get(s, r["control_id"])
        await log(s, c, "system", "state", f"{c['state']} → Effective (issue {r['number']} closed)", state="Effective")
    if r.get("risk_id"):
        rk = await get(s, r["risk_id"])
        ce = min(90, rk.get("control_effectiveness", 0) + 40)
        res = round(rk.get("inherent", 0) * (1 - ce / 100), 1)
        await log(s, rk, "system", "field", f"Residual risk updated {rk.get('residual')} → {res} after {r['number']} closure", control_effectiveness=ce, residual=res,
                  rating="High" if res >= THRESHOLD else "Medium" if res >= 6 else "Low")
    await ins(s, LAB, "dashboard_event", summary=f"{r['number']} closed; dashboards refreshed")


async def g_task_submit(s, r, d):
    need(r.get("evidence"), "Attach remediation evidence before submitting for validation")


async def e_task_validate(s, r, d):
    return {"validation_result": d["result"], "reviewer": "Auditor (fictional)", "completed_at": now() if d["result"] == "pass" else None}


async def a_task_close(s, r, d):
    iss = await get(s, r["issue_id"])
    tasks = await find(s, LAB, "task", issue_id=iss["id"])
    if all(t["state"] == "Closed" for t in tasks) and iss["state"] == "Remediation in Progress":
        await log(s, iss, "system", "state", "Remediation in Progress → Validation (all tasks closed)", state="Validation")
        await notify(s, "Auditor", f"{iss['number']} ready for validation", iss)


# act: (from, to, roles, required data fields, guard, effect, after); to may be callable(data)
T = {
    "policy": {"submit_for_review": (["Draft"], "Review", ["policy_owner", "grc_admin"], [], g_submit, None, a_submit),
               "complete_review": (["Review"], "Review", ["policy_reviewer"], ["comment"], None, e_review, None),
               "return_to_draft": (["Review"], "Draft", ["policy_reviewer", "approver"], ["comment"], None, None, None),
               "approve": (["Review"], "Approved", ["approver"], [], g_approve_pol, e_approve_pol, None),
               "publish": (["Approved"], "Published", ["policy_owner", "grc_admin"], [], None, e_publish, None),
               "retire": (["Published"], "Retired", ["policy_owner", "grc_admin"], ["comment"], g_retire, None, None)},
    "campaign": {"launch": (["Draft"], "Active", ["grc_admin", "policy_owner"], [], None, None, a_launch),
                 "close": (["Active"], "Closed", ["grc_admin"], [], None, e_close_camp, None)},
    "ack": {"acknowledge": (["Pending", "Overdue"], "Acknowledged", ["employee"], ["employee"], g_ack, e_ack, None)},
    "exception": {"assess_risk": (["Requested"], "Review", ["risk_analyst"], ["likelihood", "impact", "compensating_effectiveness"], None, e_exc_assess, None),
                  "approve": (["Review"], "Active", ["approver"], [], None, e_exc_approve, None),
                  "reject": (["Review"], "Rejected", ["approver"], ["comment"], None, e_exc_reject, None),
                  "request_renewal": (["Active"], "Review", ["policy_owner", "control_owner"], ["extra_days"], None, e_renew, None),
                  "close": (["Active", "Expired"], "Closed", ["policy_owner", "grc_admin"], ["closure_evidence"], None, lambda s, r, d: _ret({"closure_evidence": d["closure_evidence"], "closed_at": now()}), None)},
    "risk": {"assess": (["Identified"], "Assessed", ["risk_analyst"], ["likelihood", "impact", "control_effectiveness"], None, e_risk_assess, a_risk_assess),
             "treat": (["Assessed", "Treatment"], "Pending Approval", ["risk_analyst"], ["treatment", "mitigation_plan"], None, lambda s, r, d: _ret({"treatment": d["treatment"], "mitigation_plan": d["mitigation_plan"]}), None),
             "approve": (["Pending Approval"], lambda r: "Accepted" if r.get("treatment") == "Accept" else "Monitoring", ["approver"], [], None, e_risk_approve, None),
             "reject": (["Pending Approval"], "Treatment", ["approver"], ["comment"], None, None, None),
             "close": (["Monitoring"], "Closed", ["risk_analyst", "grc_admin"], [], g_risk_close, None, None)},
    "issue": {"analyze": (["Identified"], "Analysis", ["issue_owner"], ["root_cause"], None, lambda s, r, d: _ret({"root_cause": d["root_cause"]}), None),
              "assign": (["Analysis"], "Assigned", ["issue_owner"], ["remediation_owner", "due_date", "action_plan"], None, lambda s, r, d: _ret({k: d[k] for k in ("remediation_owner", "due_date", "action_plan")}), a_issue_assign),
              "start_remediation": (["Assigned"], "Remediation in Progress", ["remediation_owner"], [], None, None, None),
              "validate": (["Validation"], lambda r: "Closed" if r.get("_decision") == "pass" else "Remediation in Progress", ["auditor"], ["decision"], g_issue_validate,
                           lambda s, r, d: _ret({"validation": d["decision"], "closed_at": now() if d["decision"] == "pass" else None}), a_issue_validate)},
    "task": {"assign": (["Open"], "Assigned", ["issue_owner", "grc_admin"], ["assigned_to"], None, lambda s, r, d: _ret({"assigned_to": d["assigned_to"]}), None),
             "start_work": (["Assigned"], "Work in Progress", ["remediation_owner"], [], None, None, None),
             "submit_for_validation": (["Work in Progress"], "Pending Validation", ["remediation_owner"], [], g_task_submit, None, None),
             "validate": (["Pending Validation"], lambda r: "Completed" if r.get("_decision") == "pass" else "Work in Progress", ["auditor"], ["result"], None, e_task_validate, None),
             "close": (["Completed"], "Closed", ["issue_owner", "grc_admin"], ["closure_notes"], None, lambda s, r, d: _ret({"closure_notes": d["closure_notes"], "closed_at": now()}), a_task_close)},
}


async def _ret(x):
    return x


def role_of(p):
    r = p.get("role")
    if r not in ROLES:
        raise HTTPException(422, f"role must be one of {ROLES}")
    return r


@action(LAB, "meta")
async def a_meta(s, p):
    return {"roles": ROLES, "employees": EMPLOYEES, "regulations": REGS,
            "transitions": {t: {a: {"from": v[0], "roles": v[2], "requires": v[3]} for a, v in acts.items()} for t, acts in T.items()}}


@action(LAB, "transition")
async def a_transition(s, p):
    role = role_of(p)
    d = p.get("data") or {}
    rec = await get(s, str(p.get("id", "")))
    spec = T.get(rec["type"], {}).get(p.get("act"))
    if not spec:
        raise HTTPException(404, "Unknown transition")
    frm, to, roles, req, guard, effect, after = spec
    if role not in roles:
        await audit(s, "grc.permission_denied", LAB, {"record": rec["number"], "act": p["act"], "role": role})
        raise HTTPException(403, f"Role '{role}' is not permitted to {p['act']} (allowed: {', '.join(roles)})")
    need(rec["state"] in frm, f"{rec['number']} is '{rec['state']}'; '{p['act']}' requires {frm}")
    missing = [k for k in req if d.get(k) in (None, "")]
    if missing:
        raise HTTPException(422, f"Required: {', '.join(missing)}")
    if guard:
        await guard(s, rec, d)
    fields = (await effect(s, rec, d)) if effect else {}
    target = to({**rec, "_decision": d.get("decision") or d.get("result"), **fields}) if callable(to) else to
    note = f" — {d.get('comment') or d.get('note') or ''}".rstrip(" —")
    rec = await log(s, rec, role, "state", f"{rec['state']} → {target} ({p['act']}){note}", state=target, **fields)
    if after:
        await after(s, rec, d)
    rec = await get(s, rec["id"])
    await audit(s, f"grc.{rec['type']}.{p['act']}", LAB, {"record": rec["number"], "to": rec["state"], "role": role})
    return {"record": rec, "message": f"{rec['number']} → {rec['state']}"}


@action(LAB, "work_note")
async def a_note(s, p):
    role = role_of(p)
    need(role != "executive", "Executive Viewer is read-only")
    d = validate({"id": ("str", True, 40), "text": ("str", True, 1000)}, p)
    return {"record": await log(s, await get(s, d["id"]), role, "work_note", d["text"])}


@action(LAB, "attach")
async def a_attach(s, p):
    role = role_of(p)
    d = validate({"id": ("str", True, 40), "name": ("str", True, 120), "description": ("str", True, 500)}, p)
    rec = await get(s, d["id"])
    need(role in ("remediation_owner", "control_owner", "grc_admin"), "Only remediation/control owners can attach evidence")
    att = {"name": d["name"], "description": d["description"], "by": role, "at": now(), "label": "Evidence metadata (demo – no file stored)"}
    return {"record": await log(s, rec, role, "attachment", f"Attached {d['name']}", evidence=rec.get("evidence", []) + [att])}


@action(LAB, "create_policy")
async def a_create_policy(s, p):
    role = role_of(p)
    need(role in ("policy_owner", "grc_admin"), "Only Policy Owner or GRC Administrator can create policies")
    d = validate({"title": ("str", True, 200), "category": ("str", True, 60), "regulations": ("list", True, None), "control_objectives": ("list", True, None),
                  "reviewers": ("list", True, None), "approval_group": ("str", True, 80), "content": ("str", False, 4000)}, p)
    pol = await new(s, "policy", role, "Policy drafted", version="1.0", owner="Policy Owner (fictional)", state="Draft", reviewed=False, **d)
    for obj in d["control_objectives"]:
        c = await new(s, "control", role, f"Control created from {pol['number']}", name=obj, policy_id=pol["id"], policy=pol["number"], owner="Control Owner (fictional)", state="Not Assessed")
        await log(s, pol, "system", "related", f"Control {c['number']} linked")
    return {"record": await get(s, pol["id"])}


@action(LAB, "new_version")
async def a_version(s, p):
    role = role_of(p)
    need(role in ("policy_owner", "grc_admin"), "Only Policy Owner can version policies")
    old = await get(s, str(p.get("id")), "policy")
    need(old["state"] == "Published", "Only Published policies can be versioned")
    keep = {k: old[k] for k in ("title", "category", "regulations", "control_objectives", "reviewers", "approval_group", "content", "owner")}
    v = await new(s, "policy", role, f"New version drafted from {old['number']} v{old['version']}", version=f"{int(float(old['version'])) + 1}.0", state="Draft", reviewed=False, supersedes=old["number"], **keep)
    return {"record": v}


@action(LAB, "create_campaign")
async def a_campaign(s, p):
    role = role_of(p)
    need(role in ("grc_admin", "policy_owner"), "Only GRC Administrator or Policy Owner can create campaigns")
    d = validate({"policy_id": ("str", True, 40), "groups": ("list", True, None), "start_date": ("date", True, None), "due_date": ("date", True, None), "reminder_days": ("int", True, (1, 30))}, p)
    pol = await get(s, d["policy_id"], "policy")
    need(pol["state"] == "Published", "Campaigns require a Published policy")
    need(all(g in EMPLOYEES for g in d["groups"]), f"Groups must be from {list(EMPLOYEES)}")
    return {"record": await new(s, "campaign", role, f"Campaign drafted for {pol['number']}", policy=pol["number"], title=f"Acknowledge {pol['title']} v{pol['version']}", state="Draft", **d)}


async def st_camp_tasks(s, ctx):
    c = await get(s, ctx["campaign_id"])
    n = 0
    for g in c["groups"]:
        for e in EMPLOYEES[g]:
            a = await new(s, "ack", "system", f"Acknowledgment task generated by {c['number']}", campaign_id=c["id"], campaign=c["number"], policy=c["policy"], employee=e, group=g,
                          state="Pending", due_date=c["due_date"], reminders=0)
            await notify(s, e, f"Please read and acknowledge {c['policy']} by {c['due_date']}", a)
            n += 1
    return {"acknowledgment_tasks": n, "notifications": n}


engine.workflow("grc_campaign_launch", "IRM: Policy Acknowledgment Campaign Launch", LAB, "Campaign launched", "Generates acknowledgment tasks and in-app notifications for every employee in the target groups.",
                [("Generate acknowledgment tasks & notifications", st_camp_tasks, {})])


@action(LAB, "create_exception")
async def a_exc(s, p):
    role = role_of(p)
    need(role in ("control_owner", "policy_owner", "employee", "grc_admin"), "Role cannot request exceptions")
    d = validate({"policy_id": ("str", True, 40), "control_id": ("str", False, 40), "department": ("str", True, 80), "justification": ("str", True, 1000),
                  "compensating_controls": ("str", True, 1000), "duration_days": ("int", True, (1, 365))}, p)
    pol = await get(s, d["policy_id"], "policy")
    ctl = await get(s, d["control_id"]) if d.get("control_id") else None
    e = await new(s, "exception", role, "Exception requested", policy=pol["number"], control=ctl["number"] if ctl else None, owner=d["department"] + " lead (fictional)", state="Requested", **d)
    await notify(s, "Risk Analyst", f"Risk assessment needed for {e['number']}", e)
    return {"record": e}


@action(LAB, "create_risk")
async def a_risk(s, p):
    role = role_of(p)
    need(role in ("risk_analyst", "grc_admin"), "Only Risk Analyst can identify risks")
    d = validate({"statement": ("str", True, 500), "business_service": ("str", True, 100), "assets": ("list", True, None), "category": ("str", True, 60), "control_ids": ("list", False, None)}, p)
    r = await new(s, "risk", role, "Risk identified", owner="Risk Owner (fictional)", state="Identified", inherent=0, residual=0, **d)
    for cid in d.get("control_ids", []):
        c = await get(s, cid, "control")
        await log(s, c, "system", "related", f"Linked to risk {r['number']}", risk_id=r["id"], risk=r["number"])
    return {"record": r}


async def st_threshold(s, ctx):
    r = await get(s, ctx["risk_id"])
    await log(s, r, "system", "state", f"Assessed → Treatment (residual {r['residual']} ≥ threshold {THRESHOLD}); treatment plan required", state="Treatment", treatment_required=True)
    await notify(s, "Risk Owner", f"{r['number']} exceeds threshold – treatment plan required", r)
    return {"residual": r["residual"], "threshold": THRESHOLD, "routed_to": "Treatment"}


engine.workflow("grc_risk_threshold", "IRM: Risk Threshold Exceeded → Treatment Plan", LAB, "Residual ≥ threshold", "Routes high residual risks to treatment and notifies the risk owner.", [("Route to treatment", st_threshold, {})])


async def st_issue(s, ctx):
    a = await get(s, ctx["assessment_id"])
    c = await get(s, a["control_id"])
    iss = await new(s, "issue", "system", f"Auto-created from failed assessment {a['number']}", title=f"{c['name']} control failure", source="Control Assessment", control_id=c["id"], control=c["number"],
                    assessment_id=a["id"], assessment=a["number"], risk_id=c.get("risk_id"), risk=c.get("risk"), policy=c.get("policy"), severity=ctx["severity"], owner="Issue Owner (fictional)", state="Identified")
    await log(s, a, "system", "related", f"Issue {iss['number']} created", issue=iss["number"])
    await notify(s, "Issue Owner", f"New {ctx['severity']} issue {iss['number']}", iss)
    return {"issue": iss["number"]}


engine.workflow("grc_issue_from_failure", "IRM: Failed Control Assessment → Issue", LAB, "Assessment result = Fail", "Creates a linked issue, marks the control Ineffective and notifies the issue owner.", [("Create linked issue", st_issue, {})])


@action(LAB, "assess_control")
async def a_assess(s, p):
    role = role_of(p)
    need(role in ("auditor", "risk_analyst", "control_owner"), "Only Auditor, Risk Analyst or Control Owner can assess controls")
    d = validate({"control_id": ("str", True, 40), "result": ("choice", True, ["pass", "fail"]), "severity": ("choice", False, ["Low", "Medium", "High", "Critical"]), "notes": ("str", True, 1000)}, p)
    c = await get(s, d["control_id"], "control")
    a = await new(s, "assessment", role, f"Assessment of {c['number']}: {d['result']}", control_id=c["id"], control=c["number"], result=d["result"], notes=d["notes"], state="Completed")
    await log(s, c, role, "state", f"{c['state']} → {'Effective' if d['result'] == 'pass' else 'Ineffective'} ({a['number']})", state="Effective" if d["result"] == "pass" else "Ineffective")
    exe = await engine.start(s, "grc_issue_from_failure", {"assessment_id": a["id"], "severity": d.get("severity", "High"), "_lab": LAB}, "assessment_failed") if d["result"] == "fail" else None
    return {"record": a, "execution": exe}


async def st_monitor(s, ctx):
    out = {"acks_overdue": 0, "reminders": 0, "escalations": 0, "exceptions_expiring": 0, "exceptions_expired": 0, "tasks_overdue": 0}
    for a in await find(s, LAB, "ack"):
        if a["state"] in ("Pending", "Overdue") and a["due_date"] < today():
            rem = a.get("reminders", 0) + 1
            await log(s, a, "system", "reminder", f"Reminder #{rem} sent", state="Overdue", reminders=rem)
            await notify(s, a["employee"], f"Reminder #{rem}: {a['policy']} acknowledgment overdue", a)
            out["acks_overdue"] += 1
            out["reminders"] += 1
            if rem >= 2:
                await notify(s, f"{a['group']} manager", f"Escalation: {a['employee']} has not acknowledged {a['policy']}", a)
                out["escalations"] += 1
    for e in await find(s, LAB, "exception", state="Active"):
        if e.get("expires") and e["expires"] < today():
            await log(s, e, "system", "state", "Active → Expired (expiration monitoring)", state="Expired")
            await notify(s, e["owner"], f"{e['number']} expired – close or renew", e)
            out["exceptions_expired"] += 1
        elif e.get("expires") and e["expires"] <= in_days(14) and not e.get("expiry_warned"):
            await log(s, e, "system", "notification", "Expiry warning sent (≤14 days)", expiry_warned=True)
            await notify(s, e["owner"], f"{e['number']} expires {e['expires']}", e)
            out["exceptions_expiring"] += 1
    for t in await find(s, LAB, "task"):
        if t["state"] not in ("Completed", "Closed") and t.get("sla_due") and t["sla_due"] < today() and not t.get("sla_breached"):
            await log(s, t, "system", "escalation", "SLA breached – escalated to GRC management", sla_breached=True)
            await notify(s, "GRC Manager", f"SLA breach on {t['number']}", t)
            out["tasks_overdue"] += 1
    return out


engine.workflow("grc_monitoring", "IRM: Scheduled Monitoring (reminders, expirations, SLA)", LAB, "Scheduler", "Acknowledgment reminders/escalations, exception expiry monitoring and remediation SLA escalation.", [("Run monitoring rules", st_monitor, {})])


@action(LAB, "run_monitoring")
async def a_monitor(s, p):
    return {"execution": await engine.start(s, "grc_monitoring", {"_lab": LAB}, "scheduler")}


@kpi(LAB)
async def k_grc(s):
    pols, acks, exc, iss, tasks, risks, camps, rcs = [await find(s, LAB, t) for t in ("policy", "ack", "exception", "issue", "task", "risk", "campaign", "reg_change")]
    cs = []
    for c in camps:
        a = [x for x in acks if x["campaign_id"] == c["id"]]
        done = sum(x["state"] == "Acknowledged" for x in a)
        cs.append({"campaign": c["number"], "policy": c["policy"], "state": c["state"], "total": len(a), "acknowledged": done, "pending": sum(x["state"] == "Pending" for x in a),
                   "overdue": sum(x["state"] in ("Overdue", "Not Completed") for x in a), "completion_pct": round(100 * done / len(a), 1) if a else 0})
    active = [x for x in acks if any(c["id"] == x["campaign_id"] and c["state"] == "Active" for c in camps)]
    return {"kpis": [{"label": "Published policies", "value": sum(p["state"] == "Published" for p in pols)},
                     {"label": "Active campaign completion", "value": f"{round(100 * sum(x['state'] == 'Acknowledged' for x in active) / len(active), 1)}%" if active else "n/a"},
                     {"label": "Active exceptions", "value": sum(e["state"] == "Active" for e in exc)}, {"label": "Open issues", "value": sum(i["state"] != "Closed" for i in iss)},
                     {"label": "Tasks past SLA", "value": sum(t["state"] not in ("Completed", "Closed") and t.get("sla_due", "9") < today() for t in tasks)},
                     {"label": "High/Critical risks", "value": sum(r.get("rating") in ("High", "Critical") and r["state"] not in ("Closed",) for r in risks)},
                     {"label": "Open regulatory changes", "value": sum(c["state"] != "Closed" for c in rcs)}, {"label": "Regulatory changes closed", "value": sum(c["state"] == "Closed" for c in rcs)}],
            "charts": [{"title": "Policies by state", "data": by_status(pols, "state")}, {"title": "Exceptions by state", "data": by_status(exc, "state")},
                       {"title": "Issues by state", "data": by_status(iss, "state")}, {"title": "Remediation tasks by state", "data": by_status(tasks, "state")},
                       {"title": "Regulatory changes by state", "data": by_status(rcs, "state")}],
            "campaigns": cs}
