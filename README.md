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

---

## Authentication

All protected endpoints require an `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

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
