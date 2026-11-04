from fastapi import HTTPException
from core import action, kpi, SCHEMAS, ins, upd, get, find, bulk, validate, audit, by_status, in_days, today, now
import engine
from engine import APPROVAL

SEV_DUE = {"Critical": 15, "High": 30, "Medium": 60, "Low": 90}
TAXONOMY = ["Cybersecurity", "Technology", "Operational", "Compliance", "Third-Party", "Data Privacy", "AI"]

# ---------------- LAB 1: ServiceNow IRM ----------------
SCHEMAS["irm"] = {
    "risk": {"title": ("str", True, 200), "category": ("choice", True, TAXONOMY), "likelihood": ("int", True, (1, 5)),
             "impact": ("int", True, (1, 5)), "owner": ("str", True, 80), "treatment": ("choice", False, ["Mitigate", "Transfer", "Avoid", "Accept"])},
    "policy": {"title": ("str", True, 200), "version": ("str", True, 20), "owner": ("str", True, 80), "status": ("choice", False, ["Draft", "Published", "Retired"])},
    "obligation": {"title": ("str", True, 200), "framework": ("str", True, 60), "owner": ("str", True, 80)},
    "scoring_config": {"likelihood_weight": ("float", False, (0.5, 2)), "impact_weight": ("float", False, (0.5, 2)),
                       "critical_threshold": ("int", False, (1, 50)), "high_threshold": ("int", False, (1, 50)), "medium_threshold": ("int", False, (1, 50)),
                       "due_critical": ("int", False, (1, 365)), "due_high": ("int", False, (1, 365)), "due_medium": ("int", False, (1, 365)), "due_low": ("int", False, (1, 365))},
}


async def seed_irm(s):
    await bulk(s, "irm", "scoring_config", [{"name": "Default enterprise scoring", "likelihood_weight": 1.0, "impact_weight": 1.0,
                                             "critical_threshold": 20, "high_threshold": 12, "medium_threshold": 6,
                                             "due_critical": 15, "due_high": 30, "due_medium": 60, "due_low": 90}])
    controls = [("AC-2", "Account Management", "Access Control", "IAM Team – A. Patel"), ("AC-6", "Least Privilege", "Access Control", "IAM Team – A. Patel"),
                ("AU-6", "Audit Record Review", "Audit & Accountability", "SOC – M. Chen"), ("CM-3", "Configuration Change Control", "Configuration Mgmt", "Platform Eng – R. Diaz"),
                ("CP-9", "System Backup", "Contingency Planning", "Infra Ops – L. Okafor"), ("IA-2", "Multi-Factor Authentication", "Identification & Auth", "IAM Team – A. Patel"),
                ("IR-4", "Incident Handling", "Incident Response", "SOC – M. Chen"), ("RA-5", "Vulnerability Monitoring & Scanning", "Risk Assessment", "VulnMgmt – K. Novak"),
                ("SC-8", "Transmission Confidentiality", "System & Comms Protection", "Network Eng – T. Brooks"), ("SI-2", "Flaw Remediation", "System & Info Integrity", "VulnMgmt – K. Novak")]
    evidence = {"AC-2": "Quarterly access review export (fictional): 412 accounts, 9 terminated users still active.",
                "CM-3": "Change tickets sample (fictional): 25 changes, 3 lacking CAB approval record.",
                "CP-9": "Backup job report (fictional): 98% success, restore test performed 11 months ago.",
                "RA-5": "Scan coverage (fictional): 94% of in-scope assets scanned in last 30 days."}
    await bulk(s, "irm", "control", [{"ref": r, "title": t, "family": f, "owner": o, "framework": "NIST SP 800-53 Rev.5", "status": "Not Tested",
                                      "evidence": evidence.get(r, f"Fictional evidence package for {r}: policy, procedure and sample screenshots."),
                                      "last_tested": None} for r, t, f, o in controls])
    await bulk(s, "irm", "risk", [
        {"title": "Orphaned privileged accounts", "category": "Cybersecurity", "likelihood": 4, "impact": 4, "inherent": 16, "residual": 12, "rating": "High", "owner": "CISO Office", "treatment": "Mitigate", "status": "Open"},
        {"title": "Unapproved production changes", "category": "Technology", "likelihood": 3, "impact": 4, "inherent": 12, "residual": 8, "rating": "Medium", "owner": "CIO Office", "treatment": "Mitigate", "status": "Open"},
        {"title": "Critical vendor concentration", "category": "Third-Party", "likelihood": 2, "impact": 5, "inherent": 10, "residual": 8, "rating": "Medium", "owner": "Procurement", "treatment": "Transfer", "status": "Open"}])
    await bulk(s, "irm", "policy", [{"title": "Information Security Policy", "version": "4.2", "owner": "CISO Office", "status": "Published", "acknowledgments": 0},
                                    {"title": "Acceptable Use Policy", "version": "2.1", "owner": "HR & Security", "status": "Published", "acknowledgments": 0},
                                    {"title": "Third-Party Risk Policy", "version": "1.3", "owner": "Procurement", "status": "Published", "acknowledgments": 0}])
    await bulk(s, "irm", "obligation", [{"title": "Maintain MFA for remote access", "framework": "NYDFS (summary)", "owner": "IAM Team", "status": "Mapped"},
                                        {"title": "Annual risk assessment", "framework": "GLBA Safeguards (summary)", "owner": "CISO Office", "status": "Mapped"}])


