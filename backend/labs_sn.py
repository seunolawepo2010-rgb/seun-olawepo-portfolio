import csv
import io
import json
import re
import time
from fastapi import HTTPException
from core import action, kpi, SCHEMAS, ins, upd, get, find, bulk, validate, audit, by_status, in_days, now
import engine
from engine import APPROVAL

LAB = "servicenow"
FTYPES = ["string", "integer", "choice", "date", "boolean"]
OPS = ["=", "!=", ">", ">=", "<", "<=", "contains"]
ROLES = {"admin.demo": ["admin"], "ana.analyst": ["grc_analyst"], "rev.reviewer": ["grc_reviewer"], "ro.viewer": ["read_only"]}
SCHEMAS[LAB] = {}


def default_acls(table):
    return [{"table": table, "operation": "read", "roles": ["admin", "grc_analyst", "grc_reviewer", "read_only"]},
            {"table": table, "operation": "create", "roles": ["admin", "grc_analyst"]},
            {"table": table, "operation": "write", "roles": ["admin", "grc_analyst", "grc_reviewer"]},
            {"table": table, "operation": "delete", "roles": ["admin"]}]


async def seed_servicenow(s):
    await bulk(s, LAB, "sn_user", [{"user_name": u, "roles": r, "group": g, "active": True} for (u, r), g in
                                   zip(ROLES.items(), ["Platform Admins", "GRC Analysts", "GRC Reviewers", "Auditors (read)"])])
    await bulk(s, LAB, "sn_group", [{"name": g, "manager": m} for g, m in [("Platform Admins", "admin.demo"), ("GRC Analysts", "ana.analyst"), ("GRC Reviewers", "rev.reviewer"), ("Auditors (read)", "ro.viewer")]])
    await bulk(s, LAB, "sn_role", [{"name": r, "description": d} for r, d in [("admin", "Full platform administration"), ("grc_analyst", "Create & update GRC records"),
                                                                              ("grc_reviewer", "Review & approve GRC records"), ("read_only", "Read GRC records")]])
    await bulk(s, LAB, "sn_table", [{"name": "u_grc_issue", "label": "GRC Issue", "version": 1, "fields": [
        {"name": "short_description", "type": "string", "required": True, "max": 160},
        {"name": "priority", "type": "integer", "required": True, "min": 1, "max": 5},
        {"name": "state", "type": "choice", "required": False, "choices": ["New", "In Review", "Closed"]},
        {"name": "risk_rating", "type": "choice", "required": False, "choices": ["Low", "Medium", "High", "Critical"]}]}])
    await bulk(s, LAB, "sn_acl", default_acls("u_grc_issue"))
    await bulk(s, LAB, "sn_rule", [{"table": "u_grc_issue", "name": "Set High rating for P1/P2", "when": "before", "condition_field": "priority", "operator": "<=",
                                    "condition_value": "2", "set_field": "risk_rating", "set_value": "High", "active": True}])
    await bulk(s, LAB, "sn_job", [{"name": "Nightly overdue remediation check", "schedule": "Daily 02:00 UTC", "script": "automation scheduler", "active": True},
                                  {"name": "Weekly vendor review reminder", "schedule": "Mon 08:00 UTC", "script": "vendor monitor", "active": True}])
    await bulk(s, LAB, "sn_itsm", [{"kind": "Incident", "number": "INC0010001", "short_description": "VPN outage for remote staff", "priority": 2, "state": "In Progress"},
                                   {"kind": "Problem", "number": "PRB0040001", "short_description": "Recurring VPN gateway memory leak", "priority": 3, "state": "Root Cause Analysis"},
                                   {"kind": "Catalog Item", "number": "CAT-ACCESS", "short_description": "Request privileged access (approval required)", "priority": 4, "state": "Published"}])


def cmp(a, op, b):
    try:
        a_n, b_n = float(a), float(b)
    except (TypeError, ValueError):
        a_n, b_n = None, None
    if op == "contains":
        return str(b).lower() in str(a).lower()
    if op in ("=", "!="):
        eq = (a_n == b_n) if a_n is not None else str(a) == str(b)
        return eq if op == "=" else not eq
    if a_n is None:
        return False
    return {">": a_n > b_n, ">=": a_n >= b_n, "<": a_n < b_n, "<=": a_n <= b_n}[op]


