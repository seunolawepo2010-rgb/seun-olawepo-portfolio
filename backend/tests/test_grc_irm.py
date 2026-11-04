# GRC (ServiceNow IRM-style) lab: policy lifecycle, campaigns, exceptions, risks, issues, remediation tasks, reset, content (certs/education/skills)
import os
import uuid
from datetime import date, timedelta
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
TODAY = date.today()


def sess():
    s = requests.Session()
    s.headers.update({"X-Demo-Session": f"TEST-grc-{uuid.uuid4().hex[:16]}"})
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


POL = {"title": "TEST_Policy", "category": "InfoSec", "regulations": "NIST SP 800-53, ISO 27001", "control_objectives": "Obj A, Obj B",
       "reviewers": "Policy Reviewer (fictional)", "approval_group": "Gov", "content": "x"}


def published_policy(c):
    p = act(c, "create_policy", {"role": "policy_owner", **POL})["record"]
    tr(c, p["id"], "submit_for_review", "policy_owner")
    tr(c, p["id"], "complete_review", "policy_reviewer", {"comment": "ok"})
    tr(c, p["id"], "approve", "approver")
    tr(c, p["id"], "publish", "policy_owner")
    return one(c, p["id"])


@pytest.fixture
def c():
    return sess()


class TestMetaSeeds:
    def test_meta(self, c):
        m = act(c, "meta")
        assert len(m["roles"]) == 12 and "employee" in m["roles"] and "compliance_owner" in m["roles"]
        assert set(m["transitions"]) >= {"policy", "campaign", "ack", "exception", "risk", "issue", "task"}

    def test_seeds(self, c):
        r = recs(c)
        ex = {x["state"] for x in r if x["type"] == "exception"}
        assert {"Active", "Rejected", "Closed"} <= ex
        pol = {x["state"] for x in r if x["type"] == "policy"}
        assert {"Published", "Retired"} <= pol
        assert all(x.get("seeded") for x in r if x["type"] == "policy")
        assert any(x["type"] == "campaign" and x["state"] == "Active" for x in r)
        assert any(x["type"] == "issue" and x["state"] == "Closed" for x in r)

    def test_dashboard_and_reports(self, c):
        d = c.get(f"{API}/labs/grc/dashboard").json()
        assert d["kpis"] and d["campaigns"]
        for cm in d["campaigns"]:
            exp = round(100 * cm["acknowledged"] / cm["total"], 1) if cm["total"] else 0
            assert cm["completion_pct"] == exp
        p = c.get(f"{API}/labs/grc/report?format=pdf")
        assert p.status_code == 200 and p.content[:4] == b"%PDF"
        cs = c.get(f"{API}/labs/grc/report?format=csv")
        assert cs.status_code == 200 and "text/csv" in cs.headers["content-type"] and len(cs.text) > 50

    def test_bad_role_422(self, c):
        p = recs(c, "policy")[0]
        tr(c, p["id"], "retire", "hacker", {"comment": "x"}, 422)


