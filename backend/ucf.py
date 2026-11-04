from datetime import datetime, timezone, timedelta
from core import db, P, action, ins, upd, get, find, validate, in_days, today, now, audit, by_status
import engine
import agents
from grc import LAB, T, PREFIX, new, log, notify, need, role_of, H

PREFIX.update(requirement="REQ", obligation="OBL", reg_change="RCM", impact="IMA", sync_run="SYN", feed_notice="UCN", ucf_config="CFG", risk_assessment="RAS")
SHARED = "ucf-shared-monitor"
SIM = "SIMULATED – fictional UCF-style content for demonstration; not actual legal or regulatory text"
OWNER = "Compliance Owner (fictional)"
AGENT = "Regulatory Change Analysis Agent"
MODE = "Simulated UCF feed – no live UCF connection or licensed credentials configured"
FRAMEWORKS = ["HIPAA", "HITRUST", "GLBA", "CCPA", "GDPR", "NYDFS", "PCI DSS", "SOC 2", "ISO 27001", "NIST CSF", "NIST SP 800-53", "FedRAMP", "SOX ITGC", "ISO/IEC 42001"]

# (ucf_ref, framework, authority, title, version, control_refs, policy_titles, business_units)
REQS = [
    ("UCF-SIM-0101", "NYDFS", "NY financial regulator (simulated)", "Multi-factor authentication for remote and privileged access", "2.0", ["IA-2"], ["Information Security Policy"], ["IT", "Operations"]),
    ("UCF-SIM-0102", "NIST SP 800-53", "NIST (simulated)", "Account management and periodic access review", "5.0", ["AC-2"], ["Information Security Policy"], ["IT"]),
    ("UCF-SIM-0103", "SOX ITGC", "ITGC framework (simulated)", "Change management approval and segregation of duties", "1.0", ["CM-3"], ["Information Security Policy"], ["IT", "Finance"]),
    ("UCF-SIM-0104", "HIPAA", "Healthcare regulator (simulated)", "Contingency planning: data backup and restore testing", "1.0", ["CP-9"], ["Information Security Policy"], ["IT", "Operations"]),
    ("UCF-SIM-0105", "PCI DSS", "Payment card standard (simulated)", "Audit log review and retention", "4.0", ["AC-2"], ["Information Security Policy"], ["IT"]),
    ("UCF-SIM-0106", "GLBA", "Safeguards requirement (simulated)", "Information security program oversight and reporting", "1.0", ["AC-2", "IA-2"], ["Information Security Policy"], ["Finance", "IT"]),
    ("UCF-SIM-0107", "ISO 27001", "ISO (simulated)", "Acceptable use of information assets", "2.0", [], ["Acceptable Use Policy"], ["HR"]),
    ("UCF-SIM-0108", "SOC 2", "Trust services criteria (simulated)", "Logical access provisioning and deprovisioning", "1.0", ["AC-2"], ["Information Security Policy"], ["IT", "HR"]),
    ("UCF-SIM-0109", "NIST CSF", "NIST (simulated)", "Recovery planning and testing", "2.0", ["CP-9"], ["Information Security Policy"], ["Operations"]),
    ("UCF-SIM-0110", "HITRUST", "HITRUST (simulated)", "Workforce security awareness acknowledgment", "1.0", [], ["Acceptable Use Policy"], ["HR"]),
    ("UCF-SIM-0111", "GDPR", "EU data protection (simulated)", "Records of processing activities", "1.0", [], [], ["Operations"]),
    ("UCF-SIM-0112", "CCPA", "California privacy (simulated)", "Consumer data request handling", "1.0", [], [], ["Operations"]),
    ("UCF-SIM-0113", "FedRAMP", "Federal cloud program (simulated)", "Legacy remote access configuration baseline", "1.0", [], ["Legacy Remote Access Standard"], ["IT"]),
    ("UCF-SIM-0114", "ISO 27001", "ISO (simulated)", "Cryptographic key management", "1.0", ["IA-2"], [], ["IT"]),
]
REQ_BY_REF = {r[0]: r for r in REQS}
POOL = [
    {"change_type": "Modified", "ucf_ref": "UCF-SIM-0101", "risk_rating": "High", "description": "Simulated amendment: MFA scope expanded from privileged and remote access to all third-party and contractor access; phishing-resistant factors preferred."},
    {"change_type": "New", "ucf_ref": "UCF-SIM-0201", "framework": "ISO/IEC 42001", "authority": "ISO (simulated)", "title": "AI system impact assessment before deployment", "control_refs": [], "policy_titles": ["Information Security Policy"],
     "business_units": ["IT", "Operations"], "risk_rating": "Medium", "description": "Simulated new requirement: document an impact assessment for each AI system prior to production use."},
    {"change_type": "Modified", "ucf_ref": "UCF-SIM-0104", "risk_rating": "High", "description": "Simulated amendment: restore testing frequency changed from annual to semi-annual for critical systems."},
    {"change_type": "Retired", "ucf_ref": "UCF-SIM-0113", "risk_rating": "Low", "description": "Simulated retirement: legacy remote access baseline withdrawn and superseded by zero-trust guidance."},
    {"change_type": "Modified", "ucf_ref": "UCF-SIM-0105", "risk_rating": "Low", "description": "Simulated clarification: log review wording clarified; retention period unchanged."},
]
NOTICE_KEYS = ["notice_id", "ucf_ref", "framework", "authority", "title", "change_type", "new_version", "description", "risk_rating", "source_publication_date", "effective_date",
               "control_refs", "policy_titles", "business_units", "record_id"]


