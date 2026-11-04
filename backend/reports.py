import csv
import io
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

NAVY = colors.HexColor("#0B132B")
TEAL = colors.HexColor("#0D9488")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=18, alignment=0)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=TEAL, fontSize=12, spaceBefore=10)
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontSize=8.5, leading=11)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=7, textColor=colors.grey)

REPORT_TYPES = {
    "irm": [("control", ["ref", "title", "status", "owner", "last_tested"]), ("assessment", ["control_ref", "result", "notes", "created_at"]),
            ("finding", ["title", "severity", "risk_score", "status"]), ("remediation", ["title", "owner", "due_date", "status"]), ("exception", ["policy", "status", "duration_days"])],
    "servicenow": [("sn_table", ["name", "label", "version"]), ("sn_record", ["number", "table", "created_by", "rules_fired"]), ("acl_log", ["user", "table", "operation", "decision"]),
                   ("api_log", ["method", "path", "user", "status_code", "latency_ms"]), ("sn_change", ["number", "title", "state"]), ("update_set", ["change", "table", "from_version", "to_version", "state"])],
    "cyber": [("asset", ["name", "asset_type", "criticality", "data_class"]), ("vulnerability", ["asset", "title", "cvss", "severity", "status"]),
              ("cyber_risk", ["title", "asset", "inherent", "residual", "rating", "status"]), ("remediation", ["title", "severity", "due_date", "status"])],
    "audit": [("engagement", ["name", "framework", "status"]), ("control_test", ["title", "framework", "status", "exceptions"]), ("evidence_request", ["title", "status"]),
              ("audit_finding", ["title", "severity", "status", "due_date"]), ("action_plan", ["title", "owner", "due_date", "status"])],
    "vendor": [("vendor", ["name", "tier", "inherent", "residual", "status", "reviewer"]), ("questionnaire", ["vendor", "status", "compliance"]), ("vendor_remediation", ["vendor", "title", "status"])],
    "aigov": [("ai_system", ["name", "tier", "status", "owner"]), ("ai_assessment", ["system", "kind", "status"]), ("model_evaluation", ["system", "metric", "value", "threshold", "result"]), ("ai_incident", ["system", "severity", "status"])],
    "agents": [("agent", ["name", "version", "status", "model"]), ("agent_run", ["agent_name", "mode", "status", "latency_ms", "tokens_in", "tokens_out", "cost_usd"]),
               ("security_event", ["agent", "kind", "decision", "detail"]), ("eval_run", ["agent", "mode", "accuracy", "live_cases"])],
    "pm": [("project", ["name", "health", "budget", "spent"]), ("milestone", ["project", "name", "due_date", "status"]), ("escalation", ["project", "title", "status"]), ("status_report", ["project", "health", "summary"])],
    "safe": [("team", ["name", "focus"]), ("feature", ["name", "kind", "team", "iteration", "wsjf", "status"]), ("dependency", ["consumer", "provider", "status"]),
             ("program_risk", ["description", "owner", "roam"]), ("objective", ["team", "description", "business_value", "progress", "actual_value"]), ("ia_report", ["pi", "art_predictability", "features_done", "features_planned"])],
    "ir": [("incident", ["title", "severity", "phase", "status"]), ("ir_task", ["title", "status"]), ("recovery_item", ["process", "rto_hours", "hours_to_recover", "status"]),
           ("timeline", ["event", "at"]), ("bia_process", ["process", "rto_hours", "rpo_hours", "priority"])],
    "grc": [("policy", ["number", "title", "version", "state", "effective_date"]), ("campaign", ["number", "policy", "state", "due_date", "final_completion_pct"]), ("ack", ["number", "campaign", "employee", "state", "acknowledged_at"]),
            ("exception", ["number", "policy", "department", "risk_rating", "state", "expires"]), ("risk", ["number", "statement", "inherent", "residual", "rating", "state"]), ("control", ["number", "ref", "name", "state"]),
            ("assessment", ["number", "control", "result", "issue"]), ("issue", ["number", "title", "severity", "state", "validation"]), ("task", ["number", "issue", "assigned_to", "state", "sla_due", "validation_result"])],
}


def cell(v):
    if isinstance(v, list):
        v = ", ".join(map(str, v))
    return Paragraph(escape(str(v if v is not None else "—"))[:400], BODY)


def table(headers, rows):
    data = [[Paragraph(f"<b>{escape(h)}</b>", BODY) for h in headers]] + [[cell(c) for c in r] for r in rows]
    t = Table(data, repeatRows=1, colWidths=[7.2 * inch / len(headers)] * len(headers))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def build_pdf(title, subtitle, sections):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch, topMargin=0.6 * inch, bottomMargin=0.6 * inch, title=title)
    els = [Paragraph(escape(title), H1), Paragraph(escape(subtitle), SMALL),
           Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Seun Olawepo Enterprise Technology Lab · FICTIONAL DEMO DATA", SMALL), Spacer(1, 8)]
    for heading, kind, data in sections:
        els.append(Paragraph(escape(heading), H2))
        if kind == "table":
            els.append(table(*data) if data[1] else Paragraph("No records.", BODY))
        else:
            for line in str(data).split("\n"):
                els.append(Paragraph(escape(line) or "&nbsp;", BODY))
    doc.build(els)
    return buf.getvalue()


def lab_sections(lab, kpis, records, executions):
    secs = [("Key indicators", "table", (["Indicator", "Value"], [[k["label"], k["value"]] for k in kpis.get("kpis", [])]))]
    for type_, cols in REPORT_TYPES.get(lab, []):
        rows = [[r.get(c) for c in cols] for r in records if r["type"] == type_][-60:]
        secs.append((type_.replace("_", " ").title(), "table", (cols, rows)))
    secs.append(("Automation execution log", "table", (["Execution", "Workflow", "Status", "Started"], [[e["id"], e["name"], e["status"], e["created_at"][:19]] for e in executions[-40:]])))
    return secs


def execution_sections(exe):
    secs = [("Summary", "table", (["Field", "Value"], [["Workflow", exe["name"]], ["Status", exe["status"]], ["Trigger", exe["trigger"]], ["Started", exe["created_at"]], ["Updated", exe["updated_at"]]]))]
    secs.append(("Steps", "table", (["#", "Step", "Status", "Attempts", "Output / Error"], [[i + 1, s["name"], s["status"], s["attempts"], s.get("error") or s.get("output")] for i, s in enumerate(exe["steps"])])))
    if exe["ctx"].get("report"):
        secs.append(("Final report", "text", exe["ctx"]["report"]))
    return secs


def to_csv(lab, records):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["record_type", "id", "created_at", "fields"])
    cols = dict(REPORT_TYPES.get(lab, []))
    for r in records:
        keys = cols.get(r["type"], [k for k in r if k not in ("session", "lab", "type", "id", "created_at", "updated_at")])
        w.writerow([r["type"], r["id"], r["created_at"], "; ".join(f"{k}={r.get(k)}" for k in keys)])
    return buf.getvalue()
