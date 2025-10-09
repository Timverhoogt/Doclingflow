# Port Configuration

All external ports have been updated to the 2xxx range to avoid conflicts.

## External Access Ports (from host machine)

| Service | External Port | Internal Port | URL |
|---------|--------------|---------------|-----|
| **Frontend** | 2001 | 3000 | http://localhost:2001 |
| **Backend API** | 2000 | 2000 | http://localhost:2000 |
| **Backend API Docs** | 2000 | 2000 | http://localhost:2000/docs |
| **PostgreSQL** | 2432 | 5432 | localhost:2432 |
| **Qdrant HTTP** | 2333 | 6333 | http://localhost:2333 |
| **Qdrant Dashboard** | 2333 | 6333 | http://localhost:2333/dashboard |
| **Qdrant gRPC** | 2334 | 6334 | localhost:2334 |
| **Redis** | 2379 | 6379 | localhost:2379 |

## Internal Docker Network Ports

Services communicate with each other using internal Docker network and standard ports:

```yaml
# Backend environment variables (inside containers)
DATABASE_URL: postgresql://doclingflow:doclingflow_password@postgres:5432/doclingflow
QDRANT_HOST: qdrant
QDRANT_PORT: 6333
REDIS_URL: redis://redis:6379/0
```

## Configuration Files Updated

✅ `docker-compose.yml` - All port mappings updated to 2xxx range
✅ `.env` - NEXT_PUBLIC_API_URL updated to port 2000
✅ `.env.example` - All external ports updated to 2xxx range
✅ `README.md` - All documentation URLs updated
✅ `backend/README.md` - API documentation URL updated
✅ `backend/Dockerfile` - EXPOSE and CMD updated to port 2000
✅ `frontend/Dockerfile` - Documentation comment added

## Testing the Configuration

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

3. **Access services:**
   - Frontend: http://localhost:2001
   - Backend API Docs: http://localhost:2000/docs
   - Qdrant Dashboard: http://localhost:2333/dashboard

4. **Check health:**
   ```bash
   curl http://localhost:2000/api/health
   ```

5. **Test database connection:**
   ```bash
   docker-compose exec postgres psql -U doclingflow -d doclingflow -c "SELECT 1;"
   ```

## Port Mapping Summary

### For Host Access (from your machine):
- Use ports in the **2xxx range**
- Example: `http://localhost:2000` for backend API

### For Container-to-Container Communication:
- Use **service names** and **standard ports**
- Example: `http://backend:2000` or `postgres:5432`

### For Development (.env file):
When running services **inside Docker**, use service names:
```env
DATABASE_URL=postgresql://doclingflow:doclingflow_password@postgres:5432/doclingflow
QDRANT_HOST=qdrant
```

When running services **outside Docker** (local development), use localhost with 2xxx ports:
```env
DATABASE_URL=postgresql://doclingflow:doclingflow_password@localhost:2432/doclingflow
QDRANT_HOST=localhost
QDRANT_PORT=2333
```
