from datetime import date, timedelta
from fastapi import HTTPException
from core import action, kpi, SCHEMAS, ins, upd, get, find, bulk, validate, by_status, in_days, today, now
import engine
from engine import APPROVAL

LAB = "safe"
SCHEMAS[LAB] = {}
ITER = 5  # iteration 5 = Innovation & Planning


async def seed_safe(s):
    await bulk(s, LAB, "art", [{"name": "Atlas Risk Platform ART (fictional)", "rte": "RTE (portfolio demo)", "product_management": "PM – fictional", "system_architect": "Architect – fictional"}])
    teams = await bulk(s, LAB, "team", [{"name": n, "focus": f, "capacity": [c] * 4 + [c // 2], "scrum_master": f"SM {i + 1} (fictional)", "product_owner": f"PO {i + 1} (fictional)"}
                                        for i, (n, f, c) in enumerate([("Phoenix", "Risk register & scoring", 30), ("Orion", "Controls & audit", 28), ("Vega", "Vendor & integrations", 25),
                                                                       ("Lyra", "AI governance features", 22), ("Nova", "Platform & data", 32)])])
    feats = await bulk(s, LAB, "feature", [{"name": n, "kind": k, "bv": bv, "tc": tc, "rr": rr, "size": sz, "wsjf": round((bv + tc + rr) / sz, 2), "team_id": None, "team": None, "iteration": None, "status": "Backlog"}
                                           for n, k, bv, tc, rr, sz in [("Unified risk scoring API", "Enabler", 8, 8, 13, 13), ("Control self-assessment portal", "Feature", 13, 8, 5, 20),
                                                                        ("Vendor questionnaire automation", "Feature", 13, 13, 8, 13), ("AI intake form", "Feature", 8, 13, 8, 8),
                                                                        ("Audit evidence repository", "Feature", 8, 5, 5, 13), ("Executive risk dashboard", "Feature", 20, 8, 3, 13),
                                                                        ("Data pipeline hardening", "Enabler", 3, 5, 13, 8), ("SSO integration", "Enabler", 5, 8, 13, 8),
                                                                        ("Model inventory sync", "Feature", 8, 5, 8, 8), ("Policy attestation reminders", "Feature", 5, 3, 3, 5)]])
    await bulk(s, LAB, "dependency", [{"consumer_id": feats[5]["id"], "consumer": feats[5]["name"], "provider_id": feats[0]["id"], "provider": feats[0]["name"], "status": "Open"},
                                      {"consumer_id": feats[2]["id"], "consumer": feats[2]["name"], "provider_id": feats[7]["id"], "provider": feats[7]["name"], "status": "Open"},
                                      {"consumer_id": feats[8]["id"], "consumer": feats[8]["name"], "provider_id": feats[6]["id"], "provider": feats[6]["name"], "status": "Open"}])
    await bulk(s, LAB, "program_risk", [{"description": "Shared test environment availability", "owner": "Nova", "roam": None, "status": "Open"},
                                        {"description": "Key SME on leave during iteration 2", "owner": "Orion", "roam": None, "status": "Open"}])
    await bulk(s, LAB, "pi", [{"name": "PI 1 (simulation)", "status": "Not Started", "votes": {}, "warnings": []}])
    _ = teams


async def current_pi(s):
    pis = await find(s, LAB, "pi")
    if not pis:
        raise HTTPException(409, "Demo data is being prepared – please retry")
    return pis[-1]


async def require_started(s):
    pi = await current_pi(s)
    if pi["status"] == "Not Started":
        raise HTTPException(409, "Start the Program Increment first")
    return pi


async def board(s):
    teams = await find(s, LAB, "team")
    feats = await find(s, LAB, "feature")
    deps = await find(s, LAB, "dependency")
    fmap = {f["id"]: f for f in feats}
    load = []
    for t in teams:
        row = []
        for i in range(1, ITER + 1):
            pts = sum(f["size"] for f in feats if f["team_id"] == t["id"] and f["iteration"] == i)
            row.append({"iteration": i, "load": pts, "capacity": t["capacity"][i - 1], "over": pts > t["capacity"][i - 1]})
        load.append({"team_id": t["id"], "team": t["name"], "cells": row})
    conflicts = []
    for d in deps:
        c, p = fmap.get(d["consumer_id"]), fmap.get(d["provider_id"])
        if d["status"] == "Resolved" or not c or not p or not c["iteration"]:
            continue
        if not p["iteration"] or p["iteration"] >= c["iteration"]:
            conflicts.append({"dependency_id": d["id"], "consumer": c["name"], "provider": p["name"], "consumer_iteration": c["iteration"], "provider_iteration": p["iteration"],
                              "reason": "Provider not planned" if not p["iteration"] else f"Provider lands I{p['iteration']} ≥ consumer I{c['iteration']}"})
    return {"teams": [{"id": t["id"], "name": t["name"], "focus": t["focus"], "capacity": t["capacity"]} for t in teams], "features": feats, "load": load, "conflicts": conflicts, "dependencies": deps}


async def st_dep_record(s, ctx):
    await upd(s, ctx["dependency_id"], status="Conflict", conflict_reason=ctx["reason"])
    return {"conflict": ctx["reason"]}


async def st_dep_escalate(s, ctx):
    e = await ins(s, LAB, "escalation", title=f"Dependency conflict: {ctx['consumer']} ← {ctx['provider']}", to="RTE", status="Open")
    return {"escalation_id": e["id"]}


async def st_dep_agenda(s, ctx):
    a = await ins(s, LAB, "agenda_item", meeting="ART Sync", topic=f"Resolve: {ctx['consumer']} needs {ctx['provider']} ({ctx['reason']})", status="Scheduled")
    return {"agenda_item": a["id"]}


async def st_dep_track(s, ctx):
    t = await ins(s, LAB, "resolution_item", dependency_id=ctx["dependency_id"], title=f"Re-sequence {ctx['provider']} before I{ctx['consumer_iteration']}", owner="RTE", due_date=in_days(5), status="Open")
    return {"resolution_item": t["id"]}


engine.workflow("art_dependency_conflict", "WF5: ART Dependency Conflict → RTE Escalation → ART Sync Agenda → Resolution", LAB, "Cross-team dependency conflict detected",
                "Detects provider features landing in the same or later iteration than their consumers and drives RTE resolution.",
                [("Record conflict", st_dep_record, {}), ("Escalate to RTE", st_dep_escalate, {}), ("Add to ART Sync agenda", st_dep_agenda, {}), ("Track resolution", st_dep_track, {})], cross_lab=True)


async def st_cap(s, ctx):
    a = await ins(s, LAB, "alert", kind="Capacity", detail=f"{ctx['team']} I{ctx['iteration']} load {ctx['load']} > capacity {ctx['capacity']}", status="Open")
    return {"alert_id": a["id"]}


engine.workflow("safe_capacity_alert", "Capacity Alert", LAB, "Team iteration overcommitted", "Flags overcommitted teams during breakout planning.", [("Raise capacity alert", st_cap, {})])


async def st_imp(s, ctx):
    e = await ins(s, LAB, "escalation", title=f"Critical impediment: {ctx['description']}", to="RTE → Business Owners", status="Open")
    await upd(s, ctx["impediment_id"], escalated=True, status="Escalated")
    return {"escalation_id": e["id"]}


engine.workflow("safe_impediment_escalation", "Impediment Escalation", LAB, "Critical impediment unresolved", "Escalates critical blockers to the RTE and business owners.", [("Escalate impediment", st_imp, {})])


async def run_checks(s, team_id=None):
    b = await board(s)
    started = []
    for row in b["load"]:
        for c in row["cells"]:
            if c["over"] and (not team_id or row["team_id"] == team_id):
                if not [a for a in await find(s, LAB, "alert", status="Open") if a["detail"].startswith(f"{row['team']} I{c['iteration']} ")]:
                    started.append((await engine.start(s, "safe_capacity_alert", {"team": row["team"], "iteration": c["iteration"], "load": c["load"], "capacity": c["capacity"], "_lab": LAB}, "capacity_check"))["id"])
    for cf in b["conflicts"]:
        d = await get(s, cf["dependency_id"])
        if d["status"] == "Open":
            started.append((await engine.start(s, "art_dependency_conflict", {**cf, "_lab": LAB}, "dependency_check"))["id"])
    return started, b


@action(LAB, "start_pi")
async def a_start(s, p):
    d = validate({"name": ("str", True, 60), "start_date": ("date", True, None), "planning_date": ("date", True, None)}, p)
    pi = await current_pi(s)
    if pi["status"] not in ("Not Started", "Closed"):
        raise HTTPException(409, f"Current PI is {pi['status']}")
    st = date.fromisoformat(d["start_date"])
    cal = [{"iteration": i + 1, "start": (st + timedelta(days=14 * i)).isoformat(), "end": (st + timedelta(days=14 * i + 13)).isoformat(), "label": "IP" if i == ITER - 1 else f"I{i + 1}"} for i in range(ITER)]
    return {"pi": await upd(s, pi["id"], name=d["name"], status="Planning Scheduled", start_date=d["start_date"], planning_date=d["planning_date"], calendar=cal,
                            business_context="Top priorities: executive risk visibility, vendor automation, AI intake (fictional business owners)")}


@action(LAB, "create_feature")
async def a_feat(s, p):
    d = validate({"name": ("str", True, 120), "kind": ("choice", True, ["Feature", "Enabler"]), "bv": ("int", True, (1, 20)), "tc": ("int", True, (1, 20)), "rr": ("int", True, (1, 20)), "size": ("int", True, (1, 40))}, p)
    return {"feature": await ins(s, LAB, "feature", wsjf=round((d["bv"] + d["tc"] + d["rr"]) / d["size"], 2), team_id=None, team=None, iteration=None, status="Backlog", **d)}


@action(LAB, "assign_feature")
async def a_assign(s, p):
    d = validate({"feature_id": ("str", True, 40), "team_id": ("str", True, 40), "iteration": ("int", True, (1, ITER))}, p)
    pi = await current_pi(s)
    if pi["status"] == "Not Started":
        raise HTTPException(409, "Start the Program Increment first")
    t = await get(s, d["team_id"], "team")
    await upd(s, (await get(s, d["feature_id"], "feature"))["id"], team_id=t["id"], team=t["name"], iteration=d["iteration"], status="Planned")
    if pi["status"] == "Planning Scheduled":
        await upd(s, pi["id"], status="Breakout Planning")
    started, b = await run_checks(s, t["id"])
    return {"automations": started, "conflicts": len(b["conflicts"])}


@action(LAB, "set_capacity")
async def a_cap(s, p):
    d = validate({"team_id": ("str", True, 40), "iteration": ("int", True, (1, ITER)), "capacity": ("int", True, (0, 200))}, p)
    t = await get(s, d["team_id"], "team")
    cap = list(t["capacity"])
    cap[d["iteration"] - 1] = d["capacity"]
    await upd(s, t["id"], capacity=cap)
    return {"capacity": cap}


@action(LAB, "add_dependency")
async def a_dep(s, p):
    d = validate({"consumer_id": ("str", True, 40), "provider_id": ("str", True, 40)}, p)
    if d["consumer_id"] == d["provider_id"]:
        raise HTTPException(422, "A feature cannot depend on itself")
    c, pr = await get(s, d["consumer_id"], "feature"), await get(s, d["provider_id"], "feature")
    dep = await ins(s, LAB, "dependency", consumer_id=c["id"], consumer=c["name"], provider_id=pr["id"], provider=pr["name"], status="Open")
    started, _ = await run_checks(s)
    return {"dependency": dep, "automations": started}


@action(LAB, "resolve_dependency")
async def a_resolve(s, p):
    d = validate({"dependency_id": ("str", True, 40), "resolution": ("str", True, 300)}, p)
    dep = await get(s, d["dependency_id"], "dependency")
    cf = [c for c in (await board(s))["conflicts"] if c["dependency_id"] == dep["id"]]
    if cf:
        raise HTTPException(409, f"Conflict still present on the board ({cf[0]['reason']}). Re-plan the provider feature into an earlier iteration first.")
    await upd(s, dep["id"], status="Resolved", resolution=d["resolution"])
    for r in await find(s, LAB, "resolution_item", dependency_id=dep["id"]):
        await upd(s, r["id"], status="Closed")
    return {"message": "Dependency resolved"}


@action(LAB, "roam_risk")
async def a_roam(s, p):
    d = validate({"risk_id": ("str", True, 40), "roam": ("choice", True, ["Resolved", "Owned", "Accepted", "Mitigated"]), "note": ("str", False, 300)}, p)
    return {"risk": await upd(s, (await get(s, d["risk_id"], "program_risk"))["id"], roam=d["roam"], status="Closed" if d["roam"] == "Resolved" else "ROAMed", note=d.get("note", ""))}


@action(LAB, "add_risk")
async def a_risk(s, p):
    d = validate({"description": ("str", True, 300), "owner": ("str", True, 60)}, p)
    return {"risk": await ins(s, LAB, "program_risk", roam=None, status="Open", **d)}


@action(LAB, "create_objective")
async def a_obj(s, p):
    d = validate({"team_id": ("str", True, 40), "description": ("str", True, 300), "business_value": ("int", True, (1, 10)), "committed": ("bool", False, None), "feature_ids": ("list", False, None)}, p)
    await require_started(s)
    t = await get(s, d["team_id"], "team")
    return {"objective": await ins(s, LAB, "objective", team=t["name"], team_id=t["id"], description=d["description"], business_value=d["business_value"], committed=d.get("committed", True),
                                   feature_ids=d.get("feature_ids", []), progress=0, actual_value=0)}


@action(LAB, "vote")
async def a_vote(s, p):
    d = validate({"team_id": ("str", True, 40), "confidence": ("int", True, (1, 5))}, p)
    pi = await require_started(s)
    t = await get(s, d["team_id"], "team")
    votes = {**pi.get("votes", {}), t["name"]: d["confidence"]}
    avg = round(sum(votes.values()) / len(votes), 2)
    await upd(s, pi["id"], votes=votes, confidence=avg)
    return {"votes": votes, "average": avg, "guidance": "Average < 3 → re-plan before commitment" if avg < 3 else "Confidence sufficient"}


@action(LAB, "finalize_pi")
async def a_final(s, p):
    pi = await current_pi(s)
    if pi["status"] not in ("Breakout Planning", "Planning Scheduled"):
        raise HTTPException(409, f"PI is {pi['status']}")
    b = await board(s)
    teams = await find(s, LAB, "team")
    warnings = []
    if b["conflicts"]:
        warnings.append(f"{len(b['conflicts'])} unresolved dependency conflict(s)")
    over = [f"{r['team']} I{c['iteration']}" for r in b["load"] for c in r["cells"] if c["over"]]
    if over:
        warnings.append(f"Overcommitted: {', '.join(over)}")
    if [r for r in await find(s, LAB, "program_risk") if not r.get("roam")]:
        warnings.append("Program risks not ROAMed")
    if len(pi.get("votes", {})) < len(teams):
        raise HTTPException(409, f"All {len(teams)} teams must vote confidence before commitment ({len(pi.get('votes', {}))} voted)")
    if pi.get("confidence", 0) < 3:
        raise HTTPException(409, f"ART confidence {pi.get('confidence')} < 3 – re-plan required")
    objs = await find(s, LAB, "objective")
    if not objs:
        raise HTTPException(409, "Create PI objectives before commitment")
    planned = sum(o["business_value"] for o in objs if o["committed"])
    return {"pi": await upd(s, pi["id"], status="Committed", warnings=warnings, planned_bv=planned, committed_at=now(), planned_features=sum(1 for f in b["features"] if f["iteration"]))}


@action(LAB, "complete_feature")
async def a_done(s, p):
    d = validate({"feature_id": ("str", True, 40)}, p)
    pi = await current_pi(s)
    if pi["status"] not in ("Committed", "Executing"):
        raise HTTPException(409, "Finalize the PI plan before tracking execution")
    await upd(s, (await get(s, d["feature_id"], "feature"))["id"], status="Done")
    await upd(s, pi["id"], status="Executing")
    feats = {f["id"]: f for f in await find(s, LAB, "feature")}
    for o in await find(s, LAB, "objective"):
        if o["feature_ids"]:
            prog = sum(1 for f in o["feature_ids"] if feats.get(f, {}).get("status") == "Done") / len(o["feature_ids"])
            await upd(s, o["id"], progress=round(prog * 100), actual_value=round(o["business_value"] * prog, 1))
    return {"message": "Feature done; PI objective progress updated"}


@action(LAB, "add_impediment")
async def a_imp(s, p):
    d = validate({"description": ("str", True, 300), "team": ("str", True, 60), "severity": ("choice", True, ["Low", "Medium", "Critical"])}, p)
    return {"impediment": await ins(s, LAB, "impediment", status="Open", escalated=False, **d)}


@action(LAB, "escalate_impediments")
async def a_esc(s, p):
    ids = [(await engine.start(s, "safe_impediment_escalation", {"impediment_id": i["id"], "description": i["description"], "_lab": LAB}, "impediment_check"))["id"]
           for i in await find(s, LAB, "impediment", status="Open") if i["severity"] == "Critical" and not i["escalated"]]
    return {"executions": ids, "message": f"{len(ids)} critical impediment(s) escalated"}


@action(LAB, "resolve_impediment")
async def a_res_imp(s, p):
    d = validate({"impediment_id": ("str", True, 40)}, p)
    return {"impediment": await upd(s, (await get(s, d["impediment_id"], "impediment"))["id"], status="Resolved")}


@action(LAB, "sync_event")
async def a_sync(s, p):
    d = validate({"kind": ("choice", True, ["Scrum of Scrums", "ART Sync", "PO Sync", "System Demo"]), "notes": ("str", True, 800)}, p)
    b = await board(s)
    agenda = [a["topic"] for a in await find(s, LAB, "agenda_item", status="Scheduled")] + [f"Impediment: {i['description']}" for i in await find(s, LAB, "impediment") if i["status"] != "Resolved"]
    m = await ins(s, LAB, "meeting", kind=d["kind"], notes=d["notes"], agenda=agenda or ["No open items"], conflicts_open=len(b["conflicts"]))
    for a in await find(s, LAB, "agenda_item", status="Scheduled"):
        if d["kind"] == "ART Sync":
            await upd(s, a["id"], status="Discussed")
    return {"meeting": m}


@action(LAB, "inspect_adapt")
async def a_ia(s, p):
    pi = await current_pi(s)
    if pi["status"] not in ("Committed", "Executing"):
        raise HTTPException(409, "Inspect & Adapt requires a committed PI")
    objs = await find(s, LAB, "objective")
    feats = await find(s, LAB, "feature")
    per = {}
    for o in objs:
        if o["committed"]:
            x = per.setdefault(o["team"], [0, 0])
            x[0] += o["business_value"]
            x[1] += o["actual_value"]
    teams = [{"team": t, "planned_bv": v[0], "actual_bv": v[1], "predictability": round(100 * v[1] / v[0]) if v[0] else 0} for t, v in per.items()]
    tp, ta = sum(t["planned_bv"] for t in teams), sum(t["actual_bv"] for t in teams)
    planned = [f for f in feats if f["iteration"]]
    rep = await ins(s, LAB, "ia_report", pi=pi["name"], art_predictability=round(100 * ta / tp) if tp else 0, teams=teams,
                    features_done=sum(1 for f in planned if f["status"] == "Done"), features_planned=len(planned),
                    impediments=len(await find(s, LAB, "impediment")), escalations=len(await find(s, LAB, "escalation")),
                    improvement_backlog=["Reduce cross-team dependencies via earlier enabler sequencing", "Hold capacity buffer ≥ 15% per team"] if teams else [],
                    note="Evidence-based: computed from recorded objectives, features and events in this demo session")
    return {"report": rep}


@kpi(LAB)
async def k_safe(s):
    b = await board(s)
    pi = await current_pi(s)
    used = sum(c["load"] for r in b["load"] for c in r["cells"])
    cap = sum(c["capacity"] for r in b["load"] for c in r["cells"])
    risks = await find(s, LAB, "program_risk")
    return {"kpis": [{"label": "PI status", "value": pi["status"]}, {"label": "Capacity used", "value": f"{round(100 * used / max(cap, 1))}%"},
                     {"label": "Dependency conflicts", "value": len(b["conflicts"])}, {"label": "Risks ROAMed", "value": f"{sum(1 for r in risks if r.get('roam'))}/{len(risks)}"},
                     {"label": "Confidence", "value": pi.get("confidence", "—")}],
            "charts": [{"title": "Features by status", "data": by_status(b["features"])}, {"title": "Team load (points)", "data": [{"name": r["team"], "value": sum(c["load"] for c in r["cells"])} for r in b["load"]]}],
            "board": b, "pi": pi}
