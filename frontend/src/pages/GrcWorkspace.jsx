import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Search, Download, RotateCcw, Play, Loader2, CheckCircle2 } from "lucide-react";
import { api, download, errMsg } from "../lib/api";
import { useLab, resetDemo } from "./LabPage";
import { ActionForm } from "../components/ActionForm";
import { Dashboard } from "../components/Dashboard";
import { Approvals, ExecutionList } from "../components/Executions";
import { Badge, Card, SimNotice, fmt } from "../components/kit";

const F = (n, l, t = "text", x = {}) => ({ n, l, t, ...x });
const MODULES = [
  ["policy", "Policies", ["number", "title", "version", "category", "state", "effective_date"]], ["control", "Controls", ["number", "ref", "name", "policy", "state"]],
  ["assessment", "Control Assessments", ["number", "control", "result", "issue", "created_at"]], ["campaign", "Acknowledgment Campaigns", ["number", "policy", "groups", "due_date", "state", "final_completion_pct"]],
  ["ack", "Acknowledgments", ["number", "campaign", "employee", "group", "state", "acknowledged_at", "reminders"]], ["exception", "Policy Exceptions", ["number", "policy", "department", "risk_rating", "approver", "state", "expires"]],
  ["risk", "Risks", ["number", "statement", "inherent", "residual", "rating", "treatment", "state"]], ["issue", "Issues", ["number", "title", "source", "severity", "control", "state"]],
  ["task", "Remediation Tasks", ["number", "issue", "assigned_to", "priority", "sla_due", "state", "validation_result"]], ["notification", "Notifications", ["number", "to", "subject", "related", "channel", "created_at"]],
];
const ROLE_LABEL = (r) => r.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()).replace("Grc", "GRC");
const HIDE = new Set(["session", "lab", "type", "history", "id", "updated_at"]);
const LINKS = ["policy_id", "control_id", "issue_id", "campaign_id", "risk_id", "assessment_id"];
const Q = ["MFA enforced for privileged access?", "Access reviewed quarterly?", "Automated deprovisioning?", "Logging & monitoring in place?"];
const CREATE = {
  policy: { action: "create_policy", title: "New policy (Draft)", fields: [F("title", "Title", "text", { d: "Information Security Policy v4" }), F("category", "Category", "text", { d: "Information Security" }), F("regulations", "Applicable regulations (comma)", "text", { d: "NIST SP 800-53, ISO 27001, GLBA" }), F("control_objectives", "Control objectives (comma)", "text", { d: "Privileged access review, Encryption at rest" }), F("reviewers", "Reviewers (comma)", "text", { d: "Policy Reviewer (fictional)" }), F("approval_group", "Approval group", "text", { d: "Information Security Governance Committee" }), F("content", "Policy text", "textarea", { d: "Purpose, scope, requirements, exceptions and enforcement (fictional)." })] },
  campaign: { action: "create_campaign", title: "New acknowledgment campaign", fields: [F("policy_id", "Published policy", "record", { rt: "policy", rl: (r) => `${r.number} ${r.title} (${r.state})` }), F("groups", "Target groups (comma: Finance, IT, HR, Operations)", "text", { d: "Finance, IT" }), F("start_date", "Start", "date", { d: new Date().toISOString().slice(0, 10) }), F("due_date", "Due", "date", { d: new Date(Date.now() + 14 * 864e5).toISOString().slice(0, 10) }), F("reminder_days", "Reminder every (days)", "number", { d: 3 })] },
  exception: { action: "create_exception", title: "Request policy exception", fields: [F("policy_id", "Policy", "record", { rt: "policy", rl: (r) => `${r.number} ${r.title}` }), F("control_id", "Control", "record", { rt: "control", rl: (r) => `${r.number} ${r.name}` }), F("department", "Requesting department", "text", { d: "Finance" }), F("justification", "Business justification", "textarea", { d: "Legacy ERP cannot enforce MFA until Q3 upgrade." }), F("compensating_controls", "Compensating controls", "textarea", { d: "IP allowlisting, enhanced logging, weekly review" }), F("duration_days", "Duration (days)", "number", { d: 90 })] },
  risk: { action: "create_risk", title: "Identify risk", fields: [F("statement", "Risk statement", "textarea", { d: "Privileged accounts may be misused due to infrequent review" }), F("business_service", "Business service", "text", { d: "Online Banking (fictional)" }), F("assets", "Related assets (comma)", "text", { d: "Core Ledger DB, Admin Portal" }), F("category", "Category", "text", { d: "Cybersecurity" }), F("control_ids", "Associated controls", "multirecord", { rt: "control", rl: (r) => `${r.number} ${r.name}` })] },
  control: { action: "assess_control", title: "Perform control assessment", fields: [F("control_id", "Control", "record", { rt: "control", rl: (r) => `${r.number} ${r.name} (${r.state})` }), F("result", "Result", "select", { o: ["fail", "pass"], d: "fail" }), F("severity", "Issue severity if failed", "select", { o: ["High", "Critical", "Medium", "Low"], d: "High" }), F("notes", "Test notes", "textarea", { d: "3 of 20 sampled privileged accounts lacked review evidence." })] },
};

