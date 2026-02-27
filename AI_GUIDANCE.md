# AI Guidance and Usage Notes

## Purpose
This file captures how AI was used and constrained while building this project.

## AI-Assisted Areas
- Initial project scaffolding (backend/frontend folders, starter files)
- REST endpoint and model boilerplate generation
- Baseline React component and CSS generation
- Documentation drafting (README and walkthrough structure)

## Human-Controlled Decisions
- Scope of MVP and domain entity boundaries
- Candidate/check status transition design
- API payload contracts and validation rules
- Risk assessment and extension roadmap

## Prompting Rules Used
- Keep backend logic authoritative; frontend should remain thin.
- Prefer explicit and readable code over abstraction-heavy patterns.
- Design for interview/demo clarity first, production-hardening second.
- Include extension notes for auth, audit, and async integrations.

## Quality Constraints
- ASCII-only content where possible
- Minimal dependencies
- Deterministic status logic with explicit allowed values
- Clear docs for running and explaining the project

## Known Limitations from AI-Accelerated Build
- Tests are not included in MVP
- No schema migration framework yet
- Security/compliance hardening deferred to next phase
