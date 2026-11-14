# TeamSpend

Multi-tenant expense approval app (Flask + Next.js + PostgreSQL). This is a portfolio project, so code quality, tests, and clear commit history matter as much as features.

**Read `docs/SPEC.md` before starting any task.** It holds the scope, data model, permission matrix, state machine, and API outline. This file holds the working rules.

## Stack

- Backend: Python 3.12, Flask, SQLAlchemy 2.x, Alembic, Pydantic, PyJWT, argon2-cffi, Pytest, ruff
- Frontend: Next.js (App Router), TypeScript, Material UI, TanStack Query, Recharts
- Database: PostgreSQL 16+
- Infra: Docker Compose, GitHub Actions

## Commands

> Provisional. Once the scaffold exists, verify each command works and correct this section.

```bash
docker compose up --build                       # start everything
docker compose exec backend pytest              # backend tests
docker compose exec backend ruff check .        # lint
docker compose exec backend flask db upgrade    # apply migrations
docker compose exec backend flask seed          # load demo data
docker compose exec frontend npm run lint       # frontend lint
```

## Architecture rules (non-negotiable)

1. **Tenant isolation lives in one place.** Tenant-scoped models use `TenantMixin`, and the scoping hook in `backend/app/tenancy/` filters every ORM query by the current `org_id`. Never write per-route `org_id` filters as a substitute.
2. **Unscoped queries** are allowed only inside `auth/` and `tenancy/`, and only through the explicitly named `unscoped()` helper. No raw SQL or `text()` in routes.
3. **Never trust a client-supplied `org_id`.** It comes from the URL plus the membership check.
4. **Cross-tenant access returns `404`**, not `403`, so existence isn't leaked.
5. **RBAC via decorator:** every tenant endpoint uses `@require_permission("...")` backed by the matrix in `rbac/permissions.py`. No inline role checks in route handlers.
6. **Expense status changes go only through `expenses/state_machine.py`.** No route or model sets `status` directly. Illegal transition → `409`, role violation → `403`.
7. **Audit everything that mutates tenant data.** The audit row and the `expense_events` row are written in the same transaction as the change.
8. **Money is integer cents.** No floats anywhere in the money path.
9. **Secrets** come from environment variables. Never commit `.env`. Invite tokens are stored hashed.

## Definition of done for any endpoint

- [ ] RBAC decorator applied
- [ ] Input validated with Pydantic
- [ ] Audit log entry written (if it mutates data)
- [ ] Isolation test added (cross-org access → 404)
- [ ] Permission tests added for the roles that should and shouldn't have access
- [ ] Route coverage meta-test still passes

## Workflow

- **Plan first.** For any non-trivial task, propose a short plan and wait for approval before writing code.
- **Small vertical slices** (e.g. "invites: model, endpoint, tests"), not layers.
- **Tests first** for isolation, RBAC, and the state machine: write the failing tests, then implement.
- **One branch per task**, named `p<phase>/<slug>` (e.g. `p2/tenant-scoping`). Use conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Run the full test suite and linter before saying a task is done, and report the actual results.
- **Do not add dependencies** beyond those listed in the spec without asking.
- **Do not change `docs/SPEC.md`** without asking. If code and spec conflict, flag it and let me decide.
- Keep solutions simple. Prefer fewer, well-tested abstractions over clever ones.

## Code style

- Python: type hints on public functions, small modules, business logic in service functions (not route handlers).
- Frontend: TypeScript strict mode. The UI hides actions a role can't perform, but never relies on that for security.
- Comments explain *why*, not *what*. The tenant-scoping hook, the permission matrix, and the state machine should be especially well documented, since they are the parts I'll be asked about.

## When unsure

Ask. A short question is cheaper than a wrong abstraction.