def notice(item, tag, pub_days=-2):
    base = REQ_BY_REF.get(item["ucf_ref"])
    d = {"framework": base[1], "authority": base[2], "title": base[3], "control_refs": base[5], "policy_titles": base[6], "business_units": base[7]} if base else {}
    return {**d, **item, "notice_id": f"UCN-{tag}", "new_version": f"{in_days(pub_days)}.{tag}", "source_publication_date": in_days(pub_days), "effective_date": in_days(pub_days + 90),
            "simulated": True, "label": SIM}


async def mk_obligation(s, req, by="system"):
    ctls = [c for c in await find(s, LAB, "control") if c.get("ref") in req["control_refs"]]
    pids = {c.get("policy_id") for c in ctls}
    pols = [p for p in await find(s, LAB, "policy") if p["state"] == "Published" and (p["title"] in req["policy_titles"] or p["id"] in pids)]
    o = await new(s, "obligation", by, f"Obligation mapped from {req['number']}", title=f"{req['framework']}: {req['title']}", requirement_id=req["id"], requirement=req["number"], framework=req["framework"],
                  control_ids=[c["id"] for c in ctls], controls=[c["number"] for c in ctls], policy_ids=[p["id"] for p in pols], policies=[p["number"] for p in pols], owner=OWNER, state="Active", label=SIM)
    await upd(s, req["id"], obligation_id=o["id"], obligation=o["number"])
    return o


async def create_change(s, n, trigger):
    found = await find(s, LAB, "requirement", ucf_ref=n["ucf_ref"])
    req = found[0] if found else None
    if not req:
        req = await new(s, "requirement", "integration", f"Requirement added from UCF notice {n['notice_id']}", ucf_ref=n["ucf_ref"], framework=n["framework"], authority=n["authority"], title=n["title"],
                        version="—", control_refs=n.get("control_refs", []), policy_titles=n.get("policy_titles", []), business_units=n.get("business_units", []), state="Pending Implementation", label=SIM)
        await mk_obligation(s, req, "integration")
        req = await get(s, req["id"])
    obl = await get(s, req["obligation_id"])
    ch = await new(s, "reg_change", "integration", f"Created from UCF change notification {n['notice_id']} ({trigger})", title=f"{n['change_type']}: {req['title']}", framework=req["framework"],
                   authority=req["authority"], ucf_ref=req["ucf_ref"], requirement_id=req["id"], requirement=req["number"], requirement_title=req["title"],
                   previous_version=None if n["change_type"] == "New" else req["version"], updated_version="Retired" if n["change_type"] == "Retired" else n["new_version"], change_type=n["change_type"],
                   source_publication_date=n["source_publication_date"], date_received=today(), effective_date=n["effective_date"], description=n["description"], business_units=req["business_units"],
                   obligation_id=obl["id"], obligation=obl["number"], control_ids=obl["control_ids"], controls=obl["controls"], policy_ids=obl["policy_ids"], policies=obl["policies"], compliance_owner=OWNER,
                   risk_rating=n["risk_rating"], impact_assessment=None, remediation_status="Not started", approval_history=[], closure_evidence=None, dedupe_key=f"{n['ucf_ref']}@{n['new_version']}",
                   notice_id=n["notice_id"], trigger=trigger, simulated=True, label=SIM, state="Impact Assessment")
    imp = await new(s, "impact", "system", f"Impact assessment task generated for {ch['number']}", reg_change_id=ch["id"], reg_change=ch["number"], title=f"Assess impact of {ch['number']}",
                    assigned_to=OWNER, due_date=in_days(10), state="Open")
    await log(s, req, "integration", "related", f"Change {ch['number']} detected ({n['change_type']}) via {trigger}")
    await notify(s, "Compliance Owner", f"New {n['risk_rating']} regulatory change {ch['number']}: {req['title']} – impact assessment {imp['number']} due {imp['due_date']}", ch)
    return await upd(s, ch["id"], impact_id=imp["id"], impact=imp["number"])


# ---------- synchronization workflow ----------
async def st_connect(s, ctx):
    if ctx.get("simulate_failure"):
        raise RuntimeError("Simulated UCF endpoint timeout (HTTP 504)")
    cfg = (await find(s, LAB, "ucf_config"))[0]
    return {"source": cfg["source"], "connection": cfg["connection_status"], "frameworks_subscribed": len(cfg["frameworks"])}


async def st_retrieve(s, ctx):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    g = await db.ucf_feed.find({"published_at": {"$gte": cutoff}}, P).to_list(100)
    loc = await find(s, LAB, "feed_notice", state="Pending")
    ctx["notices"] = [{k: n.get(k) for k in NOTICE_KEYS} for n in g] + [{**{k: n.get(k) for k in NOTICE_KEYS}, "record_id": n["id"]} for n in loc]
    return {"shared_feed_notices": len(g), "session_notices": len(loc)}