class TestPolicy:
    def test_lifecycle_and_guards(self, c):
        p = act(c, "create_policy", {"role": "policy_owner", **POL})["record"]
        assert p["state"] == "Draft" and p["number"].startswith("POL")
        ctls = recs(c, "control", policy_id=p["id"])
        assert len(ctls) == 2
        act(c, "create_policy", {"role": "employee", **POL}, 409)
        tr(c, p["id"], "publish", "policy_owner", code=409)  # cannot skip
        tr(c, p["id"], "submit_for_review", "employee", code=403)
        tr(c, p["id"], "submit_for_review", "policy_owner")
        tr(c, p["id"], "approve", "employee", code=403)
        tr(c, p["id"], "approve", "approver", code=409)  # review not complete
        tr(c, p["id"], "complete_review", "policy_reviewer", code=422)  # comment required
        tr(c, p["id"], "complete_review", "policy_reviewer", {"comment": "fine"})
        tr(c, p["id"], "approve", "approver")
        tr(c, p["id"], "publish", "policy_owner")
        pub = one(c, p["id"])
        assert pub["state"] == "Published" and pub["effective_date"] == TODAY.isoformat()
        # versioning
        v = act(c, "new_version", {"role": "policy_owner", "id": p["id"]})["record"]
        assert v["version"] == "2.0" and v["state"] == "Draft" and v["supersedes"] == pub["number"]
        # retire blocked by active campaign
        cm = act(c, "create_campaign", {"role": "grc_admin", "policy_id": p["id"], "groups": ["HR"], "start_date": TODAY.isoformat(),
                                        "due_date": (TODAY + timedelta(days=10)).isoformat(), "reminder_days": 3})["record"]
        tr(c, cm["id"], "launch", "grc_admin")
        tr(c, p["id"], "retire", "policy_owner", {"comment": "old"}, 409)
        tr(c, cm["id"], "close", "grc_admin")
        tr(c, p["id"], "retire", "policy_owner", {"comment": "old"})
        assert one(c, p["id"])["state"] == "Retired"
        assert len(one(c, p["id"])["history"]) >= 6


class TestCampaign:
    def test_campaign_flow(self, c):
        draft = act(c, "create_policy", {"role": "policy_owner", **POL})["record"]
        act(c, "create_campaign", {"role": "grc_admin", "policy_id": draft["id"], "groups": ["IT"], "start_date": TODAY.isoformat(),
                                   "due_date": TODAY.isoformat(), "reminder_days": 3}, 409)
        p = published_policy(c)
        n0 = len(recs(c, "notification"))
        cm = act(c, "create_campaign", {"role": "grc_admin", "policy_id": p["id"], "groups": ["Finance", "IT"], "start_date": TODAY.isoformat(),
                                        "due_date": (TODAY + timedelta(days=10)).isoformat(), "reminder_days": 3})["record"]
        tr(c, cm["id"], "launch", "grc_admin")
        acks = recs(c, "ack", campaign_id=cm["id"])
        assert len(acks) == 6 and all(a["state"] == "Pending" for a in acks)
        assert len(recs(c, "notification")) - n0 >= 6
        a = acks[0]
        tr(c, a["id"], "acknowledge", "grc_admin", {"employee": a["employee"]}, 403)
        tr(c, a["id"], "acknowledge", "employee", {"employee": acks[1]["employee"]}, 409)
        tr(c, a["id"], "acknowledge", "employee", {"employee": a["employee"]})
        tr(c, acks[1]["id"], "acknowledge", "employee", {"employee": acks[1]["employee"]})
        assert one(c, a["id"])["acknowledged_at"]
        d = c.get(f"{API}/labs/grc/dashboard").json()
        row = next(x for x in d["campaigns"] if x["campaign"] == cm["number"])
        assert row["total"] == 6 and row["acknowledged"] == 2 and row["completion_pct"] == 33.3
        tr(c, cm["id"], "close", "grc_admin")
        cl = one(c, cm["id"])
        assert cl["final_completion_pct"] == 33.3 and cl["final_total"] == 6
        st = [x["state"] for x in recs(c, "ack", campaign_id=cm["id"])]
        assert st.count("Not Completed") == 4 and st.count("Acknowledged") == 2
        tr(c, acks[2]["id"], "acknowledge", "employee", {"employee": acks[2]["employee"]}, 409)

    def test_monitoring_reminders_escalation(self, c):
        camp = next(x for x in recs(c, "campaign") if x["state"] == "Active")
        act(c, "run_monitoring")
        acks = [a for a in recs(c, "ack", campaign_id=camp["id"]) if a["state"] != "Acknowledged"]
        assert acks and all(a["state"] == "Overdue" and a["reminders"] == 1 for a in acks)
        n1 = len([n for n in recs(c, "notification") if "Escalation" in n["subject"]])
        assert n1 == 0
        act(c, "run_monitoring")
        acks = [a for a in recs(c, "ack", campaign_id=camp["id"]) if a["state"] != "Acknowledged"]
        assert all(a["reminders"] == 2 for a in acks)
        esc = [n for n in recs(c, "notification") if "Escalation" in n["subject"]]
        assert len(esc) == len(acks)
        # overdue acks can still be acknowledged
        tr(c, acks[0]["id"], "acknowledge", "employee", {"employee": acks[0]["employee"]})


