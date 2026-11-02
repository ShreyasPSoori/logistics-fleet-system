# Enterprise Logistics and Fleet Operations Management System
## Phase 2 Implementation Report

**Course:** Building Enterprise Applications (BCS703B)  
**Department:** Information Science and Engineering  
**Academic year:** 2026â€“2027  
**Team:** Shreyas P Soori (1BY23IS206), Srikanth Joshi (1BY23IS217), Suhas B P (1BY23IS220), Theju N T (1BY23IS236)  
**Guide:** Prof. Rachana CV, Assistant Professor, Department of ISE

## Abstract

The Enterprise Logistics and Fleet Operations Management System is a web prototype for coordinating shipment records and fleet operations in one place. It provides authenticated access, role-aware API permissions, operational dashboards, shipment registration, vehicle and driver directories, trip scheduling and assignment, delivery status changes, maintenance records, and expense tracking. The React interface communicates with a FastAPI REST API, which stores relational data through SQLAlchemy in PostgreSQL. SQLite is available for local development. Docker Compose starts the frontend, backend, and database together.

The current implementation demonstrates core workflows and validation for a course project. It does not provide GPS tracking, route optimization, payment processing, predictive maintenance, or external logistics integrations. The 30% reduction in manual reconciliation stated as a project target has not been measured; it remains an evaluation goal.

## Repository and setup

The implementation is in the local workspace `E:\BEA`. No Git repository, branch history, or remote URL was configured when this report was prepared; the team should add the actual URL and branch names after creating or connecting its shared repository.

### Technology stack

- React 19 and Vite 8 web client
- FastAPI REST API with Pydantic validation
- SQLAlchemy ORM and PostgreSQL 16 in Docker Compose
- SQLite fallback for local development
- Bearer-token authentication, Argon2 password hashing, and role-based API permissions

### Project structure

```text
E:\BEA\
â”œâ”€â”€ backend\
â”‚   â”œâ”€â”€ app\main.py       API routes, models, auth, and startup seed
â”‚   â”œâ”€â”€ requirements.txt  Python dependencies
â”‚   â””â”€â”€ Dockerfile
â”œâ”€â”€ frontend\
â”‚   â”œâ”€â”€ src\App.jsx       Dashboard, workflow screens, and forms
â”‚   â”œâ”€â”€ src\api.js        Authenticated API client
â”‚   â”œâ”€â”€ src\styles.css   Responsive interface styles
â”‚   â”œâ”€â”€ package.json
â”‚   â””â”€â”€ Dockerfile
â”œâ”€â”€ scripts\seed_demo.py  Idempotent local demonstration data loader
â”œâ”€â”€ docker-compose.yml
â”œâ”€â”€ .gitignore
â””â”€â”€ README.md
```

The backend test suite is in `backend/tests/test_api.py`; pinned test and lint tools are listed in `backend/requirements-dev.txt`.

### Run with Docker Compose

Install Docker Desktop with Compose, open a terminal in the project root, then run:

```powershell
docker compose up --build
```

Open `http://localhost:5173`. The interactive API documentation is at `http://localhost:8000/docs`. Demo login: `admin@bea.local` / `Admin123!`.

The local SQLite database can be populated with clearly labeled demonstration vehicles, drivers, shipments, and trips by running `..\scripts\seed_demo.py` from `backend/` with its virtual environment's Python interpreter. The seed is idempotent and retains the team's existing records.

### Run locally

Use Python 3.11+, Node.js 22.12+, and PostgreSQL 15+ (or keep the default SQLite database). In one terminal:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

For a local PostgreSQL connection, set `DATABASE_URL` before starting the backend, for example:
`postgresql+psycopg://bea:bea_dev_password@localhost:5432/bea_logistics`.

## Core implementation

### User interface and presentation

The React client provides a sign-in screen, operations overview, recent shipment table, fleet availability summary, shipment register, trip schedule, vehicle register, driver directory, maintenance register, and expense register. Forms create the core records. The trip screen allows a dispatcher to choose an available vehicle and driver, start a trip, and mark a delivery complete. Search filters the visible register. The layout adapts to smaller screens.

**Application screenshots:** eight screenshots supplied by the project team are embedded in Appendix A of the completed DOCX report. They document the dashboard, shipments, trips, fleet, drivers, maintenance, and expenses. The first dashboard capture predates demo-data seeding; later captures show the populated demo records.

### Business logic and processing

The API validates required fields and positive capacities or costs. It assigns tracking numbers, prevents scheduling a second active trip for the same shipment, rejects unavailable vehicles or drivers, reserves both resources when a trip is assigned, and releases them when a trip is delivered or cancelled. A trip cannot enter transit or delivery without an assignment. Maintenance changes an available vehicle to maintenance status; completing a service record returns it to available. Role checks restrict account creation, shipment creation, fleet changes, trip scheduling and assignment, maintenance, expenses, and trip status updates.

