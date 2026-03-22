# PodiumForge

PodiumForge is a self-hosted local-first tournament manager that combines the richer format engine and public views from version 1 with the operational tooling from version 2.

It is built for events where a match can have 3, 4, 5, or more entrants and produces an ordered result such as 1st through 5th place. The MVP focuses on LAN parties, board game nights, scouting activities, and other local events where classic 1v1 brackets are not enough.

## What works now

- Multiplayer matches are first-class: a match supports multiple entrants, ranked finishing order, points, scores, and tie-group input.
- Scoring controls are configurable: tournaments can label the score field, choose whether higher or lower values are better, and run leaderboards by points or cumulative score where it fits.
- Public pages are available without login: home, tournament overview, rounds, standings, round detail, match detail, dashboard, and TV mode.
- Protected admin/editor pages support login, user management, tournament creation, tournament editing, live result entry, and next-round generation.
- The ranking engine updates standings, qualification, elimination, provisional classification places, and final overall placements.
- Public standings include tie-break explanations and qualification/cut-line context where it applies.
- Tournament overview pages now use clear section tabs: `Overview`, `Rounds`, `Standings`, and `Dashboard`.
- The public dashboard includes a TV mode with larger presentation-focused panels and optional auto-rotation.
- Password reset emails are supported through configurable SMTP settings.
- Everything runs locally with Docker Compose and PostgreSQL.

## Supported tournament formats

- `FFA_ELIMINATION`
  - multiplayer heats where top finishers advance per match
- `GROUP_POINTS`
  - shared leaderboard progression across groups or heats
- `LEADERBOARD_SERIES`
  - fixed number of grouped rounds feeding one cumulative leaderboard
- `STANDALONE_MATCH`
  - one ranked match that locks the full final order immediately
- `BRACKET`
  - seeded single-elimination head-to-head bracket
- `DOUBLE_ELIMINATION`
  - winners bracket + losers bracket with grand final flow
- `ROUND_ROBIN`
  - everyone plays everyone once and the table decides the champion
- `SWISS`
  - fixed number of rounds with score-based pairings and rotating byes
- `PAGE_PLAYOFF`
  - seeded top-four finals format with qualifier, eliminator, preliminary final, and grand final

Roadmapped but not yet implemented as engines:

- `Ladder`
- `McMahon`

## Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy 2.0 + Pydantic
- Database: PostgreSQL
- Migrations: Alembic
- Auth: JWT with securely hashed passwords
- Containers: Docker Compose

## Project structure

```text
.
|- apps/
|  |- api/
|  |  |- alembic/
|  |  |- app/
|  |  |  |- core/
|  |  |  |- models/
|  |  |  |- modules/
|  |  |  |- repositories/
|  |  |  |- schemas/
|  |  |  |- services/
|  |  |  |- tests/
|  |- web/
|  |  |- nginx/
|  |  |- src/
|- packages/
|  |- shared/
|- docker-compose.yml
|- docker-compose.images.yml
```

## Quick start

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:8080`
- API docs: `http://localhost:8000/docs`
- Mailpit: `http://localhost:8025`

On first startup the API runs Alembic migrations, ensures roles exist, and creates the configured admin account if needed.

## Published images

The repository now includes a GitHub Actions workflow at `.github/workflows/publish-docker-images.yml` that publishes two multi-arch GHCR images:

- `ghcr.io/<owner>/podiumforge-api`
- `ghcr.io/<owner>/podiumforge-web`

The release images are built from:

- `apps/api/Dockerfile.release`
- `apps/web/Dockerfile.release`

They are trimmed for smaller download size by keeping the frontend runtime to static assets + Nginx and the backend runtime to an Alpine Python image with production-only dependencies.

If you want the published packages to be publicly pullable from GHCR, make sure the package visibility is set to `public` after the first publish.

Example usage with the published images:

```bash
docker compose -f docker-compose.images.yml up -d
```

Override the default example image names if needed:

```bash
PODIUMFORGE_API_IMAGE=ghcr.io/<owner>/podiumforge-api:latest \
PODIUMFORGE_WEB_IMAGE=ghcr.io/<owner>/podiumforge-web:latest \
docker compose -f docker-compose.images.yml up -d
```

## Default login

Default local admin account:

- Username: `admin`
- Email: `admin@podiumforge.local`
- Password: `admin1234`

Change or replace this account in real usage.

## Main URLs

Public:

- `/`
- `/tournaments/:slug`
- `/tournaments/:slug/standings`
- `/tournaments/:slug/rounds/:roundId`
- `/matches/:matchId`
- `/dashboard/:slug`

Protected:

- `/login`
- `/reset-password?token=...`
- `/admin`
- `/admin/users`
- `/admin/tournaments/new`
- `/admin/tournaments/:tournamentId`
- `/admin/matches/:matchId/entry`

