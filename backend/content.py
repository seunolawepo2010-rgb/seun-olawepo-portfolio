from core import db, P, new_id, now

PROFILE = {
    "key": "profile", "name": "Seun Olawepo", "site_title": "Seun Olawepo | Enterprise Technology & AI Governance",
    "headline": "Senior Cybersecurity GRC & IT Risk Professional | ServiceNow IRM | AI Governance & AI Agent Management | Program & Agile Delivery",
    "supporting": "Cybersecurity Governance • Technology Risk • ServiceNow IRM • IT Audit • AI Agents • Responsible AI • Enterprise Automation • Project & Program Management • SAFe Release Train Engineering",
    "summary": "I am an enterprise technology professional with experience spanning cybersecurity governance, IT risk and controls, regulatory compliance, enterprise audit, third-party risk, ServiceNow IRM, business analysis, project delivery, Agile practices, and AI-powered automation.\n\nMy work focuses on helping organizations identify and manage risk, strengthen controls, improve governance processes, coordinate technology initiatives, and use automation to make enterprise operations more efficient.\n\nThrough independent AI product development, I also work with AI agents, AI/ML feature evaluation, workflow automation, model performance, latency, and API/token cost considerations.",
    "metrics": [{"value": "70+", "label": "Enterprise applications supported"}, {"value": "~94", "label": "NIST SP 800-53 controls assessed"},
                {"value": "70+", "label": "Audit findings tracked"}, {"value": "6", "label": "Enterprise departments collaborated across"}],
    "github_url": "", "linkedin_url": "", "public_email": "", "location": "",
    "d3_command": {"title": "D3 Command | Independent AI Product Development",
                   "description": "D3 Command is a functional AI software product I developed independently using Emergent. It is separate from my employment history and from this portfolio's fictional demonstrations.",
                   "capabilities": ["AI agents", "Workflow automation", "Document processing", "Business intelligence", "Cybersecurity capabilities"],
                   "experience": ["AI/ML feature development", "AI feature launches", "Model evaluation", "AI agent workflows", "API/token cost considerations", "Model latency", "AI product unit economics", "Product iteration"],
                   "links": ["https://www.d3command.com", "https://app.d3command.com"]},
}

EXPERIENCE = [
    ("loandepot", "LoanDepot", "Senior Information Security GRC Analyst", "October 2025", "Present", ["irm", "cyber", "vendor", "aigov"],
     ["Cybersecurity risk management and enterprise GRC activities", "Security policy governance and control assessment support", "Third-party risk and regulatory compliance support (e.g., GLBA, NYDFS)"]),
    ("tspi-usda", "TSPI / USDA", "Senior GRC Analyst", "May 2023", "October 2025", ["irm", "audit", "cyber"],
     ["NIST RMF and NIST SP 800-53 control assessment activities", "POA&M tracking and remediation coordination", "FedRAMP and federal compliance documentation support"]),
    ("fidelity", "Fidelity Investments", "Senior IT Risk & Controls Analyst", "January 2019", "April 2023", ["audit", "irm", "cyber"],
     ["Technology risk and controls testing", "SOX ITGC and audit management support", "Audit finding tracking and remediation follow-up"]),
    ("unitedhealth", "UnitedHealth Group", "Business Analyst", "February 2016", "January 2019", ["pm", "servicenow"],
     ["Business requirements and process analysis", "HIPAA-aware requirements and stakeholder coordination", "Agile ceremony participation and backlog support"]),
    ("mastercard", "Mastercard", "Business Systems Analyst", "January 2012", "February 2016", ["pm", "safe"],
     ["Business systems analysis and requirements documentation", "PCI DSS-aware solution coordination", "Testing and UAT coordination"]),
    ("att", "AT&T", "Project Coordinator", "January 2009", "January 2012", ["pm", "safe"],
     ["Project coordination, schedules and status reporting", "RAID log and stakeholder communication support", "Milestone tracking across delivery teams"]),
]

