# Disc Golf Tracker

A disc golf companion app: course discovery and maps, solo and group round scoring,
per-hole and per-layout statistics, friends and activity feed, and gamification
(achievements, XP, streaks). Offline-first on mobile.

This is a monorepo with two applications:

- **`backend/`** — FastAPI + PostgreSQL/PostGIS API server. See `backend/README.md`
  (added in Phase 1) for setup, migrations, and running tests.
- **`mobile/`** — Flutter client with an offline-first local database (Drift) that
  syncs with the backend. See `mobile/README.md` (added in Phase 9) for setup and
  running the app.
- **`docs/`** — Architecture decisions and other project documentation.

See `docs/architecture.md` for the stack and data model rationale, and `BACKLOG.md`
for features explicitly deferred past v1.

## Running the backend

```
cd backend
uv sync
docker compose up -d
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Running the mobile app

```
cd mobile
flutter pub get
flutter run
```
