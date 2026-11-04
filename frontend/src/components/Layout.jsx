import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ErrorBoundary } from "./ErrorBoundary";
import { Menu, X, Download } from "lucide-react";
import { api, download } from "../lib/api";

export const NAV = [
  ["/", "Home"], ["/about", "About Me"], ["/experience", "Experience"], ["/expertise", "Expertise & Technology"], ["/lab", "Technology Lab"],
  ["/agents", "AI Agent Command Center"], ["/irm", "ServiceNow IRM"], ["/case-studies", "Projects & Case Studies"], ["/certifications", "Certifications & Education"], ["/resume", "Resume"], ["/contact", "Contact"],
];

export const downloadResume = () => download("/resume", "Seun_Olawepo_Professional_Resume.pdf");

export default function Layout() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
    api.post("/telemetry/pageview", { path: loc.pathname }).catch(() => {});
  }, [loc.pathname]);
  const link = ({ isActive }) => `whitespace-nowrap rounded px-2 py-1.5 text-[13px] font-medium transition-colors ${isActive ? "text-teal-700" : "text-slate-600 hover:text-slate-900"}`;
  return (
    <div className="min-h-screen bg-[#F8FAFC] font-body text-slate-900">
      <a href="#main" className="sr-only focus:not-sr-only">Skip to content</a>
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
          <Link to="/" className="flex items-center gap-2" data-testid="brand-link">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded bg-[#0B132B] font-heading text-xs font-extrabold text-teal-300">SO</span>
            <span className="leading-tight"><span className="block whitespace-nowrap font-heading text-sm font-bold">Seun Olawepo</span><span className="hidden whitespace-nowrap text-[11px] text-slate-500 2xl:block">Enterprise Technology & AI Governance</span></span>
          </Link>
          <nav className="hidden items-center gap-0.5 xl:flex" aria-label="Main">
            {NAV.slice(1).map(([to, l]) => <NavLink key={to} to={to} className={link} data-testid={`nav-${to.slice(1)}`}>{l}</NavLink>)}
          </nav>
          <button className="rounded p-2 xl:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu" data-testid="mobile-menu-toggle">{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
        </div>
        {open && (
          <nav className="border-t border-slate-200 bg-white px-5 py-3 xl:hidden" data-testid="mobile-menu">
            {NAV.map(([to, l]) => <NavLink key={to} to={to} end className={({ isActive }) => `block py-2 text-sm ${isActive ? "text-teal-700" : "text-slate-700"}`} data-testid={`mobile-nav-${to.slice(1) || "home"}`}>{l}</NavLink>)}
          </nav>
        )}
      </header>
      <main id="main"><ErrorBoundary resetKey={loc.pathname}><Outlet /></ErrorBoundary></main>
      <footer className="mt-20 bg-[#0B132B] text-slate-300">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 md:grid-cols-3">
          <div>
            <p className="font-heading text-base font-bold text-white">Seun Olawepo</p>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">Cybersecurity GRC · ServiceNow IRM · AI Governance & AI Agent Management · Program & Agile Delivery</p>
          </div>
          <div className="grid grid-cols-2 gap-1 text-xs">
            {[...NAV.slice(1), ["/automation", "Automation Control Center"], ["/demo", "Explore My Work — Live Demo"], ["/articles", "Articles"]].map(([to, l]) => <Link key={to} to={to} className="py-1 hover:text-white">{l}</Link>)}
          </div>
          <div className="text-xs text-slate-400">
            <button onClick={downloadResume} className="inline-flex items-center gap-2 rounded-md border border-slate-600 px-3 py-2 text-slate-200 hover:border-teal-400" data-testid="footer-resume-download"><Download className="h-4 w-4" />Download Resume</button>
            <p className="mt-4">All lab data is fictional. Labs are independent simulations and are not affiliated with, or records of, any employer or vendor. ServiceNow is a trademark of ServiceNow, Inc.; this site is not an official ServiceNow product.</p>
            <p className="mt-2">Privacy: no cookies for visitors; anonymous page counts only. <Link to="/admin" className="underline">Admin</Link></p>
          </div>
        </div>
      </footer>
    </div>
  );
}
