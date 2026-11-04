import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Play, Loader2, CheckCircle2, RefreshCw, ArrowRight } from "lucide-react";
import { api, download, errMsg } from "../lib/api";
import { Dashboard } from "../components/Dashboard";
import { Badge, Card, fmt } from "../components/kit";
import { RecTable } from "../components/irm/PolicyPanels";

const tr = (rec, act, role, data = {}) => api.post("/labs/grc/actions/transition", { id: rec.id, act, role, data });
const A = async (a, role, body = {}) => (await api.post(`/labs/grc/actions/${a}`, { role, ...body })).data;
const recs = async () => (await api.get("/labs/grc/records")).data;
const byId = (r, id) => r.find((x) => x.id === id);
const iso = (d) => new Date(Date.now() + d * 864e5).toISOString().slice(0, 10);
const FLOW = ["UCF regulatory content (simulated feed)", "Integration service", "ServiceNow IRM", "Compliance monitoring", "Impact assessment", "Remediation"];

const STEPS = [
  ["Simulated UCF feed publishes an updated requirement", async (c) => { c.r = await A("ucf_simulate_update", "compliance_owner", { change_type: "Modified" }); const n = c.r.notice; return `${n.number}: ${n.change_type} ${n.ucf_ref} → version ${n.new_version} (SIMULATED)`; }],
  ["Integration service receives the change notification", async (c) => `Sync ${c.r.sync_run.number} · execution ${c.r.execution.id} ${c.r.execution.status} (${c.r.execution.steps.length} steps) · ${c.r.sync_run.result}`],
  ["Affected regulatory requirement identified", async (c) => { c.ch = c.r.change; return `${c.ch.requirement} · ${c.ch.framework} – ${c.ch.requirement_title} (${c.ch.previous_version} → ${c.ch.updated_version})`; }],
  ["Regulatory change record created", async (c) => `${c.ch.number} · ${c.ch.state} · risk ${c.ch.risk_rating} · UCF ref ${c.ch.ucf_ref}`],
  ["Related compliance obligation identified", async (c) => `${c.ch.obligation} linked to ${c.ch.requirement}`],
  ["Associated controls and policies identified", async (c) => `Controls: ${c.ch.controls.join(", ") || "none"} · Policies: ${c.ch.policies.join(", ") || "none"}`],
  ["Compliance owner receives an in-app notification", async (c) => { const n = (await recs()).filter((r) => r.type === "notification" && r.related_id === c.ch.id).pop(); return `${n.number} → ${n.to}: ${n.subject}`; }],
  ["Regulatory impact assessment task created", async (c) => { const r = await recs(); const i = byId(r, c.ch.impact_id); return `${i.number} assigned to ${i.assigned_to}, due ${i.due_date}`; }],
  ["Owner reviews the change (AI agent drafts advisory analysis; human accepts)", async (c) => { const a = await A("ucf_ai_analyze", "compliance_owner", { id: c.ch.id }); await tr(c.ch, "review_ai", "compliance_owner", { ai_decision: "accept", comment: "Reviewed by compliance owner – advisory only" }); return `Agent run ${a.run.id} (${a.run.mode}) · human review recorded`; }],
  ["Owner determines existing controls are NOT sufficient", async (c) => (await tr(c.ch, "assess_impact", "compliance_owner", { controls_sufficient: "no", policy_revision: "yes", assessment_notes: "Current control scope does not cover the updated requirement" })).data.message],
  ["Gap → issue and remediation task automatically created", async (c) => { const r = await recs(); c.ch = byId(r, c.ch.id); c.iss = byId(r, c.ch.issue_ids[0]); c.task = r.find((t) => t.type === "task" && t.issue_id === c.iss.id); return `${c.iss.number} (${c.iss.state}) · ${c.task.number} (${c.task.state})`; }],
  ["Policy revision workflow triggered", async (c) => { c.pol = byId(await recs(), c.ch.revision_policy_ids[0]); return `${c.pol.number} v${c.pol.version} Draft (supersedes ${c.pol.supersedes})`; }],
  ["Revised policy: Draft → Review → Approved → Published", async (c) => { await tr(c.pol, "submit_for_review", "policy_owner"); await tr(c.pol, "complete_review", "policy_reviewer", { comment: "Updated scope reviewed" }); await tr(c.pol, "approve", "approver", { comment: "Approved for publication" }); return (await tr(c.pol, "publish", "policy_owner")).data.message; }],
  ["Policy acknowledgment campaign launched", async (c) => { const camp = (await A("create_campaign", "grc_admin", { policy_id: c.pol.id, groups: ["IT", "Operations"], start_date: iso(0), due_date: iso(14), reminder_days: 3 })).record; return (await tr(camp, "launch", "grc_admin")).data.message; }],
  ["Remediation owner completes work and attaches evidence", async (c) => { await tr(c.iss, "start_remediation", "remediation_owner"); await tr(c.task, "start_work", "remediation_owner"); await A("attach", "remediation_owner", { id: c.task.id, name: "control-update-evidence.pdf", description: "Configuration change and test results (fictional)" }); return (await tr(c.task, "submit_for_validation", "remediation_owner")).data.message; }],
  ["Updated controls are reassessed", async (c) => { const out = []; for (const id of c.ch.control_ids) { const a = await A("assess_control", "auditor", { control_id: id, result: "pass", severity: "Low", notes: "Control re-tested against updated requirement" }); out.push(a.record?.number || "assessed"); } return `${out.length} control assessment(s) passed: ${out.join(", ")}`; }], // eslint-disable-line no-await-in-loop
  ["Remediation evidence reviewed and validated", async (c) => { await tr(c.task, "validate", "auditor", { result: "pass" }); await tr(c.task, "close", "issue_owner", { closure_notes: "Evidence validated" }); return (await tr(c.iss, "validate", "auditor", { decision: "pass" })).data.message; }],
  ["Regulatory change formally closed after validation", async (c) => { await tr(c.ch, "submit_for_validation", "compliance_owner"); return (await tr(c.ch, "validate", "auditor", { decision: "pass", closure_evidence: "Policy published, controls re-tested, issue closed" })).data.message; }],
  ["Executive compliance dashboard updates", async () => { const d = await A("ucf_dashboard", "executive"); const k = Object.fromEntries(d.kpis.map((x) => [x.label, x.value])); return `Closed changes: ${k["Regulatory changes closed"]} · awaiting assessment: ${k["Awaiting impact assessment"]} · open remediation tasks: ${k["Open remediation tasks"]}`; }],
  ["Regulatory change impact report generated", async (c) => { await download(`/labs/grc/ucf/report/${c.ch.id}`, `regulatory-change-${c.ch.number}.pdf`); return `regulatory-change-${c.ch.number}.pdf downloaded`; }],
];

