# .devcontainer Configuration

This directory contains the configuration for GitHub Codespaces and VS Code Dev Containers.

## 📁 Files

### `devcontainer.json`
Main configuration file that defines:
- **Container settings**: Base image, features, extensions
- **VS Code customizations**: Extensions, settings, themes
- **Port forwarding**: Auto-forward service ports
- **Secrets**: OpenAI and Anthropic API keys
- **Post-create command**: Runs `setup.sh` automatically

### `Dockerfile`
Custom container image with:
- **Python 3.12**: For LLM service and worker
- **Node.js 20 LTS**: For frontend and backend
- **Development tools**: git, docker, kubectl, helm
- **Python packages**: pytest, black, pylint
- **Node packages**: typescript, eslint, prettier

### `docker-compose.yml`
Service dependencies for the devcontainer:
- **PostgreSQL**: Main database
- **Redis**: Cache and sessions
- **RabbitMQ**: Message queue
- **Qdrant**: Vector database

### `setup.sh`
Automatic setup script that:
1. Installs Python dependencies (llm-service, worker-service)
2. Installs Node.js dependencies (backend, frontend)
3. Creates `.env` from template
4. Waits for services to be ready
5. Initializes RabbitMQ queues
6. Verifies database connection
7. Displays service URLs and credentials

## 🚀 Quick Start

1. **Open in Codespaces**:
   - Go to your GitHub repo
   - Click "Code" → "Codespaces" → "Create codespace on main"

2. **Wait for Setup** (~5-10 minutes first time):
   - Container builds
   - Dependencies install
   - Services start
   - `setup.sh` runs automatically

3. **Configure API Keys**:
   ```bash
   nano /workspace/devops/.env
   # Add your OPENAI_API_KEY and ANTHROPIC_API_KEY
   ```

4. **Start Application Services**:
   ```bash
   cd /workspace/devops
   docker-compose up -d
   ```

5. **Test**:
   ```bash
   cd /workspace/devops/services/llm-service
   python test_complete.py
   ```

## 🔧 Customization

### Adding VS Code Extensions

Edit `devcontainer.json`:

```json
"customizations": {
  "vscode": {
    "extensions": [
      "your-extension-id"
    ]
  }
}
```

### Adding System Packages

Edit `Dockerfile`:

```dockerfile
RUN apt-get update && apt-get install -y \
    your-package \
    && apt-get clean
```

### Adding Python Packages

Edit `setup.sh` or manually run:

```bash
pip install package-name
```

### Adding Node Packages

Edit `setup.sh` or manually run:

```bash
npm install -g package-name
```

## 🌐 Port Forwarding

Automatically forwarded ports:
- **3000**: Approval Backend API
- **3001**: Approval Frontend (React)
- **3002**: Grafana
- **5432**: PostgreSQL
- **5672**: RabbitMQ
- **6333**: Qdrant
- **6379**: Redis
- **8000**: LLM Service API
- **9090**: Prometheus
- **15672**: RabbitMQ Management

Access via: `https://CODESPACE_NAME-PORT.app.github.dev`

## 🐛 Troubleshooting

### Container Build Fails

```bash
# Rebuild container
Cmd/Ctrl + Shift + P → "Rebuild Container"
```

### Services Not Starting

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs

# Restart services
docker-compose restart
```

### Dependencies Not Installing

```bash
# Re-run setup script
bash .devcontainer/setup.sh

# Or install manually
cd /workspace/devops/services/llm-service
pip install -r requirements.txt
```

### Port Forwarding Issues

```bash
# Forward port manually in VS Code
Cmd/Ctrl + Shift + P → "Forward a Port"
```

## 📚 Documentation

- **Detailed Setup**: `/workspace/devops/CODESPACES-SETUP.md`
- **GitHub Push**: `/workspace/devops/GITHUB-PUSH-GUIDE.md`
- **Docker Compose**: `/workspace/devops/DOCKER-COMPOSE-GUIDE.md`
- **Test Results**: `/workspace/devops/TEST-RESULTS.md`

## 🔐 Security

- **`.env` is gitignored**: Never committed to repo
- **Use GitHub Secrets**: Store API keys in Codespaces secrets
- **Secrets in devcontainer.json**: Auto-inject from GitHub Secrets

## 📝 Notes

- **First build is slow**: ~5-10 minutes (subsequent starts: ~30 seconds)
- **Prebuilds available**: For faster starts (organization repos)
- **Auto-shutdown**: After 30 minutes of inactivity
- **Workspace persistence**: Files persist between stops

---

**Last Updated**: 2025-10-18
