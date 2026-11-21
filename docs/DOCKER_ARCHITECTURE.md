# Docker Architecture & Multi-Compose Service Topology

## 1. Architectural Model: Independent Micro-Composes

To guarantee independent lifecycle management, scalability, and zero inter-service tight coupling, the platform does not rely on a single monolithic `docker-compose.yml`. Instead, the system is architected into **four independently deployable Docker Compose projects** that collaborate over a dedicated external bridge network: `finance-network`.

```
                                finance-network (External Docker Bridge)
       ┌───────────────────────────────┬───────────────────────────────┬───────────────────────────────┐
       │                               │                               │                               │
       ▼                               ▼                               ▼                               ▼
┌──────────────┐                ┌──────────────┐                ┌──────────────┐                ┌──────────────┐
│  frontend/   │                │   backend/   │                │ ai-service/  │                │infrastructure│
│docker-compose│                │docker-compose│                │docker-compose│                │docker-compose│
│              │                │              │                │              │                │              │
│finance-      │                │finance-      │                │finance-      │                │finance-      │
│frontend (:80)│                │backend(:5000)│                │ai-service    │                │postgres,     │
│              │                │              │                │        (:8000│                │redis, rabbit │
└──────────────┘                └──────────────┘                └──────────────┘                └──────────────┘
```

---

## 2. Shared External Network: `finance-network`

The shared Docker network must exist before any container project starts:

```bash
# Create shared external network (one-time setup)
docker network create finance-network
```

All four `docker-compose.yml` configurations reference this network as an external resource:
```yaml
networks:
  finance-network:
    external: true
```

---

## 3. Independent Compose Projects

### Project 1: Infrastructure (`infrastructure/docker-compose.yml`)
- **Containers:**
  - `finance-postgres`: PostgreSQL 16 with `pgvector` extension.
    - Container Port: `5432`
    - Host Port: `5434` (configurable via `POSTGRES_PORT` in `.env` to avoid host conflicts)
    - Healthcheck: `pg_isready -U postgres -d finance_controller`
    - Volume: `finance_postgres_data`
  - `finance-redis`: Redis 7 Alpine with Append-Only File (AOF) persistence.
    - Container Port: `6379`
    - Host Port: `6380` (configurable via `REDIS_PORT` in `.env`)
    - Healthcheck: `redis-cli -a <password> ping`
    - Volume: `finance_redis_data`
  - `finance-rabbitmq`: RabbitMQ 3 Management.
    - Container Ports: `5672` (AMQP), `15672` (Management Dashboard)
    - Host Ports: `5672:5672`, `15672:15672`
    - Healthcheck: `rabbitmq-diagnostics -q check_running`
    - Volume: `finance_rabbitmq_data`

### Project 2: Backend Service (`backend/docker-compose.yml`)
- **Container:** `finance-backend` (Node.js 20 Alpine)
- **Container Port:** `5000`
- **Host Port:** `5000:5000`
- **Healthcheck:** `GET /api/health`
- **Internal Network Targets:** `finance-postgres:5432`, `finance-redis:6379`, `finance-rabbitmq:5672`, `finance-ai-service:8000`

### Project 3: AI & Data Processing Service (`ai-service/docker-compose.yml`)
- **Container:** `finance-ai-service` (Python 3.11 Slim)
- **Container Port:** `8000`
- **Host Port:** `8000:8000`
- **Healthcheck:** `GET /internal/health`
- **Internal Network Targets:** `finance-postgres:5432`, `finance-redis:6379`, `finance-rabbitmq:5672`

### Project 4: Frontend Service (`frontend/docker-compose.yml`)
- **Container:** `finance-frontend` (Nginx Alpine serving optimized React production bundle)
- **Container Port:** `80`
- **Host Port:** `3000:80`
- **Healthcheck:** `GET /`

---

## 4. Independent Operation Lifecycle Commands

Every service can be built, started, stopped, inspected, and restarted without impacting the other services:

```bash
# ====================================================================
# INFRASTRUCTURE
# ====================================================================
docker compose -f infrastructure/docker-compose.yml up -d
docker compose -f infrastructure/docker-compose.yml ps
docker compose -f infrastructure/docker-compose.yml logs -f [postgres|redis|rabbitmq]
docker compose -f infrastructure/docker-compose.yml restart [service]
docker compose -f infrastructure/docker-compose.yml down

# ====================================================================
# BACKEND SERVICE
# ====================================================================
docker compose -f backend/docker-compose.yml up -d --build
docker compose -f backend/docker-compose.yml logs -f
docker compose -f backend/docker-compose.yml restart
docker compose -f backend/docker-compose.yml down

# ====================================================================
# AI & DATA PROCESSING SERVICE
# ====================================================================
docker compose -f ai-service/docker-compose.yml up -d --build
docker compose -f ai-service/docker-compose.yml logs -f
docker compose -f ai-service/docker-compose.yml restart
docker compose -f ai-service/docker-compose.yml down

# ====================================================================
# FRONTEND SERVICE
# ====================================================================
docker compose -f frontend/docker-compose.yml up -d --build
docker compose -f frontend/docker-compose.yml logs -f
docker compose -f frontend/docker-compose.yml restart
docker compose -f frontend/docker-compose.yml down
```

---

## 5. Persistent Volume Guarantees

All persistent data resides in dedicated Docker volumes:
- `finance_postgres_data`: Preserves all SQL tables, pgvector embeddings, and transaction records across container recreations.
- `finance_redis_data`: Preserves append-only transaction logs.
- `finance_rabbitmq_data`: Preserves durable queues, message payloads, and virtual host settings.

> [!CAUTION]
> Running `docker compose down -v` will delete named volumes and cause permanent data loss. Always omit the `-v` flag during standard service restarts and upgrades.
