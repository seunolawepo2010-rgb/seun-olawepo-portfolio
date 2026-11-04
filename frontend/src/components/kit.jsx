import { motion } from "framer-motion";

const TONE = {
  good: "bg-emerald-50 text-emerald-700 border-emerald-200",
  bad: "bg-rose-50 text-rose-700 border-rose-200",
  warn: "bg-amber-50 text-amber-700 border-amber-200",
  info: "bg-sky-50 text-sky-700 border-sky-200",
  teal: "bg-teal-50 text-teal-700 border-teal-200",
  muted: "bg-slate-100 text-slate-600 border-slate-200",
};

export function toneFor(v) {
  const s = String(v ?? "").toLowerCase();
  if (/^(effective|completed|closed|approved|pass|passed|accepted|allow|done|green|success|recovered|resolved|verified|deployed|live|true|committed|attested|acknowledged)/.test(s)) return "good";
  if (/(fail|ineffective|critical|rejected|deny|blocked|red|high|breach|open\b|overdue|conflict|rolled back|missed)/.test(s)) return "bad";
  if (/(pending|awaiting|medium|review|amber|in progress|remediation|sent|submitted|scheduled|planning|warning)/.test(s)) return "warn";
  if (/(simulation|running|planned|active|executing|low)/.test(s)) return "info";
  return "muted";
}

export function Badge({ children, tone, testid }) {
  return (
    <span data-testid={testid} className={`inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${TONE[tone || toneFor(children)]}`}>
      {String(children)}
    </span>
  );
}

export function Eyebrow({ children }) {
  return <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-teal-700">{children}</p>;
}

export function PageHeader({ eyebrow, title, children }) {
  return (
    <section className="bg-[#0B132B] text-white">
      <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-teal-300">{eyebrow}</p>
        <h1 className="mt-3 max-w-4xl font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">{title}</h1>
        {children && <div className="mt-4 max-w-3xl text-sm text-slate-300 sm:text-base">{children}</div>}
      </div>
    </section>
  );
}

export function Card({ children, className = "", testid }) {
  return <div data-testid={testid} className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{children}</div>;
}

export function Kpi({ label, value, i = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }} className="rounded-lg border border-slate-200 bg-white p-4" data-testid={`kpi-${String(label).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
      <p className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 font-heading text-2xl font-bold text-slate-900">{String(value)}</p>
    </motion.div>
  );
}

export function SimNotice({ children }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800" data-testid="simulation-notice">
      <span className="font-semibold">Portfolio simulation · fictional data.</span> {children}
    </div>
  );
}

export function fmt(v) {
  if (v == null || v === "") return "—";
  if (Array.isArray(v)) return v.map((x) => (typeof x === "object" ? x.name || x.item || x.team || JSON.stringify(x) : x)).join(", ");
  if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${k}: ${typeof x === "object" ? JSON.stringify(x) : x}`).join("; ");
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v)) return v.slice(0, 16).replace("T", " ");
  return String(v);
}

export const BADGE_COLS = new Set(["status", "severity", "rating", "result", "decision", "health", "tier", "mode", "state", "roam", "rto_met", "criticality"]);