function TransitionForm({ rec, act, spec, role, employees, onDone }) {
  const [v, setV] = useState(() => Object.fromEntries(spec.requires.map((k) => [k, k === "employee" ? rec.employee : k === "decision" || k === "result" ? "pass" : k === "treatment" ? "Mitigate" : ""])));
  const [q, setQ] = useState(Object.fromEntries(Q.map((x) => [x, "yes"])));
  const go = async () => {
    try {
      const data = { ...v, ...(rec.type === "risk" && act === "assess" ? { questionnaire: q } : {}) };
      await api.post("/labs/grc/actions/transition", { id: rec.id, act, role, data });
      toast.success(`${act.replace(/_/g, " ")} done`);
      onDone();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="rounded-md border border-slate-200 p-3" data-testid={`grc-transition-${act}`}>
      <div className="grid gap-2 sm:grid-cols-2">
        {spec.requires.map((k) => (k === "decision" || k === "result" || k === "treatment" || k === "employee" ? (
          <select key={k} aria-label={k} className="rounded border border-slate-300 px-2 py-1 text-xs" value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} data-testid={`grc-transition-${act}-${k}`}>
            {(k === "treatment" ? ["Mitigate", "Transfer", "Avoid", "Accept"] : k === "employee" ? Object.values(employees).flat() : ["pass", "fail"]).map((o) => <option key={o}>{o}</option>)}
          </select>
        ) : <input key={k} placeholder={k.replace(/_/g, " ")} type={k === "due_date" ? "date" : "text"} className="rounded border border-slate-300 px-2 py-1 text-xs" value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} data-testid={`grc-transition-${act}-${k}`} />))}
        {rec.type === "risk" && act === "assess" && Q.map((x) => <label key={x} className="flex items-center justify-between gap-2 text-xs">{x}<select value={q[x]} onChange={(e) => setQ({ ...q, [x]: e.target.value })} className="rounded border px-1"><option>yes</option><option>no</option></select></label>)}
      </div>
      <button onClick={go} className="mt-2 rounded bg-teal-700 px-3 py-1 text-xs font-medium capitalize text-white hover:bg-teal-800" data-testid={`grc-do-${act}`}>{act.replace(/_/g, " ")}</button>
      <span className="ml-2 text-[10px] text-slate-500">Allowed: {spec.roles.map(ROLE_LABEL).join(", ")}</span>
    </div>
  );
}

