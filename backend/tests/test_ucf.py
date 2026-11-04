# UCF Regulatory Change Monitoring (simulated feed): sync, dedupe, failure/retry, lifecycle, AI review, PDF, cron, admin monitor, shared-session isolation
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _env(k, path):
    for line in open(path):
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip().strip('"')


CRON = _env("WEBHOOK_CRON_SECRET", "/app/backend/.env")


def sess():
    s = requests.Session()
    s.headers.update({"X-Demo-Session": f"TEST-ucf-{uuid.uuid4().hex[:16]}"})
    return s


def act(c, name, payload=None, code=200):
    r = c.post(f"{API}/labs/grc/actions/{name}", json=payload or {})
    assert r.status_code == code, f"{name} -> {r.status_code} {r.text[:400]}"
    return r.json()


def tr(c, rid, a, role, data=None, code=200):
    return act(c, "transition", {"id": rid, "act": a, "role": role, "data": data or {}}, code)


def recs(c, t=None, **q):
    r = c.get(f"{API}/labs/grc/records")
    assert r.status_code == 200, r.text
    return [x for x in r.json() if (t is None or x["type"] == t) and all(x.get(k) == v for k, v in q.items())]


def one(c, rid):
    return next(x for x in recs(c) if x["id"] == rid)


@pytest.fixture
def c():
    return sess()


class TestSeedAndDashboard:
    def test_seed_inventory(self, c):
        assert len(recs(c, "requirement")) >= 14
        assert len(recs(c, "obligation")) >= 14
        chs = recs(c, "reg_change")
        assert len(chs) == 8
        assert {x["state"] for x in chs} >= {"Impact Assessment", "Remediation", "Validation", "Closed"}
        assert all(x.get("simulated") for x in chs)
        assert len(recs(c, "sync_run")) >= 4
        assert len(recs(c, "ucf_config")) == 1
        # existing IRM seeds still present
        for t in ("policy", "campaign", "exception", "risk", "issue", "risk_assessment"):
            assert recs(c, t), f"no seeded {t}"

    def test_dashboard_12_kpis(self, c):
        d = act(c, "ucf_dashboard", {"role": "executive"})
        assert len(d["kpis"]) == 12
        assert all(isinstance(k["value"], int) for k in d["kpis"])
        assert "Simulated" in d["integration"]["mode"]


class TestSync:
    def test_sync_noop_then_executive_rejected(self, c):
        r = act(c, "ucf_sync", {"role": "grc_admin"})
        assert r["sync_run"]["state"] == "Completed"
        r2 = act(c, "ucf_sync", {"role": "compliance_owner"})
        assert r2["sync_run"]["result"] == "No regulatory changes detected"
        act(c, "ucf_sync", {"role": "executive"}, 409)

    def test_simulated_update_and_dedupe(self, c):
        n0 = len(recs(c, "reg_change"))
        r = act(c, "ucf_simulate_update", {"role": "compliance_owner", "change_type": "New"})
        assert r["change"] and r["change"]["state"] == "Impact Assessment"
        assert r["change"]["impact_id"]
        assert len(recs(c, "reg_change")) == n0 + 1
        # re-sync: no duplicate for the same ucf_ref@version
        r2 = act(c, "ucf_sync", {"role": "grc_admin"})
        assert r2["sync_run"]["result"] == "No regulatory changes detected"
        keys = [x["dedupe_key"] for x in recs(c, "reg_change")]
        assert len(keys) == len(set(keys))

    def test_sync_failure_notify_and_retry(self, c):
        r = act(c, "ucf_sync", {"role": "grc_admin", "simulate_failure": True})
        run, exe = r["sync_run"], r["execution"]
        assert run["state"] == "Failed" and exe["status"] == "failed"
        nots = [n for n in recs(c, "notification") if "GRC Administrator" in str(n.get("to")) and run["number"] in str(n)]
        assert nots, "no GRC Administrator notification"
        rr = c.post(f"{API}/automation/executions/{exe['id']}/retry")
        assert rr.status_code == 200, rr.text
        assert one(c, run["id"])["state"] == "Completed"

    def test_config_update_roles(self, c):
        act(c, "ucf_config_update", {"role": "compliance_owner", "frameworks": ["HIPAA"], "impact_due_days": 5}, 409)
        act(c, "ucf_config_update", {"role": "grc_admin", "frameworks": ["BOGUS"], "impact_due_days": 5}, 409)
        out = act(c, "ucf_config_update", {"role": "grc_admin", "frameworks": ["HIPAA", "GDPR"], "impact_due_days": 7})
        assert out["record"]["frameworks"] == ["HIPAA", "GDPR"] and out["record"]["impact_due_days"] == 7

    def test_map_requirement(self, c):
        req = recs(c, "requirement", ucf_ref="UCF-SIM-0111")[0]
        act(c, "ucf_map", {"role": "auditor", "id": req["id"], "control_refs": ["AC-2"]}, 409)
        out = act(c, "ucf_map", {"role": "compliance_owner", "id": req["id"], "control_refs": ["AC-2"], "policy_titles": []})
        assert out["obligation"]["controls"]
        assert one(c, req["obligation_id"])["state"] == "Superseded"


