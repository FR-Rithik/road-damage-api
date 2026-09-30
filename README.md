# Road Damage API

A REST API for reporting and managing road damage data.

Built with FastAPI, PostgreSQL, Docker, and SQLAlchemy.

---

## Requirements

- Docker
- Docker Compose

---

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/FR-Rithik/road-damage-api.git
   cd road-damage-api
   ```

2. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Start the containers:
   ```bash
   docker compose up --build
   ```

4. Run database migrations:
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. API is running at: http://localhost:8000

---

## Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/auth/me` | Yes | Get current API client info |
| POST | `/images` | Yes | Upload an image and receive a road-damage report |
| POST | `/predict` | Yes | Run road-damage detection without saving the image |

---

## Authentication

All protected endpoints require an `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

## Road-damage detection

The API loads `best.pt` lazily on the first prediction. Set `MODEL_PATH` to use a
checkpoint stored elsewhere. `POST /images` both saves the upload and returns the
raw detections plus a compact `report` grouped by the model's class labels.

```bash
curl -X POST http://localhost:8000/images \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@road.jpg"
```

The response includes `prediction.detections` (bounding boxes and confidence) and
`report`, for example `damage_detected`, counts by class, and a display-ready
summary. Place your checkpoint at `best.pt` or configure `MODEL_PATH` on the
server. The current model uses the labels `D00`, `D10`, `D20`, and `D40`.

---

## Running Tests

```bash
docker compose exec api pytest -q
```

---

## Project Structure

```
app/
├── main.py          # App entry point
├── config.py        # Settings from .env
├── database.py      # DB connection
├── models.py        # SQLAlchemy models
├── auth.py          # API key authentication
├── errors.py        # Error handlers
├── logger.py        # Logging setup
└── routers/
    └── auth.py      # Auth endpoints
tests/
└── test_auth.py     # Tests
```
