# seun-olawepo-portfolio

Seun Olawepo | Enterprise Technology & AI Governance: a portfolio and enterprise technology demo platform built with FastAPI, MongoDB and React.

## Architecture
- **Backend** (`/backend`, FastAPI, Motor/MongoDB)
  - `engine.py`: the workflow engine. It handles steps, human approval gates, retries (3 attempts), skip conditions and fault injection, and keeps the audit trail.
  - `labs_grc.py` (IRM, Cyber, Audit, Vendor), `labs_sn.py` (the ServiceNow-style simulator), `labs_ops.py` (AI Gov, Project, IR/BCDR), `agents.py` (the AI Agent Command Center), `safe.py` (SAFe PI Planning).
  - `reports.py`: PDF (reportlab) and CSV output. `content.py`: portfolio content and seeds. `auth.py`: JWT httpOnly cookie admin auth with bcrypt and lockout.
  - `seed_labs.py`: isolated demo sessions, keyed by the `X-Demo-Session` header that each browser generates. Supports lazy seeding and reset.
  - API docs are served at `/api/docs`.
- **Frontend** (`/frontend`, React, Tailwind, shadcn/ui, recharts). One config-driven LabPage (`src/lib/labs.js`) renders all ten labs.

## Environment (backend/.env)
`MONGO_URL, DB_NAME, CORS_ORIGINS, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, NOTIFY_EMAIL, EMERGENT_LLM_KEY, EMERGENT_EMAIL_KEY, EMAIL_FROM_NAME, LIVE_AI_DAILY_LIMIT, LIVE_AI_SESSION_LIMIT, AGENT_DAILY_BUDGET_USD`

## Tests
`REACT_APP_BACKEND_URL=<url> python -m pytest backend/tests -q` (36 API tests)

## Content updates
Sign in at `/admin` to edit the profile and homepage, experience, skills, certifications, case studies and articles. You can also upload a resume (PDF or DOCX), read contact messages, review automation logs and errors, and toggle live AI or change its model and limits.
