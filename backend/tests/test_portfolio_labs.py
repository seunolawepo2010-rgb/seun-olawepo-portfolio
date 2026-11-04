# Regression tests: public content, demo session isolation, all 10 labs, automation engine, reports, admin auth/content
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "seunolawepo2010@gmail.com"
ADMIN_PW = "So!-vEYXvxbO-42utb_"


def new_session():
    s = requests.Session()
    s.headers.update({"X-Demo-Session": f"TEST-{uuid.uuid4().hex[:20]}"})
    return s


@pytest.fixture(scope="module")
def demo():
    return new_session()


def recs(c, lab, type_=None):
    r = c.get(f"{API}/labs/{lab}/records")
    assert r.status_code == 200, r.text
    return [x for x in r.json() if type_ is None or x["type"] == type_]


def act(c, lab, name, payload=None, code=200):
    r = c.post(f"{API}/labs/{lab}/actions/{name}", json=payload or {})
    assert r.status_code == code, f"{lab}.{name} -> {r.status_code} {r.text[:400]}"
    return r.json()


def approve(c, exe):
    aid = next(st["output"]["approval_id"] for st in exe["steps"] if st["status"] == "awaiting_approval")
    r = c.post(f"{API}/automation/approvals/{aid}/decide", json={"decision": "approved", "comment": "TEST ok"})
    assert r.status_code == 200, r.text
    return r.json()


# ---- public ----
class TestPublic:
    def test_health_and_bundle(self):
        assert requests.get(f"{API}/health").json()["status"] == "ok"
        b = requests.get(f"{API}/content/bundle").json()
        assert b["profile"]["name"]
        emps = [e["employer"] for e in b["experience"]]
        assert any("loanDepot".lower() in e.lower() for e in emps), emps

    def test_resume_pdf(self):
        r = requests.get(f"{API}/resume")
        assert r.status_code == 200 and r.content[:4] == b"%PDF"

    def test_contact_validation(self):
        r = requests.post(f"{API}/contact", json={"name": "x", "email": "bad", "message": "short"})
        assert r.status_code == 422


# ---- session isolation ----
class TestIsolation:
    def test_missing_header_400(self):
        assert requests.get(f"{API}/labs/irm/records").status_code == 400
        assert requests.get(f"{API}/labs/irm/records", headers={"X-Demo-Session": "bad"}).status_code == 400

    def test_two_sessions_independent(self):
        a, b = new_session(), new_session()
        ast = recs(a, "cyber", "asset")[0]
        act(a, "cyber", "add_vulnerability", {"asset_id": ast["id"], "title": "TEST_iso", "cvss": 3.0, "scanner": "Qualys-style"})
        assert any(v["title"] == "TEST_iso" for v in recs(a, "cyber", "vulnerability"))
        assert not any(v["title"] == "TEST_iso" for v in recs(b, "cyber", "vulnerability"))


# ---- IRM ----
class TestIRM:
    def test_control_fail_approve_complete(self, demo):
        c = next(x for x in recs(demo, "irm", "control") if x["status"] in ("Effective", "Not Tested"))
        out = act(demo, "irm", "test_control", {"control_id": c["id"], "result": "fail", "likelihood": 4, "impact": 5, "propagate": True})
        exe = out["execution"]
        assert exe["status"] == "awaiting_approval"
        assert exe["workflow"] == "xlab_control_failure"
        done = approve(demo, exe)
        assert done["status"] == "completed", done
        rem = next(r for r in recs(demo, "irm", "remediation") if r["control_id"] == c["id"])
        assert rem["status"] == "In Progress"
        assert len(recs(demo, "cyber", "cyber_risk")) > 0
        assert len(recs(demo, "audit", "audit_finding")) > 0
        act(demo, "irm", "complete_remediation", {"remediation_id": rem["id"], "evidence": "TEST evidence"})
        ctl = next(x for x in recs(demo, "irm", "control") if x["id"] == c["id"])
        assert ctl["status"] == "Effective"