class TestException:
    def test_exception_flow(self, c):
        p = recs(c, "policy", state="Published")[0]
        body = {"policy_id": p["id"], "department": "Finance", "justification": "TEST_ legacy", "compensating_controls": "logs", "duration_days": 30}
        act(c, "create_exception", {"role": "auditor", **body}, 409)
        e = act(c, "create_exception", {"role": "control_owner", **body})["record"]
        assert e["state"] == "Requested"
        tr(c, e["id"], "approve", "approver", code=409)  # assess first
        tr(c, e["id"], "assess_risk", "approver", {"likelihood": 3, "impact": 4, "compensating_effectiveness": 50}, 403)
        tr(c, e["id"], "assess_risk", "risk_analyst", {"likelihood": 3, "impact": 4, "compensating_effectiveness": 50})
        r = one(c, e["id"])
        assert r["state"] == "Review" and r["risk_score"] == 6.0 and r["risk_rating"] == "Medium"
        tr(c, e["id"], "reject", "approver", code=422)  # comment required
        tr(c, e["id"], "approve", "approver")
        r = one(c, e["id"])
        assert r["state"] == "Active" and r["expires"] == (TODAY + timedelta(days=30)).isoformat()
        tr(c, e["id"], "request_renewal", "control_owner", {"extra_days": 15})
        assert one(c, e["id"])["state"] == "Review" and one(c, e["id"])["duration_days"] == 45
        tr(c, e["id"], "approve", "approver")
        tr(c, e["id"], "close", "policy_owner", code=422)
        tr(c, e["id"], "close", "policy_owner", {"closure_evidence": "migrated"})
        assert one(c, e["id"])["state"] == "Closed"

    def test_exception_reject(self, c):
        p = recs(c, "policy", state="Published")[0]
        e = act(c, "create_exception", {"role": "employee", "policy_id": p["id"], "department": "IT", "justification": "TEST_",
                                        "compensating_controls": "none", "duration_days": 10})["record"]
        tr(c, e["id"], "assess_risk", "risk_analyst", {"likelihood": 5, "impact": 5, "compensating_effectiveness": 0})
        assert one(c, e["id"])["risk_rating"] == "High"
        tr(c, e["id"], "reject", "approver", {"comment": "too risky"})
        assert one(c, e["id"])["state"] == "Rejected"


