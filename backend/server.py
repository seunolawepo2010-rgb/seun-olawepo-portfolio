from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import asyncio  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
from contextlib import suppress  # noqa: E402
from datetime import datetime, timezone, timedelta  # noqa: E402
from html import escape  # noqa: E402
import httpx  # noqa: E402
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, UploadFile, File, Query  # noqa: E402
from fastapi.responses import Response, JSONResponse  # noqa: E402
from pydantic import BaseModel, EmailStr, Field  # noqa: E402
from pymongo import ASCENDING, DESCENDING, IndexModel  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from core import db, client, P, ACTIONS, KPIS, SCHEMAS, ins, upd, get, find, validate, audit, rate_limit, client_ip, now, new_id, log  # noqa: E402
import engine  # noqa: E402
import labs_grc, labs_sn, labs_ops, agents, safe  # noqa: E402,F401
from seed_labs import session_dep, reset_session, purge_session  # noqa: E402
from reports import build_pdf, lab_sections, execution_sections, to_csv  # noqa: E402
from auth import router as auth_router, get_admin, seed_admin  # noqa: E402
from content import seed_content, bundle, clean_item, CONTENT_FIELDS, PROFILE_FIELDS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LABS = ["irm", "servicenow", "cyber", "audit", "vendor", "aigov", "agents", "pm", "safe", "ir"]
INDEXES = {
    "records": [IndexModel([("session", ASCENDING), ("lab", ASCENDING), ("type", ASCENDING)], name="s_lab_type"), IndexModel([("session", ASCENDING), ("id", ASCENDING)], name="s_id")],
    "executions": [IndexModel([("id", ASCENDING)], name="id", unique=True), IndexModel([("session", ASCENDING), ("created_at", DESCENDING)], name="s_created")],
    "approvals": [IndexModel([("session", ASCENDING), ("status", ASCENDING)], name="s_status")],
    "audit": [IndexModel([("session", ASCENDING), ("at", DESCENDING)], name="s_at")],
    "demo_sessions": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "users": [IndexModel([("email", ASCENDING)], name="email", unique=True)],
    "login_attempts": [IndexModel([("identifier", ASCENDING)], name="identifier")],
    "ai_usage": [IndexModel([("day", ASCENDING), ("session", ASCENDING)], name="day_session")],
    "pageviews": [IndexModel([("day", ASCENDING)], name="day")],
}

app = FastAPI(title="Seun Olawepo Portfolio & Enterprise Technology Lab API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
api = APIRouter(prefix="/api")
EMAIL_BASE_URL = "https://integrations.emergentagent.com"


def pdf_response(data, name):
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---------- public ----------
@api.get("/health")
async def health():
    return {"status": "ok", "time": now()}


@api.get("/content/bundle")
async def content_bundle():
    return await bundle()


@api.get("/resume")
async def resume():
    f = await db.files.find_one({"kind": "resume"}, P)
    if f:
        return Response(f["data"], media_type=f["content_type"], headers={"Content-Disposition": f'attachment; filename="{f["filename"]}"'})
    b = await bundle()
    pr = b["profile"]
    secs = [("Summary", "text", pr["summary"]), ("Highlights", "text", "\n".join(f"{m['value']} {m['label']}" for m in pr["metrics"]))]
    for e in b["experience"]:
        secs.append((f"{e['title']} — {e['employer']} ({e['start']} – {e['end']})", "text", "\n".join(f"• {h}" for h in e["highlights"])))
    secs.append(("Skills", "text", "\n".join(f"{c}: {', '.join(s['name'] for s in b['skills'] if s['category'] == c)}" for c in dict.fromkeys(s["category"] for s in b["skills"]))))
    return pdf_response(build_pdf(pr["name"], pr["headline"], secs), "Seun_Olawepo_Resume.pdf")


class Contact(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    company: str = Field(default="", max_length=120)
    message: str = Field(min_length=10, max_length=3000)


async def notify_owner(msg):
    to = os.environ.get("NOTIFY_EMAIL")
    if not to:
        return "not_configured"
    html = (f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            f'<p><strong>New portfolio contact message</strong></p><p>From: {escape(msg["name"])} ({escape(msg["email"])})<br/>Company: {escape(msg["company"] or "—")}</p>'
            f'<p style="white-space:pre-wrap">{escape(msg["message"])}</p><p style="font-size:12px;color:#888">Sent by {escape(os.environ["EMAIL_FROM_NAME"])} contact form. '
            f'Reply directly to respond.</p></td></tr></table>')
    payload = {"to": [to], "subject": f"Portfolio contact: {msg['name'][:60]}", "html": html, "from_name": os.environ["EMAIL_FROM_NAME"], "contact_email": msg["email"]}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}, json=payload)
        r.raise_for_status()
        return "sent"
    except Exception as e:  # noqa: BLE001 - message is still stored in the admin inbox
        log.warning("contact email failed: %s", e)
        return "failed"