async def st_detect(s, ctx):
    have = {c.get("dedupe_key") for c in await find(s, LAB, "reg_change")}
    fresh, dup = [], 0
    for n in ctx["notices"]:
        k = f"{n['ucf_ref']}@{n['new_version']}"
        if k in have:
            dup += 1
            if n.get("record_id"):
                await log(s, await get(s, n["record_id"]), "integration", "state", "Pending → Duplicate (already processed)", state="Duplicate")
            continue
        have.add(k)
        fresh.append(n)
    ctx["new"], ctx["dups"] = fresh, dup
    return {"changes_detected": len(fresh), "duplicates_skipped": dup, "by_type": by_status(fresh, "change_type")}


async def st_create(s, ctx):
    made = []
    for n in ctx["new"]:
        ch = await create_change(s, n, ctx["trigger"])
        made.append(ch["number"])
        if n.get("record_id"):
            await log(s, await get(s, n["record_id"]), "integration", "state", f"Pending → Processed ({ch['number']})", state="Processed", reg_change=ch["number"], reg_change_id=ch["id"])
    ctx["created"] = made
    return {"regulatory_changes_created": made, "impact_assessments_created": len(made), "owner_notifications": len(made)}


async def st_record(s, ctx):
    made = ctx["created"]
    msg = f"{len(made)} regulatory change(s) detected: {', '.join(made)}" if made else "No regulatory changes detected"
    run = await get(s, ctx["sync_run_id"])
    await log(s, run, "integration", "state", f"{run['state']} → Completed: {msg}", state="Completed", result=msg, changes_detected=len(made), duplicates_skipped=ctx["dups"],
              notices_received=len(ctx["notices"]), changes=made, ended_at=now(), error=None)
    cfg = (await find(s, LAB, "ucf_config"))[0]
    await upd(s, cfg["id"], last_sync=now(), last_status="Completed", last_result=msg)
    return {"result": msg}


engine.workflow("ucf_sync", "IRM + UCF: Regulatory Content Synchronization", LAB, "Scheduled daily check / on-demand / simulated update",
                "Connects to the simulated UCF feed, retrieves change notifications, de-duplicates, creates regulatory change records with impact assessments and owner notifications.",
                [("Connect to UCF content source (simulated)", st_connect, {}), ("Retrieve change notifications", st_retrieve, {}), ("Detect new / modified / retired requirements & de-duplicate", st_detect, {}),
                 ("Create change records, map obligations, notify owners, create impact assessments", st_create, {}), ("Record synchronization result", st_record, {})])


async def run_sync(s, trigger, fail=False):
    run = await new(s, "sync_run", "integration", f"Synchronization started ({trigger})", trigger=trigger, source="Simulated UCF feed", state="Running", started_at=now(),
                    changes_detected=0, duplicates_skipped=0, notices_received=0, label=SIM)
    exe = await engine.start(s, "ucf_sync", {"sync_run_id": run["id"], "trigger": trigger, "simulate_failure": fail, "_lab": LAB}, "ucf_feed")
    await upd(s, run["id"], execution_id=exe["id"])
    if exe["status"] == "failed":
        err = next(x["error"] for x in exe["steps"] if x["status"] == "failed")
        await db.executions.update_one({"id": exe["id"]}, {"$set": {"ctx.simulate_failure": False}})
        run = await log(s, run, "integration", "state", f"Running → Failed: {err} (no records changed; retry available)", state="Failed", error=err, result="Synchronization failed", ended_at=now())
        cfg = (await find(s, LAB, "ucf_config"))[0]
        await upd(s, cfg["id"], last_sync=now(), last_status="Failed", last_result=err)
        await notify(s, "GRC Administrator", f"UCF synchronization {run['number']} failed – review integration status and retry", run)
    await audit(s, "ucf.sync", LAB, {"sync_run": run["number"], "trigger": trigger, "status": exe["status"]})
    return {"sync_run": await get(s, run["id"]), "execution": exe}


# ---------- regulatory change lifecycle ----------
async def e_assess(s, r, d):
    need(d["controls_sufficient"] in ("yes", "no") and d["policy_revision"] in ("yes", "no"), "controls_sufficient and policy_revision must be yes or no")
    return {"controls_sufficient": d["controls_sufficient"], "policy_revision": d["policy_revision"], "impact_assessment": d["assessment_notes"], "assessed_at": now(), "assessed_by": OWNER,
            "risk_rating": d.get("risk_rating") or r["risk_rating"], "remediation_status": "Not required" if d["controls_sufficient"] == "yes" and d["policy_revision"] == "no" else "In progress"}


