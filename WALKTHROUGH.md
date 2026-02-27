# Walkthrough (10-15 Minutes)

## 1. Problem and Goal (1-2 min)
- Goal: Reduce manual HR risk by centralizing candidate verification status.
- Product: Employment Background Verification dashboard with clear pass/fail workflow.

## 2. Architecture Overview (2 min)
- React frontend (Vite) for HR operations UI.
- Flask API handling all domain logic and persistence.
- PostgreSQL relational database with two core tables:
  - `candidates`
  - `background_checks` (FK to candidate)

## 3. Code Structure (2 min)
- Backend:
  - `backend/app.py`: models, routes, status computation
  - `backend/requirements.txt`
- Frontend:
  - `frontend/src/App.jsx`: UI state and actions
  - `frontend/src/api.js`: API abstraction
  - `frontend/src/styles.css`: responsive styling

## 4. Demo Flow (4-5 min)
1. Start backend and frontend.
2. Login as `admin` or `super_admin`.
3. Open `Dashboard` and show company-level metrics.
4. Open `Employers` and create/manage employers.
5. Open `Reports` and download Excel/PDF report using date range filters.
6. (Optional super admin flow) Create employer verification steps and employer users.
7. (Optional operations flow) Login as `agent`; mark checks `passed`/`failed` and show candidate status recompute.
8. (Optional self-view) Login as `candidate` and show read-only self-view.

## 5. Technical Decisions (2 min)
- Flask/SQLAlchemy for simple, maintainable API modeling.
- Derived candidate status to prevent inconsistent manual updates.
- PostgreSQL for production-oriented relational persistence.
- Thin frontend; backend owns business rules.

## 6. AI Usage (1 min)
- AI-assisted scaffolding for initial full-stack boilerplate.
- AI-assisted drafting of docs and endpoint skeletons.
- Human validated domain logic, status transitions, and scope boundaries.

## 7. Risks and Next Extensions (1-2 min)
- Risks:
  - No audit trail yet for every status mutation
  - No provider integrations or async queues
  - No audit compliance logging
- Extensions:
  - Add audit log table + immutable event records
  - Add async integrations (queue + webhooks)
  - Add test suite and production DB migration
