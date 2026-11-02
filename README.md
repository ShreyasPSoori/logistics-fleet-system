# Enterprise Logistics and Fleet Operations Management System

A course-project prototype for coordinating shipments and fleet operations. The repository contains a React/Vite frontend, FastAPI REST API, PostgreSQL database, and Docker Compose setup. SQLite is supported for quick local development when `DATABASE_URL` is not set.

## Implemented scope

- Dashboard counts for shipments, in-transit deliveries, available vehicles, drivers, maintenance, and expenses.
- Create and list shipments, vehicles, drivers, trips, maintenance records, and expenses.
- Assign an available vehicle and driver to a trip; assignments update availability.
- Track shipment and trip statuses, with delivered or cancelled trips releasing assigned resources.
- Record maintenance and expenses; completed maintenance returns a vehicle to available.
- API validation, bearer-token authentication, password hashing, role-based permissions for administrator, logistics-manager, and fleet-manager accounts, and a seeded demo administrator.
- PostgreSQL schema created on startup for the prototype.

GPS tracking, route optimization, payment processing, predictive maintenance, and external integrations are outside this prototype's scope.

## Run with Docker Compose

Prerequisites: Docker Desktop with Compose enabled.

```powershell
docker compose up --build
```

Open <http://localhost:5173>. API documentation is at <http://localhost:8000/docs>. Demo login: `admin@bea.local` / `Admin123!`.

## Run locally

Prerequisites: Python 3.11+, Node.js 22.12+, and PostgreSQL 15+ (or use SQLite).

Backend, from `backend/`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend, from `frontend/` in another terminal:

```powershell
npm install
npm run dev
```

By default the API uses `sqlite:///./bea.db`. For PostgreSQL set `DATABASE_URL`, for example:
`postgresql+psycopg://bea:bea_dev_password@localhost:5432/bea_logistics`.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | SQLite file | SQLAlchemy connection string |
| `JWT_SECRET` | local development key | Token signing key; replace outside local development |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated frontend origins |
| `VITE_API_URL` | `http://localhost:8000` | API base URL used by Vite |

## Repository layout

```text
backend/app/main.py       FastAPI routes, ORM models, auth and seed data
frontend/src/             React dashboard and API client
docker-compose.yml        Local multi-container environment
```

## Demo workflow

1. Sign in with the demo administrator account.
2. Add a vehicle and a driver if you want additional resources.
3. Create a shipment, then create a trip linked to that shipment.
4. Assign an available vehicle and driver to the trip.
5. Update trip progress to `in_transit`, then `delivered` to complete the shipment and release resources.
6. Record maintenance or operating expenses and review the dashboard counts.

To add a repeatable demonstration dataset to the local SQLite database, start in `backend/` after installing dependencies and run:

```powershell
.\.venv\Scripts\python.exe ..\scripts\seed_demo.py
```

The seed adds three `DEMO-` vehicles, three `DEMO-` drivers, and four shipments/trips spanning scheduled, assigned, in-transit, and delivered states. Existing records are retained and the seed can be rerun without duplicating its demo records. Run it from `backend/` so it targets the same `bea.db` used by the local API.

## Phase 2 notes

This implementation is a functional educational prototype, not a production deployment. Change the development secrets, configure a production database and TLS, add frontend UI tests, migrations, and conduct a security review before any real deployment. The backend has eight passing API integration tests and Ruff checks; see `backend/requirements-dev.txt`. Repository hosting and branch history must describe the team's actual repository.

Driver and customer-facing account workflows are not implemented in this prototype. The administrator account endpoint currently provisions administrator and manager roles only.

