import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Download, RefreshCw, RotateCcw, Briefcase, ListChecks } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { api, download, errMsg } from "../lib/api";
import { labByKey } from "../lib/labs";
import { ActionForm } from "../components/ActionForm";
import { RecordTable } from "../components/RecordTable";
import { Approvals, ExecutionList } from "../components/Executions";
import { Dashboard } from "../components/Dashboard";
import { ProgramBoard, Kanban } from "../components/Boards";
import { Badge, Card, Eyebrow, SimNotice } from "../components/kit";

export function useLab(key) {
  const [state, setState] = useState({ records: [], dash: null, exes: [], approvals: [], ai: null });
  const refresh = useCallback(async () => {
    try {
      const [r, d, e, a] = await Promise.all([api.get(`/labs/${key}/records`), api.get(`/labs/${key}/dashboard`), api.get(`/automation/executions?lab=${key}`), api.get(`/automation/approvals`)]);
      setState({ records: r.data, dash: d.data, exes: e.data, approvals: a.data });
    } catch (err) {
      toast.error(errMsg(err));
    }
  }, [key]);
  useEffect(() => {
    refresh();
  }, [refresh]);
  return { ...state, refresh };
}

export async function resetDemo(refresh) {
  if (!window.confirm("Reset all demo data in this browser to the initial fictional dataset?")) return;
  try {
    await api.post("/demo/reset");
    toast.success("Demo data reset");
    refresh?.();
  } catch (e) {
    toast.error(errMsg(e));
  }
}

