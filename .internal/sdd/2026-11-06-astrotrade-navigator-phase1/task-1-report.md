# Task 1 report: Postgres service and store skeleton

Status: DONE_WITH_CONCERNS (Postgres-only test not run; Docker was down)

## Built
- docker-compose.yml: `postgres` service (postgres:16-alpine, 127.0.0.1:5433, `${NAV_PG_PASSWORD:?...}`), `nav_pgdata` volume.
- requirements.txt: `psycopg[binary]>=3.2,<4.0`. requirements.lock regenerated with the documented uv command, compiled in place so existing pins held; diff is only psycopg 3.3.8, psycopg-binary 3.3.8 and a typing-extensions annotation.
- .env.example (placeholders only; no .env created).
- sbc/navigator/{__init__.py, store.py, migrations/001_init.sql}. Import makes no connection; errors never include the URL.
- tests/test_navigator_store.py: brief's three tests plus one extra asserting the password is not leaked in StoreUnavailable.

## Tests
- Red first: ImportError (no `store`). Now: 3 passed, 1 skipped (`test_migrate_is_idempotent`, needs `NAV_TEST_DATABASE_URL`).
- NOT verified: idempotent migrate against live Postgres, and compose behaviour (port binding, refusal without NAV_PG_PASSWORD). Docker daemon was down; I did not start it. Controller must run before closing.

## Commit
469fc9d feat(navigator): add Postgres service and store skeleton

## Bead SBC_Tool-cyf
Suggested close reason: "Postgres service, schema, store skeleton, lock updated; close only after live migrate test passes."

## Concerns
- `${NAV_PG_PASSWORD:?}` is evaluated for the whole compose file, so `docker compose up app` also fails without NAV_PG_PASSWORD (as the brief specifies).
- `migrate()` runs each file in one connection context; psycopg commits on clean exit, fine for DDL.

## Fix round 1

1. store.py: connect() now catches psycopg.ProgrammingError ("NAV_DATABASE_URL is invalid") and psycopg.Error ("Postgres is unreachable"), both `from None`. RED: malformed-URL test failed with raw ProgrammingError leaking the URL; unreachable test failed on __cause__ being ConnectionTimeout. GREEN after fix.
2. .dockerignore: added .env, **/.env, .internal.
3. Boot test replaced: psycopg.connect monkeypatched to record calls; create_app() makes zero calls and /healthz is in url_map.
4. docker-compose.yml restored to pre-task content; postgres + nav_pgdata moved unchanged to docker-compose.navigator.yml (`docker compose -f docker-compose.navigator.yml up -d postgres`).
5. .env.example: comments on percent-encoding and host-only 127.0.0.1:5433; placeholders only.

Full suite: 1004 passed, 5 skipped, 1 failed. The failure (tests/test_route_pruning.py::test_every_route_has_a_ui_caller_or_is_listed, routes /api/briefing_summary and /health) is pre-existing: it also fails with this round's changes stashed on 469fc9d.
