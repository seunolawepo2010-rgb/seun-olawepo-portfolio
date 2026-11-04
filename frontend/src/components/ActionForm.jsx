import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Loader2, Play } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { ResultView } from "./ResultView";

const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-");
const input = "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20";

export function initial(fields, records, row) {
  const v = {};
  fields.forEach((f) => {
    if (f.t === "record") v[f.n] = records.filter((r) => r.type === f.rt)[f.idx || 0]?.id || records.find((r) => r.type === f.rt)?.id || "";
    else if (f.t === "rowselect") v[f.n] = f.from(row || {})[0] || "";
    else if (f.t === "multirecord") v[f.n] = [];
    else if (f.t === "bool") v[f.n] = !!f.d;
    else if (f.t !== "evidence") v[f.n] = f.d ?? (row ? row[f.n] ?? "" : "");
  });
  return v;
}

export function Field({ f, value, onChange, records, row, values, tid }) {
  const id = `${tid}-${f.n}`;
  const label = <label htmlFor={id} className="mb-1 block text-xs font-medium text-slate-600">{f.l}</label>;
  if (f.t === "evidence") {
    const ctl = records.find((r) => r.id === values.control_id);
    return <div className="sm:col-span-2 rounded-md bg-slate-50 p-3 text-xs text-slate-700" data-testid={id}><span className="font-semibold">Evidence: </span>{ctl?.evidence || "Select a control"}</div>;
  }
  if (f.t === "bool") {
    return (
      <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2">
        <input id={id} data-testid={id} type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4 accent-teal-700" />
        {f.l}
      </label>
    );
  }
  let el;
  if (f.t === "select" || f.t === "record" || f.t === "rowselect") {
    const opts = f.t === "select" ? f.o.map((o) => [o, o]) : f.t === "rowselect" ? f.from(row || {}).map((o) => [o, o]) : records.filter((r) => r.type === f.rt).map((r) => [r.id, f.rl(r)]);
    el = <select id={id} data-testid={id} className={input} value={value} onChange={(e) => onChange(e.target.value)}>{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>;
  } else if (f.t === "multirecord") {
    el = <select id={id} data-testid={id} multiple className={`${input} h-28`} value={value} onChange={(e) => onChange([...e.target.selectedOptions].map((o) => o.value))}>
      {records.filter((r) => r.type === f.rt).map((r) => <option key={r.id} value={r.id}>{f.rl(r)}</option>)}
    </select>;
  } else if (f.t === "textarea") {
    el = <textarea id={id} data-testid={id} rows={3} className={input} value={value} onChange={(e) => onChange(e.target.value)} />;
  } else {
    el = <input id={id} data-testid={id} type={f.t === "number" ? "number" : f.t === "date" ? "date" : "text"} step="any" className={input} value={value} onChange={(e) => onChange(e.target.value)} />;
  }
  return <div className={f.t === "textarea" || f.t === "multirecord" ? "sm:col-span-2" : ""}>{label}{el}</div>;
}

export async function runAction(lab, action, values, fields) {
  const payload = {};
  fields.forEach((f) => { if (f.t !== "evidence") payload[f.n] = values[f.n]; });
  return (await api.post(`/labs/${lab}/actions/${action}`, payload)).data;
}

export function ActionForm({ lab, form, records, onDone }) {
  const [values, setValues] = useState(() => initial(form.fields, records));
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const tid = `form-${lab}-${slug(form.action)}`;
  const recCount = useMemo(() => records.map((r) => r.id).join(","), [records]);
  useEffect(() => {
    setValues((v) => {
      const next = { ...v };
      form.fields.forEach((f) => { if (f.t === "record" && !records.some((r) => r.id === v[f.n])) next[f.n] = records.find((r) => r.type === f.rt)?.id || ""; });
      return next;
    });
  }, [recCount]); // eslint-disable-line react-hooks/exhaustive-deps
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = form.createType ? (await api.post(`/labs/${lab}/records/${form.createType}`, values)).data : await runAction(lab, form.action, values, form.fields);
      setResult(res);
      toast.success(`${form.title}: done`);
      onDone();
    } catch (err) {
      toast.error(errMsg(err));
      setResult({ error: errMsg(err) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" data-testid={tid}>
      <h3 className="font-heading text-base font-semibold text-slate-900">{form.title}</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {form.fields.map((f) => <Field key={f.n} f={f} tid={tid} value={values[f.n]} values={values} records={records} onChange={(v) => setValues((s) => ({ ...s, [f.n]: v }))} />)}
      </div>
      <button type="submit" disabled={busy} data-testid={`${tid}-submit`} className="mt-4 inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-800 disabled:opacity-60">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Run
      </button>
      {result && <ResultView result={result} testid={`${tid}-result`} />}
    </form>
  );
}
