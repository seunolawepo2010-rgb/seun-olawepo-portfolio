import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Play, Clock, Zap } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { LABS } from "../lib/labs";
import { Approvals, ExecutionList } from "../components/Executions";
import { Badge, Card, Kpi, PageHeader, SimNotice, Eyebrow } from "../components/kit";
import { resetDemo } from "./LabPage";

const DEMO_KEYS = new Set(["xlab_control_failure", "vendor_onboarding", "ai_registration", "project_delay", "art_dependency_conflict", "critical_incident", "agent_control_issue", "agent_grc_assessment"]);
const labLink = (k) => (k === "agents" ? "/agents" : `/lab/${k}`);

export function Automation() {
  const [cat, setCat] = useState([]);
  const [exes, setExes] = useState([]);
  const [appr, setAppr] = useState([]);
  const [stats, setStats] = useState(null);
  const [fault, setFault] = useState(false);
  const load = useCallback(async () => {
    const [c, e, a, s] = await Promise.all([api.get("/automation/workflows"), api.get("/automation/executions"), api.get("/automation/approvals"), api.get("/automation/analytics")]);
    setCat(c.data); setExes(e.data); setAppr(a.data); setStats(s.data);
  }, []);
  useEffect(() => { load().catch((e) => toast.error(errMsg(e))); }, [load]);
  const run = async (key) => {
    try { await api.post(`/automation/run/${key}`, { inject_failure: fault }); toast.success("Workflow triggered"); load(); } catch (e) { toast.error(errMsg(e)); }
  };
  const sched = async () => {
    try { const r = await api.post("/automation/scheduler/run"); toast.success(r.data.message); load(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div>
      <PageHeader eyebrow="Section 5" title="Enterprise Automation Control Center">A real workflow execution service: triggers, rule evaluation, conditional routing, task creation, human approvals, retries and a persistent audit trail across all ten labs.</PageHeader>
      <div className="mx-auto max-w-7xl space-y-6 px-5 py-10 sm:px-8">
        <SimNotice>Workflows run on the backend against your isolated demo session.</SimNotice>
        {stats && <div className="grid grid-cols-2 gap-3 md:grid-cols-4"><Kpi label="Executions" value={stats.total} /><Kpi label="Pending approvals" value={stats.pending_approvals} i={1} />{stats.by_status.slice(0, 2).map((s, i) => <Kpi key={s.name} label={s.name} value={s.value} i={i + 2} />)}</div>}
        <Card testid="automation-approvals"><h2 className="mb-3 font-heading text-base font-semibold">Approval management</h2><Approvals approvals={appr} onDone={load} /></Card>
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={sched} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:border-teal-600" data-testid="run-scheduler"><Clock className="h-4 w-4" />Run scheduled checks now</button>
          <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={fault} onChange={(e) => setFault(e.target.checked)} className="accent-teal-700" data-testid="inject-failure-toggle" />Inject a transient fault in step 2 (demonstrates retry handling)</label>
          <span className="text-xs text-slate-500">Scheduled checks also run automatically every 15 minutes.</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2" data-testid="workflow-catalog">
          {cat.map((w) => (
            <Card key={w.key} testid={`workflow-${w.key}`}>
              <div className="flex items-start justify-between gap-2"><h3 className="font-heading text-sm font-semibold">{w.name}</h3>{w.cross_lab && <Badge tone="teal">cross-lab</Badge>}</div>
              <p className="mt-1 text-xs text-slate-600">{w.description}</p>
              <p className="mt-2 font-mono text-[11px] text-slate-500">Trigger: {w.trigger}</p>
              <div className="mt-2 flex flex-wrap gap-1">{w.steps.map((s, i) => <span key={i} className={`rounded px-1.5 py-0.5 text-[10px] ${s.kind === "approval" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"}`}>{i + 1}. {s.name}</span>)}</div>
              <div className="mt-3 flex gap-2">
                {DEMO_KEYS.has(w.key) && <button onClick={() => run(w.key)} className="inline-flex items-center gap-1 rounded-md bg-teal-700 px-3 py-1.5 text-xs text-white hover:bg-teal-800" data-testid={`run-workflow-${w.key}`}><Play className="h-3 w-3" />Run demo trigger</button>}
                <Link to={labLink(w.lab)} className="rounded-md border border-slate-300 px-3 py-1.5 text-xs hover:border-teal-600">Open lab</Link>
              </div>
            </Card>
          ))}
        </div>
        {stats?.by_workflow?.length > 0 && <Card testid="automation-analytics"><h2 className="font-heading text-base font-semibold">Automation analytics</h2><table className="mt-3 w-full text-xs"><thead><tr className="text-left uppercase tracking-wider text-slate-500"><th>Workflow</th><th>Runs</th><th>Completed</th><th>Awaiting</th><th>Failed</th><th>Retries</th></tr></thead><tbody>{stats.by_workflow.map((w) => <tr key={w.workflow} className="border-t border-slate-100"><td className="py-1">{w.workflow}</td><td>{w.runs}</td><td>{w.completed}</td><td>{w.awaiting}</td><td>{w.failed}</td><td>{w.retries}</td></tr>)}</tbody></table></Card>}
        <div><h2 className="mb-3 font-heading text-base font-semibold">Execution history & audit trail</h2><ExecutionList executions={exes} onChanged={load} /></div>
      </div>
    </div>
  );
}

export function LabIndex() {
  return (
    <div>
      <PageHeader eyebrow="Enterprise Technology Lab" title="Ten interconnected interactive labs">Each lab has a fictional scenario, working forms, backend business rules, automation, approvals, dashboards, downloadable reports and a safe reset.</PageHeader>
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
        <div className="mb-6 flex flex-wrap gap-3"><Link to="/tour" className="rounded-md bg-[#0B132B] px-4 py-2 text-sm text-white hover:bg-[#1C2541]" data-testid="lab-index-tour">5-minute recruiter tour</Link><Link to="/demo" className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white hover:bg-teal-800" data-testid="lab-index-guided">Guided recruiter demo</Link><Link to="/automation" className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:border-teal-600"><Zap className="h-4 w-4" />Automation Control Center</Link></div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" data-testid="lab-index">
          {LABS.map((l) => (
            <Link key={l.key} to={labLink(l.key)} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-teal-500" data-testid={`lab-card-${l.key}`}>
              <div className="flex items-center justify-between"><span className="font-mono text-xs text-teal-700">LAB {l.n}</span>{l.flagship && <Badge tone="teal">Flagship</Badge>}</div>
              <h2 className="mt-2 font-heading text-base font-semibold">{l.name}</h2>
              <p className="mt-2 text-sm text-slate-600">{l.problem}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export function DemoTour() {
  return (
    <div>
      <PageHeader eyebrow="Explore my work — live demo" title="Guided demonstrations">No account needed. Your data is isolated to this browser and can be reset at any time.</PageHeader>
      <div className="mx-auto max-w-7xl space-y-4 px-5 py-10 sm:px-8">
        <div className="flex flex-wrap gap-3"><Link to="/tour" className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white hover:bg-teal-800" data-testid="demo-open-tour">One-click 5-minute tour</Link><button onClick={() => resetDemo()} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:border-rose-400" data-testid="demo-reset">Reset Demo</button></div>
        {LABS.map((l) => (
          <Card key={l.key} testid={`demo-${l.key}`}>
            <div className="grid gap-4 lg:grid-cols-3">
              <div><Eyebrow>Demo {l.n}</Eyebrow><h2 className="mt-1 font-heading text-base font-semibold">{l.name}</h2><p className="mt-2 text-xs text-slate-600"><b>Problem:</b> {l.problem}</p><p className="mt-1 text-xs text-slate-600"><b>Experience:</b> {l.experience}</p></div>
              <div className="text-xs text-slate-600"><p><b>Approach:</b> {l.approach}</p><div className="mt-2 flex flex-wrap gap-1">{l.tools.map((t) => <Badge key={t} tone="muted">{t}</Badge>)}</div></div>
              <div><ol className="space-y-1 text-xs text-slate-700">{l.guided.map((g, i) => <li key={i}>{i + 1}. {g}</li>)}</ol><Link to={labLink(l.key)} className="mt-3 inline-block rounded-md bg-teal-700 px-3 py-1.5 text-xs text-white" data-testid={`demo-open-${l.key}`}>Start demo</Link></div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
