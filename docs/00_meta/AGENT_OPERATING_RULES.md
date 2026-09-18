# Agent Operating Rules

> **Status:** Active | **Last updated:** 2026-09-18

## Before changing code

1. Read `docs/README.md`.
2. Read current progress, decisions and backlog.
3. Distinguish implemented state from target direction.
4. Do not silently replace architectural decisions.
5. Preserve Hebrew/RTL support in every UI change.
6. Preserve PostgreSQL unless a new decision supersedes it.

## After changing code

1. Run the narrowest relevant tests/build.
2. Update `07_progress.md`.
3. Add a decision only when an actual decision was made.
4. Update backlog when scope changes.
5. Never present a planned feature as implemented.

## UI rule

Prefer logical CSS properties such as `margin-inline-start`, `padding-inline-end`,
`inset-inline-start` and `text-align: start`.