async def irm_score(s, L, I):
    cfg = (await find(s, "irm", "scoring_config"))[0]
    score = round(L * cfg["likelihood_weight"] * I * cfg["impact_weight"], 1)
    rating = "Critical" if score >= cfg["critical_threshold"] else "High" if score >= cfg["high_threshold"] else "Medium" if score >= cfg["medium_threshold"] else "Low"
    return score, rating, in_days(cfg[f"due_{rating.lower()}"])


async def st_irm_finding(s, ctx):
    c = await get(s, ctx["control_id"])
    f = await ins(s, "irm", "finding", title=f"Control {c['ref']} ({c['title']}) failed testing", control_id=c["id"], control_ref=c["ref"],
                  source="Control Assessment", status="Open", notes=ctx.get("notes", ""))
    ctx["finding_id"], ctx["control_ref"], ctx["owner"] = f["id"], c["ref"], c["owner"]
    return {"finding_id": f["id"], "title": f["title"]}


async def st_irm_score(s, ctx):
    score, rating, due = await irm_score(s, ctx["likelihood"], ctx["impact"])
    ctx.update(score=score, rating=rating, due_date=due)
    await upd(s, ctx["finding_id"], risk_score=score, severity=rating)
    return {"likelihood": ctx["likelihood"], "impact": ctx["impact"], "score": score, "rating": rating, "rule": "score = L×wL × I×wI vs configured thresholds"}


async def st_irm_remediation(s, ctx):
    r = await ins(s, "irm", "remediation", title=f"Remediate {ctx['control_ref']} deficiency", finding_id=ctx["finding_id"], control_id=ctx["control_id"],
                  owner=ctx["owner"], due_date=ctx["due_date"], severity=ctx["rating"], status="Pending Approval", poam_milestone=f"POA&M milestone due {ctx['due_date']}")
    ctx["remediation_id"] = r["id"]
    return {"remediation_id": r["id"], "owner": r["owner"], "due_date": r["due_date"]}


async def st_irm_activate(s, ctx):
    await upd(s, ctx["remediation_id"], status="In Progress")
    await upd(s, ctx["finding_id"], status="Remediation In Progress")
    await upd(s, ctx["control_id"], status="Remediation In Progress")
    return {"remediation": "In Progress", "control": "Remediation In Progress", "dashboard": "updated"}


async def rej_irm(s, ctx):
    await upd(s, ctx["remediation_id"], status="Rejected – Rework Plan")


async def st_xlab_cyber(s, ctx):
    r = await ins(s, "cyber", "cyber_risk", title=f"Control weakness {ctx['control_ref']} increases exposure", asset="Enterprise", threat="Control failure",
                  likelihood=ctx["likelihood"], impact=ctx["impact"], inherent=ctx["likelihood"] * ctx["impact"], control_effectiveness=0,
                  residual=float(ctx["likelihood"] * ctx["impact"]), rating=ctx["rating"], status="Open", source=f"IRM finding {ctx['finding_id']}")
    ctx["cyber_risk_id"] = r["id"]
    return {"cyber_risk_id": r["id"]}


async def st_xlab_audit(s, ctx):
    f = await ins(s, "audit", "audit_finding", title=f"{ctx['control_ref']} control deficiency (from IRM)", framework="NIST RMF", severity=ctx["rating"],
                  status="Open", source=f"IRM finding {ctx['finding_id']}", owner=ctx["owner"], due_date=ctx["due_date"])
    ctx["audit_finding_id"] = f["id"]
    return {"audit_finding_id": f["id"]}


async def st_dashboard(s, ctx):
    await ins(s, ctx.get("_lab", "automation"), "dashboard_event", summary=f"Dashboards refreshed after workflow ({ctx.get('rating', 'n/a')})")
    return {"refreshed_at": now()}


engine.workflow("irm_control_failure", "Control Failure → Finding → Remediation → Approval", "irm", "Control test result = Fail",
                "Failed control assessment generates a scored finding, remediation task with owner & due date, and routes for approval.",
                [("Create finding", st_irm_finding, {}), ("Calculate risk score", st_irm_score, {}), ("Create remediation task", st_irm_remediation, {}),
                 ("Risk owner approval", APPROVAL, {"title": lambda c: f"Approve remediation plan for {c['control_ref']} ({c['rating']})", "role": "Risk Owner", "on_reject": rej_irm}),
                 ("Activate remediation & update control", st_irm_activate, {})])
engine.workflow("xlab_control_failure", "WF1: IRM Control Failure → Cyber Risk → Audit Finding → Remediation", "irm", "Control fails with cross-lab propagation",
                "Cross-lab: control failure creates IRM finding, cybersecurity risk, audit finding, remediation, approval and dashboard updates.",
                [("Create IRM finding", st_irm_finding, {}), ("Calculate risk score", st_irm_score, {}), ("Create cybersecurity risk", st_xlab_cyber, {}),
                 ("Raise audit finding", st_xlab_audit, {}), ("Create remediation task", st_irm_remediation, {}),
                 ("Risk owner approval", APPROVAL, {"title": lambda c: f"Approve cross-lab remediation for {c['control_ref']}", "role": "Risk Owner", "on_reject": rej_irm}),
                 ("Activate remediation", st_irm_activate, {}), ("Update executive dashboards", st_dashboard, {})], cross_lab=True)