Presentation:

- `/dashboard/:slug/tv`

## Public vs admin experience

- The public site focuses on tournament overviews, standings, round pages, match results, and dashboards.
- Admin and editor workflows are intentionally reduced to authenticated pages only.
- Setup-oriented details such as local credentials, SMTP/Mailpit, and role management belong in this README or the admin experience, not on the public home page.

## How the ranking and progression engine works

The backend keeps tournament logic in service modules instead of route handlers.

- `apps/api/app/services/tournament_builder.py`
  - creates tournaments, stages, rounds, seeded entrants, and the first batch of multiplayer matches
- `apps/api/app/services/match_service.py`
  - validates result submissions, stores ranked outcomes, awards points, and updates match/round/tournament status
- `apps/api/app/services/progression_service.py`
  - determines who advances from a completed round and generates the next round when requested
- `apps/api/app/services/standings_service.py`
  - calculates standings, alive/qualified entrants, eliminated entrants, provisional classification places, and final placements

For elimination flows, entrants still alive reserve the top open placements while eliminated entrants are classified behind them. Example: after two 5-player heats with top 2 advancing, the four finalists reserve places 1-4 and the other six entrants are immediately classified into places 5-10.

## Auth and roles

Roles are stored in the database and attached to users.

- `ADMIN`
  - manage users
  - assign roles
  - create and edit tournaments
  - enter results
- `TOURNAMENT_EDITOR`
  - create and edit tournaments
  - enter results
  - manage participants, rounds, matches, and standings-related data

Relevant files:

- `apps/api/app/core/security.py`
- `apps/api/app/core/dependencies.py`
- `apps/api/app/modules/auth/router.py`
- `apps/api/app/modules/users/router.py`

Frontend route protection lives in:

- `apps/web/src/features/auth/AuthContext.tsx`
- `apps/web/src/features/auth/ProtectedRoute.tsx`

## Running tests

Frontend build:

```bash
npm install
npm run build --workspace=@podiumforge/web
```

Backend tests with Python 3.12:

```bash
python3.12 -m venv /tmp/podiumforge-api-venv
/tmp/podiumforge-api-venv/bin/pip install -r apps/api/requirements.txt
PYTHONPATH="$PWD/apps/api" /tmp/podiumforge-api-venv/bin/pytest apps/api/app/tests -q
```

Or inside Docker:

```bash
docker compose run --rm api pytest app/tests -q
```

## Assumptions in this MVP

- Team-based tournaments are supported at the participant level, but team roster management is not implemented yet.
- Next round generation is manual from the protected tournament page.
- Tie handling at an advancement cutoff requires either manual place resolution or distinct score values.
- Page playoffs currently run as a standalone seeded top-four finals format rather than an automatically chained second stage after round-robin or Swiss play.
- CSV import/export, drag-and-drop reseeding, kiosk mode, and print layouts are not included yet.

## OpenCode Project Report

This repository was built through OpenCode sessions for this worktree. The report below is based on the retained OpenCode project/session history for `PodiumForge`, the git history in this repository, and the resulting codebase.

### What OpenCode created

OpenCode produced the full working product that exists here today, including:

- the current FastAPI + SQLAlchemy backend
- the React + TypeScript + Vite frontend
- Docker Compose, Nginx, PostgreSQL, and Mailpit local infrastructure
- the tournament engine, standings engine, and admin/public route structure
- authentication, roles, user management, and password reset flow
- public dashboards, TV mode, and tournament navigation tabs
- the additional tournament formats added after the first MVP: brackets, double elimination, round robin, Swiss, and Page playoff
- the associated test coverage, refactors, and QA fixes

### Delivery timeline from OpenCode history

- `2026-03-10` - `7517ce6` - `feat: build multiplayer tournament MVP`
  - initial end-to-end product for multiplayer ranked tournaments
  - first public pages, admin flows, tournament engine, demo data, and tests
- `2026-03-10` - `e23642c` - `chore: add compose startup and clean build artifacts`
  - container startup, Docker Compose workflow, startup scripts, and first README pass
- `2026-03-11` - `e1e63dd` - `feat: rebuild PodiumForge as a local-first platform`
  - architecture reset from the earlier Node/Prisma stack into the current FastAPI/PostgreSQL/local-first structure
  - protected admin area, public API split, service-layer tournament engine, seeded admin account, and expanded tests
- `2026-03-15` - `dc00157` - `feat: add bracket play and account recovery flows`
  - single-elimination brackets, double elimination, richer tournament format guidance, password reset, Mailpit-backed recovery, stronger user management, and broader auth/engine tests
