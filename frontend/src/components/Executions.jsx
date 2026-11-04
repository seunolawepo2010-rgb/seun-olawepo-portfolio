import { useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, Circle, Clock, XCircle, PauseCircle, MinusCircle, Download, RotateCcw } from "lucide-react";
import { api, download, errMsg } from "../lib/api";
import { Badge, fmt } from "./kit";

const ICON = { completed: CheckCircle2, approved: CheckCircle2, failed: XCircle, rejected: XCircle, awaiting_approval: PauseCircle, skipped: MinusCircle, cancelled: MinusCircle, pending: Circle };
const COLOR = { completed: "text-emerald-600 border-emerald-300 bg-emerald-50", approved: "text-emerald-600 border-emerald-300 bg-emerald-50", failed: "text-rose-600 border-rose-300 bg-rose-50", rejected: "text-rose-600 border-rose-300 bg-rose-50", awaiting_approval: "text-amber-600 border-amber-300 bg-amber-50", pending: "text-slate-400 border-slate-200 bg-white", skipped: "text-slate-400 border-slate-200 bg-slate-50", cancelled: "text-slate-400 border-slate-200 bg-slate-50" };

export function StepGraph({ exe }) {
  return (
    <div className="flex flex-wrap items-stretch gap-2" data-testid={`step-graph-${exe.id}`}>
      {exe.steps.map((s, i) => {
        const I = ICON[s.status] || Clock;
        return (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-44 rounded-md border px-3 py-2 ${COLOR[s.status] || COLOR.pending}`} data-testid={`step-${exe.id}-${i}`}>
              <div className="flex items-center gap-1.5 text-[11px] font-semibold"><I className="h-3.5 w-3.5" />{s.kind === "approval" ? "Human gate" : `Step ${i + 1}`}</div>
              <p className="mt-1 text-xs text-slate-800">{s.name}</p>
              <p className="mt-1 font-mono text-[10px] text-slate-500">{s.status}{s.attempts > 1 ? ` · ${s.attempts} attempts` : ""}</p>
            </div>
            {i < exe.steps.length - 1 && <span className="text-slate-300">→</span>}
          </div>
        );
      })}
    </div>
  );
}

export function ExecutionDetail({ id, onChanged }) {
  const [exe, setExe] = useState(null);
  const load = () => api.get(`/automation/executions/${id}`).then((r) => setExe(r.data));
  useEffect(() => {
    load();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!exe) return <p className="text-xs text-slate-400">Loading…</p>;
  const retry = async () => {
    try { await api.post(`/automation/executions/${id}/retry`); toast.success("Retried"); load(); onChanged?.(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="space-y-3" data-testid={`execution-detail-${id}`}>
      <StepGraph exe={exe} />
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="bg-slate-50 text-left text-[10px] uppercase tracking-wider text-slate-500"><th className="px-2 py-1">Step</th><th className="px-2 py-1">Status</th><th className="px-2 py-1">Started</th><th className="px-2 py-1">Ended</th><th className="px-2 py-1">Output / error</th></tr></thead>
          <tbody>{exe.steps.map((s, i) => <tr key={i} className="border-t border-slate-100 align-top"><td className="px-2 py-1">{s.name}</td><td className="px-2 py-1"><Badge>{s.status}</Badge></td><td className="px-2 py-1 font-mono">{fmt(s.started_at)}</td><td className="px-2 py-1 font-mono">{fmt(s.ended_at)}</td><td className="max-w-md px-2 py-1 text-slate-600">{s.error ? <span className="text-rose-600">{s.error}</span> : null} {fmt(s.output)}</td></tr>)}</tbody>
        </table>
      </div>
      {exe.ctx?.report && <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs text-slate-700" data-testid={`execution-report-${id}`}>{exe.ctx.report}</pre>}
      <div className="flex gap-2">
        <button onClick={() => download(`/automation/executions/${id}/report`, `${id}.pdf`)} data-testid={`execution-pdf-${id}`} className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1 text-xs hover:border-teal-600"><Download className="h-3 w-3" />PDF evidence</button>
        {exe.status === "failed" && <button onClick={retry} data-testid={`execution-retry-${id}`} className="inline-flex items-center gap-1 rounded border border-rose-300 px-2 py-1 text-xs text-rose-700"><RotateCcw className="h-3 w-3" />Retry</button>}
      </div>
    </div>
  );
}

export function Approvals({ approvals, onDone }) {
  const decide = async (a, decision) => {
    try {
      await api.post(`/automation/approvals/${a.id}/decide`, { decision, comment: decision === "approved" ? "Approved in demo" : "Rejected in demo" });
      toast.success(`Approval ${decision}`);
      onDone();
    } catch (e) { toast.error(errMsg(e)); }
  };
  if (!approvals.length) return <p className="text-xs text-slate-500" data-testid="approvals-empty">No pending approvals.</p>;
  return (
    <div className="space-y-2" data-testid="approvals-list">
      {approvals.map((a, i) => (
        <div key={a.id} className="flex flex-col gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 sm:flex-row sm:items-center sm:justify-between" data-testid={`approval-${i}`}>
          <div><p className="text-sm font-medium text-slate-900">{a.title}</p><p className="text-[11px] text-slate-600">Approver role: {a.approver_role} · {a.lab} · {fmt(a.requested_at)}</p></div>
          <div className="flex gap-2">
            <button onClick={() => decide(a, "approved")} data-testid={`approval-${i}-approve`} className="rounded-md bg-teal-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-800">Approve</button>
            <button onClick={() => decide(a, "rejected")} data-testid={`approval-${i}-reject`} className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-rose-400">Reject</button>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ExecutionList({ executions, onChanged }) {
  const [open, setOpen] = useState(null);
  if (!executions.length) return <p className="text-xs text-slate-500" data-testid="executions-empty">No workflow executions yet. Run an action to trigger automation.</p>;
  return (
    <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white" data-testid="executions-list">
      {executions.map((e, i) => (
        <div key={e.id} className="p-3">
          <button className="flex w-full flex-col gap-1 text-left sm:flex-row sm:items-center sm:justify-between" onClick={() => setOpen(open === e.id ? null : e.id)} data-testid={`execution-${i}`}>
            <span className="text-sm font-medium text-slate-900">{e.name}</span>
            <span className="flex items-center gap-2"><span className="font-mono text-[11px] text-slate-500">{e.id} · {fmt(e.created_at)}</span><Badge testid={`execution-${i}-status`}>{e.status}</Badge></span>
          </button>
          {open === e.id && <div className="mt-3"><ExecutionDetail id={e.id} onChanged={onChanged} /></div>}
        </div>
      ))}
    </div>
  );
}
