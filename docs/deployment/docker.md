# Docker Deployment

This guide covers deploying KYCC using Docker and Docker Compose.

## Overview

| Service | Image | Port |
|---------|-------|------|
| Backend | Python 3.11 | 8000 |
| PostgreSQL | postgres:15-alpine | 5433 |
| Dagster | Python 3.11 | 3000 |

---

## Docker Compose Configuration

### docker-compose.yml

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    container_name: kycc-postgres
    environment:
      POSTGRES_USER: kycc
      POSTGRES_PASSWORD: kycc_password
      POSTGRES_DB: kycc_db
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kycc -d kycc_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: kycc-backend
    environment:
      DATABASE_URL: postgresql://kycc:kycc_password@postgres:5432/kycc_db
      PYTHONUNBUFFERED: 1
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  dagster:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: kycc-dagster
    environment:
      DATABASE_URL: postgresql://kycc:kycc_password@postgres:5432/kycc_db
      DAGSTER_HOME: /app/dagster_home
    ports:
      - "3000:3000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - dagster_storage:/app/dagster_instance
    command: dagster dev -h 0.0.0.0 -p 3000 -f dagster_home/definitions.py
    working_dir: /app

volumes:
  postgres_data:
  dagster_storage:
```

---

## Backend Dockerfile

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Quick Start

### Start All Services

```bash
docker-compose up -d
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Stop Services

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

---

## Individual Service Commands

### PostgreSQL

```bash
# Start only PostgreSQL
docker-compose up -d postgres

# Connect to database
docker exec -it kycc-postgres psql -U kycc -d kycc_db

# View logs
docker-compose logs -f postgres
```

### Backend

```bash
# Start backend
docker-compose up -d backend

# Run migrations
docker exec kycc-backend alembic upgrade head

# View logs
docker-compose logs -f backend

# Shell access
docker exec -it kycc-backend bash
```

### Dagster

```bash
# Start Dagster
docker-compose up -d dagster

# View logs
docker-compose logs -f dagster
```

---

## Database Migrations

### Run Migrations in Container

```bash
docker exec kycc-backend alembic upgrade head
```

### Create New Migration

```bash
docker exec kycc-backend alembic revision --autogenerate -m "description"
```

### Rollback Migration

```bash
docker exec kycc-backend alembic downgrade -1
```

---

## Seeding Data

### Seed Synthetic Data

```bash
docker exec kycc-backend python -c "
from app.services.synthetic_seed_service import ingest_seed_file
from app.db.database import SessionLocal
db = SessionLocal()
ingest_seed_file(db, 'data/synthetic_profiles.json', batch_id='BATCH_001')
db.close()
"
```

### Verify Data

```bash
docker exec kycc-backend python -c "
from app.db.database import SessionLocal
from app.models.models import Party
db = SessionLocal()
count = db.query(Party).count()
print(f'Total parties: {count}')
db.close()
"
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| PYTHONUNBUFFERED | Disable output buffering | `1` |
| DAGSTER_HOME | Dagster home directory | `/app/dagster_home` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| LOG_LEVEL | Logging level | `INFO` |
| CORS_ORIGINS | Allowed CORS origins | `*` |
| API_KEY | API authentication key | None |

### Using .env File

Create `.env` file:

```
DATABASE_URL=postgresql://kycc:kycc_password@postgres:5432/kycc_db
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

Reference in docker-compose.yml:

```yaml
services:
  backend:
    env_file:
      - .env
```

---

## Volume Management

### List Volumes

```bash
docker volume ls
```

### Inspect Volume

```bash
docker volume inspect kycc_postgres_data
```

### Backup Database Volume

```bash
docker run --rm \
  -v kycc_postgres_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar cvf /backup/postgres_backup.tar /data
```

### Restore Database Volume

```bash
docker run --rm \
  -v kycc_postgres_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xvf /backup/postgres_backup.tar -C /
```

---

## Networking

### Default Network

Docker Compose creates a default network: `kycc_default`

### Service Discovery

Services can reach each other by service name:
- `postgres:5432` - PostgreSQL
- `backend:8000` - Backend API
- `dagster:3000` - Dagster UI

### External Access

- Backend API: `http://localhost:8000`
- Dagster UI: `http://localhost:3000`
- PostgreSQL: `localhost:5433`

---

## Health Checks

### PostgreSQL Health Check

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U kycc -d kycc_db"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### Backend Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Check Health Status

```bash
docker-compose ps
docker inspect kycc-backend --format='{{.State.Health.Status}}'
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Check container status
docker ps -a

# Inspect container
docker inspect kycc-backend
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Test connection from backend
docker exec kycc-backend python -c "
from app.db.database import engine
print(engine.connect())
"
```

### Permission Issues

```bash
# Fix volume permissions
docker exec -u root kycc-backend chown -R appuser:appuser /app
```

### Out of Disk Space

```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a
```

---

## Production Considerations

1. **Remove --reload flag** in production
2. **Use secrets management** for passwords
3. **Enable SSL/TLS** for database connections
4. **Set resource limits** on containers
5. **Use external PostgreSQL** for production
6. **Configure logging** to external service
7. **Set up monitoring** with Prometheus/Grafana
