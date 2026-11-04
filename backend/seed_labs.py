import asyncio
from fastapi import HTTPException, Request
from pymongo.errors import DuplicateKeyError
from core import db, now, SESSION_RE, rate_limit
from labs_grc import seed_irm, seed_cyber, seed_audit, seed_vendor
from labs_sn import seed_servicenow
from labs_ops import seed_aigov, seed_pm, seed_ir
from agents import seed_agents
from safe import seed_safe
from grc_seed import seed_grc

SEEDERS = [seed_irm, seed_servicenow, seed_cyber, seed_audit, seed_vendor, seed_aigov, seed_agents, seed_pm, seed_safe, seed_ir, seed_grc]


_locks = {}


async def ensure_seeded(s):
    lock = _locks.setdefault(s, asyncio.Lock())
    async with lock:
        doc = await db.demo_sessions.find_one({"id": s})
        if doc and doc.get("seeded"):
            await db.demo_sessions.update_one({"id": s}, {"$set": {"last_seen": now()}})
            if not doc.get("grc_seeded"):
                await seed_grc(s)
                await db.demo_sessions.update_one({"id": s}, {"$set": {"grc_seeded": True}})
            return
        if doc:
            await purge_session(s)
        try:
            await db.demo_sessions.insert_one({"id": s, "created_at": now(), "last_seen": now(), "seeded": False})
        except DuplicateKeyError:
            return
        for fn in SEEDERS:
            await fn(s)
        await db.demo_sessions.update_one({"id": s}, {"$set": {"seeded": True, "grc_seeded": True}})


async def purge_session(s):
    for c in ("records", "executions", "approvals", "audit"):
        await db[c].delete_many({"session": s})
    await db.ai_usage.update_many({"session": s}, {"$set": {"session": f"reset-{s}"}})
    await db.demo_sessions.delete_one({"id": s})


async def reset_session(s):
    async with _locks.setdefault(s, asyncio.Lock()):
        await purge_session(s)
    await ensure_seeded(s)


async def session_dep(request: Request):
    s = request.headers.get("x-demo-session", "")
    if not SESSION_RE.match(s):
        raise HTTPException(400, "Missing or invalid X-Demo-Session header")
    rate_limit(f"s:{s}", 240, 60)
    await ensure_seeded(s)
    return s