- `2026-03-17` - `d252b32` - `feat: expand tournament format support and admin QA fixes`
  - round robin, Swiss, and Page playoff support
  - public overview tabs, TV mode upgrades, standings cut-line and tie-break UI, format roadmap cards, refactors, and bug-fix/QA follow-up work

### OpenCode session history that shaped this repo

The retained OpenCode session titles for this worktree show the main delivery phases and audit passes:

- `PodiumForge tournament app MVP build`
- `PodiumForge tournament app implementation`
- `Admin-added user not appearing`
- `User deletion and password reset with Mailpit`
- `Website review and tournament scheme ideas`
- `Commit and push changes to main branch`

Supporting subagent and audit sessions were also used, including:

- `Scan UI bugs`
- `Scan backend UI edges`
- `Audit public UX bugs`
- `Audit frontend routes`
- `Audit admin backend`
- `Audit backend UX risks`
- `Review final UI impact`
- `Final code sanity`
- `Explore format architecture`
- `Find refactor targets`

These titles line up closely with the git history and the functional additions now present in the repository.

### Specific user instructions that materially changed direction

The surviving chat and session history shows that some major directions came from explicit user instructions rather than from the agent deciding alone. The clearest recoverable instructions were:

- build a tournament manager for ranked multiplayer matches, not just classic 1v1 brackets
- keep the product self-hosted and local-first
- add bracket play and account recovery flows
- review the website on `localhost:8080`, click through it carefully, and suggest improvements
- improve public tournament structure with clearer `Overview`, `Rounds`, `Standings`, and `Dashboard` sections
- upgrade TV mode with larger typography, fewer controls, stronger current-match emphasis, and auto-rotation
- add standings cut-line UI and tie-break explanations
- research tournament schemes on the internet and add or document them
- implement `ROUND_ROBIN`, then `SWISS`, then `PAGE_PLAYOFF`
- keep changes uncommitted until they had been reviewed
- perform careful browser QA, continue deeper QA, and fix unexpected behavior found during testing

In other words, the user set the product goals and some UX/format priorities, but the agent still handled most implementation decisions.

### What the agent or LLM decided autonomously

Most of the day-to-day engineering choices were decided inside OpenCode sessions after the agent inspected the repository, read existing conventions, and tested the results. Examples include:

- choosing the current FastAPI + SQLAlchemy + Alembic backend structure
- organizing tournament logic into service modules such as `tournament_builder`, `progression_service`, `standings_service`, and `match_service`
- splitting the frontend into public/admin/auth/tournament feature areas
- adding shared metadata helpers for tournament formats and standings presentation
- introducing a browser-driven QA loop against `localhost:8080`
- using Mailpit for local password reset verification
- extracting cleanup helpers such as `apps/api/app/core/tournament_formats.py` and `apps/web/src/features/tournaments/formatMeta.ts`
- deciding the exact UI treatment for tabs, standings chips, TV rotation panels, and format guidance cards

This means the repository is not just a transcription of user instructions. The product direction was collaborative, but the implementation details were largely agent-led.

### How OpenCode worked on this project in practice

Across the recorded sessions, the typical OpenCode workflow was:

- inspect the current codebase and session state
- implement code changes directly in the repository
- run builds and backend tests
- rebuild the Docker stack with `docker compose build` and `docker compose up -d --force-recreate`
- click through the running product at `http://localhost:8080`
- inspect result pages, admin flows, dashboards, TV mode, and password reset emails
- fix bugs found during QA
- refactor repeated logic after the behavior was stable

That cycle is visible in both the OpenCode session titles and the commit history.

### Browser and verification tooling used by OpenCode

This project includes `opencode.json`, which enables the browser MCP integration used during QA:

- OpenCode could navigate the local app in a browser session
- click through public and admin routes
- inspect page snapshots and console output
- verify TV mode behavior and public/private route differences

Mailpit on `http://localhost:8025` was used to verify password reset delivery end to end.

### Current result of the OpenCode build history

The current repository is a self-hosted tournament operations platform with:

- public tournament discovery and spectator views
- admin tournament operations and user management
- ranked multiplayer match handling
- multiple tournament engines across elimination, standings, bracket, and league-style formats
- local Docker-based development and verification workflow
- explicit test coverage around tournament progression and auth-critical flows

### Important note on source fidelity

The retained OpenCode history is very good at preserving session titles, file diffs, and commit-level progression. It is less complete at preserving every verbatim user prompt in a human-readable way. For that reason, the report above is a best-available reconstruction from:

- OpenCode project metadata
- OpenCode session titles and diff history
- repository commit history
- the resulting code now present in this worktree

## Good next improvements

- CSV participant import/export and standings export
- richer group-stage scheduling for repeated rounds
- manual reseeding tools and wildcard labels
- deeper team roster support
- kiosk mode and projector-focused dashboard variants