async def a_assess(s, r, d):
    r = await get(s, r["id"])
    imp = await get(s, r["impact_id"])
    gap = r["controls_sufficient"] == "no"
    await log(s, imp, "compliance_owner", "state", f"Open → Completed ({'gap identified' if gap else 'existing controls sufficient'})", state="Completed", result="Gap identified" if gap else "No gap",
              notes=r["impact_assessment"], completed_at=now())
    out = {}
    if gap:
        ctls = [await get(s, c) for c in r["control_ids"]]
        for c in ctls:
            await log(s, c, "system", "state", f"{c['state']} → Needs Reassessment ({r['number']})", state="Needs Reassessment")
        ctl = ctls[0] if ctls else None
        sev = r["risk_rating"] if r["risk_rating"] in ("High", "Critical") else "Medium"
        iss = await new(s, "issue", "system", f"Auto-created from regulatory change {r['number']} (compliance gap)", title=f"Compliance gap: {r['requirement_title']}", source="Regulatory Change",
                        reg_change_id=r["id"], reg_change=r["number"], control_id=ctl["id"] if ctl else None, control=ctl["number"] if ctl else None, policy=", ".join(r["policies"]) or None,
                        severity=sev, root_cause=r["impact_assessment"], owner="Issue Owner (fictional)", remediation_owner="Remediation Owner (fictional)", due_date=in_days(30),
                        action_plan=f"Update controls to meet {r['ucf_ref']} {r['updated_version']}", state="Assigned")
        t = await new(s, "task", "system", f"Remediation task created from {iss['number']} ({r['number']})", issue_id=iss["id"], issue=iss["number"], reg_change_id=r["id"], title=f"Remediate gap: {r['requirement_title']}",
                      assignment_group="GRC Remediation", assigned_to="Remediation Owner (fictional)", priority="2 - High" if sev != "Medium" else "3 - Moderate", sla_due=in_days(30), due_date=in_days(30),
                      action_plan=iss["action_plan"], evidence=[], state="Assigned")
        await notify(s, "Issue Owner", f"Compliance gap issue {iss['number']} created from {r['number']}", iss)
        await notify(s, "Remediation Owner", f"Remediation task {t['number']} assigned ({r['number']})", t)
        out["issue_ids"] = [iss["id"]]
        out["issues"] = [iss["number"]]
    if r["policy_revision"] == "yes" and r["policy_ids"]:
        old = await get(s, r["policy_ids"][0])
        keep = {k: old.get(k) for k in ("title", "category", "regulations", "control_objectives", "reviewers", "approval_group", "content", "owner")}
        v = await new(s, "policy", "system", f"Revision drafted for {r['number']} from {old['number']} v{old['version']}", version=f"{int(float(old['version'])) + 1}.0", state="Draft", reviewed=False,
                      supersedes=old["number"], reg_change_id=r["id"], reg_change=r["number"], revision_reason=f"{r['framework']} change {r['ucf_ref']}: {r['description']}", **keep)
        await notify(s, "Policy Owner", f"Policy revision {v['number']} required by {r['number']}", v)
        out["revision_policy_ids"] = [v["id"]]
        out["revision_policies"] = [v["number"]]
    if out:
        await upd(s, r["id"], **out)


async def g_rc_submit(s, r, d):
    iss = [await get(s, i) for i in r.get("issue_ids", [])]
    pols = [await get(s, p) for p in r.get("revision_policy_ids", [])]
    ctls = [await get(s, c) for c in r.get("control_ids", [])]
    gaps = [f"issue {i['number']} is {i['state']}" for i in iss if i["state"] != "Closed"] + [f"policy {p['number']} is {p['state']}" for p in pols if p["state"] != "Published"] + \
           [f"control {c['number']} is {c['state']}" for c in ctls if c["state"] in ("Needs Reassessment", "Ineffective")]
    need(not gaps, "Outstanding before validation: " + "; ".join(gaps))


async def a_rc_submit(s, r, d):
    await notify(s, "Auditor", f"{r['number']} ready for compliance validation", r)


async def e_rc_validate(s, r, d):
    ok = d["decision"] == "pass"
    return {"closure_evidence": d["closure_evidence"], "closed_at": now() if ok else None, "remediation_status": r["remediation_status"] if not ok else ("Completed" if r.get("issue_ids") or r.get("revision_policy_ids") else "Not required"),
            "approval_history": r.get("approval_history", []) + [{"by": "Auditor (fictional)", "decision": "Validated" if ok else "Returned for remediation", "at": now(), "comment": d["closure_evidence"]}]}


async def a_rc_validate(s, r, d):
    r = await get(s, r["id"])
    if r["state"] != "Closed":
        return
    req = await get(s, r["requirement_id"])
    if r["change_type"] == "Retired":
        await log(s, req, "system", "state", f"{req['state']} → Retired ({r['number']} closed)", state="Retired", retired_at=today())
    else:
        await log(s, req, "system", "field", f"Version {req['version']} → {r['updated_version']} ({r['number']} closed)", version=r["updated_version"], state="Active")
    await ins(s, LAB, "dashboard_event", summary=f"{r['number']} closed; compliance dashboards refreshed")


async def g_ai(s, r, d):
    need(r.get("ai_analysis"), "Run the Regulatory Change Analysis Agent first")
    need(d["ai_decision"] in ("accept", "reject"), "ai_decision must be accept or reject")


async def e_ai(s, r, d):
    a = r["ai_analysis"]
    return {"ai_analysis": {**a, "status": "Accepted by human reviewer (advisory only – mappings unchanged)" if d["ai_decision"] == "accept" else "Rejected by human reviewer", "reviewed_at": now(), "review_comment": d["comment"]}}


