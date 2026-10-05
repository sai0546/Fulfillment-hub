# Fulfillment Hub

A small operations app for XYZ's daily order fulfillment workflow. It connects the office order queue to warehouse stock, picking, packing, staging, courier handoff, and exception resolution.

## Start locally

Requirements: Python 3.10+ and Node.js 18+.

### 1. Start the API

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is at `http://localhost:8000`; interactive API docs are at `http://localhost:8000/docs`.

### 2. Start the web app

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (normally `http://localhost:5173`). The frontend calls the FastAPI backend. SQLite data is persisted in the project root as `fulfillment.db` and survives restarts. Delete that file to reset, then restart the API to reseed.

## Demo path

1. Overview shows the deadline queue and blocked work.
2. Inventory → request transfer of 2 keyboards for ORD-2082 → receive it. Main and secondary counts update transactionally and the order becomes pickable.
3. Picking → ORD-2082 → try an incorrect SKU to see verification reject it, then verify the correct SKU/variant/quantity.
4. Complete each pick to pack, assign a staging bay, and confirm courier pickup.
5. Exceptions → assign and resolve issues; Orders → open a record to see its events and current state.

## Project structure

See `ARCHITECTURE.md`, `BUSINESS_RULES.md`, `DATABASE.md`, `API.md`, `TEST_PLAN.md`, and `REQUIREMENTS.md`. The workflow and all records are backed by the API and database; courier labels and tracking are simulated because external accounts are not available.

## Current scope

Single local demo without login or role enforcement. SQLite is the default for a simple local setup; set `DATABASE_URL` to a SQLAlchemy-supported PostgreSQL URL when using a shared database. Add authentication, authorization, migrations, and backups before using this beyond a local demo.