SKILLS = {
    "Cybersecurity GRC": (["NIST CSF", "NIST 800-53", "RMF", "FedRAMP", "ISO 27001", "SOC 2", "SOX ITGC", "PCI DSS", "HIPAA", "HITRUST", "GLBA", "NYDFS"], ["irm", "cyber", "audit"]),
    "ServiceNow": (["IRM", "GRC", "Policy & Compliance", "Risk Management", "Audit Management", "Administration", "Configuration", "Development demonstrations", "Flow Designer concepts", "REST APIs"], ["irm", "servicenow"]),
    "AI Governance": (["NIST AI RMF", "ISO/IEC 42001", "Model risk", "Responsible AI", "AI security", "AI risk assessments"], ["aigov"]),
    "AI Agent Management": (["Agent orchestration", "Agent evaluation", "AI operations", "Human-in-the-loop workflows", "Agent monitoring", "Token economics", "Latency", "Model selection"], ["agents"]),
    "Project & Agile Delivery": (["PMP", "Scrum", "SAFe", "RTE", "PI Planning", "ART coordination", "Product Ownership", "Project management", "Program management", "Business analysis"], ["pm", "safe"]),
    "Enterprise Tools": (["ServiceNow", "OneTrust", "Azure DevOps", "Jira", "Confluence", "SharePoint", "Power BI", "Power Apps", "SQL", "Microsoft Project", "GitHub"], ["servicenow", "pm"]),
    "Security Operations": (["Tenable", "Qualys", "Entra ID", "SailPoint", "CyberArk", "Vulnerability management", "Incident response", "BCDR"], ["cyber", "ir"]),
}

CASES = [
    ("servicenow-irm-migration", "ServiceNow IRM Migration", "irm", "Risk, control and issue data scattered across spreadsheets limits visibility and auditability.", "Risk register, control library, issues, policies.", "Map data model, define taxonomy and scoring, configure workflows, migrate and validate.", "ServiceNow-style IRM simulator", "NIST SP 800-53, NIST CSF", "Data model, scoring rules, approval workflow, executive dashboard"),
    ("servicenow-admin-workflow", "ServiceNow Administration & Workflow Development", "servicenow", "Manual GRC intake and approvals create delays and inconsistent records.", "Custom tables, ACLs, business rules, flows, REST, change deployment.", "Configure table, enforce ACLs, declarative rules, flow with approval, change with rollback.", "ServiceNow-style admin/dev simulator", "ITIL change concepts", "Table config, ACL matrix, flow, update set history"),
    ("policy-governance", "Enterprise Policy Governance", "irm", "Policies lack acknowledgment tracking and exception control.", "Policy lifecycle, acknowledgments, exceptions.", "Publish policies, collect acknowledgments, risk-assess and approve exceptions.", "IRM lab", "ISO 27001 (summary)", "Acknowledgment log, exception register"),
    ("nist-800-53-assessment", "NIST 800-53 Control Assessment", "irm", "Controls require consistent testing with traceable evidence.", "10 sample controls across families.", "Review evidence, record test results, generate findings and POA&M items automatically.", "IRM lab, automation engine", "NIST SP 800-53 Rev.5, RMF", "Assessment report (PDF), POA&M"),
    ("sox-soc2-remediation", "SOX ITGC & SOC 2 Audit Remediation", "audit", "Audit findings need structured action plans and verified closure.", "Access, change, privileged access, backup testing.", "Plan engagement, request evidence, test, auto-create findings & action plans, verify remediation.", "Audit lab", "SOX ITGC, SOC 2", "Readiness dashboard, findings report"),
    ("vendor-risk", "Third-Party Vendor Risk Assessment", "vendor", "Vendor onboarding lacks risk-based tiering and consistent due diligence.", "Onboarding through monitoring.", "Automated classification, tiered questionnaires, SOC 2 review, reviewer & approval routing.", "TPRM lab", "SOC 2, GLBA (summary)", "Vendor inventory, risk scores"),
    ("ai-governance", "AI Governance Implementation", "aigov", "AI use cases are adopted without inventory, risk tiering or oversight.", "AI intake, inventory, assessments, approvals, monitoring.", "Risk-tier AI systems, generate required assessments, agent review, board approval.", "AI governance lab", "NIST AI RMF, ISO/IEC 42001 (summary)", "AI inventory, assessment checklists"),
    ("ai-agent-orchestration", "AI Agent Orchestration", "agents", "Enterprise AI agents need defined roles, permissions and human oversight.", "Multi-agent GRC assessment.", "Orchestrate specialized agents with an approval gate and audit trail.", "Agent Command Center", "NIST AI RMF (Govern/Manage)", "Workflow graph, agent runs, final report"),
    ("agent-cost-performance", "AI Agent Cost & Performance Management", "agents", "AI agent costs and latency must be visible and controlled.", "Runs, tokens, latency, budgets.", "Track measured/estimated metrics, compare model configurations, enforce quotas.", "Agent Command Center", "AI operations practices", "Cost comparison, performance dashboard"),
    ("enterprise-project-delivery", "Enterprise Project Delivery", "pm", "Critical milestone slippage is detected late.", "Five sample programs.", "Automated health checks, escalation and revised executive status reports.", "Project lab", "PMI practices, Scrum", "Status reports, RAID log"),
    ("safe-pi-planning", "SAFe PI Planning Coordination", "safe", "Five teams must align capacity, dependencies and objectives.", "One ART, five teams, one PI.", "WSJF prioritization, breakout planning, dependency & capacity alerts, ROAM, confidence vote, I&A.", "SAFe lab", "SAFe (concepts)", "Program board, PI report, I&A report"),
    ("incident-response-bcdr", "Incident Response & BCDR", "ir", "Critical incidents require coordinated response and recovery against RTO/RPO.", "Incident lifecycle and BIA.", "Severity scoring, playbook tasks, escalation, BCDR impact review, recovery tracking.", "IR & BCDR lab", "NIST incident handling concepts", "Incident timeline, recovery report"),
]