T["reg_change"] = {
    "assess_impact": (["Impact Assessment"], lambda r: "Validation" if r.get("controls_sufficient") == "yes" and r.get("policy_revision") == "no" else "Remediation", ["compliance_owner", "grc_admin"],
                      ["controls_sufficient", "policy_revision", "assessment_notes"], None, e_assess, a_assess),
    "submit_for_validation": (["Remediation"], "Validation", ["compliance_owner"], [], g_rc_submit, None, a_rc_submit),
    "validate": (["Validation"], lambda r: "Closed" if r.get("_decision") == "pass" else "Remediation", ["auditor"], ["decision", "closure_evidence"], None, e_rc_validate, a_rc_validate),
    "review_ai": (["Impact Assessment", "Remediation", "Validation"], lambda r: r["state"], ["compliance_owner"], ["ai_decision", "comment"], g_ai, e_ai, None),
}


# ---------- actions ----------
@action(LAB, "ucf_simulate_update")
async def a_simulate(s, p):
    role = role_of(p)
    need(role != "executive", "Executive Viewer is read-only")
    d = validate({"change_type": ("choice", False, ["New", "Modified", "Retired"])}, p)
    k = len(await find(s, LAB, "feed_notice"))
    opts = [x for x in POOL if x["change_type"] == d["change_type"]] if d.get("change_type") else POOL
    item = opts[k % len(opts)]
    n = notice(item, f"s{k + 1}", 0)
    rec = await new(s, "feed_notice", "integration", f"Simulated UCF change notification received ({n['change_type']} {n['ucf_ref']})", state="Pending", **{x: n.get(x) for x in NOTICE_KEYS if x != "record_id"},
                    label=SIM, simulated=True)
    res = await run_sync(s, "Recruiter-triggered simulated update")
    rc = await find(s, LAB, "reg_change", notice_id=n["notice_id"])
    return {**res, "notice": rec, "change": rc[-1] if rc else None}


@action(LAB, "ucf_sync")
async def a_sync(s, p):
    role = role_of(p)
    need(role in ("grc_admin", "compliance_owner"), "Only GRC Administrator or Compliance Owner can run synchronization")
    return await run_sync(s, "On-demand synchronization", bool(p.get("simulate_failure")))


@action(LAB, "ucf_config_update")
async def a_cfg(s, p):
    role = role_of(p)
    need(role == "grc_admin", "Only GRC Administrator can change integration configuration")
    d = validate({"frameworks": ("list", True, None), "auto_create_changes": ("bool", False, None), "notify_owners": ("bool", False, None), "impact_due_days": ("int", True, (1, 60))}, p)
    bad = [f for f in d["frameworks"] if f not in FRAMEWORKS]
    need(not bad, f"Unknown frameworks: {bad}")
    cfg = (await find(s, LAB, "ucf_config"))[0]
    return {"record": await log(s, cfg, role, "config", f"Integration configuration updated ({len(d['frameworks'])} frameworks)", **d)}


@action(LAB, "ucf_map")
async def a_map(s, p):
    role = role_of(p)
    need(role in ("compliance_owner", "grc_admin"), "Only Compliance Owner or GRC Administrator can approve requirement mappings")
    d = validate({"id": ("str", True, 40), "control_refs": ("list", False, None), "policy_titles": ("list", False, None)}, p)
    req = await get(s, d["id"], "requirement")
    req = await log(s, req, role, "mapping", f"Mapping approved by {role}: controls {d.get('control_refs', [])}, policies {d.get('policy_titles', [])}",
                    control_refs=d.get("control_refs", []), policy_titles=d.get("policy_titles", []))
    old = await get(s, req["obligation_id"])
    o = await mk_obligation(s, req, role)
    await log(s, old, role, "state", f"Active → Superseded by {o['number']}", state="Superseded")
    return {"record": await get(s, req["id"]), "obligation": o}


def sim_analysis(ch):
    pr = {"Critical": "P1 – assess within 2 business days", "High": "P1 – assess within 5 business days", "Medium": "P2 – assess within 10 business days"}.get(ch["risk_rating"], "P3 – assess within 30 days")
    acts = [f"Confirm whether {', '.join(ch['controls']) or 'mapped controls'} meet the updated requirement", f"Review {', '.join(ch['policies']) or 'related policies'} for wording changes"]
    if ch["change_type"] == "Retired":
        acts = ["Confirm no remaining obligations depend on the retired requirement", "Archive mapping after validation"]
    return {"priority": pr, "affected_controls": ch["controls"], "affected_policies": ch["policies"], "proposed_actions": acts}


@action(LAB, "ucf_ai_analyze")
async def a_ai(s, p):
    role = role_of(p)
    need(role in ("compliance_owner", "grc_admin"), "Only Compliance Owner or GRC Administrator can request AI analysis")
    ch = await get(s, str(p.get("id", "")), "reg_change")
    found = await find(s, "agents", "agent", name=AGENT)
    agent = found[0] if found else await ins(s, "agents", "agent", **agents.agent_row(AGENT))
    task = (f"Summarize simulated regulatory change {ch['number']} ({ch['change_type']}, {ch['framework']}): {ch['description']} Identify potentially affected policies and controls, "
            "recommend an impact assessment priority, draft proposed remediation actions and a short summary. Advisory only; a human reviewer decides.")
    run = await agents.execute_agent(s, agent, task, {"requirement": ch["requirement_title"], "controls": ch["controls"], "policies": ch["policies"], "risk_rating": ch["risk_rating"]},
                                     tools_needed=["map_obligations", "read_controls"], workflow="ucf_change_analysis")
    analysis = {"run_id": run["id"], "mode": run["mode"], "output": run["output"], "structured": sim_analysis(ch), "status": "Pending human review", "generated_at": now(),
                "disclaimer": "AI-generated recommendation – advisory only, not a legal interpretation. Approved control mappings are never changed without human approval."}
    return {"record": await log(s, ch, "ai_agent", "ai_analysis", f"{AGENT} analysis generated ({run['mode']}) – pending human review", ai_analysis=analysis), "run": run}


