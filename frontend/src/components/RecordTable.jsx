import { useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { api, errMsg } from "../lib/api";
import { Badge, BADGE_COLS, fmt } from "./kit";
import { Field, initial } from "./ActionForm";
import { ResultView } from "./ResultView";

const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-");

function RowDialog({ lab, act, row, records, onClose, onDone }) {
  const fields = act.answers ? row.questions.map((q) => ({ n: q, l: q, t: "select", o: ["yes", "no"], d: "yes" })) : act.fields || [];
  const [values, setValues] = useState(() => initial(fields, records, row));
  const [result, setResult] = useState(null);
  const tid = `dialog-${lab}-${slug(act.action || "patch")}`;
  const submit = async (e) => {
    e.preventDefault();
    try {
      let res;
      if (act.patch) res = (await api.patch(`/labs/${lab}/records/${row.id}`, values)).data;
      else if (act.answers) res = (await api.post(`/labs/${lab}/actions/${act.action}`, { [act.idKey]: row.id, answers: values })).data;
      else res = (await api.post(`/labs/${lab}/actions/${act.action}`, { [act.idKey]: row.id, ...values })).data;
      setResult(res);
      toast.success(`${act.label}: done`);
      onDone();
    } catch (err) {
      toast.error(errMsg(err));
      setResult({ error: errMsg(err) });
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl" data-testid={tid}>
        <DialogHeader><DialogTitle>{act.label}</DialogTitle><DialogDescription>{row.title || row.name || row.ref || row.number || row.id}</DialogDescription></DialogHeader>
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
          {fields.map((f) => <Field key={f.n} f={f} tid={tid} row={row} value={values[f.n]} values={values} records={records} onChange={(v) => setValues((s) => ({ ...s, [f.n]: v }))} />)}
          <button type="submit" data-testid={`${tid}-submit`} className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 sm:col-span-2">Confirm</button>
        </form>
        {result && <ResultView result={result} testid={`${tid}-result`} />}
      </DialogContent>
    </Dialog>
  );
}

export function RecordTable({ lab, table, records, onDone }) {
  const rows = records.filter((r) => r.type === table.type).slice().reverse();
  const [open, setOpen] = useState(null);
  const tid = `table-${lab}-${slug(table.type)}`;
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm" data-testid={tid}>
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h3 className="font-heading text-sm font-semibold text-slate-900">{table.title}</h3>
        <span className="font-mono text-[11px] text-slate-500" data-testid={`${tid}-count`}>{rows.length} records</span>
      </div>
      <div className="max-h-96 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-50">
            <tr>
              {table.cols.map((c) => <th key={c} className="whitespace-nowrap px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-600">{c.replace(/_/g, " ")}</th>)}
              {table.actions && <th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-600">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={table.cols.length + 1} className="px-3 py-6 text-center text-xs text-slate-400">No records yet</td></tr>}
            {rows.map((r, i) => (
              <tr key={r.id} className="border-t border-slate-100 transition-colors hover:bg-slate-50" data-testid={`${tid}-row-${i}`}>
                {table.cols.map((c) => (
                  <td key={c} className="max-w-xs px-3 py-2 align-top text-xs text-slate-700">
                    {BADGE_COLS.has(c) && r[c] != null ? <Badge>{fmt(r[c])}</Badge> : c === "fields" && Array.isArray(r[c]) ? r[c].map((f) => `${f.name}:${f.type}`).join(", ") : <span className="line-clamp-3">{fmt(r[c])}</span>}
                  </td>
                ))}
                {table.actions && (
                  <td className="px-3 py-2 align-top">
                    <div className="flex flex-wrap gap-1">
                      {table.actions.filter((a) => !a.show || a.show(r)).map((a) => (
                        <button key={a.label} onClick={() => (a.fields || a.answers || a.patch ? setOpen({ a, r }) : api.post(`/labs/${lab}/actions/${a.action}`, { [a.idKey]: r.id }).then(() => { toast.success(`${a.label}: done`); onDone(); }).catch((e) => toast.error(errMsg(e))))}
                          data-testid={`${tid}-row-${i}-${slug(a.label)}`} className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 transition-colors hover:border-teal-600 hover:text-teal-700">{a.label}</button>
                      ))}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open && <RowDialog lab={lab} act={open.a} row={open.r} records={records} onClose={() => setOpen(null)} onDone={onDone} />}
    </div>
  );
}
