import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Kpi, fmt } from "./kit";

const COLORS = ["#0D9488", "#1E293B", "#0284C7", "#D97706", "#10B981", "#F43F5E", "#64748B"];

function Chart({ c, i }) {
  return (
    <Card testid={`chart-${i}`}>
      <h4 className="font-heading text-sm font-semibold text-slate-900">{c.title}</h4>
      <div className="mt-3 h-56">
        {c.data.length === 0 ? <p className="pt-16 text-center text-xs text-slate-400">No data yet</p> : i % 2 === 0 ? (
          <ResponsiveContainer><BarChart data={c.data}><XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} /><YAxis allowDecimals={false} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="value" radius={[3, 3, 0, 0]}>{c.data.map((_, j) => <Cell key={j} fill={COLORS[j % COLORS.length]} />)}</Bar></BarChart></ResponsiveContainer>
        ) : (
          <ResponsiveContainer><PieChart><Pie data={c.data} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} label={({ name, value }) => `${name}: ${value}`} labelLine={false} fontSize={10}>{c.data.map((_, j) => <Cell key={j} fill={COLORS[j % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

function HeatMap({ heat }) {
  const tone = (n, l, im) => (n === 0 ? "bg-slate-50 text-slate-300" : l * im >= 15 ? "bg-rose-500 text-white" : l * im >= 8 ? "bg-amber-400 text-white" : "bg-emerald-500 text-white");
  return (
    <Card testid="risk-heatmap">
      <h4 className="font-heading text-sm font-semibold text-slate-900">Risk heat map (open risks · likelihood × impact)</h4>
      <div className="mt-3 grid grid-cols-6 gap-1 text-center text-xs">
        {[5, 4, 3, 2, 1].map((l) => [<div key={`l${l}`} className="py-2 font-mono text-slate-500">L{l}</div>, ...[1, 2, 3, 4, 5].map((im) => <div key={`${l}${im}`} className={`rounded py-2 font-semibold ${tone(heat[l - 1][im - 1], l, im)}`}>{heat[l - 1][im - 1]}</div>)])}
        <div />{[1, 2, 3, 4, 5].map((im) => <div key={im} className="font-mono text-slate-500">I{im}</div>)}
      </div>
    </Card>
  );
}

export function Dashboard({ dash }) {
  if (!dash) return null;
  return (
    <div className="space-y-4" data-testid="lab-dashboard">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">{dash.kpis.map((k, i) => <Kpi key={k.label} {...k} i={i} />)}</div>
      <div className="grid gap-4 md:grid-cols-2">
        {dash.charts.map((c, i) => <Chart key={c.title} c={c} i={i} />)}
        {dash.heatmap && <HeatMap heat={dash.heatmap} />}
      </div>
      {dash.table && dash.table.length > 0 && (
        <Card testid="agent-metrics-table">
          <h4 className="font-heading text-sm font-semibold text-slate-900">Agent performance by version (computed from recorded runs)</h4>
          <div className="mt-3 overflow-x-auto"><table className="w-full text-xs"><thead><tr>{Object.keys(dash.table[0]).map((k) => <th key={k} className="bg-slate-50 px-2 py-1 text-left uppercase tracking-wider text-slate-500">{k.replace(/_/g, " ")}</th>)}</tr></thead>
            <tbody>{dash.table.map((r, i) => <tr key={i} className="border-t border-slate-100">{Object.values(r).map((v, j) => <td key={j} className="px-2 py-1">{fmt(v)}</td>)}</tr>)}</tbody></table></div>
        </Card>
      )}
    </div>
  );
}
