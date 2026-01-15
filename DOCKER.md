# Docker Deployment Guide

This guide explains how to deploy the Proj3 MVP application using Docker.

## Prerequisites

1. **Docker** and **Docker Compose** installed
   ```bash
   docker --version
   docker-compose --version
   ```

2. **MongoDB Atlas** cluster with vector search index configured
   - See main README.md for vector index setup instructions

3. **API Keys**:
   - Deepgram API key
   - Groq API key
   - Google AI API key

## Quick Start

### Development Mode

1. **Set up environment variables**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your MongoDB URL and API keys
   ```

2. **Start services**:
   ```bash
   cd ..  # Back to project root
   docker-compose up --build
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Production Mode

1. **Set up production environment variables**:
   ```bash
   cd backend
   cp .env.example .env.prod
   # Edit .env.prod with your production MongoDB URL and API keys
   ```

2. **Start services**:
   ```bash
   cd ..  # Back to project root
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

3. **Access the application**:
   - Frontend: http://localhost (port 80)
   - Backend API: http://localhost:8000

4. **View logs**:
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

5. **Stop services**:
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

## Architecture

### Services

1. **backend**: FastAPI application
   - Port: 8000
   - Health check: `/health`
   - Auto-reload in development mode
   - Multiple workers in production mode

2. **frontend**: React application served by Nginx
   - Port: 3000 (dev) or 80 (prod)
   - Proxies API requests to backend
   - Serves static files with caching

### Network

All services communicate through a Docker bridge network (`proj3-network` or `proj3-network-prod`).

## Configuration

### Backend Environment Variables

Create `backend/.env` (development) or `backend/.env.prod` (production):

```env
MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net
DB_NAME=mvp_db
DEEPGRAM_API_KEY=your-key
GROQ_API_KEY=your-key
GOOGLE_API_KEY=your-key
```

### Frontend Environment Variables

For development, you can set these in `docker-compose.yml` or create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_PIPECAT_ENDPOINT=/api/v1/stream/connect
```

**Note**: In production, the frontend is built at image creation time. If you need to change these values, rebuild the image or use nginx configuration.

## Development vs Production

### Development (`docker-compose.yml`)

- **Backend**: 
  - Source code mounted as volume (hot reload)
  - Single worker with auto-reload
  - Debug-friendly logging

- **Frontend**:
  - Built once, served by nginx
  - Port 3000

### Production (`docker-compose.prod.yml`)

- **Backend**:
  - No volume mounts (code baked into image)
  - Multiple workers (2) for better performance
  - No auto-reload

- **Frontend**:
  - Optimized production build
  - Port 80 (standard HTTP)
  - Better caching headers

## Troubleshooting

### Backend won't start

1. **Check MongoDB connection**:
   ```bash
   docker-compose logs backend
   ```
   Ensure `MONGO_URL` in `.env` is correct.

2. **Check health endpoint**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Verify vector index**:
   ```bash
   curl http://localhost:8000/health/vector-index
   ```

### Frontend can't connect to backend

1. **Check CORS settings**: Ensure backend `main.py` includes frontend origin
2. **Check network**: Ensure both services are on the same Docker network
3. **Check nginx logs**:
   ```bash
   docker-compose logs frontend
   ```

### Port conflicts

If ports 8000 or 3000/80 are already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change host port
```

### Rebuild after code changes

**Development**: Changes are reflected automatically (hot reload)

**Production**: Rebuild required:
```bash
docker-compose -f docker-compose.prod.yml up --build -d
```

## Useful Commands

```bash
# View logs
docker-compose logs -f [service-name]

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild specific service
docker-compose build [service-name]

# Execute command in container
docker-compose exec backend uv run python scripts/verify_vector_index.py

# View running containers
docker ps

# Clean up unused images
docker system prune -a
```

## Production Deployment Considerations

1. **Environment Variables**: Use secrets management (Docker secrets, AWS Secrets Manager, etc.)
2. **Reverse Proxy**: Consider adding nginx/traefik in front for SSL termination
3. **Database**: Use managed MongoDB Atlas (already configured)
4. **Monitoring**: Add health checks and monitoring (Prometheus, Grafana)
5. **Logging**: Configure centralized logging (ELK stack, CloudWatch, etc.)
6. **Backup**: Set up regular MongoDB backups
7. **Scaling**: Use Docker Swarm or Kubernetes for multi-instance deployment

## Security Notes

- Never commit `.env` files to version control
- Use strong MongoDB credentials
- Rotate API keys regularly
- Enable MongoDB IP whitelisting
- Consider adding authentication for production
- Use HTTPS in production (add reverse proxy with SSL)

