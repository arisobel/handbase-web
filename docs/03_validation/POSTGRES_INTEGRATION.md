# PostgreSQL integration testing

> **Status:** Active | **Last updated:** 2026-09-18

## The two suites

| | Fast suite | Integration suite |
|---|---|---|
| Database | in-memory SQLite | real PostgreSQL |
| Schema from | `Base.metadata.create_all` (a fixture) | `alembic upgrade head` |
| Location | `backend/tests/` | `backend/tests/integration/` |
| Marker | — | `@pytest.mark.postgres` |
| Runs by default | yes | no |

**SQLite is a test adapter, never a deployment option** (DEC-009). PostgreSQL is
the only supported application database. The fast suite exists because it needs
no server and finishes in seconds; this suite exists because that is not
evidence about production.

## Running

```bash
# 1. a throwaway server on host port 5433
docker compose -f docker-compose.test.yml up -d

# 2. wait for it to report healthy — the suite probes once and, finding
#    nothing, skips the whole run in a tenth of a second
docker compose -f docker-compose.test.yml ps

# 3. the integration suite
pytest -m postgres

# 4. tear it down (its data lives in tmpfs and is discarded anyway)
docker compose -f docker-compose.test.yml down -v
```

The fast suite stays usable with no PostgreSQL at all:

```bash
pytest          # excludes the postgres marker via addopts in pytest.ini
```

`pytest -m postgres` overrides that exclusion because command-line arguments are
applied after `addopts`.

If no server is reachable the suite **skips** rather than fails, so a developer
without Docker is not blocked — but a skip is not a pass, and CI should treat it
as a missing signal.

The reachability probe runs once per pytest process and its result is memoized,
so an unreachable server costs one 5-second connect timeout for the whole suite,
not one per test. The flip side: starting the container and running pytest in the
same breath skips everything, because the probe ran before the server was ready.

## Configuration

`TEST_DATABASE_URL`, default
`postgresql+psycopg://handbase:handbase@localhost:5433/handbase_test`.

The session fixture runs `DROP SCHEMA public CASCADE` before migrating, and each
test truncates every table. **Never point this at a database you care about.**

Port 5433 keeps it clear of the application stack in `docker-compose.yml`, whose
`db` service publishes nothing to the host.

## What it covers that SQLite cannot

* the Alembic chain applied to a genuinely empty database;
* `id` really being a native `UUID` column and `data` really being `JSONB`;
* `ix_records_table_created` and the `ix_records_data_gin` GIN index existing,
  and `ix_records_table_id` being gone after revision `20260918_02`;
* `ON DELETE CASCADE` from workspace down to records;
* the `uq_membership_workspace_user` constraint rejecting a duplicate;
* Hebrew round-tripping through JSONB (`data ->> 'notes'` read back in SQL);
* `/api/ready` reporting the schema revision it actually finds;
* the full authenticated CRUD cycle, strict validation (DEC-012), role
  enforcement and cross-workspace isolation on the real engine;
* refresh-token rows being written, rotated and revoked.

## Alembic and a caller-supplied URL

`alembic/env.py` only falls back to `DATABASE_URL` when the `Config` it receives
has no `sqlalchemy.url` set. That is what lets the fixtures point a migration
run at the throwaway database without touching the environment.