async def ucf_metrics(s):
    chs, reqs, imps, runs, iss, tasks = [await find(s, LAB, t) for t in ("reg_change", "requirement", "impact", "sync_run", "issue", "task")]
    ids = {c["id"] for c in chs}
    iss = [i for i in iss if i.get("reg_change_id") in ids]
    iids = {i["id"] for i in iss}
    rt = [t for t in tasks if t.get("reg_change_id") in ids or t.get("issue_id") in iids]
    op = [c for c in chs if c["state"] != "Closed"]
    cnt = lambda f: sum(1 for c in chs if f(c))  # noqa: E731
    kpis = [("Regulatory requirements monitored", sum(r["state"] != "Retired" for r in reqs)), ("New regulatory changes", cnt(lambda c: c["change_type"] == "New")),
            ("Modified requirements", cnt(lambda c: c["change_type"] == "Modified")), ("Retired requirements", cnt(lambda c: c["change_type"] == "Retired")),
            ("Awaiting impact assessment", cnt(lambda c: c["state"] == "Impact Assessment")), ("High-risk regulatory changes", sum(c["risk_rating"] in ("High", "Critical") for c in op)),
            ("Affected policies", len({x for c in op for x in c.get("policy_ids", []) + c.get("revision_policy_ids", [])})), ("Affected controls", len({x for c in op for x in c.get("control_ids", [])})),
            ("Open remediation tasks", sum(t["state"] != "Closed" for t in rt)),
            ("Overdue compliance actions", sum(i["state"] == "Open" and i["due_date"] < today() for i in imps) + sum(t["state"] not in ("Completed", "Closed") and t.get("sla_due", "9") < today() for t in rt)),
            ("Completed impact assessments", sum(i["state"] == "Completed" for i in imps)), ("Regulatory changes closed", cnt(lambda c: c["state"] == "Closed"))]
    last = runs[-1] if runs else None
    return {"kpis": [{"label": k, "value": v} for k, v in kpis], "charts": [{"title": "Regulatory changes by state", "data": by_status(chs, "state")}, {"title": "Changes by framework", "data": by_status(chs, "framework")},
            {"title": "Changes by type", "data": by_status(chs, "change_type")}, {"title": "Synchronization results", "data": by_status(runs, "state")}],
            "integration": {"mode": MODE, "last_sync": last and (last.get("ended_at") or last["created_at"]), "last_status": last and last["state"], "last_result": last and last.get("result"),
                            "total_syncs": len(runs), "failed_syncs": sum(r["state"] == "Failed" for r in runs), "duplicates_skipped": sum(r.get("duplicates_skipped", 0) for r in runs)}}


@action(LAB, "ucf_dashboard")
async def a_dash(s, p):
    return await ucf_metrics(s)


async def change_report(s, rid):
    from reports import build_pdf
    ch = await get(s, rid, "reg_change")
    req = await get(s, ch["requirement_id"])
    obl = await get(s, ch["obligation_id"])
    pols = [await get(s, p) for p in ch.get("policy_ids", []) + ch.get("revision_policy_ids", [])]
    ctls = [await get(s, c) for c in ch.get("control_ids", [])]
    iss = await find(s, LAB, "issue", reg_change_id=rid)
    tasks = [t for i in iss for t in await find(s, LAB, "task", issue_id=i["id"])]
    camps = [c for p in pols for c in await find(s, LAB, "campaign", policy_id=p["id"])]
    imp = await get(s, ch["impact_id"])
    exes = await db.executions.find({"session": s, "workflow": "ucf_sync", "ctx.created": ch["number"]}, {"_id": 0, "ctx": 0}).to_list(5)
    fields = ["number", "framework", "authority", "ucf_ref", "requirement_title", "previous_version", "updated_version", "change_type", "source_publication_date", "date_received", "effective_date",
              "description", "business_units", "obligation", "controls", "policies", "compliance_owner", "risk_rating", "impact_assessment", "remediation_status", "state", "closure_evidence"]
    ai = ch.get("ai_analysis")
    secs = [("Notice", "text", SIM + ". " + MODE + "."), ("Regulatory change record", "table", (["Field", "Value"], [[f.replace("_", " "), ch.get(f)] for f in fields])),
            ("Requirement & obligation", "table", (["Record", "Title", "Version / State"], [[req["number"], req["title"], f"{req['version']} / {req['state']}"], [obl["number"], obl["title"], obl["state"]]])),
            ("Impact assessment", "table", (["Task", "State", "Result", "Notes"], [[imp["number"], imp["state"], imp.get("result"), imp.get("notes")]])),
            ("Affected & revised policies", "table", (["Policy", "Title", "Version", "State"], [[p["number"], p["title"], p["version"], p["state"]] for p in pols])),
            ("Affected controls", "table", (["Control", "Ref", "Name", "State"], [[c["number"], c.get("ref"), c["name"], c["state"]] for c in ctls])),
            ("Issues", "table", (["Issue", "Title", "Severity", "State"], [[i["number"], i["title"], i["severity"], i["state"]] for i in iss])),
            ("Remediation tasks", "table", (["Task", "Assigned to", "State", "Validation"], [[t["number"], t.get("assigned_to"), t["state"], t.get("validation_result")] for t in tasks])),
            ("Acknowledgment campaigns", "table", (["Campaign", "Policy", "State", "Due"], [[c["number"], c["policy"], c["state"], c["due_date"]] for c in camps])),
            ("Approval history", "table", (["By", "Decision", "At", "Comment"], [[a["by"], a["decision"], a["at"], a.get("comment")] for a in ch.get("approval_history", [])])),
            ("AI analysis (advisory)", "text", f"{ai['status']} · mode: {ai['mode']}\n{ai['output']}\n{ai['disclaimer']}" if ai else "Not requested"),
            ("Activity history", "table", (["At", "By", "Kind", "Text"], [[h["at"][:19], h["by"], h["kind"], h["text"]] for h in ch.get("history", [])])),
            ("Synchronization executions", "table", (["Execution", "Status", "Started"], [[e["id"], e["status"], e["created_at"][:19]] for e in exes]))]
    return build_pdf(f"Regulatory Change Impact Report – {ch['number']}", "ServiceNow IRM + UCF demonstration · simulated feed", secs)