@action("irm", "test_control")
async def a_test_control(s, p):
    d = validate({"control_id": ("str", True, 40), "result": ("choice", True, ["pass", "fail"]), "notes": ("str", False, 1000),
                  "likelihood": ("int", False, (1, 5)), "impact": ("int", False, (1, 5)), "propagate": ("bool", False, None)}, p)
    c = await get(s, d["control_id"], "control")
    if c["status"] == "Remediation In Progress":
        raise HTTPException(409, "Control has an open remediation. Complete it first.")
    a = await ins(s, "irm", "assessment", control_id=c["id"], control_ref=c["ref"], result=d["result"], notes=d.get("notes", ""), tester="Demo assessor")
    await audit(s, "control.tested", "irm", {"control": c["ref"], "result": d["result"]})
    if d["result"] == "pass":
        await upd(s, c["id"], status="Effective", last_tested=today())
        return {"assessment": a, "message": f"{c['ref']} marked Effective"}
    await upd(s, c["id"], status="Ineffective", last_tested=today())
    key = "xlab_control_failure" if d.get("propagate") else "irm_control_failure"
    exe = await engine.start(s, key, {"control_id": c["id"], "likelihood": d.get("likelihood", 4), "impact": d.get("impact", 4), "notes": d.get("notes", ""), "_lab": "irm"}, "control_test_failed")
    return {"assessment": a, "execution": exe}


@action("irm", "complete_remediation")
async def a_complete_rem(s, p):
    d = validate({"remediation_id": ("str", True, 40), "evidence": ("str", True, 1000)}, p)
    r = await get(s, d["remediation_id"], "remediation")
    if r["status"] != "In Progress":
        raise HTTPException(409, f"Remediation must be approved and In Progress (current: {r['status']})")
    await upd(s, r["id"], status="Closed", closure_evidence=d["evidence"], closed_at=today())
    await upd(s, r["finding_id"], status="Closed")
    await upd(s, r["control_id"], status="Effective", last_tested=today())
    await ins(s, "irm", "assessment", control_id=r["control_id"], result="pass", notes=f"Retest after remediation: {d['evidence']}", tester="Demo assessor")
    await audit(s, "remediation.closed", "irm", {"remediation": r["id"]})
    return {"message": "Remediation closed, control retested Effective, dashboard updated"}


@action("irm", "acknowledge_policy")
async def a_ack(s, p):
    d = validate({"policy_id": ("str", True, 40), "employee": ("str", True, 80)}, p)
    pol = await get(s, d["policy_id"], "policy")
    await ins(s, "irm", "acknowledgment", policy_id=pol["id"], policy=pol["title"], employee=d["employee"], status="Acknowledged")
    await upd(s, pol["id"], acknowledgments=pol.get("acknowledgments", 0) + 1)
    return {"message": f"{d['employee']} acknowledged {pol['title']}"}


async def st_exc_assess(s, ctx):
    rating = "High" if ctx["duration_days"] > 90 else "Medium"
    ctx["rating"] = rating
    return {"exception_risk": rating, "rule": "> 90 days = High"}


async def st_exc_record(s, ctx):
    await upd(s, ctx["exception_id"], status="Approved", expires=in_days(ctx["duration_days"]))
    return {"status": "Approved", "expires": in_days(ctx["duration_days"])}


async def rej_exc(s, ctx):
    await upd(s, ctx["exception_id"], status="Rejected")


engine.workflow("policy_exception", "Policy Exception Request", "irm", "Exception requested", "Risk-assess and route policy exceptions for approval.",
                [("Assess exception risk", st_exc_assess, {}), ("Policy owner approval", APPROVAL, {"title": lambda c: f"Policy exception: {c['justification'][:60]}", "role": "Policy Owner", "on_reject": rej_exc}),
                 ("Record approved exception", st_exc_record, {})])


@action("irm", "request_exception")
async def a_exc(s, p):
    d = validate({"policy_id": ("str", True, 40), "justification": ("str", True, 500), "duration_days": ("int", True, (1, 365))}, p)
    pol = await get(s, d["policy_id"], "policy")
    e = await ins(s, "irm", "exception", policy=pol["title"], justification=d["justification"], duration_days=d["duration_days"], status="Pending")
    exe = await engine.start(s, "policy_exception", {"exception_id": e["id"], **d, "_lab": "irm"}, "exception_requested")
    return {"exception": e, "execution": exe}


async def st_acc_validate(s, ctx):
    r = await get(s, ctx["risk_id"])
    ctx["rating"] = r.get("rating", "Medium")
    ctx["role"] = "CISO" if ctx["rating"] in ("Critical", "High") else "Risk Owner"
    return {"rating": ctx["rating"], "required_approver": ctx["role"]}


