import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, ArrowRight, Search } from "lucide-react";
import { useContent } from "../context/ContentContext";
import { labByKey } from "../lib/labs";
import { downloadResume } from "../components/Layout";
import { ContactForm } from "../components/ContactForm";
import { Badge, Card, Eyebrow, PageHeader } from "../components/kit";

const Loading = () => <div className="p-10 text-sm text-slate-500">Loading…</div>;
const labLink = (k) => (k === "agents" ? "/agents" : `/lab/${k}`);

export function About() {
  const c = useContent();
  if (!c) return <Loading />;
  const p = c.profile;
  return (
    <div>
      <PageHeader eyebrow="About me" title={p.name}>{p.headline}</PageHeader>
      <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 lg:grid-cols-3">
        <div className="lg:col-span-2">{p.summary.split("\n\n").map((t, i) => <p key={i} className="mb-4 text-sm leading-relaxed text-slate-700 sm:text-base">{t}</p>)}</div>
        <Card><Eyebrow>Verified highlights</Eyebrow>{p.metrics.map((m) => <p key={m.label} className="mt-3 text-sm"><span className="font-heading text-xl font-bold text-teal-700">{m.value}</span> {m.label}</p>)}</Card>
        <div className="lg:col-span-3"><Eyebrow>Education</Eyebrow><div className="mt-3"><EducationList edu={c.education} /></div></div>
      </div>
    </div>
  );
}

