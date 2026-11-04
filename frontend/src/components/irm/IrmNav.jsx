import { useState } from "react";
import { ChevronDown, ChevronRight, Menu } from "lucide-react";

export const NAV = [
  ["Overview", [["scenario", "End-to-End Governance Scenario"], ["dashboard", "Executive Dashboard"]]],
  ["Compliance Management", [
    ["Policy Management", [
      ["pol-all", "All Policies"], ["pol-new", "Create New Policy"], ["pol-review", "Policies Pending Review"], ["pol-approval", "Policies Pending Approval"], ["pol-published", "Published Policies"], ["pol-retired", "Retired Policies"],
      ["Policy Acknowledgment", [["camp", "Acknowledgment Campaigns"], ["ack", "Employee Acknowledgments"], ["ack-report", "Acknowledgment Reports"]]],
      ["Policy Exceptions", [["exc-all", "All Exceptions"], ["exc-new", "New Exception Request"], ["exc-pending", "Pending Approvals"], ["exc-active", "Active Exceptions"], ["exc-closed", "Closed Exceptions"]]],
    ]],
    ["Control Management", [["objectives", "Control Objectives"], ["control", "Controls"], ["assessment", "Control Assessments"], ["ucf", "Regulatory Change Monitoring (UCF Integration)"]]],
  ]],
  ["Risk Management", [["risk", "Risk Register"], ["risk_assessment", "Risk Assessments"], ["treatment", "Risk Treatment Plans"]]],
  ["Issues Management", [["issue", "Issues"], ["task", "Remediation Tasks"]]],
  ["Administration & Monitoring", [["notification", "Notifications"], ["automation", "Workflow Executions"], ["audit", "Audit History"]]],
];

const isGroup = (n) => Array.isArray(n[1]);
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-");
export const navLabel = (key, nodes = NAV) => {
  for (const n of nodes) {
    if (isGroup(n)) { const f = navLabel(key, n[1]); if (f) return f; } else if (n[0] === key) return n[1];
  }
  return null;
};

function Node({ node, depth, mod, go, counts, closed, toggle }) {
  if (!isGroup(node)) {
    const [k, l] = node;
    return <button onClick={() => go(k)} style={{ paddingLeft: 8 + depth * 12 }} className={`flex w-full justify-between gap-2 rounded py-1.5 pr-2 text-left text-xs ${mod === k ? "bg-teal-50 font-semibold text-teal-800" : "text-slate-700 hover:bg-slate-50"}`} data-testid={`grc-nav-${k}`}><span>{l}</span>{counts[k] !== undefined && <span className="font-mono text-[10px] text-slate-400">{counts[k]}</span>}</button>;
  }
  const [label, kids] = node;
  const shut = closed.has(label);
  return (
    <div>
      <button onClick={() => toggle(label)} style={{ paddingLeft: 4 + depth * 12 }} aria-expanded={!shut} className={`flex w-full items-center gap-1 py-1.5 pr-2 text-left ${depth === 0 ? "text-[11px] font-bold uppercase tracking-wide text-slate-900" : "text-xs font-semibold text-slate-800"}`} data-testid={`grc-nav-group-${slug(label)}`}>
        {shut ? <ChevronRight className="h-3 w-3 shrink-0" /> : <ChevronDown className="h-3 w-3 shrink-0" />}{label}
      </button>
      {!shut && <div>{kids.map((n) => <Node key={n[0]} node={n} depth={depth + 1} mod={mod} go={go} counts={counts} closed={closed} toggle={toggle} />)}</div>}
    </div>
  );
}

export function IrmNav({ mod, go, counts }) {
  const [closed, setClosed] = useState(new Set());
  const [mobileOpen, setMobileOpen] = useState(false);
  const toggle = (l) => setClosed((s) => { const n = new Set(s); n.has(l) ? n.delete(l) : n.add(l); return n; });
  const pick = (k) => { go(k); setMobileOpen(false); };
  return (
    <nav className="h-fit rounded-lg border border-slate-200 bg-white p-2 lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-auto" data-testid="grc-navigator" aria-label="Application navigator">
      <button onClick={() => setMobileOpen(!mobileOpen)} className="flex w-full items-center justify-between px-2 py-1 lg:cursor-default" data-testid="grc-nav-mobile-toggle">
        <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">Application navigator · ServiceNow IRM</span><Menu className="h-4 w-4 text-slate-500 lg:hidden" />
      </button>
      <div className={`${mobileOpen ? "block" : "hidden"} mt-1 lg:block`}>
        {NAV.map((n) => <Node key={n[0]} node={n} depth={0} mod={mod} go={pick} counts={counts} closed={closed} toggle={toggle} />)}
      </div>
    </nav>
  );
}
