import os
import re
import time
import uuid
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
log = logging.getLogger("portfolio")
P = {"_id": 0}

ACTIONS = {}
KPIS = {}
SCHEMAS = {}


def now():
    return datetime.now(timezone.utc).isoformat()


def today():
    return datetime.now(timezone.utc).date().isoformat()


def in_days(n):
    return (datetime.now(timezone.utc) + timedelta(days=n)).date().isoformat()


def new_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def action(lab, name):
    def deco(fn):
        ACTIONS[(lab, name)] = fn
        return fn
    return deco


def kpi(lab):
    def deco(fn):
        KPIS[lab] = fn
        return fn
    return deco


async def ins(s, lab, type_, **f):
    doc = {"id": new_id(), "session": s, "lab": lab, "type": type_, "created_at": now(), "updated_at": now(), **f}
    await db.records.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def upd(s, rid, **f):
    f["updated_at"] = now()
    doc = await db.records.find_one_and_update({"session": s, "id": rid}, {"$set": f}, projection=P, return_document=True)
    if not doc:
        raise HTTPException(404, "Record not found")
    return doc


async def get(s, rid, type_=None):
    q = {"session": s, "id": rid}
    if type_:
        q["type"] = type_
    doc = await db.records.find_one(q, P)
    if not doc:
        raise HTTPException(404, f"{type_ or 'Record'} not found")
    return doc


async def find(s, lab=None, type_=None, **q):
    q["session"] = s
    if lab:
        q["lab"] = lab
    if type_:
        q["type"] = type_
    return await db.records.find(q, P).sort("created_at", 1).to_list(2000)


async def bulk(s, lab, type_, rows):
    docs = [{"id": r.pop("id", None) or new_id(), "session": s, "lab": lab, "type": type_, "created_at": now(), "updated_at": now(), **r} for r in rows]
    if docs:
        await db.records.insert_many(docs)
    return docs


def by_status(rows, field="status"):
    out = {}
    for r in rows:
        out[r.get(field) or "n/a"] = out.get(r.get(field) or "n/a", 0) + 1
    return [{"name": k, "value": v} for k, v in out.items()]


async def audit(s, action_, lab="", details=None, actor="demo-visitor"):
    await db.audit.insert_one({"id": new_id(), "session": s, "actor": actor, "action": action_, "lab": lab,
                               "details": details or {}, "at": now()})


def validate(schema, payload, partial=False):
    """schema: {field: (type, required, extra)}"""
    out = {}
    payload = payload or {}
    for k, (t, req, extra) in schema.items():
        v = payload.get(k)
        if v is None or v == "" or v == []:
            if req and not partial:
                raise HTTPException(422, f"Field '{k}' is required")
            continue
        try:
            if t == "int":
                v = int(v)
                if extra and not (extra[0] <= v <= extra[1]):
                    raise ValueError
            elif t == "float":
                v = float(v)
                if extra and not (extra[0] <= v <= extra[1]):
                    raise ValueError
            elif t == "choice":
                if v not in extra:
                    raise ValueError
            elif t == "date":
                v = str(v)[:10]
                datetime.fromisoformat(v)
            elif t == "bool":
                v = v in (True, "true", "True", 1, "1", "yes")
            elif t == "list":
                if isinstance(v, str):
                    v = [x.strip() for x in v.split(",") if x.strip()]
                v = [str(x)[:120] for x in v][:30]
            elif t == "dict":
                if not isinstance(v, dict):
                    raise ValueError
            else:
                v = str(v).strip()[: (extra or 2000)]
        except (ValueError, TypeError):
            hint = f" (allowed: {', '.join(map(str, extra))})" if t == "choice" else (f" (range {extra[0]}-{extra[1]})" if t in ("int", "float") and extra else "")
            raise HTTPException(422, f"Invalid value for '{k}'{hint}")
        out[k] = v
    return out


_hits = defaultdict(deque)


def rate_limit(key, limit, window):
    t = time.time()
    q = _hits[key]
    while q and q[0] < t - window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Rate limit exceeded. Please slow down and try again shortly.")
    q.append(t)


def client_ip(request: Request):
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "unknown")


SESSION_RE = re.compile(r"^[a-zA-Z0-9-]{8,64}$")
