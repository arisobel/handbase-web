# Validation

> **Status:** Active | **Last updated:** 2026-09-18

Release checks:
- `pytest` passes (fast SQLite suite);
- `pytest -m postgres` passes — a skip is a missing signal, not a pass
  (see `POSTGRES_INTEGRATION.md`);
- `npm run build` passes;
- migrations apply to an empty PostgreSQL database;
- `docker compose up` reaches a healthy stack;
- `/api/health` returns 200 and `/api/ready` reports `ready`;
- login, refresh and logout work against the built image;
- an unauthenticated request is rejected and a non-member cannot reach another
  workspace's records by id;
- English LTR and Hebrew RTL render correctly, including emails and UUIDs
  inside Hebrew text;
- mixed Hebrew/Latin/numeric input round-trips through JSONB.
