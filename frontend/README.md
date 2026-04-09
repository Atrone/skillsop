# SkillsAI React Frontend

React + Vite frontend for interacting with the SkillsAI federation gateway.

## Features

- Gateway request workbench for query and command routes
- Route-specific forms for all currently implemented backend paths
- Structured display of request payload and backend response
- Runtime backend URL override for local or remote API targets

## Supported backend routes

### Query routes

- `GET /identity`
- `GET /skills`
- `GET /coaching`
- `GET /assessments`
- `GET /analytics`

### Command routes

- `POST /command/identity/link`
- `POST /command/core/infer`
- `POST /command/activation/coaching`
- `POST /command/assessments/submit`
- `POST /command/analytics/materialize`

## Backend contract assumed by frontend

The UI sends all requests to:

- `POST {VITE_BACKEND_BASE_URL}/api/v1/platform/request`

With payload shape:

```json
{
  "method": "GET",
  "path": "/analytics",
  "actor_id": "emp-1",
  "token": "valid-token",
  "payload": {
    "metric": "skill_coverage",
    "cohort": "all",
    "start": "2026-01-01",
    "end": "2026-12-31"
  }
}
```

## Setup

```bash
cd frontend
npm install
```

Create `.env.local`:

```bash
VITE_BACKEND_BASE_URL=http://localhost:8000
```

Run the app:

```bash
npm run dev
```

## Build and lint

```bash
npm run lint
npm run build
```
