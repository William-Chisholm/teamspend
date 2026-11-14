# TeamSpend: Project Spec

Status: draft v1. This is the source of truth for scope and design. If code and spec disagree, flag it and update the spec in the same commit.

## 1. Overview

TeamSpend is a multi-tenant expense approval app. Users can belong to multiple organizations, with a separate role in each. Members submit expenses, approvers approve or reject them, and admins mark them reimbursed. Every meaningful action is recorded in an audit log.

**Portfolio goals** (what a reviewer should notice):

1. Tenant isolation enforced in one place and proven by tests.
2. RBAC driven by a permission matrix, not scattered `if` checks.
3. An explicit, tested approval state machine.
4. An audit trail with before/after values.
5. One-command local setup, CI, a live demo with seeded data, and a README with architecture and tradeoffs.

## 2. Stack and repo layout

| Layer | Choice |
|---|---|
| Backend | Python 3.12, Flask, SQLAlchemy 2.x, Alembic (Flask-Migrate) |
| Database | PostgreSQL 16+ |
| Validation | Pydantic |
| Auth | PyJWT, argon2-cffi |
| Backend tests | Pytest |
| Frontend | Next.js (App Router), TypeScript, Material UI |
| Charts / data fetching | Recharts, TanStack Query |
| Tooling | Docker Compose, GitHub Actions, ruff |

Dependencies above are pre-approved. Anything else needs explicit sign-off.

```
teamspend/
  CLAUDE.md
  README.md
  docker-compose.yml
  docs/SPEC.md
  backend/
    app/
      __init__.py          # create_app()
      config.py
      extensions.py
      models/              # SQLAlchemy models + TenantMixin
      auth/                # register, login, refresh, token utils
      tenancy/             # org context, scoping hooks, unscoped() helper
      rbac/                # permissions.py (matrix), decorators.py
      expenses/            # routes, service, state_machine.py
      audit/               # audit writer
      storage/             # storage interface + local implementation
    migrations/
    tests/
      unit/
      integration/
      isolation/
    pyproject.toml
  frontend/
```

## 3. Roles and permissions

Roles are **per membership**: being `admin` in Org A grants nothing in Org B.

| Capability | owner | admin | approver | member |
|---|:-:|:-:|:-:|:-:|
| Delete org / transfer ownership | ✅ | | | |
| Manage members and roles | ✅ | ✅ (not owners) | | |
| Create and revoke invites | ✅ | ✅ | | |
| Manage categories | ✅ | ✅ | | |
| Create, edit, delete own **draft** expenses | ✅ | ✅ | ✅ | ✅ |
| Submit / withdraw own expenses | ✅ | ✅ | ✅ | ✅ |
| View own expenses | ✅ | ✅ | ✅ | ✅ |
| View all org expenses | ✅ | ✅ | ✅ | |
| Approve / reject others' expenses | ✅ | ✅ | ✅ | |
| Approve / reject **own** expenses | ❌ | ❌ | ❌ | ❌ |
| Mark approved expenses reimbursed | ✅ | ✅ | | |
| View audit log | ✅ | ✅ | | |
| View org-wide dashboard | ✅ | ✅ | ✅ | |
| View personal dashboard | ✅ | ✅ | ✅ | ✅ |

Implementation: `rbac/permissions.py` maps each permission string (e.g. `expense.approve`) to the set of roles that hold it. Routes declare the permission they need via `@require_permission("expense.approve")`. Ownership rules (e.g. "not your own expense") are enforced in the service layer and tested.

## 4. Data model (PostgreSQL)

Primary keys are UUIDs. Timestamps are `TIMESTAMPTZ`. Money is integer cents.

```
users(id, email UNIQUE, password_hash, name, created_at)
organizations(id, name, slug UNIQUE, created_at)
memberships(id, user_id, org_id, role, created_at, UNIQUE(user_id, org_id))
invites(id, org_id, email, role, token_hash, expires_at, accepted_at, created_by, created_at)
categories(id, org_id, name, UNIQUE(org_id, name))
expenses(id, org_id, submitted_by, category_id, amount_cents CHECK > 0, currency DEFAULT 'USD',
         description, expense_date, status, receipt_key, created_at, updated_at)
expense_events(id, org_id, expense_id, actor_id, from_status, to_status, comment, created_at)
audit_log(id, org_id, actor_id, action, entity_type, entity_id, diff_json JSONB, created_at)
```

Indexes: `(org_id, status, created_at)` on `expenses`, `(org_id, created_at)` on `audit_log`, `(org_id, expense_id)` on `expense_events`.

**Global tables** (not tenant-scoped): `users`, `organizations`. `memberships` is queried by `user_id` during login and org listing, which is only allowed through the explicit `unscoped()` helper inside `auth/` and `tenancy/`.

**Tenant-scoped tables** (automatically filtered by `org_id`): `categories`, `expenses`, `expense_events`, `audit_log`, `invites`.

## 5. Expense state machine

```
draft ──submit──▶ submitted ──approve──▶ approved ──reimburse──▶ reimbursed
  ▲                  │  │
  │                  │  └──reject (comment required)──▶ rejected
  └────withdraw──────┘                                      │
  ▲                                                         │
  └─────────────────────edit/reopen─────────────────────────┘
```

| From | To | Who | Rules |
|---|---|---|---|
| draft | submitted | submitter | Requires amount, category, date |
| submitted | draft | submitter | Withdraw |
| submitted | approved | approver+ | Not the submitter |
| submitted | rejected | approver+ | Not the submitter; comment required |
| rejected | draft | submitter | Reopen to edit and resubmit |
| approved | reimbursed | admin+ | Terminal state |