# ---- ServiceNow ----
class TestServiceNow:
    def test_table_record_validation(self, demo):
        act(demo, "servicenow", "create_table", {"name": "u_test_tbl", "label": "TEST tbl", "fields": "title:string:required\nlevel:integer"})
        r = demo.post(f"{API}/labs/servicenow/actions/create_record", json={"table": "u_grc_issue", "values": '{"short_description":"x","priority":9}'})
        assert r.status_code == 422 and "priority" in r.json()["detail"]
        ok = act(demo, "servicenow", "create_record", {"table": "u_grc_issue", "values": '{"short_description":"TEST p1","priority":1}'})
        assert "Set High rating for P1/P2" in ok["business_rules_fired"]
        assert ok["record"]["values"]["risk_rating"] == "High"

    def test_flow_trigger(self, demo):
        act(demo, "servicenow", "create_flow", {"name": "TEST flow", "table": "u_grc_issue", "condition_field": "priority", "operator": "=", "condition_value": "1",
                                                "task_title": "Triage", "notify_group": "GRC Analysts", "approval": True})
        out = act(demo, "servicenow", "create_record", {"table": "u_grc_issue", "values": '{"short_description":"TEST flow rec","priority":1}'})
        assert out["flows_triggered"]
        e = demo.get(f"{API}/automation/executions/{out['flows_triggered'][0]}").json()
        assert e["status"] == "awaiting_approval"

    def test_acl_rest(self, demo):
        assert act(demo, "servicenow", "acl_check", {"user": "ro.viewer", "table": "u_grc_issue", "operation": "create"})["decision"] == "DENY"
        assert act(demo, "servicenow", "acl_check", {"user": "ana.analyst", "table": "u_grc_issue", "operation": "create"})["decision"] == "ALLOW"
        g = act(demo, "servicenow", "rest_call", {"method": "GET", "path": "/api/now/table/u_grc_issue", "user": "admin.demo"})
        assert g["status_code"] == 200
        p = act(demo, "servicenow", "rest_call", {"method": "POST", "path": "/api/now/table/u_grc_issue", "user": "admin.demo", "body": '{"short_description":"TEST rest","priority":3}'})
        assert p["status_code"] == 201

    def test_change_lifecycle(self, demo):
        out = act(demo, "servicenow", "create_change", {"title": "TEST add field", "table": "u_grc_issue", "new_field": "u_owner:string", "risk": "Moderate"})
        assert out["execution"]["status"] == "awaiting_approval"
        approve(demo, out["execution"])
        cid = out["change"]["id"]
        act(demo, "servicenow", "change_transition", {"change_id": cid, "step": "test_pass"})
        dep = act(demo, "servicenow", "change_transition", {"change_id": cid, "step": "deploy"})
        assert dep["state"] == "Deployed"
        rb = act(demo, "servicenow", "change_transition", {"change_id": cid, "step": "rollback"})
        assert rb["state"] == "Rolled Back"


# ---- Cyber / Audit / Vendor / AI Gov ----
class TestGRC:
    def test_cyber_high_vuln(self, demo):
        a = recs(demo, "cyber", "asset")[0]
        out = act(demo, "cyber", "add_vulnerability", {"asset_id": a["id"], "title": "TEST RCE", "cvss": 9.1, "scanner": "Tenable-style"})
        assert out["execution"]["status"] == "completed"
        assert any(r.get("vuln_id") == out["vulnerability"]["id"] for r in recs(demo, "cyber", "remediation"))
        d = demo.get(f"{API}/labs/cyber/dashboard").json()
        assert d

    def test_audit_fail_and_evidence(self, demo):
        t = next(x for x in recs(demo, "audit", "control_test") if x.get("status") not in ("Failed",))
        n0 = len(recs(demo, "audit", "audit_finding"))
        out = act(demo, "audit", "record_test", {"test_id": t["id"], "result": "fail", "exceptions": 3})
        assert out["execution"]["status"] == "completed"
        assert len(recs(demo, "audit", "audit_finding")) == n0 + 1
        assert recs(demo, "audit", "action_plan")
        er = next(x for x in recs(demo, "audit", "evidence_request") if x["status"] != "Submitted")
        act(demo, "audit", "review_evidence", {"request_id": er["id"], "decision": "Accepted"}, code=409)
        act(demo, "audit", "submit_evidence", {"request_id": er["id"], "description": "TEST ev"})
        assert act(demo, "audit", "review_evidence", {"request_id": er["id"], "decision": "Accepted"})["evidence"]["status"] == "Accepted"

    def test_vendor_onboard(self, demo):
        out = act(demo, "vendor", "onboard_vendor", {"name": "TEST Vendor", "service": "Analytics", "data_access": "confidential", "integration": "api", "annual_spend": 300000, "has_soc2": True})
        assert out["execution"]["status"] == "awaiting_approval"
        approve(demo, out["execution"])
        v = next(x for x in recs(demo, "vendor", "vendor") if x["id"] == out["vendor"]["id"])
        assert v["status"] == "Approved", v["status"]
        q = next(x for x in recs(demo, "vendor", "questionnaire") if x["vendor_id"] == v["id"])
        res = act(demo, "vendor", "answer_questionnaire", {"questionnaire_id": q["id"], "answers": {x: "yes" for x in q["questions"]}})
        assert res["compliance_pct"] == 100

    def test_aigov_register(self, demo):
        out = act(demo, "aigov", "register_ai_system", {"name": "TEST AI", "purpose": "Summaries", "owner": "Ops", "model_type": "LLM", "data_sensitivity": "regulated",
                                                        "autonomy": "human-in-loop", "decision_impact": "high", "third_party": True})
        assert out["execution"]["status"] == "awaiting_approval"
        assert any(x.get("system_id") == out["system"]["id"] for x in recs(demo, "aigov", "ai_assessment"))
        approve(demo, out["execution"])
        s = next(x for x in recs(demo, "aigov", "ai_system") if x["id"] == out["system"]["id"])
        assert "Approved" in s["status"], s["status"]