class TestRiskIssueTask:
    def test_full_chain(self, c):
        p = published_policy(c)
        ctl = recs(c, "control", policy_id=p["id"])[0]
        rk = act(c, "create_risk", {"role": "risk_analyst", "statement": "TEST_risk", "business_service": "Bank", "assets": ["A"], "category": "Cyber", "control_ids": [ctl["id"]]})["record"]
        act(c, "create_risk", {"role": "employee", "statement": "x", "business_service": "b", "assets": ["A"], "category": "c"}, 409)
        tr(c, rk["id"], "assess", "risk_analyst", {"likelihood": 4, "impact": 5, "control_effectiveness": 20})
        r = one(c, rk["id"])
        assert r["state"] == "Treatment" and r["residual"] == 16.0 and r["inherent"] == 20
        # failed assessment -> issue
        out = act(c, "assess_control", {"role": "auditor", "control_id": ctl["id"], "result": "fail", "severity": "High", "notes": "TEST_ fail"})
        assert out["execution"]["status"] == "completed", out["execution"]
        assert one(c, ctl["id"])["state"] == "Ineffective"
        iss = recs(c, "issue", control_id=ctl["id"])[0]
        assert iss["assessment_id"] == out["record"]["id"] and iss["risk_id"] == rk["id"] and iss["state"] == "Identified"
        # risk treat/approve; close blocked by open issue
        tr(c, rk["id"], "treat", "risk_analyst", {"treatment": "Mitigate", "mitigation_plan": "fix"})
        assert one(c, rk["id"])["state"] == "Pending Approval"
        tr(c, rk["id"], "approve", "approver")
        assert one(c, rk["id"])["state"] == "Monitoring"
        tr(c, rk["id"], "close", "risk_analyst", code=409)
        # issue -> task
        tr(c, iss["id"], "analyze", "issue_owner", {"root_cause": "rc"})
        tr(c, iss["id"], "assign", "issue_owner", {"remediation_owner": "RO", "due_date": (TODAY + timedelta(days=20)).isoformat(), "action_plan": "plan"})
        task = recs(c, "task", issue_id=iss["id"])[0]
        assert task["state"] == "Open"
        tr(c, iss["id"], "start_remediation", "remediation_owner")
        tr(c, task["id"], "assign", "issue_owner", {"assigned_to": "RO"})
        tr(c, task["id"], "start_work", "remediation_owner")
        tr(c, task["id"], "submit_for_validation", "remediation_owner", code=409)
        act(c, "attach", {"role": "employee", "id": task["id"], "name": "e.pdf", "description": "d"}, 409)
        act(c, "attach", {"role": "remediation_owner", "id": task["id"], "name": "e.pdf", "description": "d"})
        tr(c, task["id"], "submit_for_validation", "remediation_owner")
        tr(c, task["id"], "validate", "auditor", {"result": "fail"})
        assert one(c, task["id"])["state"] == "Work in Progress"
        tr(c, task["id"], "submit_for_validation", "remediation_owner")
        tr(c, task["id"], "validate", "auditor", {"result": "pass"})
        assert one(c, task["id"])["state"] == "Completed"
        tr(c, task["id"], "close", "issue_owner", {"closure_notes": "done"})
        assert one(c, task["id"])["state"] == "Closed"
        assert one(c, iss["id"])["state"] == "Validation"
        tr(c, iss["id"], "validate", "auditor", {"decision": "pass"})
        assert one(c, iss["id"])["state"] == "Closed"
        assert one(c, ctl["id"])["state"] == "Effective"
        r = one(c, rk["id"])
        assert r["residual"] < 16.0
        tr(c, rk["id"], "close", "risk_analyst")
        assert one(c, rk["id"])["state"] == "Closed"

    def test_issue_validate_blocked_without_closed_tasks(self, c):
        p = published_policy(c)
        ctl = recs(c, "control", policy_id=p["id"])[0]
        act(c, "assess_control", {"role": "auditor", "control_id": ctl["id"], "result": "fail", "notes": "x"})
        iss = recs(c, "issue", control_id=ctl["id"])[0]
        # issue can't jump to validate
        tr(c, iss["id"], "validate", "auditor", {"decision": "pass"}, 409)

    def test_risk_accept_and_low_residual(self, c):
        rk = act(c, "create_risk", {"role": "risk_analyst", "statement": "TEST_", "business_service": "b", "assets": "A", "category": "c"})["record"]
        tr(c, rk["id"], "assess", "risk_analyst", {"likelihood": 2, "impact": 2, "control_effectiveness": 10})
        assert one(c, rk["id"])["state"] == "Assessed"
        tr(c, rk["id"], "treat", "risk_analyst", {"treatment": "Accept", "mitigation_plan": "accept"})
        tr(c, rk["id"], "approve", "approver")
        assert one(c, rk["id"])["state"] == "Accepted"

    def test_work_note_executive_readonly(self, c):
        p = recs(c, "policy")[0]
        act(c, "work_note", {"role": "executive", "id": p["id"], "text": "x"}, 409)
        out = act(c, "work_note", {"role": "auditor", "id": p["id"], "text": "TEST_ note"})
        assert out["record"]["history"][-1]["kind"] == "work_note"


