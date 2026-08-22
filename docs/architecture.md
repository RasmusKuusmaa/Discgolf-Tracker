# Architecture decisions

These decisions are load-bearing. Do not deviate from them without writing an
ADR explaining why.

## Backend

- Python 3.12, FastAPI, Pydantic v2
- PostgreSQL 16 + **PostGIS** for spatial queries ("courses near me", hole
  distances)
- SQLAlchemy 2.0 async + Alembic migrations
- `uv` for dependency management
- JWT access token (15 min) + rotating refresh token (30 days), Argon2 password
  hashing
- pytest + httpx `AsyncClient` + a dedicated test database
- Docker Compose for local dev

## Mobile

- Flutter (stable), Dart 3
- Riverpod (code-gen) for state, `go_router` for navigation
- **Drift** (SQLite) as the local source of truth — the app reads from the
  local database, never directly from the network
- `dio` for HTTP, `freezed` + `json_serializable` for models
- `flutter_map` (OpenStreetMap / MapLibre tiles) — no Google Maps API key,
  offline tile caching possible
- `geolocator` for GPS, `flutter_secure_storage` for tokens

## Cross-cutting

### Client-generated IDs

All IDs are UUIDv7, generated client-side. This is what makes offline creation
work without an ID reconciliation step: a round or course created while offline
already has its final ID, so nothing needs to be rewritten once it syncs.

### Soft deletes and timestamps

Every syncable row has `created_at`, `updated_at`, and `deleted_at` (soft
delete). Nothing is ever hard-deleted from a syncable table; it is marked
deleted and filtered out of reads.

### Sync strategy

Sync is **delta pull + push queue**, last-write-wins per entity by
`updated_at`. The client drains its local mutation queue on reconnect, then
pulls everything changed since its last cursor. A completed round is
immutable — it never conflicts, because nothing can write to it again once
`completed_at` is set.

### Course → Layout → Hole

Holes never attach directly to a course. A course has one or more
**layouts** (short tees, long tees, alternate baskets, a temporary winter
layout), and every layout has its own holes. All scoring, statistics,
personal bests, and friend comparisons are keyed to a **layout**, not a
course. Getting this wrong means rewriting the entire stats layer later, so
every model and endpoint that touches scoring must take a `layout_id`, never
a bare `course_id`.