async def table_by_name(s, name):
    t = await find(s, LAB, "sn_table", name=name)
    if not t:
        raise HTTPException(404, f"Table '{name}' not found")
    return t[0]


async def acl_eval(s, user, table, op):
    roles = ROLES.get(user)
    if roles is None:
        raise HTTPException(422, f"Unknown user {user}")
    acls = await find(s, LAB, "sn_acl", table=table, operation=op)
    matched = [a for a in acls if set(a["roles"]) & set(roles)]
    allowed = "admin" in roles or bool(matched)
    await ins(s, LAB, "acl_log", user=user, roles=roles, table=table, operation=op, decision="ALLOW" if allowed else "DENY",
              rule=f"{table}.{op} requires one of {acls[0]['roles'] if acls else '[no ACL – deny by default]'}")
    return allowed, roles, acls


def validate_values(table, values):
    out, errors = {}, []
    for f in table["fields"]:
        v = values.get(f["name"])
        if v in (None, ""):
            if f.get("required"):
                errors.append(f"{f['name']} is mandatory")
            continue
        if f["type"] == "integer":
            try:
                v = int(v)
                if ("min" in f and v < f["min"]) or ("max" in f and v > f["max"]):
                    errors.append(f"{f['name']} must be between {f.get('min')} and {f.get('max')}")
            except (TypeError, ValueError):
                errors.append(f"{f['name']} must be an integer")
        elif f["type"] == "choice" and v not in f.get("choices", []):
            errors.append(f"{f['name']} must be one of {f.get('choices')}")
        elif f["type"] == "boolean":
            v = v in (True, "true", "1", 1)
        elif f["type"] == "string":
            v = str(v)[: f.get("max", 255)]
        out[f["name"]] = v
    unknown = set(values) - {f["name"] for f in table["fields"]}
    if unknown:
        errors.append(f"Unknown fields: {', '.join(sorted(unknown))}")
    if errors:
        raise HTTPException(422, "Data policy violation: " + "; ".join(errors))
    return out


async def insert_record(s, table, values, user="admin.demo"):
    allowed, _, _ = await acl_eval(s, user, table["name"], "create")
    if not allowed:
        raise HTTPException(403, f"ACL denied: {user} cannot create on {table['name']}")
    vals = validate_values(table, values)
    fired = []
    for r in await find(s, LAB, "sn_rule", table=table["name"], active=True):
        if cmp(vals.get(r["condition_field"]), r["operator"], r["condition_value"]):
            vals[r["set_field"]] = r["set_value"]
            fired.append(r["name"])
    n = len(await find(s, LAB, "sn_record", table=table["name"])) + 1
    rec = await ins(s, LAB, "sn_record", table=table["name"], number=f"{table['name'].upper()[2:8]}{n:05d}", values=vals, created_by=user, rules_fired=fired)
    exes = []
    for fl in await find(s, LAB, "sn_flow", table=table["name"], active=True):
        if cmp(vals.get(fl["condition_field"]), fl["operator"], fl["condition_value"]):
            exes.append((await engine.start(s, "sn_flow", {"flow_id": fl["id"], "record_id": rec["id"], "number": rec["number"], "approval": fl["approval"], "_lab": LAB}, f"flow:{fl['name']}"))["id"])
    return rec, fired, exes


