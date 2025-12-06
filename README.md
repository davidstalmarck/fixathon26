# fixathon26

Research engine for for Small Molecules.

## Package Manager

This project uses **pnpm** for the frontend. Always use `pnpm` for installing dependencies and running scripts.

## Getting Started with Docker

### Prerequisites

- Docker and Docker Compose installed
- Environment variables set (or use defaults):
  - `POSTGRES_USER` (default: `postgres`)
  - `POSTGRES_PASSWORD` (default: `postgres`)
  - `POSTGRES_DB` (default: `molecule_research`)
  - `ANTHROPIC_API_KEY` (required)
  - `MODAL_TOKEN_ID` (required)
  - `MODAL_TOKEN_SECRET` (required)

### Starting the Project

```bash
# Start all services (database, backend, frontend)
docker compose up

# Or run in detached mode
docker compose up -d
```

This will start:
- **PostgreSQL** (pgvector) on port `5432`
- **Backend** (FastAPI) on port `8000`
- **Frontend** (Next.js) on port `3000`

### Running Database Migrations

After starting the services, run migrations inside the backend container:

```bash
# Run pending migrations
docker compose exec backend uv run alembic upgrade head

# Check current migration status
docker compose exec backend uv run alembic current

# Generate a new migration (after model changes)
docker compose exec backend uv run alembic revision --autogenerate -m "description"
```

## Directory Structure

```
fixathon26/
├── src/
│   ├── frontend/    # Frontend application code
│   └── backend/     # Backend application code
├── docker-compose.yml
├── .gitignore
└── README.md
```
