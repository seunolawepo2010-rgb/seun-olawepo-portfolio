import { Badge, fmt } from "./kit";

function MiniTable({ rows, cols }) {
  return (
    <div className="mt-2 overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr>{cols.map((c) => <th key={c} className="bg-slate-50 px-2 py-1 text-left font-semibold uppercase tracking-wider text-slate-500">{c.replace(/_/g, " ")}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i} className="border-t border-slate-100">{cols.map((c) => <td key={c} className="px-2 py-1 text-slate-700">{typeof r[c] === "boolean" ? <Badge>{r[c] ? "pass" : "fail"}</Badge> : fmt(r[c])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export function ResultView({ result, testid }) {
  const run = result.run;
  const exe = result.execution;
  return (
    <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700" data-testid={testid}>
      {result.error && <p className="font-medium text-rose-700">{result.error}</p>}
      {result.message && <p>{result.message}</p>}
      {exe && <p>Workflow <span className="font-mono">{exe.id}</span> · <Badge>{exe.status}</Badge> — see Automation tab.</p>}
      {result.decision && <p>ACL decision: <Badge testid={`${testid}-decision`}>{result.decision}</Badge> roles {fmt(result.user_roles)} · required {fmt(result.acl_roles)}</p>}
      {result.status_code && <><p>HTTP <Badge>{result.status_code}</Badge> · {result.latency_ms} ms · {result.mode}</p><pre className="mt-2 max-h-48 overflow-auto rounded bg-white p-2 font-mono text-[11px]">{JSON.stringify(result.response, null, 2)}</pre></>}
      {run && <div><p><Badge>{run.mode}</Badge> <Badge>{run.status}</Badge> {run.latency_ms} ms ({run.latency_basis || "—"}) · {run.tokens_in + run.tokens_out} tokens (est.) · ${run.cost_usd}</p>{run.fallback_reason && <p className="mt-1 text-amber-700">Fallback: {run.fallback_reason}</p>}<p className="mt-2 whitespace-pre-wrap">{run.output}</p></div>}
      {result.evaluation?.cases && <><p>Accuracy <b>{result.evaluation.accuracy}%</b> · live cases {result.evaluation.live_cases}/8</p><MiniTable rows={result.evaluation.cases} cols={["input", "expected", "predicted", "pass", "mode"]} /></>}
      {result.comparison?.rows && <><p>Recommended (cheapest above quality floor): <b>{result.comparison.recommended || "none"}</b> · {result.comparison.basis}</p><MiniTable rows={result.comparison.rows} cols={["model", "tokens_in", "tokens_out", "est_cost_usd", "cost_per_1k_runs", "modeled_latency_ms", "quality_index"]} /></>}
      {result.report && <MiniTable rows={result.report.teams || []} cols={["team", "planned_bv", "actual_bv", "predictability"]} />}
      {!result.error && !result.message && !exe && !run && !result.decision && !result.status_code && !result.evaluation && !result.comparison && (
        <pre className="max-h-40 overflow-auto font-mono text-[11px]">{JSON.stringify(result, (k, v) => (["session", "lab"].includes(k) ? undefined : v), 2)}</pre>
      )}
    </div>
  );
}