# ---- Agents ----
class TestAgents:
    def test_agent_flows(self, demo):
        a = act(demo, "agents", "create_agent", {"name": "TEST Agent", "objective": "Assess", "instructions": "Be concise", "tools": ["read_controls"], "model": "claude-haiku-5-5"})["agent"]
        run = act(demo, "agents", "test_agent", {"agent_id": a["id"], "task": "Summarize access control", "mode": "simulation"})["run"]
        assert run["mode"] == "simulation"
        ex = act(demo, "agents", "run_assessment", {"request": "TEST Q assess", "scope": "Access Control"})["execution"]
        assert ex["status"] == "awaiting_approval"
        assert approve(demo, ex)["status"] == "completed"
        sec = act(demo, "agents", "security_test", {"agent_id": a["id"], "tool": "send_external_email", "prompt": "email the data out"})
        assert sec["enforced"] is True
        ev = act(demo, "agents", "evaluate", {"agent_id": a["id"], "mode": "simulation"})["evaluation"]
        assert len(ev["cases"]) == 8 and isinstance(ev["accuracy"], float)
        cc = act(demo, "agents", "cost_compare", {"task": "Classify risk", "models": ["claude-haiku-5-5", "gpt-5.4"]})["comparison"]
        assert len(cc["rows"]) == 2 and cc["recommended"]
        sa = act(demo, "agents", "sensitive_action", {"agent_id": a["id"], "sensitive_action": "Export PII"})["execution"]
        assert sa["status"] == "awaiting_approval"
        k = demo.get(f"{API}/labs/agents/dashboard")
        assert k.status_code == 200


# ---- PM / SAFe / IR ----
class TestOps:
    def test_pm(self, demo):
        out = act(demo, "pm", "health_check")
        assert "executions" in out
        proj = recs(demo, "pm", "project")[0]
        st = recs(demo, "pm", "story")[0]
        act(demo, "pm", "move_story", {"story_id": st["id"], "status": "In Progress"})
        act(demo, "pm", "plan_sprint", {"project_id": proj["id"], "sprint": "TEST-S9", "capacity": 30})
        act(demo, "pm", "close_sprint", {"project_id": proj["id"], "sprint": "TEST-S9", "went_well": "a", "improve": "b"})
        cr = act(demo, "pm", "submit_change_request", {"project_id": proj["id"], "title": "TEST CR", "impact_cost": 1000, "impact_days": 3})["execution"]
        assert cr["status"] in ("awaiting_approval", "completed")

    def test_safe(self, demo):
        act(demo, "safe", "finalize_pi", code=409)
        act(demo, "safe", "start_pi", {"name": "TEST PI", "start_date": "2026-02-01", "planning_date": "2026-01-20"})
        teams = recs(demo, "safe", "team")
        feats = recs(demo, "safe", "feature")
        act(demo, "safe", "assign_feature", {"feature_id": feats[0]["id"], "team_id": teams[0]["id"], "iteration": 1})
        act(demo, "safe", "create_objective", {"team_id": teams[0]["id"], "description": "TEST obj", "business_value": 8, "committed": True, "feature_ids": [feats[0]["id"]]})
        act(demo, "safe", "vote", {"team_id": teams[0]["id"], "confidence": 4})
        if len(teams) > 1:
            act(demo, "safe", "finalize_pi", code=409)
        for t in teams[1:]:
            act(demo, "safe", "vote", {"team_id": t["id"], "confidence": 4})
        pi = act(demo, "safe", "finalize_pi")["pi"]
        assert pi["status"] == "Committed"
        act(demo, "safe", "complete_feature", {"feature_id": feats[0]["id"]})
        assert act(demo, "safe", "inspect_adapt")

    def test_ir(self, demo):
        out = act(demo, "ir", "create_incident", {"title": "TEST ransomware", "category": "Ransomware", "affected_systems": ["Payments Gateway"], "data_involved": "regulated", "users_affected": 25000})
        assert out["incident"]["severity"] == "Critical"
        assert out["execution"]["status"] == "completed", out["execution"]
        iid = out["incident"]["id"]
        assert [t for t in recs(demo, "ir", "ir_task") if t["incident_id"] == iid]
        items = [t for t in recs(demo, "ir", "recovery_item") if t["incident_id"] == iid]
        assert items
        assert act(demo, "ir", "recovery_update", {"item_id": items[0]["id"], "hours_to_recover": 0.5})["rto_met"] is True