@api.post("/contact")
async def contact(body: Contact, request: Request):
    rate_limit(f"contact:{client_ip(request)}", 5, 3600)
    msg = {"id": new_id("msg-"), **body.model_dump(), "read": False, "created_at": now()}
    await db.messages.insert_one(dict(msg))
    status = await notify_owner(msg)
    await db.messages.update_one({"id": msg["id"]}, {"$set": {"email_status": status}})
    return {"ok": True}


class PageView(BaseModel):
    path: str = Field(max_length=200)


@api.post("/telemetry/pageview")
async def pageview(body: PageView, request: Request):
    rate_limit(f"pv:{client_ip(request)}", 120, 60)
    await db.pageviews.insert_one({"day": now()[:10], "path": body.path})
    return {"ok": True}


class ClientError(BaseModel):
    message: str = Field(max_length=1000)
    path: str = Field(default="", max_length=200)


@api.post("/telemetry/error")
async def client_error(body: ClientError, request: Request):
    rate_limit(f"err:{client_ip(request)}", 30, 60)
    await db.error_logs.insert_one({"source": "frontend", **body.model_dump(), "at": now()})
    return {"ok": True}


# ---------- labs ----------
def check_lab(lab):
    if lab not in LABS:
        raise HTTPException(404, "Unknown lab")


@api.get("/labs/{lab}/records")
async def lab_records(lab: str, s=Depends(session_dep)):
    check_lab(lab)
    return await find(s, lab)


@api.post("/labs/{lab}/records/{type_}")
async def lab_create(lab: str, type_: str, payload: dict, s=Depends(session_dep)):
    check_lab(lab)
    schema = SCHEMAS.get(lab, {}).get(type_)
    if not schema:
        raise HTTPException(404, "Record type not creatable")
    rec = await ins(s, lab, type_, status="Open" if type_ != "story" else "Backlog", **validate(schema, payload))
    await audit(s, f"record.create:{type_}", lab, {"id": rec["id"]})
    return rec


@api.patch("/labs/{lab}/records/{rid}")
async def lab_update(lab: str, rid: str, payload: dict, s=Depends(session_dep)):
    check_lab(lab)
    rec = await get(s, rid)
    schema = SCHEMAS.get(lab, {}).get(rec["type"])
    if not schema or rec["lab"] != lab:
        raise HTTPException(404, "Record type not editable")
    out = await upd(s, rid, **validate(schema, payload, partial=True))
    await audit(s, f"record.update:{rec['type']}", lab, {"id": rid})
    return out


@api.post("/labs/{lab}/actions/{name}")
async def lab_action(lab: str, name: str, request: Request, s=Depends(session_dep)):
    check_lab(lab)
    fn = ACTIONS.get((lab, name))
    if not fn:
        raise HTTPException(404, "Unknown action")
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(422, "Payload must be an object")
    result = await fn(s, payload)
    await audit(s, f"action:{name}", lab)
    return result


@api.get("/labs/{lab}/dashboard")
async def lab_dashboard(lab: str, s=Depends(session_dep)):
    check_lab(lab)
    return await KPIS[lab](s)