export function Experience() {
  const c = useContent();
  if (!c) return <Loading />;
  return (
    <div>
      <PageHeader eyebrow="Professional experience" title="Executive career timeline">Actual professional experience. Interactive labs elsewhere on this site use fictional data and are not employer records.</PageHeader>
      <div className="mx-auto max-w-5xl px-5 py-12 sm:px-8">
        <ol className="border-l-2 border-slate-200" data-testid="experience-timeline">
          {c.experience.map((e) => (
            <li key={e.slug} className="relative ml-6 pb-8">
              <span className="absolute -left-[33px] top-2 h-4 w-4 rounded-full border-4 border-white bg-teal-600 shadow" />
              <Link to={`/experience/${e.slug}`} className="block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-teal-500" data-testid={`experience-${e.slug}`}>
                <p className="font-mono text-xs text-slate-500">{e.start} – {e.end}</p>
                <h2 className="mt-1 font-heading text-lg font-semibold">{e.title}</h2>
                <p className="text-sm text-slate-600">{e.employer}</p>
                <ul className="mt-3 space-y-1 text-sm text-slate-700">{e.highlights.map((h) => <li key={h}>• {h}</li>)}</ul>
              </Link>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export function ExperienceDetail() {
  const { slug } = useParams();
  const c = useContent();
  if (!c) return <Loading />;
  const e = c.experience.find((x) => x.slug === slug);
  if (!e) return <div className="p-10">Not found. <Link to="/experience" className="text-teal-700">Back</Link></div>;
  return (
    <div>
      <PageHeader eyebrow={`${e.employer} · ${e.start} – ${e.end}`} title={e.title} />
      <div className="mx-auto grid max-w-7xl gap-6 px-5 py-12 sm:px-8 lg:grid-cols-3">
        <Card className="lg:col-span-2" testid="experience-detail"><h2 className="font-heading text-base font-semibold">Areas of responsibility</h2><ul className="mt-3 space-y-2 text-sm text-slate-700">{e.highlights.map((h) => <li key={h}>• {h}</li>)}</ul><p className="mt-4 text-xs text-slate-500">{e.note}</p></Card>
        <Card testid="experience-related-labs"><h2 className="font-heading text-base font-semibold">Related demonstrations</h2><p className="mt-1 text-xs text-slate-500">Independent portfolio simulations using fictional data — not records of {e.employer}.</p>
          {e.labs.map((k) => labByKey[k] && <Link key={k} to={labLink(k)} className="mt-3 flex items-center justify-between rounded-md border border-slate-100 p-3 text-sm hover:border-teal-500">{labByKey[k].name}<ArrowRight className="h-4 w-4 text-teal-700" /></Link>)}
        </Card>
      </div>
    </div>
  );
}

export function Expertise() {
  const c = useContent();
  const [q, setQ] = useState("");
  const groups = useMemo(() => {
    if (!c) return [];
    const f = c.skills.filter((s) => `${s.name} ${s.category}`.toLowerCase().includes(q.toLowerCase()));
    return [...new Set(f.map((s) => s.category))].map((cat) => [cat, f.filter((s) => s.category === cat)]);
  }, [c, q]);
  if (!c) return <Loading />;
  const areas = c.experience.flatMap((e) => e.labs.map((l) => [l, e]));
  return (
    <div>
      <PageHeader eyebrow="Expertise & technology" title="Skills & technology directory">Every skill links to relevant experience and a lab demonstration.</PageHeader>
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
        <div className="relative max-w-md"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search skills (e.g. NIST, PI Planning, Tenable)" className="w-full rounded-md border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm" data-testid="skills-search" /></div>
        <div className="mt-8 grid gap-5 md:grid-cols-2" data-testid="skills-directory">
          {groups.map(([cat, skills]) => {
            const labs = skills[0].labs;
            const exp = [...new Map(areas.filter(([l]) => labs.includes(l)).map(([, e]) => [e.slug, e])).values()];
            return (
              <Card key={cat} testid={`skill-group-${cat.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
                <h2 className="font-heading text-base font-semibold">{cat}</h2>
                <div className="mt-3 flex flex-wrap gap-1.5">{skills.map((s) => <Link key={s.id} to={labLink(s.labs[0])}><Badge tone="teal">{s.name}</Badge></Link>)}</div>
                <p className="mt-4 font-mono text-[11px] uppercase tracking-wider text-slate-500">Demonstrated in</p>
                <div className="mt-1 flex flex-wrap gap-2 text-xs">{labs.map((k) => <Link key={k} to={labLink(k)} className="text-teal-700 underline">{labByKey[k].short}</Link>)}</div>
                <p className="mt-3 font-mono text-[11px] uppercase tracking-wider text-slate-500">Related experience</p>
                <div className="mt-1 flex flex-wrap gap-2 text-xs">{exp.map((e) => <Link key={e.slug} to={`/experience/${e.slug}`} className="text-slate-700 underline">{e.employer}</Link>)}</div>
              </Card>
            );
          })}
          {groups.length === 0 && <p className="text-sm text-slate-500">No skills match “{q}”.</p>}
        </div>
      </div>
    </div>
  );
}

export function CaseStudies() {
  const c = useContent();
  if (!c) return <Loading />;
  return (
    <div>
      <PageHeader eyebrow="Projects & case studies" title="Case study library">Illustrative scenarios built on fictional data. They make no claims about employer outcomes.</PageHeader>
      <div className="mx-auto grid max-w-7xl gap-4 px-5 py-12 sm:px-8 md:grid-cols-2 lg:grid-cols-3" data-testid="case-study-list">
        {c.case_studies.map((cs) => <Link key={cs.slug} to={`/case-studies/${cs.slug}`} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-teal-500" data-testid={`case-${cs.slug}`}><Badge tone="teal">{labByKey[cs.lab]?.short}</Badge><h2 className="mt-3 font-heading text-base font-semibold">{cs.title}</h2><p className="mt-2 text-sm text-slate-600">{cs.challenge}</p></Link>)}
      </div>
    </div>
  );
}

export function CaseStudyDetail() {
  const { slug } = useParams();
  const c = useContent();
  if (!c) return <Loading />;
  const cs = c.case_studies.find((x) => x.slug === slug);
  if (!cs) return <div className="p-10">Not found.</div>;
  const rows = [["Business challenge", cs.challenge], ["Scope", cs.scope], ["Approach", cs.approach], ["Technology", cs.technology], ["Frameworks", cs.frameworks], ["Deliverables", cs.deliverables], ["Evidence", cs.evidence]];
  return (
    <div>
      <PageHeader eyebrow="Case study" title={cs.title}>{cs.disclaimer}</PageHeader>
      <div className="mx-auto max-w-4xl space-y-4 px-5 py-12 sm:px-8" data-testid="case-study-detail">
        {rows.map(([k, v]) => <Card key={k}><h2 className="font-heading text-sm font-semibold text-slate-900">{k}</h2><p className="mt-1 text-sm text-slate-700">{v}</p></Card>)}
        <Link to={labLink(cs.lab)} className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-800" data-testid="case-open-lab">Open related interactive lab<ArrowRight className="h-4 w-4" /></Link>
      </div>
    </div>
  );
}

export function CredentialGrid({ certs, files = [] }) {
  const cats = [...new Set(certs.map((x) => x.category || "Other"))];
  return (
    <div className="space-y-6" data-testid="credential-grid">
      {cats.map((cat) => (
        <div key={cat}>
          <p className="font-mono text-[11px] uppercase tracking-wider text-teal-700">{cat}</p>
          <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {certs.filter((x) => (x.category || "Other") === cat).map((x) => (
              <Card key={x.id} testid={`cert-${x.id}`}>
                <h3 className="font-heading text-sm font-semibold text-slate-900">{x.name}</h3>
                <p className="mt-1 text-xs text-slate-600">{x.issuer}{x.date ? ` · ${x.date}` : ""}</p>
                {x.status && <p className="mt-2"><Badge tone="muted">{x.status}</Badge></p>}
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  {(x.labs || []).map((k) => labByKey[k] && <Link key={k} to={k === "grc" ? "/irm" : labLink(k)} className="text-teal-700 underline">{k === "grc" ? "ServiceNow IRM" : labByKey[k].short}</Link>)}
                  {(x.labs || []).includes("grc") && !labByKey.grc && <Link to="/irm" className="text-teal-700 underline">ServiceNow IRM workspace</Link>}
                  {x.credential_url && <a href={x.credential_url} target="_blank" rel="noopener noreferrer" className="text-slate-700 underline">Verify credential</a>}
                  {files.includes(x.id) && <a href={`${process.env.REACT_APP_BACKEND_URL}/api/certifications/${x.id}/file`} target="_blank" rel="noopener noreferrer" className="text-slate-700 underline">View certificate</a>}
                </div>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function EducationList({ edu }) {
  return <div className="grid gap-3 sm:grid-cols-2" data-testid="education-list">{edu.map((e) => <Card key={e.id}><h3 className="font-heading text-sm font-semibold">{e.degree}</h3><p className="text-xs text-slate-700">{e.field}</p><p className="mt-1 text-xs text-slate-500">{e.institution}{e.graduation_date ? ` · ${e.graduation_date}` : ""}</p></Card>)}</div>;
}

export function Certifications() {
  const c = useContent();
  if (!c) return <Loading />;
  return (
    <div>
      <PageHeader eyebrow="Certifications & education" title="Certifications & Education">Credentials are listed as provided by Seun Olawepo. Where no verification link is shown, the credential has not been independently verified on this site.</PageHeader>
      <div className="mx-auto max-w-7xl space-y-10 px-5 py-12 sm:px-8" data-testid="certifications-list">
        <CredentialGrid certs={c.certifications} files={c.cert_files} />
        <div><p className="font-mono text-[11px] uppercase tracking-wider text-teal-700">Education</p><div className="mt-2"><EducationList edu={c.education} /></div></div>
      </div>
    </div>
  );
}

export function Resume() {
  const c = useContent();
  if (!c) return <Loading />;
  return (
    <div>
      <PageHeader eyebrow="Resume" title="Resume">{c.has_resume ? "Download my latest uploaded resume." : "A PDF resume generated from the experience and skills on this site."}</PageHeader>
      <div className="mx-auto max-w-4xl px-5 py-12 sm:px-8">
        <button onClick={downloadResume} className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-800" data-testid="resume-download"><Download className="h-4 w-4" />Download Resume</button>
        <div className="mt-8 space-y-3">{c.experience.map((e) => <Card key={e.slug}><p className="font-heading text-sm font-semibold">{e.title} · {e.employer}</p><p className="font-mono text-xs text-slate-500">{e.start} – {e.end}</p></Card>)}</div>
      </div>
    </div>
  );
}

export function Contact() {
  return (
    <div>
      <PageHeader eyebrow="Contact" title="Get in touch">Recruiters and hiring managers: messages reach my inbox directly.</PageHeader>
      <div className="mx-auto max-w-3xl px-5 py-12 sm:px-8"><ContactForm /></div>
    </div>
  );
}

export function Articles() {
  const c = useContent();
  if (!c) return <Loading />;
  return (
    <div>
      <PageHeader eyebrow="Articles" title="Notes & articles" />
      <div className="mx-auto max-w-3xl space-y-4 px-5 py-12 sm:px-8" data-testid="articles-list">{c.articles.map((a) => <Card key={a.id}><p className="font-mono text-xs text-slate-500">{a.date}</p><h2 className="mt-1 font-heading text-lg font-semibold">{a.title}</h2><p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{a.body}</p></Card>)}</div>
    </div>
  );
}