function RecordView({ rec, records, meta, role, onDone, open }) {
  const [note, setNote] = useState("");
  const [att, setAtt] = useState({ name: "", description: "" });
  const specs = Object.entries(meta.transitions[rec.type] || {}).filter(([, sp]) => sp.from.includes(rec.state));
  const related = records.filter((r) => r.id !== rec.id && (LINKS.some((k) => r[k] === rec.id) || LINKS.some((k) => rec[k] === r.id)));
  const post = (a, body) => api.post(`/labs/grc/actions/${a}`, { id: rec.id, role, ...body }).then(() => { toast.success("Saved"); onDone(); }).catch((e) => toast.error(errMsg(e)));
  return (
    <div className="space-y-4" data-testid="grc-record-view">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-heading text-lg font-bold">{rec.number} · {rec.title || rec.name || rec.statement || rec.employee || rec.subject}</h3><Badge testid="grc-record-state">{rec.state || "—"}</Badge></div>
        {rec.seeded && <p className="mt-1 text-[11px] text-amber-700">Fictional seeded demonstration record</p>}
        <dl className="mt-4 grid gap-x-6 gap-y-2 text-xs sm:grid-cols-2 lg:grid-cols-3">{Object.entries(rec).filter(([k]) => !HIDE.has(k) && !k.endsWith("_id")).map(([k, v]) => <div key={k}><dt className="font-mono text-[10px] uppercase text-slate-500">{k.replace(/_/g, " ")}</dt><dd className="whitespace-pre-wrap text-slate-800">{fmt(v)}</dd></div>)}</dl>
      </Card>
      {specs.length > 0 && <Card><h4 className="mb-2 font-heading text-sm font-semibold">Available workflow actions (state: {rec.state})</h4><div className="space-y-2">{specs.map(([a, sp]) => <TransitionForm key={a + rec.updated_at} rec={rec} act={a} spec={sp} role={role} employees={meta.employees} onDone={onDone} />)}</div></Card>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card testid="grc-related-list"><h4 className="font-heading text-sm font-semibold">Related records ({related.length})</h4>{related.map((r) => <button key={r.id} onClick={() => open(r)} className="mt-2 flex w-full justify-between rounded border border-slate-100 px-2 py-1 text-left text-xs hover:border-teal-500"><span>{r.number} · {r.title || r.name || r.employee || r.subject || r.result}</span><Badge>{r.state || r.type}</Badge></button>)}</Card>
        <Card testid="grc-activity-stream"><h4 className="font-heading text-sm font-semibold">Activity stream & audit history</h4>
          <div className="mt-2 max-h-64 space-y-2 overflow-auto">{[...(rec.history || [])].reverse().map((h, i) => <div key={i} className="border-l-2 border-teal-200 pl-2 text-xs"><p className="text-slate-800">{h.text || h.kind}</p><p className="font-mono text-[10px] text-slate-500">{fmt(h.at)} · {ROLE_LABEL(h.by)} · {h.kind}</p></div>)}</div>
          <div className="mt-3 flex gap-2"><input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add work note" className="flex-1 rounded border border-slate-300 px-2 py-1 text-xs" data-testid="grc-work-note-input" /><button onClick={() => note && post("work_note", { text: note }).then(() => setNote(""))} className="rounded border border-slate-300 px-2 text-xs" data-testid="grc-work-note-add">Post</button></div>
          {["task", "control"].includes(rec.type) && <div className="mt-2 flex gap-2"><input value={att.name} onChange={(e) => setAtt({ ...att, name: e.target.value })} placeholder="Evidence file name" className="w-1/3 rounded border border-slate-300 px-2 py-1 text-xs" data-testid="grc-attach-name" /><input value={att.description} onChange={(e) => setAtt({ ...att, description: e.target.value })} placeholder="Description" className="flex-1 rounded border border-slate-300 px-2 py-1 text-xs" data-testid="grc-attach-desc" /><button onClick={() => post("attach", att)} className="rounded border border-slate-300 px-2 text-xs" data-testid="grc-attach-add">Attach</button></div>}
        </Card>
      </div>
    </div>
  );
}

const pick = (recs, t, f) => recs.filter((r) => r.type === t && (!f || f(r))).pop();
const tr = (rec, act, role, data = {}) => api.post("/labs/grc/actions/transition", { id: rec.id, act, role, data });
const A = async (a, role, body) => (await api.post(`/labs/grc/actions/${a}`, { role, ...body })).data;
const recs = async () => (await api.get("/labs/grc/records")).data;
const SCENARIO = [
  ["Policy Owner creates an Information Security Policy (Draft)", async (c) => { c.pol = (await A("create_policy", "policy_owner", CREATE.policy.fields.reduce((o, f) => ({ ...o, [f.n]: f.d }), {}))).record; return `${c.pol.number} created with ${c.pol.control_objectives.length} linked controls`; }],
  ["Submit for review", async (c) => (await tr(c.pol, "submit_for_review", "policy_owner")).data.message],
  ["Policy Reviewer completes review", async (c) => (await tr(c.pol, "complete_review", "policy_reviewer", { comment: "Scope and MFA requirements confirmed" })).data.message],
  ["Approver approves", async (c) => (await tr(c.pol, "approve", "approver", { comment: "Approved by governance committee" })).data.message],
  ["Publish", async (c) => (await tr(c.pol, "publish", "policy_owner")).data.message],
  ["Launch acknowledgment campaign (Finance + IT)", async (c) => { c.camp = (await A("create_campaign", "grc_admin", { policy_id: c.pol.id, groups: ["Finance", "IT"], start_date: new Date().toISOString().slice(0, 10), due_date: new Date(Date.now() + 14 * 864e5).toISOString().slice(0, 10), reminder_days: 3 })).record; return (await tr(c.camp, "launch", "grc_admin")).data.message + " — 6 acknowledgment tasks + notifications"; }],
  ["Employees acknowledge (4 of 6)", async (c) => { const acks = (await recs()).filter((r) => r.type === "ack" && r.campaign_id === c.camp.id).slice(0, 4); for (const a of acks) await tr(a, "acknowledge", "employee", { employee: a.employee }); return `${acks.length} acknowledged with timestamps; 2 pending`; }], // eslint-disable-line no-await-in-loop
  ["Control Owner requests a policy exception", async (c) => { const ctl = pick(await recs(), "control", (r) => r.policy_id === c.pol.id); c.exc = (await A("create_exception", "control_owner", { policy_id: c.pol.id, control_id: ctl.id, department: "Finance", justification: "Legacy ERP cannot enforce encryption until upgrade", compensating_controls: "Network isolation, DLP monitoring", duration_days: 90 })).record; return `${c.exc.number} requested`; }],
  ["Risk Analyst assesses exception risk", async (c) => (await tr(c.exc, "assess_risk", "risk_analyst", { likelihood: 3, impact: 4, compensating_effectiveness: 50 })).data.message],
  ["Approver approves exception (becomes Active)", async (c) => (await tr(c.exc, "approve", "approver", { comment: "Time-bound approval" })).data.message],
  ["Risk Analyst identifies & assesses the related risk", async (c) => { const ctl = pick(await recs(), "control", (r) => r.policy_id === c.pol.id); c.ctl = ctl; c.risk = (await A("create_risk", "risk_analyst", { statement: "Privileged access misuse", business_service: "Online Banking (fictional)", assets: ["Admin Portal"], category: "Cybersecurity", control_ids: [ctl.id] })).record; return (await tr(c.risk, "assess", "risk_analyst", { likelihood: 4, impact: 5, control_effectiveness: 20, questionnaire: { "Access reviewed quarterly?": "no" } })).data.message + " (threshold rule evaluated)"; }],
  ["Auditor records a FAILED control assessment → issue auto-created", async (c) => { await A("assess_control", "auditor", { control_id: c.ctl.id, result: "fail", severity: "High", notes: "Review evidence missing for 3 of 20 accounts" }); c.iss = pick(await recs(), "issue", (r) => r.control_id === c.ctl.id && r.state === "Identified"); return `${c.iss.number} created, linked to ${c.iss.control} / ${c.iss.assessment} / ${c.iss.risk}`; }],
  ["Issue Owner analyzes and assigns → remediation task generated", async (c) => { await tr(c.iss, "analyze", "issue_owner", { root_cause: "No recurring review owner" }); await tr(c.iss, "assign", "issue_owner", { remediation_owner: "Remediation Owner (fictional)", due_date: new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10), action_plan: "Perform review; automate quarterly campaign" }); c.task = pick(await recs(), "task", (r) => r.issue_id === c.iss.id); await tr(c.task, "assign", "issue_owner", { assigned_to: "Remediation Owner (fictional)" }); return `${c.task.number} assigned`; }],
  ["Remediation Owner works the task, attaches evidence, submits", async (c) => { await tr(c.iss, "start_remediation", "remediation_owner"); await tr(c.task, "start_work", "remediation_owner"); await A("attach", "remediation_owner", { id: c.task.id, name: "access-review-q3.xlsx", description: "Completed review with approvals" }); return (await tr(c.task, "submit_for_validation", "remediation_owner")).data.message; }],
  ["Auditor validates evidence; Issue Owner closes task", async (c) => { await tr(c.task, "validate", "auditor", { result: "pass" }); return (await tr(c.task, "close", "issue_owner", { closure_notes: "Validated by audit" })).data.message + " → issue moved to Validation"; }],
  ["Auditor validates & closes the issue → control & risk updated", async (c) => { await tr(c.iss, "validate", "auditor", { decision: "pass" }); const r = await recs(); return `Issue closed; control ${pick(r, "control", (x) => x.id === c.ctl.id).state}; risk residual ${pick(r, "risk", (x) => x.id === c.risk.id).residual}`; }],
  ["Generate the governance report (PDF)", async () => { await download("/labs/grc/report?format=pdf", "irm-governance-report.pdf"); return "irm-governance-report.pdf downloaded; dashboards reflect the new records"; }],
];