# ---------- scheduled daily check (shared monitor; visitor sessions are never modified) ----------
async def scheduled_check(run_id):
    if await db.ucf_cron_runs.find_one({"run_id": run_id}):
        return
    await db.ucf_cron_runs.insert_one({"run_id": run_id, "at": now(), "status": "running"})
    try:
        from seed_labs import ensure_seeded
        pub = None
        if datetime.now(timezone.utc).date().toordinal() % 3 == 0:
            seq = await db.ucf_feed.count_documents({})
            pub = {**notice(POOL[seq % len(POOL)], f"g{seq + 1}", 0), "published_at": now(), "publisher": "Simulated UCF publisher (scheduled)"}
            await db.ucf_feed.insert_one(dict(pub))
        await ensure_seeded(SHARED)
        res = await run_sync(SHARED, "Scheduled daily check")
        run = res["sync_run"]
        await db.ucf_cron_runs.update_one({"run_id": run_id}, {"$set": {"status": run["state"], "result": run.get("result") or run.get("error"), "published": pub and pub["notice_id"], "ended_at": now()}})
    except Exception as e:  # noqa: BLE001 - record scheduler failures for the admin view
        await db.ucf_cron_runs.update_one({"run_id": run_id}, {"$set": {"status": "Failed", "result": f"{type(e).__name__}: {e}", "ended_at": now()}})


# ---------- seed ----------
CONFIG = {"source": "Simulated UCF content feed", "connection_status": "Not connected to live UCF – simulated feed in use", "mode": MODE, "schedule": "Daily check at 06:00 UTC + on-demand",
          "frameworks": FRAMEWORKS, "auto_create_changes": True, "notify_owners": True, "impact_due_days": 10, "dedupe_key": "UCF reference + version", "notification_channel": "In-app (simulated – no email sent)",
          "owner_routing": "Compliance Owner (fictional) per obligation", "failure_handling": "3 attempts per step, then Failed sync record + GRC Administrator notification; retry from Workflow Executions",
          "credentials": "None stored – no licensed UCF access configured", "label": SIM}
SEED_ITEMS = [  # (notice item, final state, extra)
    ({"change_type": "New", "ucf_ref": "UCF-SIM-0201", "framework": "ISO/IEC 42001", "authority": "ISO (simulated)", "title": "AI system impact assessment before deployment", "control_refs": [],
      "policy_titles": ["Information Security Policy"], "business_units": ["IT", "Operations"], "risk_rating": "Medium", "description": "Simulated new requirement: document an impact assessment for each AI system prior to production use."}, "Impact Assessment", -3),
    ({"change_type": "Modified", "ucf_ref": "UCF-SIM-0103", "risk_rating": "High", "description": "Simulated amendment: emergency changes require retrospective approval within two business days."}, "Impact Assessment", -2),
    ({"change_type": "Retired", "ucf_ref": "UCF-SIM-0113", "risk_rating": "Low", "description": "Simulated retirement: legacy remote access baseline withdrawn."}, "Closed", -40),
    ({"change_type": "Modified", "ucf_ref": "UCF-SIM-0109", "risk_rating": "Medium", "description": "Simulated amendment: recovery plan tests must include a documented lessons-learned review."}, "Validation", -12),
    ({"change_type": "Modified", "ucf_ref": "UCF-SIM-0110", "risk_rating": "Medium", "description": "Simulated amendment: annual acknowledgment must cover AI acceptable-use terms."}, "Remediation-policy", -15),
    ({"change_type": "Modified", "ucf_ref": "UCF-SIM-0104", "risk_rating": "High", "description": "Simulated amendment: restore tests must be evidenced for every critical system."}, "Remediation-control", -20),
    ({"change_type": "Modified", "ucf_ref": "UCF-SIM-0105", "risk_rating": "Low", "description": "Simulated clarification: log review wording clarified; no new obligation."}, "Closed", -30),
    ({"change_type": "Modified", "ucf_ref": "UCF-SIM-0108", "risk_rating": "High", "description": "Simulated amendment: deprovisioning within 24 hours of termination."}, "Closed-remediated", -75),
]