function Demo({ onDone, open }) {
  const [ctx, setCtx] = useState({});
  const [res, setRes] = useState([]);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    const c = {};
    setCtx(c); setBusy(true); setRes([]);
    try {
      for (const [title, fn] of STEPS) { const out = await fn(c); setRes((x) => [...x, { title, out }]); } // eslint-disable-line no-await-in-loop
      toast.success("Regulatory change processed end-to-end");
    } catch (e) { setRes((x) => [...x, { out: errMsg(e), err: true }]); toast.error(errMsg(e)); } finally { setBusy(false); onDone(); }
  };
  return (
    <Card testid="ucf-demo">
      <h3 className="font-heading text-base font-bold">Recruiter demo: UCF detects a regulatory requirement change</h3>
      <p className="mt-1 text-xs text-slate-600">{STEPS.length} steps from simulated notification through impact assessment, policy and control updates, remediation, validation and closure. Every step calls the role-enforced backend and writes persistent records with a timestamped audit trail in your own demo session.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button onClick={run} disabled={busy} className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm text-white hover:bg-teal-800 disabled:opacity-50" data-testid="ucf-demo-run">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}Trigger simulated regulatory update</button>
        {ctx.ch && !busy && <button onClick={() => open(ctx.ch)} className="rounded-md border border-slate-300 px-3 py-2 text-xs" data-testid="ucf-demo-open-change">Open {ctx.ch.number}</button>}
      </div>
      <ol className="mt-4 space-y-2">{STEPS.map(([t], i) => <li key={t} className="flex gap-2 text-xs" data-testid={`ucf-demo-step-${i}`}>{res[i] && !res[i].err ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" /> : <span className="w-4 shrink-0 text-center font-mono text-slate-400">{i + 1}</span>}<span><b>{t}</b>{res[i] && <span className={`block ${res[i].err ? "text-rose-600" : "text-slate-600"}`}>{res[i].out}</span>}</span></li>)}</ol>
      {res.some((r) => r.err) && <p className="mt-2 text-xs text-rose-600" data-testid="ucf-demo-error">{res.find((r) => r.err).out}</p>}
    </Card>
  );
}

function Config({ records, role, onDone }) {
  const cfg = records.find((r) => r.type === "ucf_config");
  const [fw, setFw] = useState(cfg?.frameworks || []);
  const [status, setStatus] = useState(null);
  useEffect(() => { api.get("/ucf/status").then((r) => setStatus(r.data)); }, []);
  if (!cfg) return null;
  const all = ["HIPAA", "HITRUST", "GLBA", "CCPA", "GDPR", "NYDFS", "PCI DSS", "SOC 2", "ISO 27001", "NIST CSF", "NIST SP 800-53", "FedRAMP", "SOX ITGC", "ISO/IEC 42001"];
  const save = () => A("ucf_config_update", role, { frameworks: fw, auto_create_changes: cfg.auto_create_changes, notify_owners: cfg.notify_owners, impact_due_days: cfg.impact_due_days }).then(() => { toast.success("Configuration saved"); onDone(); }).catch((e) => toast.error(errMsg(e)));
  const rows = ["source", "connection_status", "schedule", "dedupe_key", "notification_channel", "owner_routing", "failure_handling", "credentials", "last_sync", "last_status", "last_result"];
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card testid="ucf-config"><h4 className="font-heading text-sm font-semibold">Integration configuration (administrator view)</h4>
        <dl className="mt-2 space-y-1 text-xs">{rows.map((k) => <div key={k} className="grid grid-cols-[140px_1fr] gap-2"><dt className="font-mono text-[10px] uppercase text-slate-500">{k.replace(/_/g, " ")}</dt><dd data-testid={`ucf-config-${k}`}>{fmt(cfg[k])}</dd></div>)}</dl>
        <p className="mt-3 text-xs font-semibold">Subscribed frameworks</p>
        <div className="mt-1 flex flex-wrap gap-2 text-xs">{all.map((f) => <label key={f} className="flex items-center gap-1"><input type="checkbox" checked={fw.includes(f)} onChange={() => setFw(fw.includes(f) ? fw.filter((x) => x !== f) : [...fw, f])} data-testid={`ucf-fw-${f.replace(/[^a-z0-9]/gi, "")}`} />{f}</label>)}</div>
        <button onClick={save} className="mt-3 rounded bg-teal-700 px-3 py-1 text-xs text-white" data-testid="ucf-config-save">Save configuration (GRC Administrator)</button>
      </Card>
      <Card testid="ucf-scheduled"><h4 className="font-heading text-sm font-semibold">Scheduled daily check (shared monitor)</h4>
        <p className="mt-1 text-xs text-slate-600">{status?.mode}. {status?.schedule}. Scheduled checks run against a separate shared monitor; your demo session only changes when you sync or trigger an update.</p>
        <RecTable rows={status?.recent_scheduled_checks || []} cols={["at", "status", "result", "published"]} testid="ucf-scheduled-table" empty="No scheduled checks recorded yet" />
      </Card>
    </div>
  );
}

const TABS = [["overview", "Integration Dashboard"], ["demo", "Recruiter Demo"], ["changes", "Regulatory Changes"], ["requirements", "Requirement Inventory"], ["obligations", "Compliance Obligations"], ["notices", "Change Notifications"], ["syncs", "Sync History"], ["config", "Integration Configuration"]];
const LISTS = {
  changes: ["reg_change", ["number", "framework", "ucf_ref", "change_type", "risk_rating", "date_received", "effective_date", "remediation_status", "state"]],
  requirements: ["requirement", ["number", "ucf_ref", "framework", "title", "version", "control_refs", "state"]],
  obligations: ["obligation", ["number", "title", "controls", "policies", "owner", "state"]],
  notices: ["feed_notice", ["number", "ucf_ref", "change_type", "new_version", "state", "reg_change"]],
  syncs: ["sync_run", ["number", "trigger", "state", "result", "duplicates_skipped", "started_at"]],
};

export default function UcfModule({ records, role, refresh, open }) {
  const [tab, setTab] = useState("overview");
  const [dash, setDash] = useState(null);
  const load = () => A("ucf_dashboard", role).then(setDash);
  useEffect(() => { load(); }, [records]); // eslint-disable-line react-hooks/exhaustive-deps
  const sync = (fail) => A("ucf_sync", role, { simulate_failure: fail }).then((r) => { (r.sync_run.state === "Failed" ? toast.error : toast.success)(`${r.sync_run.number}: ${r.sync_run.result}`); refresh(); }).catch((e) => toast.error(errMsg(e)));
  const L = LISTS[tab];
  const it = dash?.integration;
  return (
    <div className="space-y-4" data-testid="ucf-module">
      <Card>
        <p className="font-mono text-[10px] uppercase tracking-wider text-teal-700">Featured · ServiceNow IRM + UCF</p>
        <h3 className="font-heading text-lg font-bold" data-testid="ucf-title">Automated Regulatory Change Monitoring</h3>
        <p className="mt-1 text-xs text-amber-700" data-testid="ucf-sim-label">SIMULATED UCF feed – no live UCF connection or licensed credentials are configured. Regulatory content is fictional and is not legal text.</p>
        <div className="mt-3 flex flex-wrap items-center gap-1 text-[11px]" data-testid="ucf-architecture">{FLOW.map((f, i) => <span key={f} className="flex items-center gap-1"><span className="rounded border border-slate-300 bg-slate-50 px-2 py-1">{f}</span>{i < FLOW.length - 1 && <ArrowRight className="h-3 w-3 text-slate-400" />}</span>)}</div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <button onClick={() => sync(false)} className="inline-flex items-center gap-1 rounded border border-slate-300 px-3 py-1.5 hover:border-teal-600" data-testid="ucf-sync-now"><RefreshCw className="h-3 w-3" />Check UCF feed now</button>
          <button onClick={() => sync(true)} className="rounded border border-slate-300 px-3 py-1.5 hover:border-rose-500" data-testid="ucf-sync-fail">Simulate connector failure</button>
          {it && <span className="self-center text-slate-600" data-testid="ucf-last-sync">Last sync: <Badge>{it.last_status}</Badge> {fmt(it.last_sync)} · {it.last_result}</span>}
        </div>
      </Card>
      <div className="flex flex-wrap gap-1 border-b border-slate-200">{TABS.map(([k, l]) => <button key={k} onClick={() => setTab(k)} className={`px-3 py-2 text-xs ${tab === k ? "border-b-2 border-teal-700 font-semibold text-teal-800" : "text-slate-600"}`} data-testid={`ucf-tab-${k}`}>{l}</button>)}</div>
      {tab === "overview" && dash && <><Dashboard dash={dash} /><Card testid="ucf-integration-status"><h4 className="font-heading text-sm font-semibold">Integration status</h4><dl className="mt-2 grid gap-2 text-xs sm:grid-cols-3">{Object.entries(it).map(([k, v]) => <div key={k}><dt className="font-mono text-[10px] uppercase text-slate-500">{k.replace(/_/g, " ")}</dt><dd>{fmt(v)}</dd></div>)}</dl></Card></>}
      {tab === "demo" && <Demo onDone={refresh} open={open} />}
      {tab === "config" && <Config records={records} role={role} onDone={refresh} />}
      {L && <Card testid={`ucf-list-${tab}`}><RecTable rows={records.filter((r) => r.type === L[0]).reverse()} cols={L[1]} onRow={open} testid={`ucf-table-${tab}`} /></Card>}
    </div>
  );
}

export function UcfAdmin() {
  const [d, setD] = useState(null);
  const load = () => api.get("/admin/ucf/monitor").then((r) => setD(r.data)).catch((e) => toast.error(errMsg(e)));
  useEffect(() => { load(); }, []);
  const run = () => api.post("/admin/ucf/run-check").then(() => { toast.success("Scheduled check executed"); load(); }).catch((e) => toast.error(errMsg(e)));
  if (!d) return <p className="text-sm text-slate-500">Loading…</p>;
  return (
    <div className="space-y-4" data-testid="admin-ucf">
      <Card><h3 className="font-heading text-base font-semibold">UCF integration monitor (shared, simulated)</h3><p className="mt-1 text-xs text-slate-600">{d.config.mode} · {d.config.schedule}</p>
        <button onClick={run} className="mt-2 rounded bg-teal-700 px-3 py-1.5 text-xs text-white" data-testid="admin-ucf-run-check">Run scheduled check now</button></Card>
      <Dashboard dash={d.metrics} />
      <Card><h4 className="font-heading text-sm font-semibold">Scheduled checks</h4><RecTable rows={d.scheduled_checks} cols={["at", "run_id", "status", "result", "published"]} testid="admin-ucf-checks" /></Card>
      <Card><h4 className="font-heading text-sm font-semibold">Sync history</h4><RecTable rows={d.sync_runs} cols={["number", "trigger", "state", "result", "started_at"]} testid="admin-ucf-syncs" /></Card>
      <Card><h4 className="font-heading text-sm font-semibold">Regulatory changes</h4><RecTable rows={d.changes} cols={["number", "framework", "change_type", "risk_rating", "state"]} testid="admin-ucf-changes" /></Card>
    </div>
  );
}
