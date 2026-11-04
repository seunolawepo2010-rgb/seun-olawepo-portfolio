import { useState } from "react";
import { toast } from "sonner";
import { Download, Bot } from "lucide-react";
import { api, download, errMsg } from "../../lib/api";
import { Badge, Card, fmt } from "../kit";

export const label = (r) => r.title || r.name || r.statement || r.employee || r.subject || r.result || r.risk || r.trigger;

export function RecTable({ rows, cols, onRow, testid, empty = "No records" }) {
  return (
    <div className="max-h-[520px] overflow-auto" data-testid={testid}>
      <table className="w-full text-xs"><thead className="sticky top-0 bg-slate-50"><tr>{cols.map((c) => <th key={c} className="px-3 py-2 text-left text-[10px] uppercase tracking-wider text-slate-500">{c.replace(/_/g, " ")}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={r.id || i} onClick={() => onRow && onRow(r)} className={`border-t border-slate-100 ${onRow ? "cursor-pointer hover:bg-teal-50/40" : ""}`} data-testid={`${testid}-row-${i}`}>{cols.map((c) => <td key={c} className="max-w-xs truncate px-3 py-2">{["state", "result", "risk_rating", "rating", "change_type", "status"].includes(c) ? <Badge>{fmt(r[c])}</Badge> : fmt(r[c])}</td>)}</tr>)}</tbody></table>
      {!rows.length && <p className="px-3 py-4 text-xs text-slate-500">{empty}</p>}
    </div>
  );
}

function Section({ title, rows, cols, open, testid, children }) {
  return <Card testid={testid}><h4 className="mb-2 font-heading text-sm font-semibold">{title} ({rows.length})</h4>{children}<RecTable rows={rows} cols={cols} onRow={open} testid={`${testid}-table`} empty="None linked yet" /></Card>;
}

const iso = (d) => new Date(Date.now() + d * 864e5).toISOString().slice(0, 10);
const GROUPS = ["Finance", "IT", "HR", "Operations"];

function LaunchCampaign({ rec, role, onDone }) {
  const [g, setG] = useState(["Finance", "IT"]);
  const [due, setDue] = useState(iso(14));
  const go = async () => {
    try {
      const c = (await api.post("/labs/grc/actions/create_campaign", { role, policy_id: rec.id, groups: g, start_date: iso(0), due_date: due, reminder_days: 3 })).data.record;
      await api.post("/labs/grc/actions/transition", { id: c.id, act: "launch", role, data: {} });
      toast.success(`${c.number} launched for ${g.join(", ")}`);
      onDone();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="flex flex-wrap items-center gap-2 rounded border border-slate-200 p-2 text-xs" data-testid="policy-launch-campaign">
      {GROUPS.map((x) => <label key={x} className="flex items-center gap-1"><input type="checkbox" checked={g.includes(x)} onChange={() => setG(g.includes(x) ? g.filter((y) => y !== x) : [...g, x])} data-testid={`policy-campaign-group-${x}`} />{x}</label>)}
      <input type="date" value={due} onChange={(e) => setDue(e.target.value)} className="rounded border border-slate-300 px-1" data-testid="policy-campaign-due" />
      <button onClick={go} className="rounded bg-teal-700 px-3 py-1 text-white hover:bg-teal-800" data-testid="policy-campaign-launch-btn">Initiate acknowledgment campaign</button>
    </div>
  );
}

function RequestException({ rec, ctls, role, onDone }) {
  const [v, setV] = useState({ control_id: ctls[0]?.id || "", department: "Finance", justification: "Legacy system cannot meet this policy requirement until upgrade.", compensating_controls: "Enhanced logging and weekly review", duration_days: 90 });
  const go = () => api.post("/labs/grc/actions/create_exception", { role, policy_id: rec.id, ...v, control_id: v.control_id || undefined, duration_days: Number(v.duration_days) }).then((r) => { toast.success(`${r.data.record.number} requested`); onDone(); }).catch((e) => toast.error(errMsg(e)));
  const inp = (k, ph) => <input value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} placeholder={ph} className="rounded border border-slate-300 px-2 py-1" data-testid={`policy-exception-${k}`} />;
  return (
    <div className="grid gap-2 rounded border border-slate-200 p-2 text-xs sm:grid-cols-2" data-testid="policy-request-exception">
      <select value={v.control_id} onChange={(e) => setV({ ...v, control_id: e.target.value })} className="rounded border border-slate-300 px-2 py-1" data-testid="policy-exception-control"><option value="">No specific control</option>{ctls.map((c) => <option key={c.id} value={c.id}>{c.number} {c.name}</option>)}</select>
      {inp("department", "Department")}{inp("justification", "Business justification")}{inp("compensating_controls", "Compensating controls")}{inp("duration_days", "Duration (days)")}
      <button onClick={go} className="rounded bg-teal-700 px-3 py-1 text-white hover:bg-teal-800 disabled:opacity-50" data-testid="policy-exception-submit">Submit exception request</button>
    </div>
  );
}