async def st_acc_record(s, ctx):
    await upd(s, ctx["risk_id"], status="Accepted", treatment="Accept", acceptance_expires=in_days(180), acceptance_justification=ctx["justification"])
    return {"status": "Accepted", "review_by": in_days(180)}


engine.workflow("risk_acceptance", "Risk Acceptance", "irm", "Risk acceptance requested", "Validates rating, routes to the right approver, records time-bound acceptance.",
                [("Validate risk & approver", st_acc_validate, {}), ("Risk acceptance approval", APPROVAL, {"title": lambda c: f"Accept {c['rating']} risk (approver: {c['role']})", "role": "CISO / Risk Owner"}),
                 ("Record acceptance", st_acc_record, {})])


@action("irm", "accept_risk")
async def a_accept(s, p):
    d = validate({"risk_id": ("str", True, 40), "justification": ("str", True, 500)}, p)
    await get(s, d["risk_id"])
    return {"execution": await engine.start(s, "risk_acceptance", {**d, "_lab": "irm"}, "acceptance_requested")}


@action("irm", "attest_control")
async def a_attest(s, p):
    d = validate({"control_id": ("str", True, 40), "attester": ("str", True, 80), "statement": ("str", True, 500)}, p)
    c = await get(s, d["control_id"], "control")
    await ins(s, "irm", "attestation", control_ref=c["ref"], attester=d["attester"], statement=d["statement"], status="Attested")
    return {"message": f"Attestation recorded for {c['ref']}"}


@kpi("irm")
async def k_irm(s):
    c = await find(s, "irm", "control")
    f = await find(s, "irm", "finding")
    r = await find(s, "irm", "remediation")
    eff = sum(1 for x in c if x["status"] == "Effective")
    return {"kpis": [{"label": "Controls", "value": len(c)}, {"label": "Effective", "value": f"{round(100 * eff / max(len(c), 1))}%"},
                     {"label": "Open findings", "value": sum(1 for x in f if x["status"] != "Closed")},
                     {"label": "Remediation in progress", "value": sum(1 for x in r if x["status"] == "In Progress")},
                     {"label": "Overdue remediation", "value": sum(1 for x in r if x["status"] != "Closed" and x["due_date"] < today())}],
            "charts": [{"title": "Controls by status", "data": by_status(c)}, {"title": "Findings by severity", "data": by_status(f, "severity")}]}


# ---------------- LAB 3: Cyber ----------------
SCHEMAS["cyber"] = {"asset": {"name": ("str", True, 120), "asset_type": ("choice", True, ["Server", "Application", "Database", "Endpoint", "Cloud Service", "Network"]),
                              "criticality": ("int", True, (1, 5)), "owner": ("str", True, 80), "data_class": ("choice", True, ["Public", "Internal", "Confidential", "Restricted"])}}


async def seed_cyber(s):
    assets = await bulk(s, "cyber", "asset", [
        {"name": "Customer Portal (web)", "asset_type": "Application", "criticality": 5, "owner": "Digital Eng", "data_class": "Restricted"},
        {"name": "Core Ledger DB", "asset_type": "Database", "criticality": 5, "owner": "Data Platform", "data_class": "Restricted"},
        {"name": "HR SaaS", "asset_type": "Cloud Service", "criticality": 3, "owner": "HR IT", "data_class": "Confidential"},
        {"name": "Build Server", "asset_type": "Server", "criticality": 4, "owner": "Platform Eng", "data_class": "Internal"},
        {"name": "Branch Firewall Cluster", "asset_type": "Network", "criticality": 4, "owner": "Network Eng", "data_class": "Internal"}])
    await bulk(s, "cyber", "vulnerability", [
        {"asset_id": assets[3]["id"], "asset": assets[3]["name"], "title": "Outdated OpenSSL library", "cvss": 5.9, "severity": "Medium", "scanner": "Qualys-style", "plugin_id": "QID-FICT-1001", "status": "Open"},
        {"asset_id": assets[2]["id"], "asset": assets[2]["name"], "title": "TLS 1.0 enabled", "cvss": 4.3, "severity": "Medium", "scanner": "Tenable-style", "plugin_id": "TN-FICT-2002", "status": "Open"}])
    await bulk(s, "cyber", "cyber_risk", [{"title": "Credential stuffing against portal", "asset": assets[0]["name"], "threat": "Account takeover", "likelihood": 3, "impact": 5,
                                           "inherent": 15, "control_effectiveness": 60, "residual": 6.0, "rating": "Medium", "csf_function": "Protect", "nist_control": "IA-2", "status": "Open"}])


def rate(v):
    return "Critical" if v >= 20 else "High" if v >= 12 else "Medium" if v >= 6 else "Low"


async def st_cy_risk(s, ctx):
    if ctx.get("risk_id"):
        r = await get(s, ctx["risk_id"])
        ctx["rating"] = r["rating"]
        return {"risk_id": r["id"], "rating": r["rating"], "note": "Risk record already created by assessment"}
    v = await get(s, ctx["vuln_id"])
    a = await get(s, v["asset_id"])
    L = 5 if v["cvss"] >= 9 else 4
    inh = L * a["criticality"]
    r = await ins(s, "cyber", "cyber_risk", title=f"Exploitation of {v['title']}", asset=a["name"], threat="Vulnerability exploitation", likelihood=L,
                  impact=a["criticality"], inherent=inh, control_effectiveness=0, residual=float(inh), rating=rate(inh), csf_function="Identify",
                  nist_control="RA-5 / SI-2", status="Open", source=f"Vulnerability {v.get('plugin_id') or v['title']}")
    ctx.update(risk_id=r["id"], rating=r["rating"])
    return {"risk_id": r["id"], "inherent": inh, "rating": r["rating"]}