@action(LAB, "create_table")
async def a_table(s, p):
    d = validate({"name": ("str", True, 40), "label": ("str", True, 80), "fields": ("str", True, 4000)}, p)
    if not re.match(r"^u_[a-z0-9_]{2,30}$", d["name"]):
        raise HTTPException(422, "Table name must match u_[a-z0-9_] (custom table prefix)")
    if await find(s, LAB, "sn_table", name=d["name"]):
        raise HTTPException(409, "Table already exists")
    fields = []
    for line in d["fields"].splitlines():
        parts = [x.strip() for x in line.split(":")]
        if not parts[0]:
            continue
        if not re.match(r"^[a-z][a-z0-9_]{1,30}$", parts[0]) or len(parts) < 2 or parts[1] not in FTYPES:
            raise HTTPException(422, f"Invalid field line '{line}'. Use name:type[:required][:choice1|choice2]")
        f = {"name": parts[0], "type": parts[1], "required": len(parts) > 2 and parts[2] == "required"}
        if parts[1] == "choice":
            f["choices"] = parts[3].split("|") if len(parts) > 3 else ["Option A", "Option B"]
        fields.append(f)
    t = await ins(s, LAB, "sn_table", name=d["name"], label=d["label"], fields=fields, version=1)
    for a in default_acls(d["name"]):
        await ins(s, LAB, "sn_acl", **a)
    await audit(s, "sn.table.created", LAB, {"table": d["name"]})
    return {"table": t, "message": f"Table {d['name']} created with {len(fields)} fields and 4 default ACLs"}


@action(LAB, "create_record")
async def a_record(s, p):
    d = validate({"table": ("str", True, 40), "values": ("str", True, 4000), "user": ("choice", False, list(ROLES))}, p)
    try:
        values = json.loads(d["values"])
        assert isinstance(values, dict)
    except (ValueError, AssertionError):
        raise HTTPException(422, "values must be a JSON object")
    rec, fired, exes = await insert_record(s, await table_by_name(s, d["table"]), values, d.get("user", "admin.demo"))
    return {"record": rec, "business_rules_fired": fired, "flows_triggered": exes}


@action(LAB, "create_business_rule")
async def a_rule(s, p):
    d = validate({"table": ("str", True, 40), "name": ("str", True, 100), "when": ("choice", True, ["before", "after"]), "condition_field": ("str", True, 40),
                  "operator": ("choice", True, OPS), "condition_value": ("str", True, 100), "set_field": ("str", True, 40), "set_value": ("str", True, 100)}, p)
    t = await table_by_name(s, d["table"])
    names = {f["name"] for f in t["fields"]}
    if d["condition_field"] not in names or d["set_field"] not in names:
        raise HTTPException(422, f"Fields must exist on {d['table']}: {sorted(names)}")
    return {"rule": await ins(s, LAB, "sn_rule", active=True, **d), "message": "Declarative business rule active (no arbitrary script execution)"}


@action(LAB, "acl_check")
async def a_acl(s, p):
    d = validate({"user": ("choice", True, list(ROLES)), "table": ("str", True, 40), "operation": ("choice", True, ["create", "read", "write", "delete"])}, p)
    allowed, roles, acls = await acl_eval(s, d["user"], d["table"], d["operation"])
    return {"decision": "ALLOW" if allowed else "DENY", "user_roles": roles, "acl_roles": acls[0]["roles"] if acls else []}


async def st_flow_task(s, ctx):
    fl = await get(s, ctx["flow_id"])
    t = await ins(s, LAB, "sn_task", title=f"{fl['task_title']} ({ctx['number']})", record_id=ctx["record_id"], assignment_group=fl["notify_group"], state="Open",
                  sla_due=in_days(2), sla_rule="P2 = 2 business days")
    ctx["task_id"], ctx["group"] = t["id"], fl["notify_group"]
    return {"task_id": t["id"], "assignment_group": fl["notify_group"]}


async def st_flow_notify(s, ctx):
    await ins(s, LAB, "sn_notification", to_group=ctx["group"], subject=f"Task assigned for {ctx['number']}", delivery="In-app simulation – no email sent")
    return {"notification": "logged (simulated, not sent)"}


engine.workflow("sn_flow", "Flow Designer-style Flow", LAB, "Record inserted matching flow condition", "Trigger → condition → create task (SLA) → optional approval → notification.",
                [("Create task with SLA", st_flow_task, {}), ("Approval (if configured)", APPROVAL, {"title": lambda c: f"Approve flow action for {c['number']}", "role": "GRC Reviewer",
                                                                                                    "skip_if": lambda c: not c.get("approval"), "skip_reason": "Flow has no approval step"}),
                 ("Send notification", st_flow_notify, {})])


