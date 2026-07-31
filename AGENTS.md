# AGENTS.md — Tax Obligation Monitor

This repository is managed by the KinHelm Studio agent.

## Application Overview

**Tax Obligation Monitor** is a multi-tenant web application for tracking tax filing deadlines, nexus exposure, payment obligations, and compliance risk across jurisdictions. It features AI-powered compliance analysis via Kindo agent integration.

## Architecture

- **Backend:** Python 3.11 / Flask 3.1 / SQLAlchemy 2.0 / Flask-Login
- **Database:** SQLite (configurable via `DATABASE_URL`)
- **Server:** Gunicorn with ProxyFix
- **AI Integration:** Kindo agent API (`POST https://api.kindo.ai/v1/agents/runs`)
- **Containerization:** Docker with health checks

## Key Modules

| Module | Purpose |
|---|---|
| `app/__init__.py` | Flask app factory, blueprint registration, DB seed |
| `app/models.py` | All SQLAlchemy models: Tenant, User, Role, Jurisdiction, Deadline, NexusExposure, PaymentObligation, AnalysisResult |
| `app/services/kindo_agent.py` | Kindo AI agent integration: submit, poll, parse |
| `app/routes/auth.py` | Login, register, logout, role_required decorator |
| `app/routes/main.py` | Dashboard, settings, landing page |
| `app/routes/deadlines.py` | Filing deadline CRUD |
| `app/routes/nexus.py` | Nexus exposure CRUD |
| `app/routes/payments.py` | Payment obligation CRUD |
| `app/routes/jurisdictions.py` | Jurisdiction CRUD |
| `app/routes/api.py` | JSON API: /api/analyze, /api/analysis-history, /api/dashboard-stats |
| `app/routes/admin.py` | User role management, tenant creation |
| `app/routes/getting_started.py` | Getting Started guide page |

## Multi-Tenancy

Data isolation is enforced via `tenant_id` columns on all data models. Every query filters by `current_user.tenant_id`. Users belong to exactly one tenant.

## RBAC Roles

| Role | Create/Edit | Delete | Admin | AI Analysis |
|---|---|---|---|---|
| Admin | ✓ | ✓ | ✓ | ✓ |
| Manager | ✓ | ✓ | ✗ | ✓ |
| Analyst | ✓ | ✗ | ✗ | ✓ |
| Viewer | ✗ | ✗ | ✗ | ✓ |

## Blueprint Registration

| Blueprint | Prefix | File |
|---|---|---|
| `auth_bp` | *(none)* | `app/routes/auth.py` |
| `main_bp` | *(none)* | `app/routes/main.py` |
| `deadlines_bp` | *(none)* | `app/routes/deadlines.py` |
| `nexus_bp` | *(none)* | `app/routes/nexus.py` |
| `payments_bp` | *(none)* | `app/routes/payments.py` |
| `jurisdictions_bp` | *(none)* | `app/routes/jurisdictions.py` |
| `api_bp` | `/api` | `app/routes/api.py` |
| `admin_bp` | `/admin` | `app/routes/admin.py` |
| `gs_bp` | *(none)* | `app/routes/getting_started.py` |

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret |
| `DATABASE_URL` | No | Database connection (default: SQLite) |
| `KINDO_API_TOKEN` | For AI | Kindo API bearer token |
| `KINDO_AGENT_ID` | For AI | Kindo agent identifier |
| `PORT` | No | HTTP port (default: 5000) |
| `SESSION_COOKIE_PATH` | No | Cookie path (default: /) |
| `SESSION_COOKIE_SECURE` | No | HTTPS-only cookies (default: false) |
| `APP_GUNICORN_TIMEOUT` | No | Gunicorn worker timeout (default: 120) |
| `APP_AGENT_POLL_TIMEOUT_SEC` | No | Agent poll timeout (default: 120) |

## Security Invariants

| # | Invariant |
|---|---|
| 1 | `SESSION_COOKIE_NAME = "tax_obligation_monitor_session"` |
| 2 | `SESSION_COOKIE_PATH` from env var with `/` default |
| 3 | `SESSION_COOKIE_SECURE` from env var |
| 4 | `SESSION_COOKIE_SAMESITE = "Lax"` |
| 5 | `SECRET_KEY` from env var (no hardcoded value) |
| 6 | `ProxyFix` present in wsgi_app chain |
| 7 | All data queries filtered by `tenant_id` |
| 8 | All service calls in routes wrapped in try/except |
| 9 | CSRF protection enabled via Flask-WTF |

## UX Features

- Light/dark theme toggle with session persistence
- Getting Started page at `/getting-started` with numbered step cards
- Per-page context help panels (slide-out drawer via ? button)
- Responsive sidebar navigation with mobile support
- Risk visualization with color-coded badges and bar charts
- AI analysis modal with findings and recommendations display