async def st_cy_rem(s, ctx):
    due = in_days(SEV_DUE.get(ctx["rating"], 60))
    t = await ins(s, "cyber", "remediation", title=f"Remediate risk {ctx['risk_id']}", risk_id=ctx["risk_id"], vuln_id=ctx.get("vuln_id"), owner="VulnMgmt – K. Novak", due_date=due, severity=ctx["rating"], status="Open")
    return {"remediation_id": t["id"], "due_date": due}


engine.workflow("cyber_high_risk", "High-Risk Vulnerability / Risk → Remediation", "cyber", "CVSS ≥ 7.0 or residual risk ≥ 12",
                "Automatically creates a risk record, remediation task with SLA due date, and updates the executive dashboard.",
                [("Classify & create risk record", st_cy_risk, {}), ("Create remediation task", st_cy_rem, {}), ("Update executive dashboard", st_dashboard, {})])


@action("cyber", "add_vulnerability")
async def a_vuln(s, p):
    d = validate({"asset_id": ("str", True, 40), "title": ("str", True, 200), "cvss": ("float", True, (0, 10)), "scanner": ("choice", True, ["Tenable-style", "Qualys-style"]), "plugin_id": ("str", False, 40)}, p)
    a = await get(s, d["asset_id"], "asset")
    sev = "Critical" if d["cvss"] >= 9 else "High" if d["cvss"] >= 7 else "Medium" if d["cvss"] >= 4 else "Low"
    v = await ins(s, "cyber", "vulnerability", asset=a["name"], severity=sev, status="Open", **d)
    exe = await engine.start(s, "cyber_high_risk", {"vuln_id": v["id"], "_lab": "cyber"}, "high_risk_vulnerability") if d["cvss"] >= 7 else None
    return {"vulnerability": v, "execution": exe, "message": "Below automation threshold (CVSS < 7.0)" if not exe else None}


@action("cyber", "assess_risk")
async def a_assess(s, p):
    d = validate({"asset_id": ("str", True, 40), "threat": ("str", True, 200), "likelihood": ("int", True, (1, 5)), "impact": ("int", True, (1, 5)),
                  "control_effectiveness": ("int", True, (0, 100)), "csf_function": ("choice", True, ["Govern", "Identify", "Protect", "Detect", "Respond", "Recover"]), "nist_control": ("str", False, 40)}, p)
    a = await get(s, d["asset_id"], "asset")
    inh = d["likelihood"] * d["impact"]
    res = round(inh * (1 - d["control_effectiveness"] / 100), 1)
    r = await ins(s, "cyber", "cyber_risk", title=d["threat"], asset=a["name"], inherent=inh, residual=res, rating=rate(res), status="Open", **{k: v for k, v in d.items() if k != "asset_id"})
    exe = await engine.start(s, "cyber_high_risk", {"risk_id": r["id"], "_lab": "cyber"}, "high_residual_risk") if res >= 12 else None
    return {"risk": r, "execution": exe, "calculation": f"inherent {inh} × (1 − {d['control_effectiveness']}%) = residual {res}"}


@action("cyber", "remediate_vuln")
async def a_rem_vuln(s, p):
    d = validate({"vuln_id": ("str", True, 40)}, p)
    await upd(s, (await get(s, d["vuln_id"], "vulnerability"))["id"], status="Remediated", remediated_at=today())
    for t in await find(s, "cyber", "remediation", vuln_id=d["vuln_id"]):
        await upd(s, t["id"], status="Closed")
        await upd(s, t["risk_id"], status="Closed", residual=0.0)
    return {"message": "Vulnerability remediated; linked remediation and risk closed"}


@action("cyber", "treat_risk")
async def a_treat(s, p):
    d = validate({"risk_id": ("str", True, 40), "treatment": ("choice", True, ["Mitigate", "Transfer", "Avoid", "Accept"]), "justification": ("str", True, 500)}, p)
    await get(s, d["risk_id"], "cyber_risk")
    if d["treatment"] == "Accept":
        return {"execution": await engine.start(s, "risk_acceptance", {"risk_id": d["risk_id"], "justification": d["justification"], "_lab": "cyber"}, "acceptance_requested")}
    return {"risk": await upd(s, d["risk_id"], treatment=d["treatment"], treatment_plan=d["justification"])}