@action(LAB, "create_flow")
async def a_flow(s, p):
    d = validate({"name": ("str", True, 100), "table": ("str", True, 40), "condition_field": ("str", True, 40), "operator": ("choice", True, OPS), "condition_value": ("str", True, 100),
                  "task_title": ("str", True, 120), "notify_group": ("str", True, 80), "approval": ("bool", False, None)}, p)
    await table_by_name(s, d["table"])
    d.setdefault("approval", False)
    return {"flow": await ins(s, LAB, "sn_flow", active=True, version=1, **d), "message": "Flow published. Insert a matching record to trigger it."}


@action(LAB, "rest_call")
async def a_rest(s, p):
    d = validate({"method": ("choice", True, ["GET", "POST", "PATCH", "DELETE"]), "path": ("str", True, 200), "body": ("str", False, 4000), "user": ("choice", True, list(ROLES))}, p)
    t0 = time.perf_counter()
    m = re.match(r"^/api/now/table/(u_[a-z0-9_]+)(?:/([a-z0-9]+))?$", d["path"])
    status, resp = 200, None
    try:
        if not m:
            raise HTTPException(400, "Path must be /api/now/table/{table}[/{sys_id}]")
        table = await table_by_name(s, m.group(1))
        op = {"GET": "read", "POST": "create", "PATCH": "write", "DELETE": "delete"}[d["method"]]
        if d["method"] != "POST":
            allowed, _, _ = await acl_eval(s, d["user"], table["name"], op)
            if not allowed:
                raise HTTPException(403, f"ACL denied {op} for {d['user']}")
        if d["method"] == "GET":
            rows = await find(s, LAB, "sn_record", table=table["name"])
            resp = {"result": [{"sys_id": r["id"], "number": r["number"], **r["values"]} for r in rows if not m.group(2) or r["id"] == m.group(2)]}
        elif d["method"] == "POST":
            rec, fired, _ = await insert_record(s, table, json.loads(d.get("body") or "{}"), d["user"])
            status, resp = 201, {"result": {"sys_id": rec["id"], "number": rec["number"], **rec["values"]}, "business_rules_fired": fired}
        else:
            if not m.group(2):
                raise HTTPException(400, "sys_id required")
            rec = await get(s, m.group(2), "sn_record")
            if d["method"] == "DELETE":
                await upd(s, rec["id"], type="sn_record_deleted")
                status, resp = 204, {}
            else:
                vals = validate_values(table, {**rec["values"], **json.loads(d.get("body") or "{}")})
                await upd(s, rec["id"], values=vals)
                resp = {"result": {"sys_id": rec["id"], **vals}}
    except HTTPException as e:
        status, resp = e.status_code, {"error": {"message": e.detail}}
    except ValueError:
        status, resp = 400, {"error": {"message": "Body must be valid JSON"}}
    ms = round((time.perf_counter() - t0) * 1000, 1)
    await ins(s, LAB, "api_log", method=d["method"], path=d["path"], user=d["user"], status_code=status, latency_ms=ms)
    return {"status_code": status, "latency_ms": ms, "response": resp, "mode": "Simulated ServiceNow-style Table API (not a real instance)"}


@action(LAB, "import_csv")
async def a_import(s, p):
    d = validate({"table": ("str", True, 40), "csv_text": ("str", True, 8000)}, p)
    table = await table_by_name(s, d["table"])
    names = {f["name"] for f in table["fields"]}
    ok, errs = 0, []
    for i, row in enumerate(csv.DictReader(io.StringIO(d["csv_text"])), 1):
        mapped = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}
        mapped = {k: v for k, v in mapped.items() if k in names}
        try:
            await insert_record(s, table, mapped)
            ok += 1
        except HTTPException as e:
            errs.append(f"Row {i}: {e.detail}")
    await ins(s, LAB, "import_set", table=d["table"], inserted=ok, errors=len(errs), transform_map="auto: header → field name")
    return {"inserted": ok, "errors": errs}


