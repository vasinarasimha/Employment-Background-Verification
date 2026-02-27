# AGENTS.md

## Coding Standards
- Keep backend business logic in Flask routes/services.
- Use explicit status enums as string sets.
- Validate request payloads on every mutating endpoint.
- Favor readable code over deep abstraction in MVP stage.

## Architecture Constraints
- Frontend is a consumer only; it must not derive authoritative risk logic.
- Candidate status is recalculated from check statuses after every check update.
- Relational schema must preserve candidate -> checks one-to-many mapping.

## AI Collaboration Rules
- AI may scaffold and refactor, but human must verify domain rules.
- AI changes should preserve endpoint contract stability.
- Every non-trivial AI change requires doc update in README/WALKTHROUGH if behavior changes.

## Security and Privacy Guardrails
- Avoid storing sensitive government identifiers in MVP.
- Do not log PII-heavy payloads in production mode.
- Add auth and audit trail before production deployment.