@kpi("cyber")
async def k_cyber(s):
    v = await find(s, "cyber", "vulnerability")
    r = await find(s, "cyber", "cyber_risk")
    heat = [[0] * 5 for _ in range(5)]
    for x in r:
        if x["status"] != "Closed":
            heat[x["likelihood"] - 1][x["impact"] - 1] += 1
    return {"kpis": [{"label": "Assets", "value": len(await find(s, "cyber", "asset"))}, {"label": "Open vulns", "value": sum(1 for x in v if x["status"] == "Open")},
                     {"label": "Critical/High vulns", "value": sum(1 for x in v if x["severity"] in ("Critical", "High") and x["status"] == "Open")},
                     {"label": "Open risks", "value": sum(1 for x in r if x["status"] == "Open")}],
            "charts": [{"title": "Vulnerabilities by severity", "data": by_status(v, "severity")}, {"title": "Risks by residual rating", "data": by_status(r, "rating")}],
            "heatmap": heat}


# ---------------- LAB 4: Audit ----------------
FRAMEWORKS = ["SOX ITGC", "SOC 2", "ISO 27001", "NIST RMF", "FedRAMP", "HIPAA", "HITRUST", "PCI DSS", "GLBA", "NYDFS"]
TESTS = [("User access review", "Access review testing"), ("Change management approvals", "Change management testing"),
         ("Privileged access monitoring", "Privileged access testing"), ("Backup & restore validation", "Backup and recovery testing")]
FW_TEST = {"SOX ITGC": "Segregation of duties in financial apps", "SOC 2": "Logical access – CC6 criteria (summary)", "ISO 27001": "Statement of Applicability review",
           "NIST RMF": "Continuous monitoring strategy", "FedRAMP": "Monthly POA&M submission", "HIPAA": "ePHI access logging", "HITRUST": "Risk analysis currency",
           "PCI DSS": "Cardholder data environment segmentation", "GLBA": "Safeguards program oversight", "NYDFS": "Annual certification readiness"}
SCHEMAS["audit"] = {}


async def create_engagement(s, d):
    e = await ins(s, "audit", "engagement", status="Fieldwork", **d)
    tests = [(t, c) for t, c in TESTS] + [(FW_TEST[d["framework"]], "Framework-specific test")]
    for t, c in tests:
        ct = await ins(s, "audit", "control_test", engagement_id=e["id"], engagement=e["name"], framework=d["framework"], title=t, category=c, status="Not Tested")
        await ins(s, "audit", "evidence_request", engagement_id=e["id"], test_id=ct["id"], title=f"Evidence for: {t}", status="Requested", due_date=in_days(10))
    return e


async def seed_audit(s):
    await create_engagement(s, {"name": "FY Audit Readiness – SOX ITGC", "framework": "SOX ITGC", "scope": "3 in-scope financial applications (fictional)", "period_start": in_days(-90), "period_end": in_days(0), "lead": "Demo Audit Lead"})


async def st_au_finding(s, ctx):
    t = await get(s, ctx["test_id"])
    sev = "High" if ctx["exceptions"] >= 3 else "Medium" if ctx["exceptions"] >= 1 else "Low"
    f = await ins(s, "audit", "audit_finding", title=f"Deficiency: {t['title']}", framework=t["framework"], test_id=t["id"], engagement_id=t["engagement_id"], severity=sev,
                  exceptions=ctx["exceptions"], status="Open", owner="Control Owner (fictional)", due_date=in_days(SEV_DUE[sev]))
    ctx.update(finding_id=f["id"], severity=sev)
    return {"finding_id": f["id"], "severity": sev, "rule": "≥3 exceptions High, ≥1 Medium"}


async def st_au_map(s, ctx):
    m = await ins(s, "audit", "action_plan", finding_id=ctx["finding_id"], title="Management action plan", owner="Control Owner (fictional)", due_date=in_days(SEV_DUE[ctx["severity"]]), status="Open")
    return {"action_plan_id": m["id"]}


engine.workflow("audit_failed_test", "Failed Control Test → Finding → Management Action Plan", "audit", "Control test = Fail",
                "Failed tests create a finding sized by exceptions and a management action plan.",
                [("Create audit finding", st_au_finding, {}), ("Create management action plan", st_au_map, {}), ("Update readiness dashboard", st_dashboard, {})])


@action("audit", "create_engagement")
async def a_eng(s, p):
    d = validate({"name": ("str", True, 150), "framework": ("choice", True, FRAMEWORKS), "scope": ("str", True, 500), "period_start": ("date", True, None), "period_end": ("date", True, None), "lead": ("str", True, 80)}, p)
    return {"engagement": await create_engagement(s, d), "message": "Engagement planned: control tests and evidence requests generated"}


@action("audit", "submit_evidence")
async def a_sub_ev(s, p):
    d = validate({"request_id": ("str", True, 40), "description": ("str", True, 500)}, p)
    await get(s, d["request_id"], "evidence_request")
    return {"evidence": await upd(s, d["request_id"], status="Submitted", evidence=d["description"], submitted_at=today())}


@action("audit", "review_evidence")
async def a_rev_ev(s, p):
    d = validate({"request_id": ("str", True, 40), "decision": ("choice", True, ["Accepted", "Rejected"])}, p)
    r = await get(s, d["request_id"], "evidence_request")
    if r["status"] != "Submitted":
        raise HTTPException(409, "Evidence must be submitted before review")
    return {"evidence": await upd(s, r["id"], status=d["decision"])}


