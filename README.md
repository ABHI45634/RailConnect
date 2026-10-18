# RailConnect 🚆

RailConnect is a college-project railway booking backend built with **FastAPI**, **Python 3.11+**, **SQLAlchemy 2 async**, **PostgreSQL**, JWT authentication, and Alembic migrations. It supports passenger accounts, train/station search, route and class management, inventory availability, multi-passenger bookings, PNR status, cancellations, a demo payment record, and admin endpoints. There is no frontend; use the auto-generated Swagger UI at `/docs` or call the REST API from curl/Thunder Client.

## Architecture

```text
VS Code / Swagger / curl
          |
          v
    FastAPI Routers ---- JWT + role dependencies
          |
          v
       Services -------- booking / fare / availability / PNR
          |
          v
 SQLAlchemy 2.0 async ORM
          |
          v
 PostgreSQL 16 (constraints + SELECT FOR UPDATE)
```

## ER diagram

```mermaid
erDiagram
    USERS ||--o{ BOOKINGS : creates
    TRAINS ||--o{ ROUTES : contains
    STATIONS ||--o{ ROUTES : serves
    STATIONS ||--o{ TRAINS : source_and_destination
    TRAINS ||--o{ TRAIN_CLASSES : offers
    TRAINS ||--o{ SEAT_AVAILABILITY : inventory
    TRAIN_CLASSES ||--o{ SEAT_AVAILABILITY : inventory_for
    TRAINS ||--o{ BOOKINGS : booked_on
    TRAIN_CLASSES ||--o{ BOOKINGS : booked_in
    BOOKINGS ||--|{ PASSENGERS : contains
    BOOKINGS ||--o{ PAYMENTS : payment
```

## Fastest way to run in VS Code (recommended: Docker)

### Prerequisites

