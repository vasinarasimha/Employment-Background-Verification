# Employment Background Verification

A small full-stack product for HR teams to manage candidate background verification workflows.

## Product Scope

This MVP supports:
- Candidate intake (name, email, phone, DOB, position)
- Background check creation per candidate
- Check lifecycle tracking (`in_progress`, `passed`, `failed`)
- Candidate risk status derived from checks (`pending`, `in_review`, `cleared`, `flagged`)
- Dashboard metrics for operational visibility
- Role-based access control with 4 groups:
  - `super_admin`
  - `admin`
  - `agent`
  - `candidate`
- Employer-specific verification step templates managed by `super_admin`
- Admin-focused menu model:
  - `Dashboard` (companies using the portal)
  - `Employers` (create/manage employers)
  - `Reports` (Excel/PDF exports with date filters)

## Stack

- Backend: Python + Flask + Flask-SQLAlchemy + Flask-CORS
- Frontend: React (Vite)
- Database: PostgreSQL

## Architecture

- Frontend calls REST API at `/api/*`
- Backend contains all business logic and persistence
- Relational schema:
  - `candidates` (1)
  - `background_checks` (many, FK to candidate)
  - `employers`
  - `employer_verification_steps`
  - `users`
  - `auth_tokens`
  - `employer_candidates`
  - `agent_employers`
- Candidate status is computed from check outcomes:
  - Any failed check -> `flagged`
  - All checks passed -> `cleared`
  - At least one in progress -> `in_review`
  - No checks -> `pending`

## Repository Structure

- `backend/app.py` - Flask app, models, API endpoints, seed endpoint
- `backend/requirements.txt` - Python dependencies
- `frontend/src/App.jsx` - main UI logic and views
- `frontend/src/api.js` - API client
- `README.md` - setup + key technical decisions
- `WALKTHROUGH.md` - 10-15 minute walkthrough guide
- `AI_GUIDANCE.md`, `AGENTS.md`, `CLAUDE.md` - AI usage and constraints

## Setup

### 1) Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

API runs at `http://localhost:5000`.

### 2) Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

UI runs at `http://localhost:5173`.

## Key Technical Decisions

1. Flask + SQLAlchemy for fast, clear API development
- Minimal framework overhead, easy-to-read endpoints, and direct model mapping.

2. PostgreSQL for relational storage
- Production-oriented relational engine with strong consistency and tooling.
- Configured via `DATABASE_URL` in `backend/.env`.

3. Derived candidate status instead of manual-only state
- Reduces operator error and keeps risk state consistent with check results.

4. Keep business logic in backend, not frontend
- Frontend remains thin and easier to replace.
- API remains reusable for future automation or third-party integrations.

5. Seed endpoint for demo readiness
- Enables quick interview demonstration without manual data entry.

6. Backend-enforced RBAC with employer scoping
- Frontend only reflects permissions; all enforcement is API-side.
- Candidate status recomputation remains backend authoritative after every check update.

## API Endpoints (Core)

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/health`
- `GET /api/dashboard/summary`
- `GET /api/employers`
- `POST /api/employers` (`super_admin`, `admin`)
- `GET /api/employers/<id>/steps`
- `POST /api/employers/<id>/steps` (`super_admin`)
- `POST /api/users` (`super_admin`, create `admin`/`agent`)
- `GET /api/reports/candidates?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&format=xlsx|pdf` (`super_admin`, `admin`)
- `GET /api/candidates`
- `POST /api/candidates` (`super_admin`)
- `GET /api/candidates/<id>`
- `PATCH /api/candidates/<id>` (`super_admin`)
- `POST /api/candidates/<id>/checks` (`super_admin`)
- `PATCH /api/checks/<id>` (`super_admin`, `agent`)
- `POST /api/seed`

All protected endpoints require `Authorization: Bearer <token>`.

## RBAC Behavior

- `super_admin`
  - Creates employers
  - Defines employer verification steps
  - Grants employer access users (`admin`, `agent`)
  - Full cross-employer visibility
- `admin`
  - Creates and manages employers
  - Access to dashboard company metrics
  - Downloads Excel/PDF reports with date range filters
  - No candidate/check mutation access
- `agent`
  - Scoped to assigned employer(s)
  - Verifies checks (`passed`/`failed`) for allowed candidates
- `candidate`
  - Logs in using admin-issued credentials
  - Read-only access to own candidate record/checks

## Default Bootstrap Credentials

On first run, backend auto-creates a super admin:
- email: `superadmin@system.local`
- password: `SuperAdmin123!`

These can be overridden with env vars:
- `DEFAULT_SUPERADMIN_EMAIL`
- `DEFAULT_SUPERADMIN_PASSWORD`
- `DEFAULT_SUPERADMIN_NAME`

## AI Usage Summary

Used AI to:
- Scaffold project structure and code boilerplate quickly
- Draft API/resource design and state transition rules
- Generate starter UI and docs

Human-directed decisions:
- Domain model choice and status logic
- Endpoint boundaries and payload shapes
- Tradeoff selection for MVP scope vs extensibility

See `AI_GUIDANCE.md` for detailed prompt and governance patterns.

## Risks / Gaps

- No audit trail for compliance actions
- No async provider integrations (checks are manually updated)
- No automated tests in this MVP
- Add auth and audit trail hardening before production deployment

## Extension Approach

1. Add auth + roles (`HR_Analyst`, `HR_Manager`, `Auditor`)
2. Add audit/event log table for every workflow mutation
3. Add async jobs (Celery/RQ) for real provider calls
4. Add webhooks for check completion
5. Add document upload + encrypted storage + retention policies
6. Add test suite (pytest + API integration + frontend unit tests)

## Walkthrough

Use `WALKTHROUGH.md` as the 10-15 minute presentation script.