@action("audit", "record_test")
async def a_rec_test(s, p):
    d = validate({"test_id": ("str", True, 40), "result": ("choice", True, ["pass", "fail"]), "exceptions": ("int", False, (0, 100)), "notes": ("str", False, 1000)}, p)
    t = await get(s, d["test_id"], "control_test")
    await upd(s, t["id"], status="Passed" if d["result"] == "pass" else "Failed", exceptions=d.get("exceptions", 0), notes=d.get("notes", ""), tested_at=today())
    exe = await engine.start(s, "audit_failed_test", {"test_id": t["id"], "exceptions": d.get("exceptions", 1), "_lab": "audit"}, "control_test_failed") if d["result"] == "fail" else None
    return {"execution": exe, "message": "Test passed" if not exe else None}


@action("audit", "verify_remediation")
async def a_verify(s, p):
    d = validate({"finding_id": ("str", True, 40), "result": ("choice", True, ["Verified", "Not Remediated"])}, p)
    f = await get(s, d["finding_id"], "audit_finding")
    await upd(s, f["id"], status="Closed" if d["result"] == "Verified" else "Open", verification=d["result"])
    for m in await find(s, "audit", "action_plan", finding_id=f["id"]):
        await upd(s, m["id"], status="Completed" if d["result"] == "Verified" else "Open")
    return {"message": f"Finding {d['result']}"}


@kpi("audit")
async def k_audit(s):
    t = await find(s, "audit", "control_test")
    ev = await find(s, "audit", "evidence_request")
    f = await find(s, "audit", "audit_finding")
    tested = [x for x in t if x["status"] != "Not Tested"]
    passed = sum(1 for x in tested if x["status"] == "Passed")
    return {"kpis": [{"label": "Readiness score", "value": f"{round(100 * passed / max(len(t), 1))}%"}, {"label": "Tests executed", "value": f"{len(tested)}/{len(t)}"},
                     {"label": "Evidence accepted", "value": sum(1 for x in ev if x["status"] == "Accepted")}, {"label": "Open findings", "value": sum(1 for x in f if x["status"] != "Closed")}],
            "charts": [{"title": "Control tests", "data": by_status(t)}, {"title": "Evidence status", "data": by_status(ev)}]}


# ---------------- LAB 5: Vendor ----------------
SCHEMAS["vendor"] = {}
DATA_PTS = {"none": 0, "internal": 15, "confidential": 30, "regulated": 40}
INT_PTS = {"none": 0, "api": 15, "network": 25}
Q_FULL = ["MFA enforced for all admin access", "Encryption at rest for client data", "Annual penetration test", "Incident notification ≤ 72h in contract",
          "Subprocessor (fourth-party) list maintained", "BCP/DR tested annually", "Background checks for staff", "Vulnerability SLA defined", "Data deletion on termination", "Right to audit clause"]


async def onboard(s, d):
    v = await ins(s, "vendor", "vendor", status="Onboarding", **d)
    return v, await engine.start(s, "vendor_onboarding", {"vendor_id": v["id"], "_lab": "vendor"}, "vendor_onboarded")


async def seed_vendor(s):
    await bulk(s, "vendor", "vendor", [
        {"name": "NimbusPay Processing (fictional)", "service": "Payment processing", "data_access": "regulated", "integration": "api", "annual_spend": 850000, "has_soc2": True, "fourth_parties": ["CloudCo"], "tier": "Tier 1", "inherent": 78, "residual": 46.8, "status": "Approved", "reviewer": "TPRM Lead – J. Rivera (fictional)", "next_review": in_days(200)},
        {"name": "BrightDesk Support (fictional)", "service": "Help desk SaaS", "data_access": "internal", "integration": "none", "annual_spend": 60000, "has_soc2": False, "fourth_parties": [], "tier": "Tier 3", "inherent": 21, "residual": 18.9, "status": "Approved", "reviewer": "TPRM Analyst – S. Kim (fictional)", "next_review": in_days(500)}])


async def st_v_classify(s, ctx):
    v = await get(s, ctx["vendor_id"])
    spend = 20 if v["annual_spend"] >= 500000 else 10 if v["annual_spend"] >= 100000 else 3
    inh = DATA_PTS[v["data_access"]] + INT_PTS[v["integration"]] + spend + 3 * len(v.get("fourth_parties", []))
    tier = "Tier 1" if inh >= 60 else "Tier 2" if inh >= 35 else "Tier 3"
    await upd(s, v["id"], inherent=inh, tier=tier, criticality={"Tier 1": "Critical", "Tier 2": "High", "Tier 3": "Low"}[tier])
    ctx.update(inherent=inh, tier=tier, has_soc2=v["has_soc2"], name=v["name"])
    return {"inherent": inh, "tier": tier, "formula": "data + integration + spend + 3×fourth-parties"}


async def st_v_q(s, ctx):
    qs = Q_FULL if ctx["tier"] == "Tier 1" else Q_FULL[:7] if ctx["tier"] == "Tier 2" else Q_FULL[:4]
    q = await ins(s, "vendor", "questionnaire", vendor_id=ctx["vendor_id"], vendor=ctx["name"], questions=qs, status="Sent", due_date=in_days(14))
    ctx["questionnaire_id"] = q["id"]
    return {"questionnaire_id": q["id"], "questions": len(qs)}


