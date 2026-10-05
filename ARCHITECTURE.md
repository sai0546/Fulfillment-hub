# Architecture

```text
React + Vite (frontend)
        │ JSON over HTTP
        ▼
FastAPI (backend/app/main.py)
        │ SQLAlchemy transactions
        ▼
SQLite by default (PostgreSQL URL supported)
```

The API owns all workflow decisions. The browser does not mutate business data directly. Mutations run in database transactions and write audit events. The frontend refreshes its API-backed view after each action. `DATABASE_URL` selects the SQLAlchemy database; the default is a local SQLite file.

## Frontend routes / work areas

- Overview: current workload and deadlines.
- Orders: filter/search, create, inspect order and event history.
- Inventory: warehouse balances and transfer requests.
- Picking: prioritized queue and verified pick actions.
- Staging: package location and courier handoff.
- Exceptions: open issue ownership and resolution.

## Backend layout

- `backend/app/main.py`: API, persistence models, seed data, validation, and transactional rules for this compact demo.
- `backend/requirements.txt`: Python dependencies.
- `database/schema.sql`: relational schema reference.
- `database/seed.sql`: human-readable seed reference (runtime seed is in the backend).

## Trust boundaries

All payloads are validated server-side. Status changes occur through workflow endpoints rather than arbitrary status updates. Courier and label values are simulated. The local demo has no authentication; do not expose it publicly as-is.
