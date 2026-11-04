# PRD — Seun Olawepo | Enterprise Technology & AI Governance Portfolio

## Original problem statement
MASTER BUILD PROMPT: Seun Olawepo — Enterprise Technology, Cybersecurity, GRC & AI Portfolio. The user asked for a production-quality full-stack portfolio and enterprise demo platform. Requirements:
- Verified career experience and a role-based career-path navigator.
- 10 interconnected interactive labs: ServiceNow IRM, ServiceNow Admin/Dev, Cyber Risk, IT Audit, Third-Party Risk, AI Governance, AI Agent Manager/Command Center, Project/Product delivery, SAFe RTE/PI Planning, IR & BCDR.
- A central Enterprise Automation Engine with 7 cross-lab workflows.
- The D3 Command independent product section.
- A public recruiter demo with isolated data and reset.
- 12 case studies and a searchable skills directory.
- A secure admin dashboard.
- Reports (PDF/CSV), automated tests, and SEO/deployment.
- No invented employer accomplishments, certifications or metrics; simulations clearly labeled.

User inputs:
- Employment dates: LoanDepot Oct 2025–Present; TSPI/USDA May 2023–Oct 2025; Fidelity Jan 2019–Apr 2023; UnitedHealth Group Feb 2016–Jan 2019; Mastercard Jan 2012–Feb 2016; AT&T Jan 2009–Jan 2012.
- Show employer names only in Experience, and never link fictional lab data to employers.
- Labs are public; only the admin area requires login.
- The admin email is set securely and is not published.
- Contact form messages go to the admin inbox and to the notification email.
- AI demos have strict daily limits and a labeled simulation fallback.

## Architecture
- **Backend:** FastAPI + MongoDB.
  - `engine.py`: workflow engine with approval gates, retries, skip rules, fault injection (ContextVar) and an audit trail.
  - Lab modules: `labs_grc.py`, `labs_sn.py`, `labs_ops.py`, `agents.py`, `safe.py`.
  - `reports.py`: reportlab PDF and CSV output.
  - `auth.py`: JWT httpOnly cookies, bcrypt, per-email lockout.
  - `content.py`: portfolio content and seeds.
  - `seed_labs.py`: per-browser demo sessions keyed by the X-Demo-Session header, seeded under a lock.
  - A background scheduler checks overdue milestones and remediation and escalates impediments every 15 minutes.
- **Frontend:** React, Tailwind, shadcn/ui, recharts. A config-driven LabPage (`lib/labs.js`), an Automation Control Center and the Admin dashboard.
- **Integrations:**
  - Emergent LLM key, live Claude (claude-haiku-5-5). Limits: 60 calls/day globally, 12 per visitor, and a $2 budget display. Multi-agent helper agents always run in simulation.
  - Emergent managed Resend sends contact notifications to NOTIFY_EMAIL.

## User personas
Recruiters, CISOs and CIOs, GRC hiring managers, ServiceNow technical managers, AI program directors and Agile leaders. The site owner (Seun) manages it as the admin.

## Implemented (2026-11-04)
- Portfolio pages: Home, About, Experience timeline and detail, Expertise directory with search, Case studies (12) with detail pages, Certifications (managed by admin), Resume, Contact, Articles, D3 Command section, role navigator for 27 roles.
- All 10 labs, each with forms, a backend business-rules API, persistence, automation, approvals, KPI dashboards, PDF/CSV reports, a guided demo and reset.
- Automation Control Center: workflow catalog, demo triggers, scheduler, fault injection with retry, analytics, execution PDF evidence.
- Admin: content CRUD, messages, resume upload, AI settings, overview of logs, page views and errors, stale-session purge, password change.
- SEO metadata, Open Graph tags, sitemap and robots.txt.
- Testing: 36 backend pytest cases pass (`backend/tests`), and the frontend passed E2E testing (iteration_1).
- 2026-11-04: Recruiter Tour Mode at /tour. A one-click 9-step tour covering IRM, AI agents and SAFe PI Planning that makes real backend calls, with progress, step lock and re-run reset. Linked from the Home hero, /lab and /demo. Passed testing (iteration_2).
- 2026-11-04: Enterprise ServiceNow IRM workspace at /irm (lab key "grc", files `grc.py` and `grc_seed.py`). It covers 11 roles with permissions enforced in the backend through the state-machine table T. It includes:
  - Policy lifecycle: Draft → Review → Approved → Published → Retired, plus versioning.
  - Acknowledgment campaigns: tasks, in-app notifications, reminders and escalation, and a close step that produces the completion report.
  - Exceptions: Requested → Review (after risk assessment) → Active or Rejected → Expired or Closed, plus renewal.
  - Risks: questionnaire scoring and threshold routing to Treatment, then approval and Monitoring or Accepted, then Closed.
  - Failed control assessment → Issue → Remediation task. Evidence is required, auditor validation is required, a failed validation creates a rework task, and closing the issue makes the control Effective and updates the risk residual.
  - Linked records, activity stream, work notes, attachment metadata, a scheduled monitoring workflow, a 17-step end-to-end scenario, and governance PDF/CSV reports.
  - Seeded completed records, labeled as fictional.
- 2026-11-04: Added 7 certifications (by category, linked to labs), education (2 degrees) and new frameworks: GDPR, CCPA, ISO/IEC 27701, NIST SP 800-171 and CMMC (also in the audit lab). Certificate upload is available in admin. 54/54 pytest pass (iteration_3).
- Pending (user-ordered sequence): deploy (needs 50 ECU confirmation) → verify URL → custom domain (Emergent sells domains in Manage Publishes → Domain; SSL is included; manual DNS: A @ 162.159.142.117 and 172.66.2.113, CNAME www → apex) → user updates the resume → upload the resume in admin.

## Backlog
- P1: Deploy to production and set a custom domain. Upload the real resume PDF, add verified certifications and the GitHub URL in admin.
- P1: Optional authorized ServiceNow Personal Developer Instance connector (architecture only so far).
- P2: Replace native date and select pickers with shadcn components; format raw JSON action results; add an OG preview image.
- P2: Push to GitHub (repo seun-olawepo-portfolio) using Save to GitHub.

## Next tasks
Owner review of the experience bullet wording (it is conservative and editable in admin). Deploy.
