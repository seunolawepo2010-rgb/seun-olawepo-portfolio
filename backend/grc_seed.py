from core import upd, in_days
from grc import new, H, LAB, EMPLOYEES

SEED = "Fictional seeded demonstration record"


async def mk(s, t, hist, **f):
    r = await new(s, t, "system", f"{SEED} – created", days=hist[0][0], seeded=True, **f)
    return await upd(s, r["id"], history=r["history"] + [H(by, k, txt, d) for d, by, k, txt in hist[1:]])


def life(start, states, roles):
    out, d, prev = [(start, "system", "created", "")], start, states[0]
    for st, by in zip(states[1:], roles):
        d += 3
        out.append((d, by, "state", f"{prev} → {st}"))
        prev = st
    return out


async def seed_grc(s):
    isp = await mk(s, "policy", life(-140, ["Draft", "Review", "Approved", "Published"], ["policy_owner", "approver", "policy_owner"]), title="Information Security Policy", version="3.0", category="Information Security",
                   owner="Policy Owner (fictional)", regulations=["NIST SP 800-53", "ISO 27001", "SOC 2", "GLBA"], control_objectives=["Account management", "Multi-factor authentication", "Change control", "Backup & recovery"],
                   reviewers=["Policy Reviewer (fictional)"], approval_group="Information Security Governance Committee", state="Published", reviewed=True, effective_date=in_days(-131), review_date=in_days(234),
                   content="1. Purpose: protect the confidentiality, integrity and availability of Northwind Financial (fictional) information.\n2. Scope: all workforce members, systems and third parties.\n3. Requirements: access is least-privilege and reviewed quarterly; MFA for remote and privileged access; production changes follow CAB approval; critical data is backed up and restore-tested annually.\n4. Exceptions: via the Policy Exception process with risk assessment and approval.\n5. Enforcement: violations may result in disciplinary action.",
                   approval_history=[{"by": "Approver", "decision": "Approved", "at": in_days(-134), "comment": "Aligned with NIST 800-53 baseline"}], review_comments=[{"by": "Policy Reviewer", "at": in_days(-137), "comment": "Clarify MFA scope for contractors"}])
    aup = await mk(s, "policy", life(-60, ["Draft", "Review", "Approved", "Published"], ["policy_owner", "approver", "policy_owner"]), title="Acceptable Use Policy", version="2.1", category="Workforce", owner="Policy Owner (fictional)",
                   regulations=["ISO 27001", "SOC 2"], control_objectives=["Acceptable use"], reviewers=["Policy Reviewer (fictional)"], approval_group="HR & Security", state="Published", reviewed=True, effective_date=in_days(-51), review_date=in_days(314))
    await mk(s, "policy", life(-400, ["Draft", "Review", "Approved", "Published", "Retired"], ["policy_owner", "approver", "policy_owner", "policy_owner"]), title="Legacy Remote Access Standard", version="1.4", category="Network",
             owner="Policy Owner (fictional)", regulations=["NIST SP 800-53"], control_objectives=[], reviewers=["Policy Reviewer (fictional)"], approval_group="Network Governance", state="Retired", reviewed=True)
    ctl = []
    for name, ref, st in [("Account management", "AC-2", "Effective"), ("Multi-factor authentication", "IA-2", "Effective"), ("Change control", "CM-3", "Not Assessed"), ("Backup & recovery", "CP-9", "Ineffective")]:
        ctl.append(await mk(s, "control", [(-130, "system", "created", "")], name=name, ref=ref, policy_id=isp["id"], policy=isp["number"], owner="Control Owner (fictional)", state=st))
    risk = await mk(s, "risk", life(-90, ["Identified", "Assessed", "Pending Approval", "Monitoring"], ["risk_analyst", "risk_analyst", "approver"]), statement="Unauthorized access to customer data due to weak account lifecycle controls",
                    business_service="Online Banking (fictional)", assets=["Customer Portal", "Core Ledger DB"], category="Cybersecurity", owner="Risk Owner (fictional)", likelihood=3, impact=5, inherent=15, control_effectiveness=60,
                    residual=6.0, rating="Medium", treatment="Mitigate", mitigation_plan="Automate deprovisioning; quarterly access reviews", questionnaire={"MFA enforced?": "yes", "Quarterly access review?": "yes", "Automated deprovisioning?": "no"}, state="Monitoring", review_date=in_days(30))
    await upd(s, ctl[0]["id"], risk_id=risk["id"], risk=risk["number"])
    await mk(s, "risk", life(-70, ["Identified", "Assessed", "Pending Approval", "Accepted"], ["risk_analyst", "risk_analyst", "approver"]), statement="Legacy mainframe cannot support MFA", business_service="Payments (fictional)",
             assets=["Mainframe"], category="Technology", owner="Risk Owner (fictional)", likelihood=2, impact=4, inherent=8, control_effectiveness=40, residual=4.8, rating="Low", treatment="Accept",
             mitigation_plan="Network isolation; replacement planned", state="Accepted")
    a1 = await mk(s, "assessment", [(-40, "auditor", "created", "")], control_id=ctl[0]["id"], control=ctl[0]["number"], result="pass", notes="Validated: 25/25 samples compliant", state="Completed")
    a2 = await mk(s, "assessment", [(-45, "auditor", "created", "")], control_id=ctl[3]["id"], control=ctl[3]["number"], result="fail", notes="Restore test overdue 11 months", state="Completed")
    _ = a1
    closed = await mk(s, "issue", life(-80, ["Identified", "Analysis", "Assigned", "Remediation in Progress", "Validation", "Closed"], ["issue_owner", "issue_owner", "remediation_owner", "system", "auditor"]),
                      title="Terminated users retained access (internal audit finding)", source="Internal Audit", control_id=ctl[0]["id"], control=ctl[0]["number"], risk_id=risk["id"], risk=risk["number"], severity="High",
                      root_cause="HR feed not integrated with IAM", owner="Issue Owner (fictional)", remediation_owner="Remediation Owner (fictional)", due_date=in_days(-50), action_plan="Integrate HR feed; disable 9 accounts", validation="pass", state="Closed")
    await mk(s, "task", life(-74, ["Open", "Assigned", "Work in Progress", "Pending Validation", "Completed", "Closed"], ["issue_owner", "remediation_owner", "remediation_owner", "auditor", "issue_owner"]), issue_id=closed["id"], issue=closed["number"],
             title="Disable terminated accounts & automate feed", assignment_group="IAM Engineering", assigned_to="Remediation Owner (fictional)", priority="2 - High", sla_due=in_days(-50), due_date=in_days(-50),
             action_plan="Disable accounts; deploy HR→IAM connector", evidence=[{"name": "deprovisioning-report.pdf", "description": "Fictional evidence", "by": "remediation_owner", "label": "Evidence metadata (demo – no file stored)"}],
             validation_result="pass", reviewer="Auditor (fictional)", closure_notes="Validated by audit", state="Closed")
    opn = await mk(s, "issue", life(-44, ["Identified", "Analysis", "Assigned", "Remediation in Progress"], ["issue_owner", "issue_owner", "remediation_owner"]), title="Backup restore testing overdue", source="Control Assessment",
                   control_id=ctl[3]["id"], control=ctl[3]["number"], assessment_id=a2["id"], assessment=a2["number"], severity="Medium", root_cause="No owner for annual restore test", owner="Issue Owner (fictional)",
                   remediation_owner="Remediation Owner (fictional)", due_date=in_days(-3), action_plan="Perform restore test; assign recurring owner", state="Remediation in Progress")
    await mk(s, "task", life(-40, ["Open", "Assigned", "Work in Progress"], ["issue_owner", "remediation_owner"]), issue_id=opn["id"], issue=opn["number"], title="Execute restore test for Core Ledger DB", assignment_group="Infra Ops",
             assigned_to="Remediation Owner (fictional)", priority="3 - Moderate", sla_due=in_days(-3), due_date=in_days(-3), action_plan="Restore to isolated env; document RTO", evidence=[], state="Work in Progress")
    for st, just, extra in [("Active", "Legacy HR system cannot enforce password history", {"expires": in_days(60), "risk_rating": "Medium", "risk_score": 6.0}),
                            ("Rejected", "Disable MFA for executive assistants", {"risk_rating": "High", "risk_score": 16.0}),
                            ("Closed", "Temporary vendor VPN without device posture check", {"risk_rating": "Medium", "risk_score": 8.0, "closure_evidence": "Vendor migrated to ZTNA"})]:
        path = ["Requested", "Review", st] if st != "Closed" else ["Requested", "Review", "Active", "Closed"]
        await mk(s, "exception", life(-100, path, ["risk_analyst", "approver", "policy_owner"]), policy_id=isp["id"], policy=isp["number"], control=ctl[1]["number"], department="IT" if st != "Rejected" else "Executive Office",
                 justification=just, compensating_controls="Enhanced monitoring", owner="Department lead (fictional)", approver="CISO (fictional)", duration_days=120, state=st, **extra)
    for state, policy, due, groups, acked in [("Closed", isp, in_days(-100), ["Finance", "IT"], 5), ("Active", aup, in_days(-1), ["HR", "Operations", "Finance"], 3)]:
        c = await mk(s, "campaign", life(-110 if state == "Closed" else -20, ["Draft", "Active"] + (["Closed"] if state == "Closed" else []), ["grc_admin", "grc_admin"]), policy_id=policy["id"], policy=policy["number"],
                     title=f"Acknowledge {policy['title']}", groups=groups, start_date=in_days(-110 if state == "Closed" else -20), due_date=due, reminder_days=3, state=state)
        emps = [(g, e) for g in groups for e in EMPLOYEES[g]]
        for i, (g, e) in enumerate(emps):
            ok = i < acked
            st = "Acknowledged" if ok else ("Not Completed" if state == "Closed" else "Pending")
            await mk(s, "ack", [(-105 if state == "Closed" else -19, "system", "created", "")] + ([(-104 + i if state == "Closed" else -18 + i, e, "state", "Pending → Acknowledged")] if ok else []),
                     campaign_id=c["id"], campaign=c["number"], policy=policy["number"], employee=e, group=g, state=st, due_date=due, reminders=0,
                     acknowledged_at=f"{in_days((-104 if state == 'Closed' else -18) + i)}T10:00:00+00:00" if ok else None)
        if state == "Closed":
            await upd(s, c["id"], final_total=len(emps), final_acknowledged=acked, final_completion_pct=round(100 * acked / len(emps), 1))
    _ = LAB