async def st_ch_assess(s, ctx):
    c = await get(s, ctx["change_id"])
    await upd(s, c["id"], state="Assess")
    return {"risk": c["risk"], "cab_required": c["risk"] != "Low"}


async def st_ch_sched(s, ctx):
    await upd(s, ctx["change_id"], state="Scheduled")
    return {"state": "Scheduled"}


async def rej_ch(s, ctx):
    await upd(s, ctx["change_id"], state="Cancelled")


engine.workflow("sn_change", "Change Request → CAB Approval", LAB, "Change submitted", "Assess change risk, route CAB approval, schedule for testing.",
                [("Assess change", st_ch_assess, {}), ("CAB approval", APPROVAL, {"title": lambda c: f"CAB: {c['title']}", "role": "Change Advisory Board", "on_reject": rej_ch}),
                 ("Schedule for testing", st_ch_sched, {})])


@action(LAB, "create_change")
async def a_change(s, p):
    d = validate({"title": ("str", True, 150), "table": ("str", True, 40), "new_field": ("str", True, 120), "risk": ("choice", True, ["Low", "Moderate", "High"])}, p)
    await table_by_name(s, d["table"])
    c = await ins(s, LAB, "sn_change", number=f"CHG{len(await find(s, LAB, 'sn_change')) + 1:05d}", state="New", **d)
    return {"change": c, "execution": await engine.start(s, "sn_change", {"change_id": c["id"], "title": d["title"], "_lab": LAB}, "change_submitted")}


@action(LAB, "change_transition")
async def a_ch_tr(s, p):
    d = validate({"change_id": ("str", True, 40), "step": ("choice", True, ["test_pass", "test_fail", "deploy", "rollback"])}, p)
    c = await get(s, d["change_id"], "sn_change")
    need = {"test_pass": "Scheduled", "test_fail": "Scheduled", "deploy": "Tested", "rollback": "Deployed"}[d["step"]]
    if c["state"] != need:
        raise HTTPException(409, f"Change must be '{need}' (current: {c['state']})")
    if d["step"].startswith("test"):
        st = "Tested" if d["step"] == "test_pass" else "Scheduled"
        await upd(s, c["id"], state=st, test_result=d["step"])
        return {"state": st}
    t = await table_by_name(s, c["table"])
    if d["step"] == "deploy":
        parts = c["new_field"].split(":")
        if len(parts) < 2 or parts[1] not in FTYPES:
            raise HTTPException(422, "new_field must be name:type")
        us = await ins(s, LAB, "update_set", change=c["number"], table=t["name"], from_version=t["version"], to_version=t["version"] + 1, snapshot=t["fields"], state="Committed")
        await upd(s, t["id"], fields=t["fields"] + [{"name": parts[0], "type": parts[1], "required": False, "choices": ["Yes", "No"] if parts[1] == "choice" else None}], version=t["version"] + 1)
        await upd(s, c["id"], state="Deployed", update_set=us["id"])
        return {"state": "Deployed", "table_version": t["version"] + 1}
    us = await get(s, c["update_set"])
    await upd(s, t["id"], fields=us["snapshot"], version=us["from_version"])
    await upd(s, us["id"], state="Backed Out")
    await upd(s, c["id"], state="Rolled Back")
    return {"state": "Rolled Back", "table_version": us["from_version"]}


@kpi(LAB)
async def k_sn(s):
    acl = await find(s, LAB, "acl_log")
    api = await find(s, LAB, "api_log")
    ch = await find(s, LAB, "sn_change")
    return {"kpis": [{"label": "Custom tables", "value": len(await find(s, LAB, "sn_table"))}, {"label": "Records", "value": len(await find(s, LAB, "sn_record"))},
                     {"label": "ACL denials", "value": sum(1 for x in acl if x["decision"] == "DENY")}, {"label": "API calls", "value": len(api)},
                     {"label": "Deployments", "value": sum(1 for x in ch if x["state"] in ("Deployed", "Rolled Back"))}],
            "charts": [{"title": "ACL decisions", "data": by_status(acl, "decision")}, {"title": "API status codes", "data": by_status(api, "status_code")}]}