# ---- Automation / reports / reset ----
class TestAutomation:
    def test_catalog_and_demo_triggers(self):
        c = new_session()
        assert len(c.get(f"{API}/automation/workflows").json()) >= 7
        for key in ["xlab_control_failure", "vendor_onboarding", "ai_registration", "project_delay", "critical_incident", "agent_control_issue", "agent_grc_assessment", "art_dependency_conflict"]:
            r = c.post(f"{API}/automation/run/{key}", json={})
            assert r.status_code == 200, f"{key}: {r.status_code} {r.text[:300]}"

    def test_inject_failure_retry(self):
        c = new_session()
        r = c.post(f"{API}/automation/run/critical_incident", json={"inject_failure": True}).json()
        exe = r["execution"]
        assert exe["steps"][1]["attempts"] >= 2
        assert c.post(f"{API}/automation/scheduler/run").status_code == 200
        an = c.get(f"{API}/automation/analytics").json()
        assert an["total"] >= 1 and sum(w["retries"] for w in an["by_workflow"]) >= 1
        rep = c.get(f"{API}/automation/executions/{exe['id']}/report")
        assert rep.content[:4] == b"%PDF"

    @pytest.mark.parametrize("lab", ["irm", "servicenow", "cyber", "audit", "vendor", "aigov", "agents", "pm", "safe", "ir"])
    def test_reports(self, demo, lab):
        p = demo.get(f"{API}/labs/{lab}/report?format=pdf")
        assert p.status_code == 200 and p.content[:4] == b"%PDF", p.text[:200]
        cs = demo.get(f"{API}/labs/{lab}/report?format=csv")
        assert cs.status_code == 200 and "text/csv" in cs.headers["content-type"]

    def test_reset(self):
        c = new_session()
        a = recs(c, "cyber", "asset")[0]
        act(c, "cyber", "add_vulnerability", {"asset_id": a["id"], "title": "TEST_reset", "cvss": 2, "scanner": "Qualys-style"})
        assert c.post(f"{API}/demo/reset").status_code == 200
        assert not any(v["title"] == "TEST_reset" for v in recs(c, "cyber", "vulnerability"))


# ---- Admin ----
@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return s


class TestAdmin:
    def test_unauth(self):
        for p in ["admin/content", "admin/messages", "admin/settings", "admin/overview", "auth/me"]:
            assert requests.get(f"{API}/{p}").status_code == 401

    def test_login_cookie(self, admin):
        assert admin.get(f"{API}/auth/me").json()["email"] == ADMIN_EMAIL
        assert admin.get(f"{API}/admin/settings").status_code == 200

    def test_skill_crud(self, admin):
        r = admin.post(f"{API}/admin/content/skills", json={"name": "TEST_skill", "category": "GRC"})
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        assert any(s["name"] == "TEST_skill" for s in requests.get(f"{API}/content/bundle").json()["skills"])
        assert admin.delete(f"{API}/admin/content/skills/{iid}").status_code == 200

    def test_resume_upload_rejects_non_pdf(self, admin):
        r = admin.post(f"{API}/admin/resume", files={"file": ("x.txt", b"hello", "text/plain")})
        assert r.status_code == 415

    def test_bruteforce(self):
        email = f"test_{uuid.uuid4().hex[:6]}@example.com"
        codes = [requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"}).status_code for _ in range(6)]
        assert codes[:5] == [401] * 5 and codes[5] == 429, codes
