import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Download, FlaskConical, Bot, Briefcase, ExternalLink, ShieldCheck, Workflow, Brain, Layers, Play } from "lucide-react";
import { useContent } from "../context/ContentContext";
import { LABS, labByKey } from "../lib/labs";
import { CAREER_PATHS } from "../lib/roles";
import { downloadResume } from "../components/Layout";
import { ContactForm } from "../components/ContactForm";
import { CredentialGrid } from "./Pages";
import { Badge, Card, Eyebrow } from "../components/kit";

const btn = "inline-flex items-center gap-2 rounded-md px-5 py-2.5 text-sm font-medium transition-colors";

function RoleNavigator({ c }) {
  const [role, setRole] = useState(CAREER_PATHS[0].role);
  const p = CAREER_PATHS.find((x) => x.role === role);
  return (
    <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8" data-testid="role-navigator">
      <Eyebrow>Role-based navigation</Eyebrow>
      <h2 className="mt-2 font-heading text-2xl font-bold tracking-tight sm:text-3xl">Hiring for a specific role? Start here.</h2>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <label htmlFor="role-select" className="text-sm text-slate-600">Career path</label>
        <select id="role-select" value={role} onChange={(e) => setRole(e.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm" data-testid="role-selector">
          {CAREER_PATHS.map((x) => <option key={x.role}>{x.role}</option>)}
        </select>
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card testid="role-experience"><h3 className="font-heading text-sm font-semibold">Most relevant experience</h3>
          {c.experience.filter((e) => p.exp.includes(e.slug)).map((e) => <Link key={e.slug} to={`/experience/${e.slug}`} className="mt-3 block rounded-md border border-slate-100 p-3 hover:border-teal-500"><p className="text-sm font-medium">{e.title}</p><p className="text-xs text-slate-500">{e.employer} · {e.start} – {e.end}</p></Link>)}
        </Card>
        <Card testid="role-skills"><h3 className="font-heading text-sm font-semibold">Key skills</h3>
          {p.cats.map((cat) => <div key={cat} className="mt-3"><p className="font-mono text-[11px] uppercase tracking-wider text-slate-500">{cat}</p><div className="mt-1 flex flex-wrap gap-1">{c.skills.filter((s) => s.category === cat).slice(0, 8).map((s) => <Badge key={s.id} tone="muted">{s.name}</Badge>)}</div></div>)}
        </Card>
        <Card testid="role-labs"><h3 className="font-heading text-sm font-semibold">Demonstrations to run</h3>
          {p.labs.map((k) => <Link key={k} to={k === "agents" ? "/agents" : `/lab/${k}`} className="mt-3 flex items-center justify-between rounded-md border border-slate-100 p-3 text-sm hover:border-teal-500" data-testid={`role-lab-${k}`}>{labByKey[k].name}<ArrowRight className="h-4 w-4 text-teal-700" /></Link>)}
        </Card>
      </div>
    </section>
  );
}

const SHOW = [["irm", ShieldCheck, "Control failure → finding → remediation → approval, with configurable scoring and executive dashboard."], ["agents", Bot, "Nine enterprise agents, multi-agent orchestration, guardrails, evaluation and cost analytics."], ["aigov", Brain, "AI intake, risk tiering, required assessments, agent review and board approval."], ["safe", Layers, "Five-team PI Planning: WSJF, program board, dependency & capacity alerts, ROAM, confidence vote."]];

export default function Home() {
  const c = useContent();
  if (!c) return <div className="p-10 text-sm text-slate-500" data-testid="home-loading">Loading…</div>;
  const p = c.profile;
  const d3 = p.d3_command;
  return (
    <div>
      <section className="relative overflow-hidden bg-[#0B132B] text-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(13,148,136,0.25),transparent_55%)]" />
        <div className="relative mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="font-mono text-[11px] uppercase tracking-[0.2em] text-teal-300">{p.name} · Enterprise Technology & AI Governance</motion.p>
          <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="mt-4 max-w-5xl font-heading text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl lg:text-5xl" data-testid="hero-headline">{p.headline}</motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }} className="mt-5 max-w-4xl text-sm text-slate-300 sm:text-base">{p.supporting}</motion.p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/experience" className={`${btn} bg-teal-600 text-white hover:bg-teal-500`} data-testid="cta-explore-experience"><Briefcase className="h-4 w-4" />Explore My Experience</Link>
            <Link to="/lab" className={`${btn} bg-white text-slate-900 hover:bg-slate-100`} data-testid="cta-launch-lab"><FlaskConical className="h-4 w-4" />Launch Enterprise Technology Lab</Link>
            <Link to="/agents" className={`${btn} border border-slate-500 text-white hover:border-teal-300`} data-testid="cta-run-agent-demo"><Bot className="h-4 w-4" />Run AI Agent Demo</Link>
            <button onClick={downloadResume} className={`${btn} border border-slate-500 text-white hover:border-teal-300`} data-testid="cta-download-resume"><Download className="h-4 w-4" />Download Resume</button>
          </div>
          <Link to="/tour" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-teal-300 hover:text-teal-200" data-testid="cta-recruiter-tour"><Play className="h-4 w-4" />Short on time? Take the 5-minute recruiter tour <ArrowRight className="h-4 w-4" /></Link>
          <div className="mt-14 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-white/10 bg-white/10 md:grid-cols-4" data-testid="verified-metrics">
            {p.metrics.map((m) => <div key={m.label} className="bg-[#0B132B] p-5"><p className="font-heading text-3xl font-extrabold text-teal-300">{m.value}</p><p className="mt-1 text-xs text-slate-400">{m.label}</p></div>)}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-5">
        <div className="lg:col-span-3"><Eyebrow>Executive summary</Eyebrow>{p.summary.split("\n\n").map((t, i) => <p key={i} className="mt-4 text-sm leading-relaxed text-slate-700 sm:text-base">{t}</p>)}</div>
        <div className="lg:col-span-2"><Eyebrow>Career timeline</Eyebrow>
          <ol className="mt-4 border-l border-slate-200">{c.experience.map((e) => <li key={e.slug} className="relative ml-4 pb-4"><span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-teal-600" /><Link to={`/experience/${e.slug}`} className="text-sm font-medium hover:text-teal-700">{e.title}</Link><p className="text-xs text-slate-500">{e.employer} · {e.start} – {e.end}</p></li>)}</ol>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-4 sm:px-8" data-testid="home-certifications">
        <Eyebrow>Certifications</Eyebrow>
        <h2 className="mt-2 mb-5 font-heading text-2xl font-bold tracking-tight sm:text-3xl">Professional credentials</h2>
        <CredentialGrid certs={c.certifications} files={c.cert_files} />
        <Link to="/certifications" className="mt-4 inline-block text-sm text-teal-700">Certifications & Education →</Link>
      </section>

      <section className="mx-auto max-w-7xl px-5 pt-12 sm:px-8">
        <Link to="/irm" className="block rounded-lg border-2 border-teal-600 bg-white p-6 transition-colors hover:bg-teal-50" data-testid="home-irm-flagship"><Eyebrow>Flagship demonstration</Eyebrow><h2 className="mt-2 font-heading text-xl font-bold">Enterprise ServiceNow IRM — End-to-End Governance Workflow</h2><p className="mt-2 text-sm text-slate-600">Policy lifecycle, acknowledgment campaigns, exceptions, risk assessments, issues and remediation. Covers 11 roles with backend-enforced permissions, linked records and activity streams.</p></Link>
      </section>

      <RoleNavigator c={c} />

      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <Eyebrow>Featured interactive demonstrations</Eyebrow>
          <h2 className="mt-2 font-heading text-2xl font-bold tracking-tight sm:text-3xl">See how I solve enterprise problems</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {SHOW.map(([k, I, d]) => <Link key={k} to={k === "agents" ? "/agents" : `/lab/${k}`} className="group rounded-lg border border-slate-200 p-6 transition-colors hover:border-teal-500" data-testid={`featured-${k}`}><I className="h-6 w-6 text-teal-700" /><h3 className="mt-3 font-heading text-lg font-semibold">{labByKey[k].name}</h3><p className="mt-2 text-sm text-slate-600">{d}</p><span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-teal-700">Run demo <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></span></Link>)}
          </div>
          <div className="mt-10 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {LABS.map((l) => <Link key={l.key} to={l.key === "agents" ? "/agents" : `/lab/${l.key}`} className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs hover:border-teal-500" data-testid={`home-lab-${l.key}`}><span className="font-mono text-teal-700">Lab {l.n}</span><p className="mt-1 font-medium text-slate-800">{l.short}</p></Link>)}
          </div>
          <Link to="/automation" className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-teal-700" data-testid="home-automation-link"><Workflow className="h-4 w-4" />Enterprise Automation Control Center — 7 cross-lab workflows</Link>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8">
        <Eyebrow>Case studies</Eyebrow>
        <div className="mt-6 grid gap-4 md:grid-cols-3">{c.case_studies.slice(0, 3).map((cs) => <Link key={cs.slug} to={`/case-studies/${cs.slug}`} className="rounded-lg border border-slate-200 bg-white p-5 hover:border-teal-500" data-testid={`home-case-${cs.slug}`}><h3 className="font-heading text-base font-semibold">{cs.title}</h3><p className="mt-2 text-sm text-slate-600">{cs.challenge}</p></Link>)}</div>
        <Link to="/case-studies" className="mt-4 inline-block text-sm text-teal-700">All 12 case studies →</Link>
      </section>

      <section className="bg-[#1C2541] py-16 text-white" data-testid="d3-command-section">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 sm:px-8 lg:grid-cols-2">
          <div><p className="font-mono text-[11px] uppercase tracking-[0.18em] text-teal-300">Independent product experience</p><h2 className="mt-2 font-heading text-2xl font-bold sm:text-3xl">{d3.title}</h2><p className="mt-4 text-sm text-slate-300">{d3.description}</p>
            <div className="mt-5 flex flex-wrap gap-3">{d3.links.map((u) => <a key={u} href={u} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-md border border-slate-500 px-3 py-2 text-xs hover:border-teal-300" data-testid={`d3-link-${u.includes("app.") ? "app" : "site"}`}>{u.replace("https://", "")}<ExternalLink className="h-3 w-3" /></a>)}</div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><p className="font-mono text-[11px] uppercase tracking-wider text-slate-400">Product capability categories</p><ul className="mt-2 space-y-1 text-sm">{d3.capabilities.map((x) => <li key={x}>• {x}</li>)}</ul></div>
            <div><p className="font-mono text-[11px] uppercase tracking-wider text-slate-400">Experience involved</p><ul className="mt-2 space-y-1 text-sm">{d3.experience.map((x) => <li key={x}>• {x}</li>)}</ul></div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-5 py-16 sm:px-8 lg:grid-cols-2">
        <div><Eyebrow>Contact</Eyebrow><h2 className="mt-2 font-heading text-2xl font-bold sm:text-3xl">Let's talk about your team's needs</h2><p className="mt-3 text-sm text-slate-600">Messages go directly to my inbox. {p.github_url && <a href={p.github_url} className="text-teal-700 underline" data-testid="home-github-link">GitHub</a>}</p></div>
        <ContactForm />
      </section>
    </div>
  );
}