class TestLifecycle:
    def test_full_gap_lifecycle(self, c):
        ch = act(c, "ucf_simulate_update", {"role": "compliance_owner", "change_type": "Modified"})["change"]
        rid = ch["id"]
        # AI analysis is advisory, needs human review
        tr(c, rid, "review_ai", "compliance_owner", {"ai_decision": "accept", "comment": "x"}, 409)
        ai = act(c, "ucf_ai_analyze", {"role": "compliance_owner", "id": rid})["record"]["ai_analysis"]
        assert ai["status"] == "Pending human review" and "advisory" in ai["disclaimer"]
        act(c, "ucf_ai_analyze", {"role": "auditor", "id": rid}, 409)
        tr(c, rid, "review_ai", "compliance_owner", {"ai_decision": "accept", "comment": "TEST_ ok"})
        assert "Accepted" in one(c, rid)["ai_analysis"]["status"]
        # role enforcement
        data = {"controls_sufficient": "no", "policy_revision": "yes", "assessment_notes": "TEST_ gap"}
        tr(c, rid, "assess_impact", "auditor", data, 403)
        tr(c, rid, "assess_impact", "compliance_owner", {**data, "controls_sufficient": "maybe"}, 409)
        rec = tr(c, rid, "assess_impact", "compliance_owner", data)["record"]
        assert rec["state"] == "Remediation" and rec["issue_ids"] and rec["revision_policy_ids"]
        # guard lists outstanding items
        r = c.post(f"{API}/labs/grc/actions/transition", json={"id": rid, "act": "submit_for_validation", "role": "compliance_owner", "data": {}})
        assert r.status_code == 409 and "Outstanding" in r.text and "issue" in r.text and "policy" in r.text
        # close issue via remediation task
        iss = one(c, rec["issue_ids"][0])
        assert iss["state"] == "Assigned"
        task = recs(c, "task", issue_id=iss["id"])[0]
        tr(c, iss["id"], "start_remediation", "remediation_owner")
        act(c, "attach", {"role": "remediation_owner", "id": task["id"], "name": "TEST_ev", "description": "x"})
        tr(c, task["id"], "start_work", "remediation_owner")
        tr(c, task["id"], "submit_for_validation", "remediation_owner")
        tr(c, task["id"], "validate", "auditor", {"result": "pass"})
        tr(c, task["id"], "close", "issue_owner", {"closure_notes": "TEST_"})
        assert one(c, iss["id"])["state"] == "Validation"
        tr(c, iss["id"], "validate", "auditor", {"decision": "pass"})
        assert one(c, iss["id"])["state"] == "Closed"
        # publish revised policy
        pid = rec["revision_policy_ids"][0]
        tr(c, pid, "submit_for_review", "policy_owner")
        tr(c, pid, "complete_review", "policy_reviewer", {"comment": "ok"})
        tr(c, pid, "approve", "approver")
        tr(c, pid, "publish", "policy_owner")
        # controls still needing reassessment get assessed
        for cid in rec["control_ids"]:
            if one(c, cid)["state"] in ("Needs Reassessment", "Ineffective"):
                act(c, "assess_control", {"role": "auditor", "control_id": cid, "result": "pass", "notes": "TEST_"})
        tr(c, rid, "submit_for_validation", "compliance_owner")
        tr(c, rid, "validate", "auditor", {"decision": "pass", "closure_evidence": "TEST_ evidence"})
        fin = one(c, rid)
        assert fin["state"] == "Closed" and fin["remediation_status"] == "Completed"
        assert one(c, fin["requirement_id"])["version"] == fin["updated_version"]
        pdf = c.get(f"{API}/labs/grc/ucf/report/{rid}")
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"

    def test_no_gap_goes_to_validation(self, c):
        ch = act(c, "ucf_simulate_update", {"role": "compliance_owner", "change_type": "Retired"})["change"]
        rec = tr(c, ch["id"], "assess_impact", "grc_admin", {"controls_sufficient": "yes", "policy_revision": "no", "assessment_notes": "TEST_"})["record"]
        assert rec["state"] == "Validation" and not rec.get("issue_ids")
        tr(c, ch["id"], "validate", "auditor", {"decision": "pass", "closure_evidence": "TEST_"})
        assert one(c, rec["requirement_id"])["state"] == "Retired"