function Overview({ lab }) {
  const blocks = [["Business problem", lab.problem], ["Relevant professional experience", lab.experience], ["Approach", lab.approach]];
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <Card><Eyebrow>Fictional scenario</Eyebrow><p className="mt-2 text-sm leading-relaxed text-slate-700">{lab.scenario}</p></Card>
        {blocks.map(([t, b]) => <Card key={t}><h3 className="font-heading text-sm font-semibold text-slate-900">{t}</h3><p className="mt-1 text-sm text-slate-600">{b}</p></Card>)}
        <Card><h3 className="font-heading text-sm font-semibold text-slate-900">Tools & frameworks</h3><div className="mt-2 flex flex-wrap gap-1.5">{lab.tools.map((t) => <Badge key={t} tone="teal">{t}</Badge>)}</div></Card>
      </div>
      <Card testid="guided-demo">
        <h3 className="flex items-center gap-2 font-heading text-sm font-semibold text-slate-900"><ListChecks className="h-4 w-4 text-teal-700" />Guided recruiter demo</h3>
        <ol className="mt-3 space-y-3">{lab.guided.map((g, i) => <li key={i} className="flex gap-3 text-sm text-slate-700"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-teal-50 font-mono text-[11px] text-teal-700">{i + 1}</span>{g}</li>)}</ol>
        <p className="mt-4 text-xs text-slate-500">Results: records, workflow logs and dashboards update live. Evidence: PDF/CSV in the Reports tab.</p>
      </Card>
    </div>
  );
}

export default function LabPage({ forceKey }) {
  const { key: pkey } = useParams();
  const key = forceKey || pkey;
  const lab = labByKey[key];
  const { records, dash, exes, approvals, refresh } = useLab(key);
  if (!lab) return <div className="p-10">Lab not found. <Link to="/lab" className="text-teal-700">Back to labs</Link></div>;
  const pending = approvals.filter((a) => a.lab === key);
  return (
    <div>
      <section className="bg-[#0B132B] text-white">
        <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-teal-300">Lab {lab.n} of 10 {lab.flagship ? "· Flagship" : ""}</p>
          <h1 className="mt-2 max-w-4xl font-heading text-3xl font-extrabold tracking-tight sm:text-4xl" data-testid="lab-title">{lab.name}</h1>
          <div className="mt-5 flex flex-wrap gap-2">
            <button onClick={refresh} className="inline-flex items-center gap-2 rounded-md border border-slate-600 px-3 py-2 text-xs hover:border-teal-400" data-testid="lab-refresh"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
            <button onClick={() => resetDemo(refresh)} className="inline-flex items-center gap-2 rounded-md border border-slate-600 px-3 py-2 text-xs hover:border-rose-400" data-testid="lab-reset-demo"><RotateCcw className="h-3.5 w-3.5" />Reset Demo</button>
            <Link to="/experience" className="inline-flex items-center gap-2 rounded-md border border-slate-600 px-3 py-2 text-xs hover:border-teal-400"><Briefcase className="h-3.5 w-3.5" />Related experience</Link>
            {dash?.live && <span className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-xs" data-testid="live-ai-status">Live AI: {dash.live.enabled ? `ON (${dash.live.model}) · ${dash.live.remaining_session} runs left today` : "OFF – simulation mode"}</span>}
          </div>
        </div>
      </section>
      <div className="mx-auto max-w-7xl space-y-5 px-5 py-8 sm:px-8">
        <SimNotice>{lab.disclaimer || "Every action is processed by the backend, persisted to your isolated demo session and recorded in the audit log."}</SimNotice>
        <Tabs defaultValue="workspace">
          <TabsList className="flex h-auto flex-wrap justify-start">
            {["overview", "workspace", "dashboard", "automation", "reports"].map((t) => (
              <TabsTrigger key={t} value={t} data-testid={`lab-tab-${t}`} className="capitalize">{t}{t === "automation" && pending.length ? ` (${pending.length})` : ""}</TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="overview" className="mt-5"><Overview lab={lab} /></TabsContent>
          <TabsContent value="workspace" className="mt-5 space-y-5">
            {key === "safe" && <ProgramBoard dash={dash} records={records} onDone={refresh} />}
            {lab.kanban && <Kanban cfg={lab.kanban} lab={key} records={records} onDone={refresh} />}
            {pending.length > 0 && <Card><h3 className="mb-3 font-heading text-sm font-semibold">Pending approvals</h3><Approvals approvals={pending} onDone={refresh} /></Card>}
            <div className="grid gap-4 lg:grid-cols-2">
              {lab.forms.map((f) => <ActionForm key={f.action} lab={key} form={f} records={records} onDone={refresh} />)}
              {(lab.create || []).map((c) => <ActionForm key={c.type} lab={key} form={{ ...c, action: `create-${c.type}`, createType: c.type }} records={records} onDone={refresh} />)}
            </div>
            {lab.tables.map((t) => <RecordTable key={t.type} lab={key} table={t} records={records} onDone={refresh} />)}
          </TabsContent>
          <TabsContent value="dashboard" className="mt-5"><Dashboard dash={dash} /></TabsContent>
          <TabsContent value="automation" className="mt-5 space-y-4">
            <Card><h3 className="mb-3 font-heading text-sm font-semibold">Human approval checkpoints</h3><Approvals approvals={pending} onDone={refresh} /></Card>
            <ExecutionList executions={exes} onChanged={refresh} />
            <Link to="/automation" className="text-sm text-teal-700 underline" data-testid="lab-open-automation-center">Open the Enterprise Automation Control Center →</Link>
          </TabsContent>
          <TabsContent value="reports" className="mt-5">
            <Card testid="lab-reports">
              <h3 className="font-heading text-sm font-semibold">Downloadable evidence</h3>
              <p className="mt-1 text-xs text-slate-500">Generated server-side from your current demo session records and execution logs.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button onClick={() => download(`/labs/${key}/report?format=pdf`, `${key}-lab-report.pdf`).catch((e) => toast.error(errMsg(e)))} className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm text-white hover:bg-teal-800" data-testid="lab-download-pdf"><Download className="h-4 w-4" />PDF report</button>
                <button onClick={() => download(`/labs/${key}/report?format=csv`, `${key}-lab-records.csv`).catch((e) => toast.error(errMsg(e)))} className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm hover:border-teal-600" data-testid="lab-download-csv"><Download className="h-4 w-4" />CSV export</button>
              </div>
              <p className="mt-4 text-xs text-slate-500">Per-workflow PDF evidence is available on each execution in the Automation tab.</p>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