function Scenario({ onDone }) {
  const [ctx] = useState({});
  const [res, setRes] = useState([]);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    setRes([]);
    try {
      for (const [title, fn] of SCENARIO) {
        const out = await fn(ctx); // eslint-disable-line no-await-in-loop
        setRes((x) => [...x, { title, out }]);
      }
      toast.success("End-to-end governance workflow complete");
    } catch (e) { toast.error(errMsg(e)); setRes((x) => [...x, { title: "Stopped", out: errMsg(e), err: true }]); } finally { setBusy(false); onDone(); }
  };
  return (
    <Card testid="grc-e2e-scenario">
      <h3 className="font-heading text-base font-bold">Enterprise ServiceNow IRM — End-to-End Governance Workflow</h3>
      <p className="mt-1 text-xs text-slate-600">17 steps across 8 roles: Policy → Review → Approval → Publication → Campaign → Acknowledgments → Exception → Risk → Failed assessment → Issue → Remediation → Validation → Closure → Report. Each step calls the role-enforced backend.</p>
      <button onClick={run} disabled={busy} className="mt-3 inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm text-white hover:bg-teal-800 disabled:opacity-50" data-testid="grc-e2e-run">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}Run end-to-end scenario</button>
      <ol className="mt-4 space-y-2">{SCENARIO.map(([t], i) => <li key={t} className="flex gap-2 text-xs" data-testid={`grc-e2e-step-${i}`}>{res[i] && !res[i].err ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" /> : <span className="w-4 shrink-0 text-center font-mono text-slate-400">{i + 1}</span>}<span><b>{t}</b>{res[i] && <span className="block text-slate-600">{res[i].out}</span>}</span></li>)}</ol>
      {res.some((r) => r.err) && <p className="mt-2 text-xs text-rose-600">{res.find((r) => r.err).out}</p>}
    </Card>
  );
}

export default function GrcWorkspace() {
  const { records, dash, exes, approvals, refresh } = useLab("grc");
  const [meta, setMeta] = useState(null);
  const [role, setRole] = useState(localStorage.getItem("grc_role") || "grc_admin");
  const [mod, setMod] = useState("scenario");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  useEffect(() => { api.post("/labs/grc/actions/meta", {}).then((r) => setMeta(r.data)); }, []);
  useEffect(() => { localStorage.setItem("grc_role", role); }, [role]);
  const m = MODULES.find((x) => x[0] === mod);
  const rows = useMemo(() => (m ? records.filter((r) => r.type === m[0] && JSON.stringify(r).toLowerCase().includes(q.toLowerCase())).reverse() : []), [records, m, q]);
  const current = sel && records.find((r) => r.id === sel);
  const open = (r) => { setMod(r.type); setSel(r.id); };
  if (!meta) return <div className="p-10 text-sm text-slate-500">Loading workspace…</div>;
  const nav = [["scenario", "▶ End-to-End Scenario"], ["dashboard", "Executive Dashboard"], ...MODULES.map(([k, l]) => [k, l]), ["automation", "Workflow Executions"]];
  return (
    <div>
      <section className="bg-[#0B132B] text-white"><div className="mx-auto max-w-[1400px] px-5 py-8 sm:px-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-teal-300">Flagship · ServiceNow IRM-style workspace</p>
        <h1 className="mt-2 font-heading text-3xl font-extrabold tracking-tight" data-testid="grc-title">Enterprise IRM — Policy & Compliance, Risk, Issues</h1>
        <div className="mt-4 flex flex-wrap items-center gap-3 text-xs">
          <label className="flex items-center gap-2">Acting as<select value={role} onChange={(e) => setRole(e.target.value)} className="rounded bg-white px-2 py-1.5 text-slate-900" data-testid="grc-role-switcher">{meta.roles.map((r) => <option key={r} value={r}>{ROLE_LABEL(r)}</option>)}</select></label>
          <button onClick={() => resetDemo(refresh)} className="inline-flex items-center gap-1 rounded border border-slate-600 px-3 py-1.5 hover:border-rose-400" data-testid="grc-reset"><RotateCcw className="h-3 w-3" />Reset Demo</button>
          <button onClick={() => download("/labs/grc/report?format=pdf", "irm-governance-report.pdf")} className="inline-flex items-center gap-1 rounded border border-slate-600 px-3 py-1.5" data-testid="grc-report-pdf"><Download className="h-3 w-3" />Governance PDF</button>
          <button onClick={() => download("/labs/grc/report?format=csv", "irm-records.csv")} className="inline-flex items-center gap-1 rounded border border-slate-600 px-3 py-1.5" data-testid="grc-report-csv"><Download className="h-3 w-3" />CSV</button>
          <button onClick={() => api.post("/labs/grc/actions/run_monitoring", {}).then(() => { toast.success("Monitoring rules executed"); refresh(); })} className="rounded border border-slate-600 px-3 py-1.5" data-testid="grc-run-monitoring">Run SLA / reminder monitoring</button>
        </div>
      </div></section>
      <div className="mx-auto grid max-w-[1400px] gap-5 px-5 py-6 sm:px-8 lg:grid-cols-[230px_1fr]">
        <nav className="h-fit rounded-lg border border-slate-200 bg-white p-2 lg:sticky lg:top-20" data-testid="grc-navigator" aria-label="Application navigator">
          <p className="px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">Application navigator</p>
          {nav.map(([k, l]) => <button key={k} onClick={() => { setMod(k); setSel(null); }} className={`block w-full rounded px-2 py-1.5 text-left text-xs ${mod === k ? "bg-teal-50 font-semibold text-teal-800" : "text-slate-700 hover:bg-slate-50"}`} data-testid={`grc-nav-${k}`}>{l}{m && k === mod ? ` (${rows.length})` : ""}</button>)}
        </nav>
        <div className="min-w-0 space-y-4">
          <SimNotice>Independent ServiceNow-style simulation (not an official ServiceNow product). Role permissions are enforced by the backend. Seeded records are fictional demonstration data.</SimNotice>
          {mod === "scenario" && <Scenario onDone={refresh} />}
          {mod === "dashboard" && dash && <><Dashboard dash={dash} /><Card testid="grc-campaign-metrics"><h4 className="font-heading text-sm font-semibold">Campaign completion (calculated from acknowledgment records)</h4><table className="mt-2 w-full text-xs"><thead><tr className="text-left text-slate-500">{["campaign", "policy", "state", "total", "acknowledged", "pending", "overdue", "completion_pct"].map((h) => <th key={h}>{h.replace("_", " ")}</th>)}</tr></thead><tbody>{dash.campaigns.map((c) => <tr key={c.campaign} className="border-t border-slate-100">{Object.values(c).map((v, i) => <td key={i} className="py-1">{v}</td>)}</tr>)}</tbody></table></Card></>}
          {mod === "automation" && <><Card><Approvals approvals={approvals.filter((a) => a.lab === "grc")} onDone={refresh} /></Card><ExecutionList executions={exes} onChanged={refresh} /></>}
          {m && !current && (
            <>
              {CREATE[mod] && <ActionForm key={role + mod} lab="grc" form={CREATE[mod]} records={records} onDone={refresh} extra={{ role }} />}
              <div className="overflow-hidden rounded-lg border border-slate-200 bg-white" data-testid={`grc-list-${mod}`}>
                <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-3 py-2"><h3 className="font-heading text-sm font-semibold">{m[1]}</h3><div className="relative"><Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-slate-400" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter" className="rounded border border-slate-300 py-1 pl-7 pr-2 text-xs" data-testid="grc-list-filter" /></div></div>
                <div className="max-h-[520px] overflow-auto"><table className="w-full text-xs"><thead className="sticky top-0 bg-slate-50"><tr>{m[2].map((c) => <th key={c} className="px-3 py-2 text-left text-[10px] uppercase tracking-wider text-slate-500">{c.replace(/_/g, " ")}</th>)}</tr></thead>
                  <tbody>{rows.map((r, i) => <tr key={r.id} onClick={() => setSel(r.id)} className="cursor-pointer border-t border-slate-100 hover:bg-teal-50/40" data-testid={`grc-row-${mod}-${i}`}>{m[2].map((c) => <td key={c} className="max-w-xs truncate px-3 py-2">{c === "state" || c === "result" || c === "risk_rating" || c === "rating" ? <Badge>{fmt(r[c])}</Badge> : fmt(r[c])}</td>)}</tr>)}</tbody></table></div>
              </div>
            </>
          )}
          {current && <><button onClick={() => setSel(null)} className="text-xs text-teal-700" data-testid="grc-back-to-list">← Back to {m?.[1]}</button><RecordView rec={current} records={records} meta={meta} role={role} onDone={refresh} open={open} /></>}
        </div>
      </div>
    </div>
  );
}