@api.get("/labs/{lab}/report")
async def lab_report(lab: str, format: str = Query("pdf", pattern="^(pdf|csv)$"), s=Depends(session_dep)):
    check_lab(lab)
    recs = await find(s, lab)
    if format == "csv":
        return Response(to_csv(lab, recs), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{lab}-lab-records.csv"'})
    exes = await db.executions.find({"session": s, "lab": lab}, P).sort("created_at", 1).to_list(200)
    return pdf_response(build_pdf(f"{lab.upper()} Lab Report", "Enterprise Technology Lab – simulation report", lab_sections(lab, await KPIS[lab](s), recs, exes)), f"{lab}-lab-report.pdf")


@api.post("/demo/reset")
async def demo_reset(s=Depends(session_dep)):
    await reset_session(s)
    return {"ok": True, "message": "Demo data reset to the initial fictional dataset"}


@api.get("/audit-log")
async def audit_log(lab: str = "", s=Depends(session_dep)):
    q = {"session": s, **({"lab": lab} if lab else {})}
    return await db.audit.find(q, {"_id": 0}).sort("at", -1).to_list(200)


@api.get("/ai/status")
async def ai_status(s=Depends(session_dep)):
    st, g, m = await agents.quota(s)
    return {"live_enabled": st["live_enabled"], "model": st["model"], "remaining_global": g, "remaining_session": m}


# ---------- automation ----------
@api.get("/automation/workflows")
async def wf_catalog():
    return engine.catalog()


@api.get("/automation/executions")
async def wf_list(lab: str = "", s=Depends(session_dep)):
    q = {"session": s, **({"lab": lab} if lab else {})}
    return await db.executions.find(q, {"_id": 0, "ctx": 0}).sort("created_at", -1).to_list(200)


@api.get("/automation/executions/{eid}")
async def wf_get(eid: str, s=Depends(session_dep)):
    e = await db.executions.find_one({"session": s, "id": eid}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Execution not found")
    return e


@api.get("/automation/executions/{eid}/report")
async def wf_report(eid: str, s=Depends(session_dep)):
    e = await wf_get(eid, s)
    return pdf_response(build_pdf(f"Workflow Execution {e['id']}", e["name"], execution_sections(e)), f"{e['id']}.pdf")


@api.post("/automation/executions/{eid}/retry")
async def wf_retry(eid: str, s=Depends(session_dep)):
    return await engine.retry(s, eid)


@api.get("/automation/approvals")
async def approvals(lab: str = "", status: str = "pending", s=Depends(session_dep)):
    q = {"session": s, **({"lab": lab} if lab else {}), **({"status": status} if status else {})}
    return await db.approvals.find(q, {"_id": 0}).sort("requested_at", -1).to_list(200)


class Decision(BaseModel):
    decision: str
    comment: str = Field(default="", max_length=500)


@api.post("/automation/approvals/{aid}/decide")
async def decide(aid: str, body: Decision, s=Depends(session_dep)):
    return await engine.decide(s, aid, body.decision, body.comment)


DEMO_TRIGGERS = {
    "xlab_control_failure": ("irm", "test_control", lambda r: {"control_id": next((c["id"] for c in r if c["type"] == "control" and c["status"] in ("Not Tested", "Effective")), ""), "result": "fail",
                                                              "likelihood": 4, "impact": 5, "propagate": True, "notes": "Cross-lab demo trigger"}),
    "vendor_onboarding": ("vendor", "onboard_vendor", lambda r: {"name": f"Demo Cloud Vendor {new_id()[:4]}", "service": "Cloud data analytics", "data_access": "confidential", "integration": "api", "annual_spend": 300000, "has_soc2": True, "fourth_parties": ["SubCo A"]}),
    "ai_registration": ("aigov", "register_ai_system", lambda r: {"name": f"Demo Underwriting Assistant {new_id()[:4]}", "purpose": "Summarize applications for human underwriters", "owner": "Lending Ops (fictional)", "model_type": "LLM (third-party)", "data_sensitivity": "regulated", "autonomy": "human-in-loop", "decision_impact": "high", "third_party": True, "user_facing": False}),
    "project_delay": ("pm", "simulate_delay", lambda r: {"milestone_id": next((m["id"] for m in r if m["type"] == "milestone" and m["status"] != "Complete" and not m.get("escalated")), "")}),
    "critical_incident": ("ir", "create_incident", lambda r: {"title": "Ransomware on payments servers (demo)", "category": "Ransomware", "affected_systems": ["Payments Gateway", "Core Ledger DB"], "data_involved": "regulated", "users_affected": 25000}),
    "agent_control_issue": ("agents", "control_scan", lambda r: {}),
    "agent_grc_assessment": ("agents", "run_assessment", lambda r: {"request": "Quarterly access & change control assessment", "scope": "Access Control, Configuration Mgmt"}),
}


class RunReq(BaseModel):
    inject_failure: bool = False


@api.post("/automation/run/{key}")
async def wf_run(key: str, body: RunReq, s=Depends(session_dep)):
    if key == "art_dependency_conflict":
        feats = {f["name"]: f for f in await find(s, "safe", "feature")}
        teams = await find(s, "safe", "team")
        pi = await safe.current_pi(s)
        if pi["status"] == "Not Started":
            await ACTIONS[("safe", "start_pi")](s, {"name": "PI 1 (simulation)", "start_date": now()[:10], "planning_date": now()[:10]})
        await ACTIONS[("safe", "assign_feature")](s, {"feature_id": feats["Executive risk dashboard"]["id"], "team_id": teams[0]["id"], "iteration": 2})
        return await ACTIONS[("safe", "assign_feature")](s, {"feature_id": feats["Unified risk scoring API"]["id"], "team_id": teams[4]["id"], "iteration": 3})
    if key not in DEMO_TRIGGERS:
        raise HTTPException(404, "No demo trigger for this workflow")
    lab, act, mk = DEMO_TRIGGERS[key]
    payload = mk(await find(s, lab))
    token = engine.FAULT.set(body.inject_failure)
    try:
        return await ACTIONS[(lab, act)](s, payload)
    finally:
        engine.FAULT.reset(token)


async def run_scheduler(s):
    started = await labs_ops.pm_health_check(s)
    for r in await find(s, "irm", "remediation"):
        if r["status"] in ("In Progress", "Pending Approval") and r["due_date"] < now()[:10] and not r.get("overdue_flag"):
            await upd(s, r["id"], overdue_flag=True)
            await ins(s, "irm", "escalation", title=f"Overdue remediation: {r['title']}", owner=r["owner"], status="Open")
    started += (await ACTIONS[("safe", "escalate_impediments")](s, {}))["executions"]
    await db.scheduler_runs.insert_one({"session": s, "at": now(), "started": started})
    return started


@api.post("/automation/scheduler/run")
async def scheduler_run(s=Depends(session_dep)):
    ids = await run_scheduler(s)
    return {"executions": ids, "message": f"Scheduled checks ran; {len(ids)} workflow(s) started"}


@api.get("/automation/analytics")
async def wf_analytics(s=Depends(session_dep)):
    ex = await db.executions.find({"session": s}, {"_id": 0, "ctx": 0}).to_list(1000)
    by = {}
    for e in ex:
        x = by.setdefault(e["name"], {"workflow": e["name"], "runs": 0, "completed": 0, "failed": 0, "awaiting": 0, "retries": 0})
        x["runs"] += 1
        x["completed"] += e["status"] == "completed"
        x["failed"] += e["status"] == "failed"
        x["awaiting"] += e["status"] == "awaiting_approval"
        x["retries"] += sum(max(0, st["attempts"] - 1) for st in e["steps"])
    status = {}
    for e in ex:
        status[e["status"]] = status.get(e["status"], 0) + 1
    return {"total": len(ex), "by_workflow": list(by.values()), "by_status": [{"name": k, "value": v} for k, v in status.items()],
            "pending_approvals": await db.approvals.count_documents({"session": s, "status": "pending"})}


# ---------- admin ----------
@api.get("/admin/content")
async def admin_content(u=Depends(get_admin)):
    return await bundle(admin=True)


@api.put("/admin/profile")
async def admin_profile(payload: dict, u=Depends(get_admin)):
    data = {k: v for k, v in payload.items() if k in PROFILE_FIELDS}
    await db.content.update_one({"key": "profile"}, {"$set": {**data, "updated_at": now()}})
    await audit("admin", "content.profile.update", "admin", {"fields": list(data)}, u["email"])
    return await db.content.find_one({"key": "profile"}, {"_id": 0})


def coll_check(coll):
    if coll not in CONTENT_FIELDS:
        raise HTTPException(404, "Unknown collection")


@api.post("/admin/content/{coll}")
async def admin_create(coll: str, payload: dict, u=Depends(get_admin)):
    coll_check(coll)
    data = clean_item(coll, payload)
    key = {"experience": "employer", "skills": "name", "certifications": "name"}.get(coll, "title")
    if not str(data.get(key) or "").strip():
        raise HTTPException(422, f"Field '{key}' is required")
    item = {"id": new_id(), **data, "created_at": now()}
    if coll in ("case_studies", "articles", "experience"):
        item["slug"] = item["id"]
    await db[coll].insert_one(dict(item))
    await audit("admin", f"content.{coll}.create", "admin", {"id": item["id"]}, u["email"])
    return item


@api.put("/admin/content/{coll}/{iid}")
async def admin_update(coll: str, iid: str, payload: dict, u=Depends(get_admin)):
    coll_check(coll)
    res = await db[coll].update_one({"id": iid}, {"$set": clean_item(coll, payload)})
    if not res.matched_count:
        raise HTTPException(404, "Item not found")
    await audit("admin", f"content.{coll}.update", "admin", {"id": iid}, u["email"])
    return await db[coll].find_one({"id": iid}, {"_id": 0})


@api.delete("/admin/content/{coll}/{iid}")
async def admin_delete(coll: str, iid: str, u=Depends(get_admin)):
    coll_check(coll)
    await db[coll].delete_one({"id": iid})
    await audit("admin", f"content.{coll}.delete", "admin", {"id": iid}, u["email"])
    return {"ok": True}


@api.get("/admin/messages")
async def admin_messages(u=Depends(get_admin)):
    return await db.messages.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.patch("/admin/messages/{mid}")
async def admin_msg_read(mid: str, u=Depends(get_admin)):
    await db.messages.update_one({"id": mid}, {"$set": {"read": True}})
    return {"ok": True}


@api.post("/admin/resume")
async def admin_resume(file: UploadFile = File(...), u=Depends(get_admin)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 5 MB)")
    if data[:4] == b"%PDF":
        ctype = "application/pdf"
    elif data[:2] == b"PK" and (file.filename or "").lower().endswith(".docx"):
        ctype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(415, "Only PDF or DOCX files are accepted")
    name = "".join(c for c in (file.filename or "resume.pdf") if c.isalnum() or c in "._- ")[:80] or "resume.pdf"
    await db.files.update_one({"kind": "resume"}, {"$set": {"kind": "resume", "filename": name, "content_type": ctype, "data": data, "size": len(data), "uploaded_at": now()}}, upsert=True)
    await audit("admin", "resume.upload", "admin", {"filename": name}, u["email"])
    return {"ok": True, "filename": name, "size": len(data)}


class AISettings(BaseModel):
    live_enabled: bool
    model: str
    daily_limit_global: int = Field(ge=0, le=1000)
    daily_limit_session: int = Field(ge=0, le=50)


@api.get("/admin/settings")
async def admin_settings(u=Depends(get_admin)):
    st = await agents.ai_settings()
    return {"ai": st, "models": list(agents.PRICING), "integrations": {"llm_key_configured": bool(os.environ.get("EMERGENT_LLM_KEY")), "email_configured": bool(os.environ.get("EMERGENT_EMAIL_KEY")),
                                                                      "notify_email_configured": bool(os.environ.get("NOTIFY_EMAIL"))}}


@api.put("/admin/settings")
async def admin_settings_put(body: AISettings, u=Depends(get_admin)):
    if body.model not in agents.PRICING:
        raise HTTPException(422, "Unknown model")
    doc = {"key": "ai", **body.model_dump(), "provider": agents.PRICING[body.model]["provider"]}
    await db.settings.update_one({"key": "ai"}, {"$set": doc}, upsert=True)
    await audit("admin", "settings.ai.update", "admin", body.model_dump(), u["email"])
    return doc


@api.get("/admin/overview")
async def admin_overview(u=Depends(get_admin)):
    since = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    pv = await db.pageviews.aggregate([{"$match": {"day": {"$gte": since}}}, {"$group": {"_id": "$path", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 15}]).to_list(15)
    return {"sessions": await db.demo_sessions.count_documents({}), "executions": await db.executions.count_documents({}),
            "messages_unread": await db.messages.count_documents({"read": False}), "ai_calls_today": await db.ai_usage.count_documents({"day": now()[:10]}),
            "pageviews_30d": [{"path": p["_id"], "views": p["n"]} for p in pv],
            "recent_executions": await db.executions.find({}, {"_id": 0, "ctx": 0, "steps": 0}).sort("created_at", -1).to_list(50),
            "admin_audit": await db.audit.find({"session": "admin"}, P).sort("at", -1).to_list(50),
            "errors": await db.error_logs.find({}, P).sort("at", -1).to_list(30)}


@api.post("/admin/demo/purge-stale")
async def admin_purge(u=Depends(get_admin)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    stale = [d["id"] for d in await db.demo_sessions.find({"last_seen": {"$lt": cutoff}}, P).to_list(5000)]
    for sid in stale:
        await purge_session(sid)
    await audit("admin", "demo.purge_stale", "admin", {"count": len(stale)}, u["email"])
    return {"purged": len(stale)}


app.include_router(auth_router)
app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ["CORS_ORIGINS"].split(","), allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    await db.error_logs.insert_one({"source": "backend", "path": request.url.path, "message": f"{type(exc).__name__}: {exc}"[:1000], "at": now()})
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


async def ensure_indexes():
    for coll, models in INDEXES.items():
        for m in models:
            try:
                await db[coll].create_indexes([m])
            except Exception as exc:  # noqa: BLE001
                log.error("index %s.%s: %s", coll, m.document["name"], exc)


async def background_scheduler():
    while True:
        await asyncio.sleep(900)
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            for d in await db.demo_sessions.find({"last_seen": {"$gte": cutoff}}, P).to_list(500):
                await run_scheduler(d["id"])
        except Exception as e:  # noqa: BLE001
            log.warning("scheduler loop: %s", e)


@app.on_event("startup")
async def startup():
    await ensure_indexes()
    await seed_admin()
    await seed_content()
    app.state.sched = asyncio.create_task(background_scheduler())


@app.on_event("shutdown")
async def shutdown():
    app.state.sched.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.sched
    client.close()
