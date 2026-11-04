import { toast } from "sonner";
import { AlertTriangle } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { Badge, Card } from "./kit";

export function ProgramBoard({ dash, records, onDone }) {
  if (!dash?.board) return null;
  const { teams, load, features, conflicts } = dash.board;
  const cal = dash.pi?.calendar;
  const conflictNames = new Set(conflicts.flatMap((c) => [c.consumer, c.provider]));
  const unassigned = features.filter((f) => !f.iteration);
  const assign = async (fid, teamId, it) => {
    try { await api.post("/labs/safe/actions/assign_feature", { feature_id: fid, team_id: teamId, iteration: it }); toast.success("Feature planned"); onDone(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Card testid="program-board">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-heading text-base font-semibold text-slate-900">Program board · {dash.pi?.name} <Badge testid="pi-status">{dash.pi?.status}</Badge></h3>
        <span className="text-xs text-slate-500">Drag a backlog feature onto a team × iteration cell, or use the Assign form.</span>
      </div>
      {conflicts.length > 0 && (
        <div className="mt-3 space-y-1 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700" data-testid="board-conflicts">
          {conflicts.map((c) => <p key={c.dependency_id} className="flex items-center gap-1"><AlertTriangle className="h-3 w-3" />{c.consumer} needs {c.provider}: {c.reason}</p>)}
        </div>
      )}
      <div className="mt-4 overflow-x-auto">
        <div className="min-w-[900px]">
          <div className="grid grid-cols-[140px_repeat(5,1fr)] gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            <div />{[1, 2, 3, 4, 5].map((i) => <div key={i} className="px-2">{i === 5 ? "IP" : `I${i}`}{cal ? <span className="ml-1 font-mono normal-case text-slate-400">{cal[i - 1].start.slice(5)}</span> : null}</div>)}
          </div>
          {load.map((row, ti) => (
            <div key={row.team_id} className="mt-1 grid grid-cols-[140px_repeat(5,1fr)] gap-1" data-testid={`pi-board-team-${ti}`}>
              <div className="rounded bg-[#0B132B] px-2 py-2 text-xs font-semibold text-white">{row.team}<p className="font-normal text-slate-400">{teams[ti].focus}</p></div>
              {row.cells.map((c) => (
                <div key={c.iteration} onDragOver={(e) => e.preventDefault()} onDrop={(e) => assign(e.dataTransfer.getData("fid"), row.team_id, c.iteration)}
                  className={`min-h-[72px] rounded border p-1.5 ${c.over ? "border-rose-300 bg-rose-50" : "border-slate-200 bg-slate-50"}`} data-testid={`pi-cell-${ti}-${c.iteration}`}>
                  <p className={`font-mono text-[10px] ${c.over ? "text-rose-600" : "text-slate-400"}`}>{c.load}/{c.capacity} pts{c.over ? " · OVER" : ""}</p>
                  {features.filter((f) => f.team_id === row.team_id && f.iteration === c.iteration).map((f) => (
                    <div key={f.id} draggable onDragStart={(e) => e.dataTransfer.setData("fid", f.id)} className={`mt-1 cursor-grab rounded border px-1.5 py-1 text-[11px] ${f.status === "Done" ? "border-emerald-300 bg-emerald-50" : conflictNames.has(f.name) ? "border-rose-300 bg-white" : "border-teal-200 bg-white"}`}>
                      {f.name}<span className="ml-1 text-slate-400">{f.size}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4">
        <p className="font-mono text-[11px] uppercase tracking-wider text-slate-500">Unplanned backlog (WSJF order)</p>
        <div className="mt-2 flex flex-wrap gap-2" data-testid="pi-backlog">
          {unassigned.sort((a, b) => b.wsjf - a.wsjf).map((f) => <span key={f.id} draggable onDragStart={(e) => e.dataTransfer.setData("fid", f.id)} className="cursor-grab rounded border border-slate-300 bg-white px-2 py-1 text-xs">{f.name} <span className="text-teal-700">WSJF {f.wsjf}</span></span>)}
          {unassigned.length === 0 && <span className="text-xs text-slate-400">All features planned</span>}
        </div>
      </div>
      {records && null}
    </Card>
  );
}

export function Kanban({ cfg, lab, records, onDone }) {
  const items = records.filter((r) => r.type === cfg.type);
  const move = async (id, status) => {
    try { await api.post(`/labs/${lab}/actions/${cfg.action}`, { [cfg.idKey]: id, status }); onDone(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Card testid="kanban-board">
      <h3 className="font-heading text-base font-semibold text-slate-900">Kanban board</h3>
      <div className="mt-3 grid gap-2 md:grid-cols-4">
        {cfg.columns.map((col) => (
          <div key={col} onDragOver={(e) => e.preventDefault()} onDrop={(e) => move(e.dataTransfer.getData("sid"), col)} className="min-h-[120px] rounded-md bg-slate-50 p-2" data-testid={`kanban-col-${col.toLowerCase().replace(/ /g, "-")}`}>
            <p className="font-mono text-[11px] uppercase tracking-wider text-slate-500">{col} · {items.filter((s) => s.status === col).length}</p>
            {items.filter((s) => s.status === col).slice(0, 12).map((s) => (
              <div key={s.id} draggable onDragStart={(e) => e.dataTransfer.setData("sid", s.id)} className="mt-2 cursor-grab rounded border border-slate-200 bg-white p-2 text-xs">
                <p className="font-medium text-slate-800">{s.title}</p>
                <div className="mt-1 flex items-center justify-between"><span className="text-slate-400">{s.points} pts · {s.priority}</span>
                  <select aria-label="Move story" className="rounded border border-slate-200 text-[10px]" value={s.status} onChange={(e) => move(s.id, e.target.value)}>{cfg.columns.map((c) => <option key={c}>{c}</option>)}</select>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}