The current account API supports administrator, logistics manager, and fleet manager roles. An administrator can create those accounts through `POST /users`; the current UI exposes only the seeded demo administrator and does not yet provide an account-management screen. Driver and customer-facing account workflows, including driver-to-profile linking, remain future work.

### Persistence and integration

SQLAlchemy models define users, shipments, vehicles, drivers, trips, maintenance records, and expenses. PostgreSQL is the Docker Compose database. For local development, the API defaults to a SQLite file named `bea.db`. Tables are created at API startup. No external logistics, mapping, GPS, or payment API is connected.

## Static analysis and test execution

Backend API tests use pytest 9.2.0, FastAPI TestClient, and a temporary SQLite database. The suite does not modify the local demonstration database. All eight API integration tests passed on Nov. 2, 2026. Python syntax compilation also passed for the backend and test files.

### Static analysis and build checks

Ruff 0.17.3 was run with `ruff check app tests` from `backend/`. The final run passed with no remaining Ruff findings after import, formatting, UTC-style, and test-fixture issues were corrected. Ruff was scoped to Python; frontend ESLint and dependency security scans were not run. Ruff does not establish that the application has zero bugs or vulnerabilities.

The frontend production build passed with Vite 8.3.5 using `npm run build`. Vite emitted two `MODULE_LEVEL_DIRECTIVE` warnings from `lucide-react` package files concerning the upstream `use client` directive. Pytest reported three deprecation warnings: use of Starlette TestClient with `httpx` and FastAPI's legacy startup event registration. These warnings did not fail the tests or build and should be reviewed before future framework upgrades.

### Test cases and results

API integration test results:

| ID | Scenario | Expected behavior | Result |
|---|---|---|---|
| TC-01 | Login with the seeded demo credentials | A bearer token and administrator role are returned | Pass |
| TC-02 | Create a shipment with all required fields | A record with a unique tracking number and pending status is stored | Pass |
| TC-03 | Submit a vehicle with zero or negative capacity | Request validation rejects the record | Pass |
| TC-04 | Create a trip for an unknown shipment | API returns not found and stores no trip | Pass |
| TC-05 | Assign an unavailable vehicle or driver | API rejects assignment; first assignment remains intact | Pass |
| TC-06 | Complete an assigned trip | Shipment is delivered and assigned vehicle/driver become available | Pass |
| TC-07 | Mark maintenance complete | Record becomes completed and vehicle becomes available | Pass |
| TC-08 | Call a restricted endpoint with an insufficient role | API returns forbidden | Pass |

**Execution summary:** 8 passed, 0 failed. Three deprecation warnings were emitted by dependencies or the current startup-event implementation. The frontend was production-built but does not yet have a dedicated automated UI test suite. Rerun with `\.venv\Scripts\python.exe -m pytest -q` and `\.venv\Scripts\ruff.exe check app tests` from `backend/`, and `npm.cmd run build` from `frontend/`. Captured commands and results are in `reports/evidence/test-and-analysis-results.txt`.

## Limitations and next steps

The prototype has a seeded demo account and development secrets. Change the secrets before use beyond local demonstration. The database is initialized with `create_all`; schema migrations, frontend UI tests, deployment hardening, user-management screens, driver-to-profile linking, and a formal security review remain follow-up work. Add the team's Git remote and branch information and measure the reconciliation-effort target before final submission.

## References

[1] Meta Platforms, â€œQuick Start,â€ *React Documentation*. [Online]. Available: https://react.dev/learn. [Accessed: Nov. 2, 2026].

[2] FastAPI, â€œLearn,â€ *FastAPI Documentation*. [Online]. Available: https://fastapi.tiangolo.com/learn/. [Accessed: Nov. 2, 2026].

[3] SQLAlchemy, â€œSQLAlchemy 2.1 Documentation.â€ [Online]. Available: https://docs.sqlalchemy.org/en/21/. [Accessed: Nov. 2, 2026].

[4] PostgreSQL Global Development Group, â€œPostgreSQL 16 Documentation.â€ [Online]. Available: https://www.postgresql.org/docs/16/. [Accessed: Nov. 2, 2026].

[5] Docker, â€œDocker Compose.â€ [Online]. Available: https://docs.docker.com/compose/. [Accessed: Nov. 2, 2026].

[6] Vite, â€œGetting Started.â€ [Online]. Available: https://vite.dev/guide/. [Accessed: Nov. 2, 2026].


