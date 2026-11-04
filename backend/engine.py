import time
from contextvars import ContextVar
from fastapi import HTTPException
from core import db, P, now, new_id, audit, log

APPROVAL = "APPROVAL"
WORKFLOWS = {}
MAX_ATTEMPTS = 3
FAULT = ContextVar("fault_injection", default=False)


def workflow(key, name, lab, trigger, description, steps, cross_lab=False):
    """steps: list of (name, fn | APPROVAL, meta)"""
    WORKFLOWS[key] = {"key": key, "name": name, "lab": lab, "trigger": trigger, "description": description,
                      "steps": steps, "cross_lab": cross_lab}


def catalog():
    return [{"key": w["key"], "name": w["name"], "lab": w["lab"], "trigger": w["trigger"], "description": w["description"],
             "cross_lab": w["cross_lab"], "steps": [{"name": n, "kind": "approval" if f == APPROVAL else "automated"} for n, f, _ in w["steps"]]}
            for w in WORKFLOWS.values()]


async def start(s, key, ctx, trigger="manual"):
    wf = WORKFLOWS[key]
    if FAULT.get():
        ctx = {**ctx, "inject_failure_step": 1}
    exe = {"id": new_id("EXE-"), "session": s, "workflow": key, "name": wf["name"], "lab": wf["lab"], "cross_lab": wf["cross_lab"],
           "status": "running", "trigger": trigger, "ctx": ctx, "current": 0, "created_at": now(), "updated_at": now(),
           "steps": [{"name": n, "kind": "approval" if f == APPROVAL else "automated", "status": "pending", "attempts": 0,
                      "started_at": None, "ended_at": None, "output": None, "error": None} for n, f, _ in wf["steps"]]}
    await db.executions.insert_one(exe)
    exe.pop("_id", None)
    await audit(s, f"workflow.start:{key}", wf["lab"], {"execution": exe["id"], "trigger": trigger})
    return await _advance(exe)


async def _save(exe):
    exe["updated_at"] = now()
    await db.executions.replace_one({"id": exe["id"]}, exe)


async def _advance(exe):
    wf = WORKFLOWS[exe["workflow"]]
    s, ctx = exe["session"], exe["ctx"]
    while exe["current"] < len(wf["steps"]):
        i = exe["current"]
        name, fn, meta = wf["steps"][i]
        st = exe["steps"][i]
        st["started_at"] = st["started_at"] or now()
        skip = meta.get("skip_if") if meta else None
        if skip and skip(ctx):
            st.update(status="skipped", ended_at=now(), output={"reason": meta.get("skip_reason", "Condition not met")})
            exe["current"] += 1
            continue
        if fn == APPROVAL:
            title = meta["title"](ctx) if callable(meta.get("title")) else meta.get("title", name)
            appr = {"id": new_id("APR-"), "session": s, "execution_id": exe["id"], "workflow": exe["workflow"], "lab": exe["lab"],
                    "step_index": i, "title": title, "approver_role": meta.get("role", "Risk Owner"),
                    "details": {k: v for k, v in ctx.items() if not isinstance(v, (dict, list))}, "status": "pending",
                    "requested_at": now(), "decided_at": None, "comment": None}
            await db.approvals.insert_one(appr)
            st.update(status="awaiting_approval", output={"approval_id": appr["id"], "approver_role": appr["approver_role"]})
            exe["status"] = "awaiting_approval"
            await _save(exe)
            return exe
        ok = False
        while st["attempts"] < MAX_ATTEMPTS:
            st["attempts"] += 1
            t0 = time.perf_counter()
            try:
                if ctx.get("inject_failure_step") == i and st["attempts"] == 1:
                    raise RuntimeError("Injected transient fault (demo of retry handling)")
                out = await fn(s, ctx)
                st.update(status="completed", output=out or {}, error=None, ended_at=now(),
                          duration_ms=round((time.perf_counter() - t0) * 1000, 1))
                ok = True
                break
            except HTTPException as e:
                st["error"] = f"Attempt {st['attempts']}: {e.detail}"
                break
            except Exception as e:  # noqa: BLE001 - engine records every step failure
                log.warning("workflow %s step %s failed: %s", exe["workflow"], name, e)
                st["error"] = f"Attempt {st['attempts']}: {e}"
        if not ok:
            st.update(status="failed", ended_at=now())
            exe["status"] = "failed"
            await _save(exe)
            await audit(s, f"workflow.failed:{exe['workflow']}", exe["lab"], {"execution": exe["id"], "step": name})
            return exe
        exe["current"] += 1
        await _save(exe)
    exe["status"] = "completed"
    exe["completed_at"] = now()
    await _save(exe)
    await audit(s, f"workflow.completed:{exe['workflow']}", exe["lab"], {"execution": exe["id"]})
    return exe


async def decide(s, approval_id, decision, comment, approver="Demo reviewer"):
    if decision not in ("approved", "rejected"):
        raise HTTPException(422, "decision must be approved or rejected")
    appr = await db.approvals.find_one({"session": s, "id": approval_id}, P)
    if not appr:
        raise HTTPException(404, "Approval not found")
    if appr["status"] != "pending":
        raise HTTPException(409, "Approval already decided")
    await db.approvals.update_one({"id": approval_id}, {"$set": {"status": decision, "decided_at": now(), "comment": comment, "approver": approver}})
    exe = await db.executions.find_one({"id": appr["execution_id"]}, P)
    wf = WORKFLOWS[exe["workflow"]]
    i = appr["step_index"]
    st = exe["steps"][i]
    st.update(status=decision, ended_at=now(), output={**(st["output"] or {}), "decision": decision, "comment": comment, "approver": approver})
    exe["ctx"]["last_decision"] = decision
    await audit(s, f"approval.{decision}", exe["lab"], {"approval": approval_id, "execution": exe["id"], "comment": comment})
    if decision == "rejected":
        on_reject = wf["steps"][i][2].get("on_reject")
        if on_reject:
            await on_reject(s, exe["ctx"])
        for later in exe["steps"][i + 1:]:
            later["status"] = "cancelled"
        exe["status"] = "rejected"
        await _save(exe)
        return exe
    exe["current"] = i + 1
    exe["status"] = "running"
    return await _advance(exe)


async def retry(s, exe_id):
    exe = await db.executions.find_one({"session": s, "id": exe_id}, P)
    if not exe:
        raise HTTPException(404, "Execution not found")
    if exe["status"] != "failed":
        raise HTTPException(409, "Only failed executions can be retried")
    st = exe["steps"][exe["current"]]
    st.update(status="pending", attempts=0, error=None)
    exe["status"] = "running"
    exe["ctx"].pop("inject_failure_step", None)
    await audit(s, "workflow.retry", exe["lab"], {"execution": exe_id})
    return await _advance(exe)