async def seed_content():
    if not await db.content.find_one({"key": "profile"}):
        await db.content.insert_one({**PROFILE, "updated_at": now()})
    if not await db.experience.count_documents({}):
        await db.experience.insert_many([{"id": slug, "slug": slug, "employer": e, "title": t, "start": st, "end": en, "labs": labs, "highlights": h, "order": i, "published": True,
                                          "note": "Summary of areas of responsibility. Edit in admin."} for i, (slug, e, t, st, en, labs, h) in enumerate(EXPERIENCE)])
    if not await db.skills.count_documents({}):
        await db.skills.insert_many([{"id": new_id(), "category": c, "name": n, "labs": labs, "order": i} for i, (c, (names, labs)) in enumerate(SKILLS.items()) for n in names])
    if not await db.case_studies.count_documents({}):
        await db.case_studies.insert_many([{"id": slug, "slug": slug, "title": t, "lab": lab, "challenge": ch, "scope": sc, "approach": ap, "technology": te, "frameworks": fw, "deliverables": dl,
                                            "evidence": "Interactive lab records, automation execution logs and downloadable PDF/CSV reports generated in the related lab.", "published": True, "order": i,
                                            "disclaimer": "Portfolio case study using fictional data. Not an employer record and makes no claims about employer outcomes."}
                                           for i, (slug, t, lab, ch, sc, ap, te, fw, dl) in enumerate(CASES)])
    if not await db.articles.count_documents({}):
        await db.articles.insert_one({"id": "why-interactive-labs", "slug": "why-interactive-labs", "title": "Why this portfolio uses interactive labs", "published": True, "date": now()[:10],
                                      "body": "This portfolio lets you run the kinds of governance, risk, delivery and AI workflows I work with, using fictional data. Every action is processed by a real backend, persisted, and logged so you can inspect how the workflow behaves."})


CONTENT_FIELDS = {
    "experience": {"employer", "title", "start", "end", "labs", "highlights", "order", "published", "note"},
    "skills": {"category", "name", "labs", "order"},
    "certifications": {"name", "issuer", "status", "date", "credential_url", "order"},
    "case_studies": {"title", "lab", "challenge", "scope", "approach", "technology", "frameworks", "deliverables", "evidence", "published", "order", "disclaimer"},
    "articles": {"title", "body", "published", "date"},
}
PROFILE_FIELDS = {"name", "site_title", "headline", "supporting", "summary", "metrics", "github_url", "linkedin_url", "public_email", "location", "d3_command"}


def clean_item(coll, data):
    out = {}
    for k, v in (data or {}).items():
        if k not in CONTENT_FIELDS[coll]:
            continue
        if isinstance(v, str):
            v = v[:8000]
        elif isinstance(v, list):
            v = [str(x)[:500] for x in v][:50]
        elif not isinstance(v, (bool, int, float)) and v is not None:
            continue
        out[k] = v
    return out


async def bundle(admin=False):
    q = {} if admin else {"published": {"$ne": False}}
    return {"profile": await db.content.find_one({"key": "profile"}, P),
            "experience": await db.experience.find(q, P).sort("order", 1).to_list(100),
            "skills": await db.skills.find({}, P).sort("order", 1).to_list(500),
            "certifications": await db.certifications.find({}, P).sort("order", 1).to_list(100),
            "case_studies": await db.case_studies.find(q, P).sort("order", 1).to_list(100),
            "articles": await db.articles.find(q, P).sort("date", -1).to_list(100),
            "has_resume": bool(await db.files.find_one({"kind": "resume"}, {"_id": 1}))}
