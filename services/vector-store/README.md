# Qdrant Vector Store Setup

This directory contains configuration and setup files for deploying Qdrant vector database for the LLM application. Qdrant is a high-performance vector search engine designed for similarity search and AI applications.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
  - [Local Docker Deployment](#local-docker-deployment)
  - [Qdrant Cloud](#qdrant-cloud)
  - [Self-Hosted Production](#self-hosted-production)
- [Collection Initialization](#collection-initialization)
- [Configuration](#configuration)
- [Backup and Recovery](#backup-and-recovery)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

This setup includes:
- **Qdrant Vector Database**: High-performance vector search engine
- **Pre-configured Collections**: Document embeddings, code snippets, conversations, knowledge base
- **Docker Compose**: Easy local deployment with persistent storage
- **Initialization Script**: Automated collection setup with proper indexes
- **Backup Solution**: Automated snapshot backups

## Quick Start

### Prerequisites

- Docker and Docker Compose (for local deployment)
- Python 3.8+ (for initialization script)
- Qdrant Python client: `pip install qdrant-client`

### 1. Local Deployment (Docker)

```bash
# Navigate to vector-store directory
cd C:\Users\s.babu21\Downloads\node-new\node-v24.10.0-win-x64\devops\services\vector-store

# Copy environment variables
cp .env.example .env

# Edit .env with your settings (optional for local development)
# For local deployment, defaults work fine

# Start Qdrant
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f qdrant
```

### 2. Initialize Collections

```bash
# Install Python dependencies
pip install qdrant-client

# Run initialization script
python init-collections.py

# Or with specific options
python init-collections.py --url http://localhost:6333 --recreate

# List existing collections
python init-collections.py --list

# Health check
python init-collections.py --health
```

### 3. Access Qdrant

- **REST API**: http://localhost:6333
- **Web Dashboard**: http://localhost:6333/dashboard
- **gRPC API**: http://localhost:6334

## Deployment Options

### Local Docker Deployment

Best for development and testing.

**Features:**
- Single-node deployment
- Persistent volumes for data storage
- Automatic backup service
- Web dashboard included

**Steps:**
1. Copy `.env.example` to `.env`
2. Run `docker-compose up -d`
3. Access at http://localhost:6333

**Data Location:**
- Vectors: `./data/storage`
- Snapshots: `./data/snapshots`
- Backups: `./backups`

### Qdrant Cloud

Best for production without infrastructure management.

**Steps:**

1. **Create Account**: https://cloud.qdrant.io/
2. **Create Cluster**: Choose region and plan
3. **Get Credentials**: Copy cluster URL and API key
4. **Configure Environment**:

```bash
# .env file
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key-here
```

5. **Initialize Collections**:

```bash
python init-collections.py --url https://your-cluster.qdrant.io --api-key your-api-key
```

**Pricing**: Free tier available, paid plans start at $25/month

### Self-Hosted Production

For production deployment on your own infrastructure.

**Architecture Options:**
- Single node (simple, limited scale)
- Clustered (high availability, horizontal scaling)

**Single Node Setup:**

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:v1.9.2
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - /var/lib/qdrant/storage:/qdrant/storage
      - /var/lib/qdrant/snapshots:/qdrant/snapshots
      - ./config/qdrant-config.yaml:/qdrant/config/production.yaml
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
      - QDRANT__LOG_LEVEL=INFO
```

**Production Checklist:**
- [ ] Enable API key authentication
- [ ] Configure TLS/SSL certificates
- [ ] Set up automated backups
- [ ] Configure monitoring and alerts
- [ ] Implement firewall rules
- [ ] Use reverse proxy (nginx/traefik)
- [ ] Set resource limits
- [ ] Configure log rotation

## Collection Initialization

The `init-collections.py` script creates the following collections:

### 1. Documents Collection
- **Vector Size**: 1536 (OpenAI ada-002)
- **Use**: General document embeddings
- **Indexes**: document_type, user_id, timestamp

### 2. Code Snippets Collection
- **Vector Size**: 1536
- **Use**: Code and technical documentation
- **Indexes**: language, framework, user_id

### 3. Conversations Collection
- **Vector Size**: 1536
- **Use**: Chat history and conversation context
- **Indexes**: session_id, user_id, timestamp

### 4. Knowledge Base Collection
- **Vector Size**: 3072 (OpenAI text-embedding-3-large)
- **Use**: High-quality curated knowledge
- **Indexes**: category, source, priority

### 5. User Profiles Collection
- **Vector Size**: 1536
- **Use**: User preferences and behavior
- **Indexes**: user_id, profile_type

### Custom Collections

To add custom collections, modify `init-collections.py`:

```python
collections_config.append({
    'name': 'my_custom_collection',
    'vector_size': 1536,
    'distance': Distance.COSINE,
    'description': 'My custom collection',
    'indexes': [
        ('custom_field', PayloadSchemaType.KEYWORD),
    ]
})
```

## Configuration

### Environment Variables

See `.env.example` for all available options.

**Key Settings:**

```bash
# Connection
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-secure-api-key

# Performance
VECTOR_DIMENSION=1536
DISTANCE_METRIC=cosine
MAX_SEARCH_RESULTS=100

# Resources
QDRANT_CPU_LIMIT=2.0
QDRANT_MEMORY_LIMIT=4G
```

### Qdrant Configuration

Edit `config/qdrant-config.yaml` for advanced settings:

- **Storage**: WAL, snapshots, optimization
- **Performance**: Indexing, HNSW parameters
- **Security**: API keys, TLS
- **Clustering**: P2P, consensus (for distributed setup)

## Backup and Recovery

### Automated Backups

The Docker Compose setup includes an automated backup service:

```bash
# Configure backup frequency
BACKUP_INTERVAL=86400  # Daily (in seconds)
BACKUP_RETENTION_DAYS=7  # Keep 7 days

# Backups are stored in ./backups directory
```

### Manual Backup

```bash
# Create snapshot via API
curl -X POST http://localhost:6333/collections/documents/snapshots

# Download snapshot
curl -X GET http://localhost:6333/collections/documents/snapshots/snapshot_name \
  -o backup.snapshot

# Or use the backup service
docker-compose exec qdrant-backup sh -c "tar -czf /backups/manual_backup.tar.gz -C /snapshots ."
```

### Restore from Backup

```bash
# Stop Qdrant
docker-compose down

# Extract backup
tar -xzf backups/qdrant_backup_20231215_120000.tar.gz -C data/snapshots/

# Restore via API after restart
curl -X PUT http://localhost:6333/collections/documents/snapshots/upload \
  -F "snapshot=@snapshot_file"

# Or copy to snapshots directory before starting
cp backup.snapshot data/snapshots/
docker-compose up -d
```

## Monitoring

### Health Checks

```bash
# Health endpoint
curl http://localhost:6333/healthz

# Collection info
curl http://localhost:6333/collections/documents

# Cluster info
curl http://localhost:6333/cluster

# Metrics (Prometheus format)
curl http://localhost:6333/metrics
```

### Web Dashboard

Access the built-in dashboard at: http://localhost:6333/dashboard

**Features:**
- Collection overview
- Search interface
- Performance metrics
- Configuration viewer

### Prometheus Metrics

Qdrant exposes Prometheus metrics at `/metrics` endpoint:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'qdrant'
    static_configs:
      - targets: ['localhost:6333']
```

**Key Metrics:**
- `qdrant_collection_vectors_count`
- `qdrant_rest_responses_total`
- `qdrant_rest_responses_duration_seconds`

## Troubleshooting

### Connection Issues

```bash
# Check if Qdrant is running
docker-compose ps

# Check logs
docker-compose logs qdrant

# Test connection
curl http://localhost:6333/collections
```

### Performance Issues

**Slow searches:**
- Increase HNSW `ef_construct` parameter
- Add payload indexes for frequent filters
- Enable on-disk storage for large collections
- Increase resource limits (CPU/Memory)

**High memory usage:**
- Enable quantization in config
- Use on-disk storage: `on_disk: true`
- Reduce HNSW `m` parameter

### Data Issues

**Collections not created:**
- Check Python script output
- Verify connection settings
- Check API key if authentication is enabled

**Backup failures:**
- Verify volume mounts
- Check disk space
- Review backup service logs: `docker-compose logs qdrant-backup`

### Common Errors

**Error: "Collection already exists"**
```bash
# Recreate collection
python init-collections.py --recreate
```

**Error: "Connection refused"**
```bash
# Wait for Qdrant to start
docker-compose up -d
sleep 10
python init-collections.py
```

**Error: "Authentication failed"**
```bash
# Check API key
echo $QDRANT_API_KEY
# Update .env file and restart
docker-compose restart
```

## Performance Tuning

### HNSW Parameters

- **m**: Number of edges per node (16-64)
  - Higher = better recall, more memory
- **ef_construct**: Build-time accuracy (100-512)
  - Higher = better index quality, slower build
- **ef**: Search-time accuracy (64-512)
  - Higher = better recall, slower search

### Indexing Threshold

- **Low threshold** (< 10k): Faster searches, more memory
- **High threshold** (> 50k): Less memory, slower searches

### Optimization Strategy

```python
# For high-throughput writes
OptimizersConfigDiff(
    indexing_threshold=50000,
    memmap_threshold=100000
)

# For low-latency searches
OptimizersConfigDiff(
    indexing_threshold=10000,
    memmap_threshold=20000
)
```

## API Examples

### Python Client

```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

client = QdrantClient(url="http://localhost:6333")

# Insert vectors
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=1,
            vector=[0.1] * 1536,
            payload={"text": "Hello world", "user_id": "user123"}
        )
    ]
)

# Search
results = client.search(
    collection_name="documents",
    query_vector=[0.1] * 1536,
    limit=10,
    query_filter={"must": [{"key": "user_id", "match": {"value": "user123"}}]}
)
```

### REST API

```bash
# Insert point
curl -X PUT http://localhost:6333/collections/documents/points \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {
        "id": 1,
        "vector": [0.1, 0.2, ...],
        "payload": {"text": "Hello world"}
      }
    ]
  }'

# Search
curl -X POST http://localhost:6333/collections/documents/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, ...],
    "limit": 10,
    "with_payload": true
  }'
```

## Resources

- **Qdrant Documentation**: https://qdrant.tech/documentation/
- **Python Client**: https://github.com/qdrant/qdrant-client
- **Qdrant Cloud**: https://cloud.qdrant.io/
- **GitHub**: https://github.com/qdrant/qdrant
- **Discord Community**: https://discord.gg/qdrant

## Support

For issues and questions:
1. Check logs: `docker-compose logs qdrant`
2. Review Qdrant documentation
3. Check GitHub issues
4. Join Discord community

## License

This configuration is provided as-is for the project. Qdrant itself is licensed under Apache 2.0.
