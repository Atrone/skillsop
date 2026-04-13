# skillsop

## Architecture Specification

The SkillsAI Architecture Option 17 specification is available in: 

- `docs/architecture/README.md`
- `docs/architecture/*.puml` (C4 Level 1/2/3 diagrams in plain PlantUML)

## FastAPI backend

The Python architecture in `skillsai/` is exposed as a FastAPI backend.

### Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### Run backend

```bash
python3 -m skillsai.main
```

The backend serves:

- `GET /api/v1/health`
- `POST /api/v1/platform/request`

### Seed data services with Docker Compose

Use the root `docker-compose.yml` to host static seed datasets for all backend API families behind the federation gateway.

```bash
docker compose up -d
```

Hosted seed-data service endpoints:

- `http://localhost:8100/index.json` -> platform/gateway API seeds
- `http://localhost:8101/index.json` -> identity API seeds
- `http://localhost:8102/index.json` -> core intelligence API seeds
- `http://localhost:8103/index.json` -> activation services API seeds
- `http://localhost:8104/index.json` -> assessments API seeds
- `http://localhost:8105/index.json` -> analytics API seeds
- `http://localhost:8106/index.json` -> Workday-style REST API mock

Workday-style mock endpoints:

- `GET http://localhost:8106/api/v1/acme`
- `GET http://localhost:8106/api/v1/acme/workers`
- `GET http://localhost:8106/api/v1/acme/workers/wid-1001`
- `GET http://localhost:8106/api/v1/acme/workers/wid-1001/basic`
- `GET http://localhost:8106/api/v1/acme/workers/wid-1001/talent`
- `GET http://localhost:8106/api/v1/acme/jobs`
- `GET http://localhost:8106/api/v1/acme/jobs/job-analytics-engineer`
- `GET http://localhost:8106/api/v1/acme/organizations`
- `GET http://localhost:8106/api/v1/acme/organizations/org-finance`
- `GET http://localhost:8106/api/v1/acme/locations`
- `GET http://localhost:8106/api/v1/acme/locations/loc-austin`

## React frontend integration

The React app in `frontend/` is wired to the backend gateway endpoint at:

- `POST {VITE_BACKEND_BASE_URL}/api/v1/platform/request`

Set the frontend environment variable to the backend origin:

```bash
VITE_BACKEND_BASE_URL=http://localhost:8000
```