async def seed_ucf(s):
    await new(s, "ucf_config", "system", "Integration configured (fictional seeded configuration)", seeded=True, state="Active", last_sync=None, **CONFIG)
    for ref, fw, auth, title, ver, crefs, pts, bu in REQS:
        req = await new(s, "requirement", "system", "Fictional seeded requirement inventory record", ucf_ref=ref, framework=fw, authority=auth, title=title, version=ver, control_refs=crefs,
                        policy_titles=pts, business_units=bu, state="Active", label=SIM, seeded=True)
        await mk_obligation(s, req)
    for days, st, res, ch, dup in [(-3, "Completed", "3 regulatory change(s) detected", 3, 0), (-2, "Completed", "No regulatory changes detected", 0, 2), (-1, "Failed", None, 0, 0), (-1, "Completed", "No regulatory changes detected", 0, 3)]:
        await new(s, "sync_run", "integration", "Fictional seeded synchronization history", days=days, trigger="Retry after failure" if st == "Completed" and days == -1 and dup == 3 else "Scheduled daily check",
                  source="Simulated UCF feed", state=st, result=res or "Synchronization failed", error=None if res else "Attempt 3: Simulated UCF endpoint timeout (HTTP 504)", changes_detected=ch, duplicates_skipped=dup,
                  started_at=f"{in_days(days)}T06:00:00+00:00", ended_at=f"{in_days(days)}T06:00:04+00:00", seeded=True, label=SIM)
    issues = await find(s, LAB, "issue")
    for i, (item, st, days) in enumerate(SEED_ITEMS):
        ch = await create_change(s, notice(item, f"seed{i + 1}", days), "Scheduled daily check (seeded history)")
        hist = [H("integration", "created", f"Fictional seeded record – received from simulated UCF feed", days)]
        f = {"seeded": True, "date_received": in_days(days)}
        if st != "Impact Assessment":
            gap = st.startswith("Remediation") or st == "Closed-remediated"
            note = "Existing controls remain sufficient" if not gap else "Gap: current control does not meet the updated requirement"
            f.update(controls_sufficient="no" if gap else "yes", policy_revision="yes" if st == "Remediation-policy" else "no", impact_assessment=note, assessed_at=f"{in_days(days + 3)}T10:00:00+00:00", assessed_by=OWNER)
            hist.append(H("compliance_owner", "state", f"Impact Assessment → {'Remediation' if gap else 'Validation'} (assess_impact)", days + 3))
            await upd(s, ch["impact_id"], state="Completed", result="Gap identified" if gap else "No gap", notes=note, completed_at=f"{in_days(days + 3)}T10:00:00+00:00", seeded=True)
        if st == "Remediation-policy":
            aup = [p for p in await find(s, LAB, "policy") if p["title"] == "Acceptable Use Policy" and p["state"] == "Published"][0]
            keep = {k: aup.get(k) for k in ("title", "category", "regulations", "control_objectives", "reviewers", "approval_group", "owner")}
            v = await new(s, "policy", "system", f"Revision drafted for {ch['number']} (fictional seeded record)", days=days + 3, version="3.0", state="Review", reviewed=False, supersedes=aup["number"],
                          reg_change_id=ch["id"], reg_change=ch["number"], revision_reason=item["description"], seeded=True, **keep)
            f.update(revision_policy_ids=[v["id"]], revision_policies=[v["number"]], remediation_status="In progress")
        if st in ("Remediation-control", "Closed-remediated"):
            title = "Backup restore testing overdue" if st == "Remediation-control" else "Terminated users retained access (internal audit finding)"
            iss = next(x for x in issues if x["title"] == title)
            await upd(s, iss["id"], reg_change_id=ch["id"], reg_change=ch["number"])
            f.update(issue_ids=[iss["id"]], issues=[iss["number"]], remediation_status="In progress" if st == "Remediation-control" else "Completed")
        if st.startswith("Closed"):
            hist.append(H("compliance_owner", "state", "Remediation → Validation (submit_for_validation)" if st == "Closed-remediated" else "Validation submitted", days + 10))
            hist.append(H("auditor", "state", "Validation → Closed (validate)", days + 12))
            f.update(closure_evidence="Validation evidence reviewed (fictional)", closed_at=f"{in_days(days + 12)}T10:00:00+00:00", remediation_status="Completed" if st == "Closed-remediated" else "Not required",
                     approval_history=[{"by": "Auditor (fictional)", "decision": "Validated", "at": in_days(days + 12), "comment": "Fictional seeded validation"}])
            req = await get(s, ch["requirement_id"])
            await upd(s, req["id"], **({"state": "Retired", "retired_at": in_days(days + 12)} if item["change_type"] == "Retired" else {"version": ch["updated_version"]}))
        final = {"Remediation-policy": "Remediation", "Remediation-control": "Remediation", "Closed-remediated": "Closed"}.get(st, st)
        await upd(s, ch["id"], state=final, history=hist, **f)