- Install [VS Code](https://code.visualstudio.com/), the Python 3.11+ extension, and [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- Download/extract the project ZIP and open the **`railconnect` folder** in VS Code (`File → Open Folder`).

### Start the API and database

In VS Code Terminal (PowerShell is fine), from the project root:

```powershell
Copy-Item .env.example .env
# Edit .env and set JWT_SECRET to a long random secret for your machine.
docker compose up --build
```

When the containers are healthy, visit:

- Swagger interactive API: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

Stop using `Ctrl+C`, then `docker compose down`. Data remains in the Docker volume. `docker compose down -v` deletes that database volume, so only use it when you explicitly want to reset local data.

## Run locally without Docker

You still need a running PostgreSQL 16 server and a database named `train_management`, owned by user `train` (or edit `DATABASE_URL` in `.env` to match your credentials).

```powershell
# Run at the project root in VS Code terminal
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env: set DATABASE_URL to your local PostgreSQL connection string.
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

If PowerShell blocks virtual-environment activation, use this for the current terminal only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

On Windows, use `py -3.11`; if the launcher is not installed, use `python` after verifying `python --version` reports 3.11 or newer. A ready-to-use VS Code launch profile is available under `.vscode/launch.json`.

## Demo accounts

Seed data is inserted idempotently when the API container starts.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@train.com` | `Admin@123` |
| Passenger | `passenger1@train.com` | `Passenger@123` |
| Passenger | `passenger2@train.com` | `Passenger@123` |

These credentials are for local coursework only. Change them and the JWT secret before any deployment beyond your machine.

## Main API endpoints

All protected endpoints require `Authorization: Bearer <access_token>`.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register` | Public | Register passenger |
| POST | `/auth/login` | Public | Log in and get JWT |
| GET | `/auth/me` | User | Current profile |
| GET | `/stations` | Public | List stations |
| POST/PUT/DELETE | `/stations`, `/stations/{id}` | Admin | Manage stations |
| GET | `/trains` | Public | List trains |
| GET | `/trains/search?source=HYB&destination=VSKP&date=YYYY-MM-DD&class=SL` | Public | Search by route, date and optional class |
| GET | `/trains/{id}` | Public | Train details |
| POST/PUT/DELETE | `/trains`, `/trains/{id}` | Admin | Manage trains |
| POST | `/trains/{id}/classes` | Admin | Add class and inventory |
| POST | `/trains/{id}/routes` | Admin | Add route stop |
| GET | `/trains/{id}/availability?date=YYYY-MM-DD&class=SL` | Public | Check seats |
| POST | `/bookings` | User | Book one or more passengers |
| GET | `/bookings/my` | User | List own bookings |
| GET | `/bookings/{id}` | Owner/Admin | Get booking |
| DELETE | `/bookings/{id}` | Owner/Admin | Cancel booking |
| GET | `/pnr/{pnr}` | Public | PNR status |
| GET | `/admin/bookings` | Admin | List bookings |
| GET | `/admin/users` | Admin | List users |
| GET | `/health` | Public | API + database health |

Open `/docs` to inspect each request schema and try endpoints interactively.

## Try a booking from PowerShell

Login and copy `access_token` from the response:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login -ContentType 'application/json' -Body (@{email='passenger1@train.com'; password='Passenger@123'} | ConvertTo-Json)
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token" }
$date = (Get-Date).ToString('yyyy-MM-dd')
Invoke-RestMethod -Uri "http://localhost:8000/trains/1/availability?date=$date&class=SL"
```

Create a booking (assuming seed train/class IDs are 1; verify via `/trains` and `/trains/1/availability` if the database already contains records):

```powershell
$body = @{
  train_id = 1
  class_id = 1
  journey_date = $date
  passengers = @(@{name='Aarav Sharma'; age=25; gender='M'})
  payment_method = 'UPI'
} | ConvertTo-Json -Depth 5
$booking = Invoke-RestMethod -Method Post -Uri http://localhost:8000/bookings -Headers $headers -ContentType 'application/json' -Body $body
$booking
Invoke-RestMethod -Uri "http://localhost:8000/pnr/$($booking.pnr)"
# Cancel only if you intend to cancel this demo booking:
# Invoke-RestMethod -Method Delete -Uri "http://localhost:8000/bookings/$($booking.booking_id)" -Headers $headers
```

## Concurrency strategy

Booking uses one PostgreSQL transaction. The service first locks the train-class row, so simultaneous first-time inventory initialization for a date is serialized, then locks the dated inventory row with `SELECT ... FOR UPDATE`. Requests for the same inventory record queue while the first transaction finishes. It checks availability and writes inventory, booking, passengers and payment atomically. A rollback undoes every write if any step fails. The available-seat field has a non-negative check constraint and a unique `(train_id, class_id, journey_date)` constraint. If waiting-list mode is disabled, an insufficient-seat request returns HTTP 409; if enabled, seats are confirmed first and remaining passengers wait.

Payments are **simulated demo records**, not real money movement. For a real production service, add a payment provider and idempotent webhooks, reservation expiry, observability, rate limiting, backups, stronger seat allocation, and a full security review.

## Tests

Tests use `pytest` and `httpx.AsyncClient`. Set `TEST_DATABASE_URL` to a **disposable test database** first; the fixtures recreate tables, so never point this variable at valuable data. With Docker DB running, create a test DB as needed and set the environment variable before running:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://train:train@localhost:5432/train_management_test'
pytest -q
```

## Five viva talking points

1. **Concurrency:** `SELECT FOR UPDATE`, atomic transactions, and the last-seat race test.
2. **Async:** FastAPI and SQLAlchemy async sessions with `asyncpg` avoid blocking the event loop on database I/O.
3. **Service layer:** Routers handle HTTP validation/dependencies; services own fare, inventory, booking, cancellation and PNR logic.
4. **JWT:** Passwords are bcrypt-hashed; HS256 access tokens expire after 30 minutes and role dependencies restrict admin routes.
5. **Relational schema:** Foreign keys, uniqueness, and separate route, class, inventory, booking, passenger and payment tables preserve data integrity.
