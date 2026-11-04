import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { LogOut, Upload, Trash2, Plus, Save } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { api, errMsg } from "../lib/api";
import { Badge, Card, fmt } from "../components/kit";
import { UcfAdmin } from "./UcfModule";

const input = "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-teal-600 focus:outline-none";

export function AdminLogin() {
  const [v, setV] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const nav = useNavigate();
  const submit = async (e) => {
    e.preventDefault();
    try { await api.post("/auth/login", v); nav("/admin"); } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <div className="mx-auto max-w-sm px-5 py-20">
      <h1 className="font-heading text-2xl font-bold">Administrator sign in</h1>
      <p className="mt-1 text-xs text-slate-500">Private area. Public labs never require login.</p>
      <form onSubmit={submit} className="mt-6 space-y-3" data-testid="admin-login-form">
        <input type="email" required placeholder="Email" className={input} value={v.email} onChange={(e) => setV({ ...v, email: e.target.value })} data-testid="admin-email" aria-label="Email" />
        <input type="password" required placeholder="Password" className={input} value={v.password} onChange={(e) => setV({ ...v, password: e.target.value })} data-testid="admin-password" aria-label="Password" />
        {err && <p className="text-sm text-rose-600" data-testid="admin-login-error">{err}</p>}
        <button className="w-full rounded-md bg-teal-700 py-2 text-sm font-medium text-white hover:bg-teal-800" data-testid="admin-login-submit">Sign in</button>
      </form>
    </div>
  );
}

const COLL = {
  experience: ["employer", "title", "start", "end", "highlights", "labs", "order", "published"],
  skills: ["category", "name", "labs", "order"],
  certifications: ["name", "issuer", "category", "status", "date", "credential_url", "labs", "order"],
  education: ["degree", "field", "institution", "graduation_date", "order"],
  case_studies: ["title", "lab", "challenge", "scope", "approach", "technology", "frameworks", "deliverables", "evidence", "published"],
  articles: ["title", "date", "body", "published"],
};
const LIST = new Set(["highlights", "labs"]);
const LONG = new Set(["body", "challenge", "approach", "scope", "evidence"]);

function toForm(item, fields) {
  return Object.fromEntries(fields.map((f) => [f, LIST.has(f) ? (item[f] || []).join("\n") : item[f] ?? (f === "published" ? true : "")]));
}
function fromForm(v) {
  return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, LIST.has(k) ? String(x).split("\n").map((s) => s.trim()).filter(Boolean) : k === "order" ? Number(x) || 0 : x]));
}