async def st_v_comp(s, ctx):
    res = round(ctx["inherent"] * (0.6 if ctx["has_soc2"] else 0.9), 1)
    await upd(s, ctx["vendor_id"], residual=res)
    await ins(s, "vendor", "soc_review", vendor_id=ctx["vendor_id"], vendor=ctx["name"], soc2_report="Provided" if ctx["has_soc2"] else "Not available",
              checklist=["Report period covers ≥ 6 months", "Opinion unqualified", "CUECs mapped", "Subservice orgs identified"], status="Reviewed" if ctx["has_soc2"] else "Gap")
    ctx["residual"] = res
    return {"residual": res, "rule": "SOC 2 available → 40% reduction, else 10%"}


async def st_v_rev(s, ctx):
    rv = "TPRM Lead – J. Rivera (fictional)" if ctx["tier"] == "Tier 1" else "TPRM Analyst – S. Kim (fictional)"
    await upd(s, ctx["vendor_id"], reviewer=rv)
    return {"reviewer": rv}


async def st_v_inv(s, ctx):
    nxt = in_days({"Tier 1": 365, "Tier 2": 540, "Tier 3": 730}[ctx["tier"]])
    await upd(s, ctx["vendor_id"], status="Approved", next_review=nxt, monitoring="Enabled")
    return {"status": "Approved", "next_review": nxt}


async def rej_v(s, ctx):
    await upd(s, ctx["vendor_id"], status="Rejected")


engine.workflow("vendor_onboarding", "WF2: Vendor Onboarding → Risk Assessment → Compliance Review → Approval → Inventory", "vendor", "Vendor onboarded",
                "Classifies, assigns questionnaire, scores, assigns reviewer, routes approval and updates the inventory.",
                [("Classify criticality & tier", st_v_classify, {}), ("Assign security questionnaire", st_v_q, {}), ("Compliance review & residual score", st_v_comp, {}),
                 ("Assign reviewer", st_v_rev, {}), ("Vendor approval", APPROVAL, {"title": lambda c: f"Approve {c['name']} ({c['tier']}, residual {c['residual']})", "role": "TPRM Committee", "on_reject": rej_v}),
                 ("Update vendor inventory", st_v_inv, {})], cross_lab=True)


@action("vendor", "onboard_vendor")
async def a_onboard(s, p):
    d = validate({"name": ("str", True, 120), "service": ("str", True, 200), "data_access": ("choice", True, list(DATA_PTS)), "integration": ("choice", True, list(INT_PTS)),
                  "annual_spend": ("float", True, (0, 1e9)), "has_soc2": ("bool", False, None), "fourth_parties": ("list", False, None)}, p)
    d.setdefault("has_soc2", False)
    d.setdefault("fourth_parties", [])
    v, exe = await onboard(s, d)
    return {"vendor": v, "execution": exe}


@action("vendor", "answer_questionnaire")
async def a_answer(s, p):
    d = validate({"questionnaire_id": ("str", True, 40), "answers": ("dict", True, None)}, p)
    q = await get(s, d["questionnaire_id"], "questionnaire")
    yes = sum(1 for x in q["questions"] if d["answers"].get(x) in ("yes", True))
    pct = yes / len(q["questions"])
    v = await get(s, q["vendor_id"])
    res = round(v["inherent"] * (1 - 0.5 * pct), 1)
    await upd(s, q["id"], status="Completed", answers=d["answers"], compliance=round(pct * 100))
    await upd(s, v["id"], residual=res)
    gaps = [x for x in q["questions"] if d["answers"].get(x) not in ("yes", True)]
    for g in gaps:
        await ins(s, "vendor", "vendor_remediation", vendor_id=v["id"], vendor=v["name"], title=f"Gap: {g}", status="Open", due_date=in_days(60))
    return {"compliance_pct": round(pct * 100), "residual": res, "gaps": len(gaps)}


@action("vendor", "monitor_event")
async def a_monitor(s, p):
    d = validate({"vendor_id": ("str", True, 40), "event": ("choice", True, ["Reported breach", "Qualified SOC 2 opinion", "Financial distress", "Fourth-party incident"])}, p)
    v = await get(s, d["vendor_id"], "vendor")
    res = round(min(100, v.get("residual", 0) + 15), 1)
    await upd(s, v["id"], residual=res, status="Under Review")
    await ins(s, "vendor", "vendor_remediation", vendor_id=v["id"], vendor=v["name"], title=f"Continuous monitoring alert: {d['event']}", status="Open", due_date=in_days(14))
    return {"message": f"{v['name']} moved to Under Review; residual {res}"}


@kpi("vendor")
async def k_vendor(s):
    v = await find(s, "vendor", "vendor")
    return {"kpis": [{"label": "Vendors", "value": len(v)}, {"label": "Tier 1", "value": sum(1 for x in v if x.get("tier") == "Tier 1")},
                     {"label": "Avg residual", "value": round(sum(x.get("residual", 0) for x in v) / max(len(v), 1), 1)},
                     {"label": "Under review", "value": sum(1 for x in v if x["status"] in ("Onboarding", "Under Review"))}],
            "charts": [{"title": "Vendors by tier", "data": by_status(v, "tier")}, {"title": "Vendors by status", "data": by_status(v)}]}
