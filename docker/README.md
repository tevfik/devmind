# 🐳 Yaver Docker Services

Yaver requires several services to run. Use Docker Compose to manage them easily.

## Quick Start

```bash
# Start all services
yaver docker start

# Check status
yaver docker status

# Stop services
yaver docker stop
```

## Available Commands

```bash
yaver docker start      # Start all services
yaver docker stop       # Stop all services
yaver docker status     # Check service status
yaver docker logs       # View real-time logs
yaver docker restart    # Restart all services
```

## Services Included

### 1. **Qdrant** (Vector Database)
- **Purpose**: Store vector embeddings for semantic search
- **Port**: 6333 (HTTP), 6334 (gRPC)
- **Web UI**: http://localhost:6333/dashboard
- **Data**: Persisted in `docker/data/qdrant/`

### 2. **Neo4j** (Graph Database)
- **Purpose**: Store code structure and relationships
- **Port**: 7687 (Bolt), 7474 (HTTP)
- **Web UI**: http://localhost:7474
- **Default Auth**: neo4j / password
- **Data**: Persisted in `docker/data/neo4j/`

### 3. **Ollama** (Optional - Local LLM)
- **Purpose**: Run LLM models locally
- **Port**: 11434
- **Note**: Can be run standalone on host machine

## Manual Docker Compose Commands

If you prefer to use Docker Compose directly:

```bash
cd docker

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart specific service
docker-compose restart neo4j
```

## Troubleshooting

### "Docker is not running"
```bash
# Start Docker Desktop (macOS/Windows) or daemon (Linux)
sudo systemctl start docker  # Linux
# or open Docker Desktop app
```

### "Port 6333 already in use"
Another service is using the port. Stop conflicting services:
```bash
docker ps  # Find container using port 6333
docker stop <container_id>
```

### "Connection refused" when running Yaver
Make sure services are running:
```bash
yaver docker status
```

If status shows services as down, try restarting:
```bash
yaver docker restart
```

### Check service logs
```bash
# All services
yaver docker logs

# Specific service
docker-compose -f docker/docker-compose.yml logs neo4j

# Real-time logs
docker-compose -f docker/docker-compose.yml logs -f qdrant
```

## Environment Configuration

Services use credentials from `.yaver/config.json`. Modify service passwords:

```bash
# Edit .env file
nano .yaver/.env

# Update Neo4j password:
NEO4J_PASSWORD=your_new_password

# Restart services to apply changes
yaver docker restart
```

## Performance Tips

### For M1/M2 Mac
Ensure Docker Desktop has sufficient resources:
- Memory: 4GB+
- CPU: 2 cores+
- Storage: 5GB+

### For Linux
```bash
# Check Docker stats
docker stats

# Increase memory limit if needed
docker-compose down
# Then edit docker-compose.yml to add memory limits
```

## Cleanup

### Stop all services
```bash
yaver docker stop
```

### Remove containers and volumes
```bash
docker-compose -f docker/docker-compose.yml down -v
# Warning: This deletes all data!
```

### Restart from scratch
```bash
# Stop
yaver docker stop

# Remove data
rm -rf docker/data/

# Start fresh
yaver docker start
```

## Network

Services are on an isolated Docker network `yaver-network`. They can communicate by container name.

## Production Deployment

For production, consider:
1. Using managed services (Qdrant Cloud, Neo4j Aura)
2. Setting strong passwords for all services
3. Using Docker secrets for sensitive data
4. Implementing proper backup strategies
5. Using reverse proxy (nginx) for external access

See `ONBOARDING.md` for cloud configuration options.
