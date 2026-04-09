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

## React frontend integration

The React app in `frontend/` is wired to the backend gateway endpoint at:

- `POST {VITE_BACKEND_BASE_URL}/api/v1/platform/request`

Set the frontend environment variable to the backend origin:

```bash
VITE_BACKEND_BASE_URL=http://localhost:8000
```