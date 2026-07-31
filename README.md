# Tax Obligation Monitor

A multi-tenant web application for tracking tax filing deadlines, nexus exposure, payment obligations, and compliance risk across jurisdictions. Features AI-powered compliance analysis via Kindo agent integration.

## Features

- **Filing Deadlines** — Track tax filing due dates, extensions, and statuses across jurisdictions
- **Nexus Exposure** — Monitor physical, economic, and affiliate nexus triggers per jurisdiction
- **Payment Obligations** — Manage tax payment schedules, amounts, and confirmation tracking
- **Jurisdiction Management** — Configure jurisdictions with types, codes, and applicable tax types
- **AI Analysis** — Kindo agent integration for compliance risk scoring and recommendations
- **Multi-Tenancy** — Data isolation per organization with tenant-based access
- **RBAC** — Admin, Manager, Analyst, and Viewer roles with appropriate permissions
- **Light/Dark Theme** — User-configurable theme with session persistence

## Quick Start

1. Copy `.env.example` to `.env` and set your `SECRET_KEY`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python wsgi.py`
4. Log in with `admin` / `admin`
5. Start by adding Jurisdictions, then create Deadlines, Nexus records, and Payments

## Docker

```bash
docker build -t tax-obligation-monitor .
docker run -p 5000:5000 -e SECRET_KEY=your-secret-key tax-obligation-monitor
```

## AI Analysis Setup

Set these environment variables to enable Kindo agent analysis:
- `KINDO_API_TOKEN` — Your Kindo API token
- `KINDO_AGENT_ID` — The agent ID for the Tax Obligation Monitor enrichment agent

## Roles

| Role | Permissions |
|------|------------|
| Admin | Full access + user/tenant management |
| Manager | Create, edit, delete all records |
| Analyst | Create and edit records, run analyses |
| Viewer | Read-only access |

## Tech Stack

- **Backend:** Python / Flask / SQLAlchemy
- **Database:** SQLite (configurable via DATABASE_URL)
- **Auth:** Flask-Login with password hashing
- **AI:** Kindo agent API integration
- **Server:** Gunicorn with ProxyFix