- Expenses are editable and deletable **only in `draft`**.
- Role violation → `403`. Illegal transition or edit in the wrong state → `409`.
- Every transition writes an `expense_events` row and an `audit_log` row in the **same DB transaction** as the status change.
- All transitions go through `expenses/state_machine.py`. No route sets `status` directly.

## 6. Tenant isolation design

1. **Routing:** tenant endpoints live under `/api/orgs/<org_id>/...`. Middleware verifies the caller has a membership in that org, then stores `org_id` and the role on the request context.
2. **Automatic scoping:** a SQLAlchemy `do_orm_execute` hook applies `with_loader_criteria` for every model using `TenantMixin`, so all ORM reads are filtered by the current `org_id`. A `before_flush` hook rejects any insert or update whose `org_id` doesn't match the context.
3. **Never trust the client:** `org_id` in request bodies is ignored or rejected. It always comes from the URL plus the membership check.
4. **No existence leaks:** cross-tenant resource IDs return `404`, and so does an org the caller isn't a member of.
5. **No raw SQL in routes.** `text()` and raw queries are allowed only in migrations and `tenancy/`.
6. **Stretch, defense in depth:** PostgreSQL Row-Level Security with `SET LOCAL app.current_org` per request and policies on tenant tables. Note that RLS is bypassed by superusers and table owners unless `FORCE ROW LEVEL SECURITY` is set, so the app must connect as a non-owner role.

## 7. Authentication

- Register and login with email and password (argon2 hashing).
- Short-lived access token (about 15 min) and refresh token (about 7 days) in `httpOnly`, `Secure`, `SameSite=Lax` cookies. Refresh tokens rotate on use.
- CSRF protection for state-changing requests (double-submit token or custom header check).
- Invites: random token, **only the hash is stored**, expires in 7 days, single-use. No email in MVP: the admin copies the invite link from the UI.

## 8. API outline

```
POST   /api/auth/register | /login | /refresh | /logout
GET    /api/me                                   # user + memberships

POST   /api/orgs
GET    /api/orgs/{org_id}
GET    /api/orgs/{org_id}/members
PATCH  /api/orgs/{org_id}/members/{user_id}      # change role
DELETE /api/orgs/{org_id}/members/{user_id}
POST   /api/orgs/{org_id}/invites
GET    /api/orgs/{org_id}/invites
DELETE /api/orgs/{org_id}/invites/{invite_id}
POST   /api/invites/accept                       # token in body

GET|POST          /api/orgs/{org_id}/categories
PATCH|DELETE      /api/orgs/{org_id}/categories/{id}

GET|POST          /api/orgs/{org_id}/expenses    # filters: status, mine, category, from, to, page
GET|PATCH|DELETE  /api/orgs/{org_id}/expenses/{id}
POST   /api/orgs/{org_id}/expenses/{id}/submit | withdraw | approve | reject | reimburse | reopen
POST   /api/orgs/{org_id}/expenses/{id}/receipt
GET    /api/orgs/{org_id}/expenses/{id}/receipt

GET    /api/orgs/{org_id}/audit-log
GET    /api/orgs/{org_id}/dashboard              # spend by category/month, pending approvals
```

## 9. Frontend pages

`/login`, `/register`, `/accept-invite`, `/orgs` (picker and create), then under `/o/[orgId]/`: `dashboard`, `expenses`, `expenses/new`, `expenses/[id]`, `approvals`, `members`, `audit-log`, `settings` (categories). The UI hides what a role can't do, but the **server is always the enforcement point**.

## 10. Testing strategy

- **Unit:** state machine transitions and the permission matrix, with a parametrized test per matrix cell.
- **Integration:** API tests against a real Postgres test database.
- **Isolation suite** (the headline feature). With two orgs seeded, assert that for every tenant endpoint:
  - a user in Org A requesting an Org B resource ID gets `404`
  - a user who isn't a member of Org B calling `/orgs/B/...` gets `404`
  - list endpoints, the dashboard, and the audit log never include Org B rows
  - a body-supplied `org_id` is ignored or rejected
  - a role held in Org A grants nothing in Org B
- **Route coverage meta-test:** enumerate the Flask URL map and fail if any `/api/orgs/<org_id>/...` route lacks an RBAC decorator or an isolation test. New endpoints can't ship unprotected.
- **CI:** GitHub Actions runs lint and the full test suite on every PR.

## 11. Non-goals (MVP)

Multi-currency, OCR, outbound email, billing, SSO, mobile app, real-time updates.

## 12. Delivery phases

Mirrors the GitHub Project roadmap (Nov 16 to Nov 29, 2026).

- **P1 Foundation:** Compose scaffold, models and migrations, auth, orgs and invites.
- **P2 Security:** RBAC, tenant scoping, isolation tests, expense CRUD.
- **P3 Workflow:** state machine, audit log, receipt upload.
- **P4 UI:** auth and layout, expense list and form, approval queue, dashboard.
- **P5 Ship:** seed data and demo logins, CI, deploy, README.

**Seed data:** two orgs (so isolation is demonstrable) with one user per role, a few categories, and expenses in every status. Demo logins are listed in the README.

## 13. Open decisions

| Decision | Default | Revisit if |
|---|---|---|
| Cookies across domains | Next.js rewrites proxy `/api/*` to the backend, so everything is same-origin | Hosting prevents proxying |
| Receipt storage | Local disk behind a storage interface | You want S3-compatible (MinIO in Compose) |
| Postgres RLS | Stretch goal, after P3 | Time is tight, so cut it |
| TypeScript vs JavaScript | TypeScript | You prefer JS for speed |
| Demo hosting | Vercel (frontend), a free-tier container host plus hosted Postgres (backend) | Free tiers don't fit |