function ItemEditor({ coll, item, onSaved }) {
  const fields = COLL[coll];
  const [v, setV] = useState(toForm(item || {}, fields));
  const save = async () => {
    try {
      if (item?.id) await api.put(`/admin/content/${coll}/${item.id}`, fromForm(v));
      else await api.post(`/admin/content/${coll}`, fromForm(v));
      toast.success("Saved");
      onSaved();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const del = async () => {
    if (!window.confirm("Delete this item?")) return;
    try { await api.delete(`/admin/content/${coll}/${item.id}`); toast.success("Deleted"); onSaved(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="grid gap-2 rounded-md border border-slate-200 bg-white p-3 sm:grid-cols-2" data-testid={`admin-${coll}-editor-${item?.id || "new"}`}>
      {fields.map((f) => (
        <label key={f} className={`text-xs text-slate-600 ${LONG.has(f) || LIST.has(f) ? "sm:col-span-2" : ""}`}>{f.replace(/_/g, " ")}{LIST.has(f) ? " (one per line)" : ""}
          {f === "published" ? <input type="checkbox" className="ml-2 accent-teal-700" checked={!!v[f]} onChange={(e) => setV({ ...v, [f]: e.target.checked })} />
            : LONG.has(f) || LIST.has(f) ? <textarea rows={3} className={input} value={v[f]} onChange={(e) => setV({ ...v, [f]: e.target.value })} />
              : <input className={input} value={v[f]} onChange={(e) => setV({ ...v, [f]: e.target.value })} />}
        </label>
      ))}
      <div className="flex gap-2 sm:col-span-2">
        <button onClick={save} className="inline-flex items-center gap-1 rounded-md bg-teal-700 px-3 py-1.5 text-xs text-white" data-testid={`admin-${coll}-save-${item?.id || "new"}`}><Save className="h-3 w-3" />Save</button>
        {item?.id && coll === "certifications" && <label className="inline-flex cursor-pointer items-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 text-xs"><Upload className="h-3 w-3" />Upload certificate<input type="file" accept=".pdf,.png,.jpg,.jpeg" className="hidden" data-testid={`admin-cert-upload-${item.id}`} onChange={(e) => { const fd = new FormData(); fd.append("file", e.target.files[0]); api.post(`/admin/certifications/${item.id}/file`, fd).then(() => toast.success("Certificate uploaded")).catch((x) => toast.error(errMsg(x))); }} /></label>}
        {item?.id && <button onClick={del} className="inline-flex items-center gap-1 rounded-md border border-rose-300 px-3 py-1.5 text-xs text-rose-700"><Trash2 className="h-3 w-3" />Delete</button>}
      </div>
    </div>
  );
}

function CollectionTab({ coll, items, reload }) {
  const [adding, setAdding] = useState(false);
  return (
    <div className="space-y-3">
      <button onClick={() => setAdding(!adding)} className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs" data-testid={`admin-${coll}-add`}><Plus className="h-3 w-3" />Add</button>
      {adding && <ItemEditor coll={coll} onSaved={() => { setAdding(false); reload(); }} />}
      {items.map((it) => <details key={it.id} className="rounded-md border border-slate-200 bg-slate-50 p-2"><summary className="cursor-pointer text-sm">{it.title || it.name || it.employer || it.degree} {it.published === false && <Badge tone="muted">draft</Badge>}</summary><div className="mt-2"><ItemEditor coll={coll} item={it} onSaved={reload} /></div></details>)}
    </div>
  );
}

function ProfileTab({ profile, reload }) {
  const [v, setV] = useState({ ...profile, metrics: profile.metrics.map((m) => `${m.value}|${m.label}`).join("\n") });
  const save = async () => {
    try {
      await api.put("/admin/profile", { ...v, metrics: v.metrics.split("\n").filter(Boolean).map((l) => ({ value: l.split("|")[0].trim(), label: (l.split("|")[1] || "").trim() })) });
      toast.success("Profile saved");
      reload();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const f = (k, long) => <label key={k} className="block text-xs text-slate-600">{k.replace(/_/g, " ")}{long ? <textarea rows={k === "summary" ? 8 : 3} className={input} value={v[k] || ""} onChange={(e) => setV({ ...v, [k]: e.target.value })} data-testid={`admin-profile-${k}`} /> : <input className={input} value={v[k] || ""} onChange={(e) => setV({ ...v, [k]: e.target.value })} data-testid={`admin-profile-${k}`} />}</label>;
  return (
    <div className="space-y-3">
      {["name", "site_title", "github_url", "linkedin_url", "public_email", "location"].map((k) => f(k))}
      {["headline", "supporting", "summary"].map((k) => f(k, true))}
      <label className="block text-xs text-slate-600">metrics (value|label per line)<textarea rows={4} className={input} value={v.metrics} onChange={(e) => setV({ ...v, metrics: e.target.value })} /></label>
      <button onClick={save} className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white" data-testid="admin-profile-save">Save profile & homepage</button>
    </div>
  );
}

function SettingsTab() {
  const [s, setS] = useState(null);
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  useEffect(() => { api.get("/admin/settings").then((r) => setS(r.data)); }, []);
  if (!s) return null;
  const save = async () => {
    try { await api.put("/admin/settings", { live_enabled: s.ai.live_enabled, model: s.ai.model, daily_limit_global: Number(s.ai.daily_limit_global), daily_limit_session: Number(s.ai.daily_limit_session) }); toast.success("AI settings saved"); } catch (e) { toast.error(errMsg(e)); }
  };
  const ai = (k, val) => setS({ ...s, ai: { ...s.ai, [k]: val } });
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card testid="admin-ai-settings"><h3 className="font-heading text-sm font-semibold">AI agent demonstrations</h3>
        <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" className="accent-teal-700" checked={s.ai.live_enabled} onChange={(e) => ai("live_enabled", e.target.checked)} data-testid="admin-live-ai-toggle" />Live AI enabled (otherwise simulation only)</label>
        <label className="mt-3 block text-xs text-slate-600">Model<select className={input} value={s.ai.model} onChange={(e) => ai("model", e.target.value)}>{s.models.map((m) => <option key={m}>{m}</option>)}</select></label>
        <label className="mt-3 block text-xs text-slate-600">Daily live calls (all visitors)<input type="number" className={input} value={s.ai.daily_limit_global} onChange={(e) => ai("daily_limit_global", e.target.value)} /></label>
        <label className="mt-3 block text-xs text-slate-600">Daily live calls per visitor<input type="number" className={input} value={s.ai.daily_limit_session} onChange={(e) => ai("daily_limit_session", e.target.value)} /></label>
        <button onClick={save} className="mt-3 rounded-md bg-teal-700 px-4 py-2 text-sm text-white" data-testid="admin-ai-save">Save</button>
      </Card>
      <Card><h3 className="font-heading text-sm font-semibold">API settings (secrets are server-side only)</h3>
        {Object.entries(s.integrations).map(([k, v]) => <p key={k} className="mt-2 text-sm">{k.replace(/_/g, " ")}: <Badge>{v ? "configured" : "missing"}</Badge></p>)}
        <h3 className="mt-6 font-heading text-sm font-semibold">Change password</h3>
        <input type="password" placeholder="Current password" className={`${input} mt-2`} value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} />
        <input type="password" placeholder="New password (12+ chars)" className={`${input} mt-2`} value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} />
        <button onClick={() => api.post("/auth/change-password", pw).then(() => toast.success("Password changed")).catch((e) => toast.error(errMsg(e)))} className="mt-2 rounded-md border border-slate-300 px-4 py-2 text-sm">Update password</button>
      </Card>
    </div>
  );
}

export function Admin() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [c, setC] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [ov, setOv] = useState(null);
  const reload = useCallback(async () => {
    const [b, m, o] = await Promise.all([api.get("/admin/content"), api.get("/admin/messages"), api.get("/admin/overview")]);
    setC(b.data); setMsgs(m.data); setOv(o.data);
  }, []);
  useEffect(() => {
    api.get("/auth/me").then((r) => { setMe(r.data); reload(); }).catch(() => nav("/admin/login"));
  }, [nav, reload]);
  if (!me || !c) return <div className="p-10 text-sm text-slate-500">Checking session…</div>;
  const upload = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    try { await api.post("/admin/resume", fd); toast.success("Resume uploaded"); reload(); } catch (x) { toast.error(errMsg(x)); }
  };
  const logout = async () => { await api.post("/auth/logout"); nav("/"); };
  return (
    <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8" data-testid="admin-dashboard">
      <div className="flex items-center justify-between"><h1 className="font-heading text-2xl font-bold">Administration</h1><button onClick={logout} className="inline-flex items-center gap-1 text-sm text-slate-600" data-testid="admin-logout"><LogOut className="h-4 w-4" />Sign out</button></div>
      <Tabs defaultValue="overview" className="mt-6">
        <TabsList className="flex h-auto flex-wrap justify-start">
          {["overview", "profile", "experience", "skills", "certifications", "education", "case_studies", "articles", "messages", "resume", "ucf", "settings"].map((t) => <TabsTrigger key={t} value={t} data-testid={`admin-tab-${t}`} className="capitalize">{t === "ucf" ? "UCF" : t.replace("_", " ")}{t === "messages" && ov?.messages_unread ? ` (${ov.messages_unread})` : ""}</TabsTrigger>)}
        </TabsList>
        <TabsContent value="overview" className="mt-5 space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{[["Demo sessions", ov.sessions], ["Workflow executions", ov.executions], ["Unread messages", ov.messages_unread], ["Live AI calls today", ov.ai_calls_today]].map(([l, v]) => <Card key={l}><p className="font-mono text-[10px] uppercase text-slate-500">{l}</p><p className="font-heading text-2xl font-bold">{v}</p></Card>)}</div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card><h3 className="font-heading text-sm font-semibold">Page views (30 days, anonymous)</h3>{ov.pageviews_30d.map((p) => <p key={p.path} className="mt-1 flex justify-between text-xs"><span>{p.path}</span><span>{p.views}</span></p>)}</Card>
            <Card testid="admin-automation-logs"><h3 className="font-heading text-sm font-semibold">Automation logs (all sessions)</h3><div className="max-h-64 overflow-auto">{ov.recent_executions.map((e) => <p key={e.id} className="mt-1 flex justify-between gap-2 text-xs"><span>{e.name}</span><Badge>{e.status}</Badge></p>)}</div></Card>
            <Card><h3 className="font-heading text-sm font-semibold">Admin audit log</h3><div className="max-h-64 overflow-auto">{ov.admin_audit.map((a, i) => <p key={i} className="mt-1 text-xs">{fmt(a.at)} · {a.actor} · {a.action}</p>)}</div></Card>
            <Card><h3 className="font-heading text-sm font-semibold">Error monitoring</h3>{ov.errors.length === 0 ? <p className="mt-1 text-xs text-slate-500">No errors recorded.</p> : ov.errors.map((e, i) => <p key={i} className="mt-1 text-xs">{fmt(e.at)} · {e.source} · {e.path} · {e.message}</p>)}
              <button onClick={() => api.post("/admin/demo/purge-stale").then((r) => { toast.success(`Purged ${r.data.purged} stale demo sessions`); reload(); })} className="mt-3 rounded-md border border-slate-300 px-3 py-1.5 text-xs" data-testid="admin-purge-demo">Purge demo sessions idle &gt; 3 days</button></Card>
          </div>
        </TabsContent>
        <TabsContent value="profile" className="mt-5"><ProfileTab profile={c.profile} reload={reload} /></TabsContent>
        {Object.keys(COLL).map((k) => <TabsContent key={k} value={k} className="mt-5"><CollectionTab coll={k} items={c[k]} reload={reload} /></TabsContent>)}
        <TabsContent value="messages" className="mt-5 space-y-2" data-testid="admin-messages">
          {msgs.length === 0 && <p className="text-sm text-slate-500">No messages yet.</p>}
          {msgs.map((m) => <Card key={m.id}><div className="flex justify-between gap-2"><p className="text-sm font-medium">{m.name} · {m.email} {m.company && `· ${m.company}`}</p>{!m.read ? <button onClick={() => api.patch(`/admin/messages/${m.id}`).then(reload)} className="text-xs text-teal-700">Mark read</button> : <Badge tone="muted">read</Badge>}</div><p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{m.message}</p><p className="mt-2 text-[11px] text-slate-500">{fmt(m.created_at)} · email: {m.email_status}</p></Card>)}
        </TabsContent>
        <TabsContent value="ucf" className="mt-5"><UcfAdmin /></TabsContent>
        <TabsContent value="resume" className="mt-5"><Card><p className="text-sm">{c.has_resume ? "A resume file is uploaded and served at Download Resume." : "No file uploaded — visitors get a PDF generated from your profile."}</p><label className="mt-3 inline-flex cursor-pointer items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm text-white"><Upload className="h-4 w-4" />Upload PDF/DOCX (max 5 MB)<input type="file" accept=".pdf,.docx" className="hidden" onChange={upload} data-testid="admin-resume-upload" /></label></Card></TabsContent>
        <TabsContent value="settings" className="mt-5"><SettingsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