export function PolicyPanels({ rec, records, role, open, onDone }) {
  const of = (t, f) => records.filter((r) => r.type === t && f(r));
  const camps = of("campaign", (r) => r.policy_id === rec.id);
  const cids = new Set(camps.map((c) => c.id));
  const acks = of("ack", (r) => cids.has(r.campaign_id));
  const excs = of("exception", (r) => r.policy_id === rec.id);
  const fam = new Set(of("policy", (p) => p.title === rec.title).map((p) => p.id));
  const ctls = of("control", (r) => fam.has(r.policy_id));
  const rcs = of("reg_change", (r) => (r.policy_ids || []).includes(rec.id) || (r.revision_policy_ids || []).includes(rec.id));
  const hist = [...(rec.approval_history || []), ...(rec.review_comments || []).map((c) => ({ ...c, decision: "Review comment" }))];
  const pub = rec.state === "Published";
  return (
    <div className="grid gap-4 xl:grid-cols-2" data-testid="policy-related-sections">
      <Section title="Acknowledgment Campaigns" rows={camps} cols={["number", "groups", "due_date", "state", "final_completion_pct"]} open={open} testid="policy-sec-campaigns">
        {pub ? <LaunchCampaign rec={rec} role={role} onDone={onDone} /> : <p className="text-[11px] text-slate-500">Campaigns can be launched once the policy is Published.</p>}
      </Section>
      <Section title="Employee Acknowledgments" rows={acks} cols={["number", "employee", "group", "state", "acknowledged_at"]} open={open} testid="policy-sec-acks" />
      <Section title="Policy Exceptions" rows={excs} cols={["number", "department", "risk_rating", "state", "expires"]} open={open} testid="policy-sec-exceptions">
        {pub ? <RequestException rec={rec} ctls={ctls} role={role} onDone={onDone} /> : <p className="text-[11px] text-slate-500">Exceptions can be requested against a Published policy.</p>}
      </Section>
      <Section title="Related Controls" rows={ctls} cols={["number", "ref", "name", "state"]} open={open} testid="policy-sec-controls" />
      <Card testid="policy-sec-approvals"><h4 className="mb-2 font-heading text-sm font-semibold">Approval History ({hist.length})</h4><RecTable rows={hist} cols={["by", "decision", "comment", "at"]} testid="policy-approval-table" empty="No review or approval decisions yet" /></Card>
      <Section title="Regulatory Changes (UCF)" rows={rcs} cols={["number", "framework", "change_type", "state"]} open={open} testid="policy-sec-regchanges" />
    </div>
  );
}

export function ChangePanel({ rec, records, role, open, onDone }) {
  const [busy, setBusy] = useState(false);
  const ids = new Set([...(rec.control_ids || []), ...(rec.policy_ids || []), ...(rec.revision_policy_ids || []), ...(rec.issue_ids || []), rec.impact_id, rec.requirement_id, rec.obligation_id]);
  const linked = records.filter((r) => ids.has(r.id) || r.reg_change_id === rec.id);
  const ai = rec.ai_analysis;
  const analyze = async () => {
    setBusy(true);
    try { await api.post("/labs/grc/actions/ucf_ai_analyze", { id: rec.id, role }); toast.success("Analysis drafted – pending human review"); onDone(); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="grid gap-4 xl:grid-cols-2" data-testid="regchange-panels">
      <Section title="Linked obligation, policies, controls, issues & tasks" rows={linked} cols={["number", "type", "title", "state"]} open={open} testid="regchange-linked" />
      <Card testid="regchange-ai">
        <div className="flex flex-wrap items-center justify-between gap-2"><h4 className="font-heading text-sm font-semibold">Regulatory Change Analysis Agent (optional, advisory)</h4>
          <div className="flex gap-2">
            <button onClick={analyze} disabled={busy || rec.state === "Closed"} className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1 text-xs hover:border-teal-600 disabled:opacity-50" data-testid="regchange-ai-run"><Bot className="h-3 w-3" />{busy ? "Analyzing…" : "Run analysis"}</button>
            <button onClick={() => download(`/labs/grc/ucf/report/${rec.id}`, `regulatory-change-${rec.number}.pdf`)} className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1 text-xs" data-testid="regchange-report"><Download className="h-3 w-3" />Impact report</button>
          </div></div>
        {ai ? (
          <div className="mt-2 space-y-2 text-xs" data-testid="regchange-ai-output">
            <p><Badge>{ai.status}</Badge> <span className="ml-1 font-mono text-[10px] text-slate-500">mode: {ai.mode}</span></p>
            <p className="whitespace-pre-wrap text-slate-700">{ai.output}</p>
            <p><b>Priority:</b> {ai.structured.priority}</p>
            <ul className="list-disc pl-4">{ai.structured.proposed_actions.map((a) => <li key={a}>{a}</li>)}</ul>
            <p className="text-[11px] text-amber-700">{ai.disclaimer}</p>
          </div>
        ) : <p className="mt-2 text-xs text-slate-500">No analysis yet. Output requires Compliance Owner review (use the review AI action) and never changes approved mappings.</p>}
      </Card>
    </div>
  );
}