class TestResetIsolation:
    def test_reset_restores_and_isolated(self):
        a, b = sess(), sess()
        act(b, "create_policy", {"role": "policy_owner", **POL})
        nb = len(recs(b, "policy"))
        base = len(recs(a, "policy"))
        act(a, "create_policy", {"role": "policy_owner", **POL})
        assert len(recs(a, "policy")) == base + 1
        r = a.post(f"{API}/demo/reset")
        assert r.status_code == 200
        assert len(recs(a, "policy")) == base
        assert len(recs(b, "policy")) == nb == base + 1


class TestContent:
    def test_certs_education_skills(self):
        b = requests.get(f"{API}/content/bundle").json()
        certs = b["certifications"]
        assert len(certs) >= 7
        cats = {x.get("category") for x in certs}
        assert len(cats) >= 3
        names = " ".join(x["name"] for x in certs)
        for k in ("CRISC", "Security+", "PMP", "RTE", "PSM I", "PSPO I", "Pega"):
            assert k in names
        assert all(x.get("labs") for x in certs)
        inst = {e["institution"] for e in b["education"]}
        assert {"Northcentral University", "University of Ilorin"} <= inst
        sk = {x["name"] for x in b["skills"]}
        assert {"GDPR", "CCPA", "ISO/IEC 27701", "NIST SP 800-171", "CMMC"} <= sk

    def test_audit_engagement_framework_cmmc(self, c):
        for fw in ("CMMC", "GDPR"):
            r = c.post(f"{API}/labs/audit/actions/create_engagement", json={"name": f"TEST_{fw}", "framework": fw, "scope": "x", "period_start": TODAY.isoformat(),
                                                                         "period_end": TODAY.isoformat(), "lead": "L"})
            assert r.status_code == 200, r.text


# Admin: education CRUD + certificate upload (TEST_ records only, cleaned up by id)
ADMIN_EMAIL = "seunolawepo2010@gmail.com"
ADMIN_PW = "So!-vEYXvxbO-42utb_"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return s


class TestAdminEduCert:
    def test_education_crud(self, admin):
        r = admin.post(f"{API}/admin/content/education", json={"degree": "TEST_Degree", "field": "F", "institution": "TEST_U"})
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        try:
            u = admin.put(f"{API}/admin/content/education/{iid}", json={"field": "TEST_F2"})
            assert u.json()["field"] == "TEST_F2"
            assert any(e["id"] == iid for e in requests.get(f"{API}/content/bundle").json()["education"])
        finally:
            assert admin.delete(f"{API}/admin/content/education/{iid}").status_code == 200
        assert not any(e["id"] == iid for e in requests.get(f"{API}/content/bundle").json()["education"])

    def test_cert_upload(self, admin):
        r = admin.post(f"{API}/admin/content/certifications", json={"name": "TEST_Cert", "issuer": "X", "category": "Cybersecurity, Risk & Compliance", "labs": ["grc"]})
        cid = r.json()["id"]
        try:
            assert admin.post(f"{API}/admin/certifications/{cid}/file", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 415
            assert requests.post(f"{API}/admin/certifications/{cid}/file", files={"file": ("a.png", PNG, "image/png")}).status_code == 401
            up = admin.post(f"{API}/admin/certifications/{cid}/file", files={"file": ("a.png", PNG, "image/png")})
            assert up.status_code == 200, up.text
            g = requests.get(f"{API}/certifications/{cid}/file")
            assert g.status_code == 200 and g.headers["content-type"] == "image/png"
            assert cid in requests.get(f"{API}/content/bundle").json()["cert_files"]
        finally:
            admin.delete(f"{API}/admin/content/certifications/{cid}")
        print("orphan file after cert delete:", requests.get(f"{API}/certifications/{cid}/file").status_code, cid)