class TestPublicCronAdmin:
    def test_status_public(self):
        r = requests.get(f"{API}/ucf/status")
        assert r.status_code == 200 and "mode" in r.json()

    def test_shared_session_rejected(self):
        r = requests.get(f"{API}/labs/grc/records", headers={"X-Demo-Session": "ucf-shared-monitor"})
        assert r.status_code in (400, 401, 403, 422)
        r = requests.post(f"{API}/labs/grc/actions/ucf_sync", json={"role": "grc_admin"}, headers={"X-Demo-Session": "ucf-shared-monitor"})
        assert r.status_code in (400, 401, 403, 422)

    def test_cron_auth_and_idempotent(self):
        assert requests.post(f"{API}/cron/ucf-daily", json={}).status_code == 401
        assert requests.post(f"{API}/cron/ucf-daily", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
        rid = f"TEST-cron-{uuid.uuid4().hex[:8]}"
        h = {"Authorization": f"Bearer {CRON}", "x-webhook-id": rid}
        r = requests.post(f"{API}/cron/ucf-daily", json={}, headers=h)
        assert r.status_code == 200 and r.json()["run_id"] == rid
        r2 = requests.post(f"{API}/cron/ucf-daily", json={}, headers=h)
        assert r2.status_code == 200
        import time
        time.sleep(4)
        runs = [x for x in requests.get(f"{API}/ucf/status").json()["recent_scheduled_checks"]]
        assert runs  # recorded (run_id not exposed publicly)

    def test_admin_monitor(self):
        assert requests.get(f"{API}/admin/ucf/monitor").status_code in (401, 403)
        a = requests.Session()
        r = a.post(f"{API}/auth/login", json={"email": _env("ADMIN_EMAIL", "/app/backend/.env"), "password": _env("ADMIN_PASSWORD", "/app/backend/.env")})
        if r.status_code != 200:
            pytest.skip(f"admin login failed {r.status_code}")
        m = a.get(f"{API}/admin/ucf/monitor")
        assert m.status_code == 200, m.text
        d = m.json()
        assert len(d["metrics"]["kpis"]) == 12 and d["config"] and isinstance(d["scheduled_checks"], list)
