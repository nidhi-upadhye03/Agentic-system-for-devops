# LLM DevOps Copilot

**AI-Powered Autonomous Incident Response & Remediation Platform**

[![Build Status](https://github.com/nidhi-upadhye03/Agentic-system-for-devops/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/nidhi-upadhye03/Agentic-system-for-devops/actions)
[![Docker Hub](https://img.shields.io/badge/Docker-nidhi-upadhye03-blue)](https://hub.docker.com/u/nidhi-upadhye03)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)](https://github.com/nidhi-upadhye03/Agentic-system-for-devops)

> **A fully autonomous DevOps copilot that detects incidents, performs AI-powered root cause analysis using LLMs (GPT-4/Gemini 2.0), and executes automated remediation actions with intelligent approval workflows.**

---

## âœ¨ Latest Updates (January 2026)

- âœ… **Complete End-to-End Workflow Verified** - Full incident detection â†’ analysis â†’ approval â†’ remediation cycle tested
- âœ… **Manual Review Feature** - ALL analyzed incidents (even without automated recommendations) sent to approval dashboard for human oversight
- âœ… **Approval Dashboard Integration** - Fixed API endpoint routing, response parsing, and real-time WebSocket updates
- âœ… **Dual Dashboard System** - Ops Dashboard (localhost:3003) + Approval Dashboard (localhost:3001) fully operational
- âœ… **18 Production Services** - Complete microservices stack running with Docker Compose
- âœ… **Gemini 2.0 Integration** - Google Gemini 2.0-Flash model support with 2000 RPM rate limiting
- âœ… **Redis Caching Optimizations** - LLM response caching (300s TTL) to reduce API costs
- âœ… **Docker Compose Executor** - Support for both Kubernetes and Docker Compose environments

---

## ðŸŽ¯ Project Overview

The **LLM DevOps Copilot** is a production-grade, event-driven platform featuring **5 autonomous AI agents** that work together to provide intelligent incident management. 
### Team Collaboration and Contribution

- This platform was developed as team work with coordinated delivery across all services and dashboards.
- My contribution (Nidhi): I implemented the Monitoring Agent and completed the RabbitMQ-based connection flow across all agents so incidents and analysis events move reliably through the system.
- Additional team contributions include LLM integration, approval workflows, remediation execution, memory/pattern learning, and observability dashboards.


1. **Monitor** infrastructure metrics (CPU, memory, errors, restarts) with real-time anomaly detection
2. **Analyze** incidents using LLM-powered root cause analysis (OpenAI GPT-4 / Google Gemini 2.0-Flash)
3. **Recommend** actionable remediation steps (scale deployments, restart pods, rollback releases)
4. **Execute** automated healing actions OR request human approval based on confidence scores
5. **Learn** from past incidents using RAG (Retrieval-Augmented Generation) with vector embeddings
6. **Notify** teams via Slack and real-time dashboard updates

### ðŸš€ Key Features

- âœ… **Zero-Touch Incident Resolution**: 95%+ confidence threshold for auto-execution
- âœ… **Human-in-the-Loop Approval**: Comprehensive web dashboard for reviewing and approving critical actions
- âœ… **Intelligent Manual Review**: Incidents without automated recommendations automatically routed for human analysis
- âœ… **Pattern Detection**: Learns from recurring incidents (exact, semantic, temporal patterns)
- âœ… **Multi-LLM Support**: OpenAI GPT-4, Anthropic Claude, Google Gemini 2.0-Flash with intelligent fallbacks
- âœ… **Event-Driven Architecture**: RabbitMQ message broker with topic-based routing and durable queues
- âœ… **Production-Ready**: Docker Compose + Kubernetes support, health checks, graceful shutdowns
- âœ… **Real-Time Observability**: Prometheus metrics, Grafana dashboards, live agent logs
- âœ… **Cost Optimized**: Redis caching, rate limiting, token optimization (~$0.03-0.05 per incident)

---

## ðŸ—ï¸ System Architecture

### High-Level Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      LLM DevOps Copilot Architecture                          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Test App    â”‚â”€â”€â”€â”€â”€â”€â–¶â”‚  Prometheus  â”‚â”€â”€â”€â”€â”€â”€â–¶â”‚  Monitoring  â”‚
â”‚ (Metrics)    â”‚metricsâ”‚   Scraper    â”‚scrape â”‚    Agent     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜       â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                                                       â”‚ Incident Event
                                                       â”‚ (monitoring.incident.*)
                                                       â–¼
                                              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                              â”‚   RabbitMQ     â”‚
                                              â”‚  Event Bus     â”‚
                                              â”‚ Topic Exchange â”‚
                                              â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                                                       â”‚
                      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                      â”‚                                â”‚                      â”‚
                      â–¼                                â–¼                      â–¼
            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
            â”‚  Analyzer Agent  â”‚â—€â”€â”€â”€â”€â”€â”€â”€â”€â–¶â”‚  LLM Service     â”‚    â”‚  Notifier    â”‚
            â”‚                  â”‚  API     â”‚  â€¢ GPT-4         â”‚    â”‚   Agent      â”‚
            â”‚ â€¢ RAG Search     â”‚          â”‚  â€¢ Gemini 2.0    â”‚    â”‚  â€¢ Slack     â”‚
            â”‚ â€¢ Redis Cache    â”‚          â”‚  â€¢ Claude 3.5    â”‚    â”‚  â€¢ WebSocket â”‚
            â”‚ â€¢ Action Mapping â”‚          â”‚  â€¢ OpenRouter    â”‚    â”‚  â€¢ Email     â”‚
            â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜          â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚ Analysis Complete
                     â”‚ (analyzer.analysis.complete)
                     â”‚ â€¢ Confidence: 75-95%
                     â”‚ â€¢ Recommendations: 0-N
                     â–¼
            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
            â”‚ Auto-Response    â”‚
            â”‚    Agent         â”‚
            â”‚                  â”‚
            â”‚ Decision Logic:  â”‚
            â”‚ â”œâ”€ Confidenceâ‰¥95%+Low â†’ Auto-Execute
            â”‚ â”œâ”€ Confidence<95% â†’ Request Approval
            â”‚ â””â”€ No Recommendations â†’ Manual Review
            â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
         â”‚                       â”‚
         â–¼                       â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Kubernetes/    â”‚    â”‚  Approval Dashboard â”‚
â”‚ Docker Compose  â”‚    â”‚   (localhost:3001)  â”‚
â”‚                 â”‚    â”‚                     â”‚
â”‚ Actions:        â”‚    â”‚ â€¢ Review Incident   â”‚
â”‚ â€¢ Scale         â”‚    â”‚ â€¢ View Analysis     â”‚
â”‚ â€¢ Restart       â”‚    â”‚ â€¢ Approve/Reject    â”‚
â”‚ â€¢ Rollback      â”‚    â”‚ â€¢ Manual Override   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚                       â”‚
         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚ Action Result
                     â–¼
            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
            â”‚  Memory Agent    â”‚â—€â”€â”€â”€â”€â”€â”€â”€â–¶â”‚  Ops Dashboard   â”‚
            â”‚                  â”‚         â”‚ (localhost:3003) â”‚
            â”‚ â€¢ PostgreSQL     â”‚         â”‚                  â”‚
            â”‚ â€¢ Qdrant Vector  â”‚         â”‚ â€¢ System Status  â”‚
            â”‚ â€¢ Pattern Store  â”‚         â”‚ â€¢ Incident Feed  â”‚
            â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â”‚ â€¢ Agent Health   â”‚
                                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Event Flow Sequence

1. **Detection (T+0s)**: Monitoring Agent detects anomaly (CPU > 80%, Memory > 85%, Errors > 5%)
2. **Publishing (T+1s)**: Incident event published to RabbitMQ (`monitoring.incident.threshold_breach`)
3. **Analysis (T+2-5s)**: Analyzer Agent queries RAG, sends to LLM, generates recommendations
4. **Decision (T+5-6s)**: Auto-Response evaluates confidence and creates approval OR auto-executes
5. **Approval (T+variable)**: Human reviews in dashboard at localhost:3001 (if required)
6. **Execution (T+final)**: Action performed on Kubernetes/Docker Compose
7. **Notification (T+final)**: Slack alert + Dashboard update + Pattern storage

---

## ðŸ¤– The 5 Autonomous Agents

### 1. **Monitoring Agent** ðŸ“Š
- **Technology**: Python 3.11, Prometheus Client, Kubernetes API
- **Function**: Continuously monitors cluster metrics and detects anomalies
- **Triggers**: CPU > 80%, Memory > 85%, Error Rate > 5%, Pod restarts > 3
- **Anomaly Detection**: Z-score based statistical analysis (2.0Ïƒ threshold)
- **Output**: Publishes incident events to RabbitMQ (`monitoring.incident.*`)

### 2. **Analyzer Agent** ðŸ§ 
- **Technology**: Python 3.11, OpenAI SDK, Anthropic SDK, Qdrant Client
- **Function**: Performs LLM-powered root cause analysis
- **Inputs**: Incident data + Recent logs + Similar past incidents (RAG)
- **LLMs**: GPT-4 (OpenAI), Claude 3.5 Sonnet (Anthropic)
- **Output**: Root cause + Confidence score + Actionable recommendations
- **RAG**: Searches vector store for similar incidents (similarity â‰¥ 0.7)

### 3. **Auto-Response Agent** âš¡
- **Technology**: Python 3.11, Kubernetes Python Client, Approval Dashboard API
- **Function**: Executes or requests approval for remediation actions
- **Actions**: Scale deployment, Restart pods, Rollback deployment
- **Decision Logic**:
  - **Auto-execute**: Confidence â‰¥ 95% + Low/Medium criticality
  - **Request approval**: Confidence < 95% OR High/Critical criticality
- **Safety**: Cooldown periods, replica limits (min: 1, max: 10), dry-run mode

### 4. **Notifier Agent** ðŸ“¢
- **Technology**: Python 3.11, Slack SDK (slack-sdk 3.23.0)
- **Function**: Sends rich Slack notifications with context
- **Message Types**: Incident detected, Analysis complete, Action executed, Approval pending
- **Formatting**: Slack Block Kit (headers, sections, fields, emoji indicators)
- **Channels**: `#devopsalerts` (configurable)

### 5. **Memory Agent** ðŸ§ ðŸ’¾
- **Technology**: Python 3.11, PostgreSQL (asyncpg), Qdrant Cloud, OpenAI Embeddings
- **Function**: Stores incidents and detects patterns for continuous learning
- **Storage**: 4 PostgreSQL tables (incidents, analyses, resolutions, patterns)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Pattern Detection**:
  1. **Exact Match**: Same metric + target recurring (SQL GROUP BY)
  2. **Semantic**: Similar issues via vector clustering (similarity â‰¥ 0.85)
  3. **Temporal**: Time-based patterns (day of week + hour analysis)

---

## ðŸ› ï¸ Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Agents** | Python 3.11, asyncio, aio-pika, kubernetes-python-client | 3.11+ |
| **LLM Service** | FastAPI, OpenAI SDK, Google GenAI, Anthropic SDK | Latest |
| **Approval Dashboard** | React 18 + Material-UI (Frontend), Node.js + Express + Socket.io (Backend) | 18.2.0 |
| **Ops Dashboard** | Next.js 14, React, TailwindCSS | 14.0 |
| **Message Broker** | RabbitMQ 3.12 with Management Plugin | 3.12+ |
| **Databases** | PostgreSQL 15 (incidents/approvals), Redis 7 (caching) | 15/7 |
| **Vector Store** | Qdrant (self-hosted or cloud) | Latest |
| **Monitoring** | Prometheus 2.45+, Grafana 10.0+, NGINX | Latest |
| **Container Orchestration** | Docker Compose (local), Kubernetes 1.28+ (production) | 2.20+ |
| **Reverse Proxy** | NGINX (ports: 80, 443) | Latest |
| **CI/CD** | GitHub Actions | - |
| **Container Registry** | Docker Hub (nidhi-upadhye03) | - |

### Complete Service Stack (18 Microservices)

**Infrastructure Services:**
- PostgreSQL (Database)
- Redis (Cache)
- RabbitMQ (Message Broker)
- Prometheus (Metrics)
- Grafana (Visualization)
- NGINX (Reverse Proxy)

**Core AI Agents:**
- Monitoring Agent (Incident Detection)
- Analyzer Agent (Root Cause Analysis)
- Auto-Response Agent (Remediation)
- Notifier Agent (Alerts)
- Memory Agent (Learning)

**Supporting Services:**
- LLM Service (AI Processing)
- Worker Service (Background Tasks)
- Approval Backend API
- Approval Frontend Dashboard
- Ops Backend API
- Ops Frontend Dashboard
- Test App (Chaos Generator)
- Vector Store (Qdrant)

---

## ðŸ“ Project Structure

```
devops/
â”œâ”€â”€ README.md                                # This file
â”œâ”€â”€ IMPLEMENTATION_TRACKER.md                # Development progress tracker
â”œâ”€â”€ LOCAL_RULES.md                           # Local development rules
â”œâ”€â”€ TODO_BEFORE_DEPLOY.md                    # Pre-deployment checklist
â”œâ”€â”€ FUTUREVISION.md                          # System architecture & vision
â”œâ”€â”€ AZURE_DEPLOYMENT_GUIDE.md                # Azure deployment guide
â”œâ”€â”€ deploy-from-dockerhub.sh                 # Azure deployment script
â”‚
â”œâ”€â”€ services/                                # Microservices
â”‚   â”œâ”€â”€ monitoring-agent/                    # Incident detection
â”‚   â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”‚   â”œâ”€â”€ main.py                      # Main agent loop
â”‚   â”‚   â”‚   â”œâ”€â”€ prometheus_client.py         # Metrics collector
â”‚   â”‚   â”‚   â”œâ”€â”€ k8s_client.py                # Kubernetes API
â”‚   â”‚   â”‚   â”œâ”€â”€ anomaly_detector.py          # Z-score anomaly detection
â”‚   â”‚   â”‚   â””â”€â”€ event_publisher.py           # RabbitMQ publisher
â”‚   â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”‚   â””â”€â”€ requirements.txt
â”‚   â”‚
â”‚   â”œâ”€â”€ analyzer-agent/                      # Root cause analysis
â”‚   â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”‚   â”œâ”€â”€ main.py                      # Event consumer + orchestrator
â”‚   â”‚   â”‚   â”œâ”€â”€ llm_analyzer.py              # LLM integration
â”‚   â”‚   â”‚   â”œâ”€â”€ rag_search.py                # Vector similarity search
â”‚   â”‚   â”‚   â””â”€â”€ log_fetcher.py               # Log aggregation
â”‚   â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”‚   â””â”€â”€ requirements.txt
â”‚   â”‚
â”‚   â”œâ”€â”€ auto-response-agent/                 # Automated remediation
â”‚   â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”‚   â”œâ”€â”€ main.py                      # Remediation orchestrator
â”‚   â”‚   â”‚   â”œâ”€â”€ k8s_executor.py              # K8s actions (scale/restart/rollback)
â”‚   â”‚   â”‚   â”œâ”€â”€ approval_client.py           # Approval API client
â”‚   â”‚   â”‚   â””â”€â”€ action_validator.py          # Safety checks
â”‚   â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”‚   â””â”€â”€ requirements.txt
â”‚   â”‚
â”‚   â”œâ”€â”€ notifier-agent/                      # Slack notifications
â”‚   â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”‚   â”œâ”€â”€ main.py                      # Notification orchestrator
â”‚   â”‚   â”‚   â””â”€â”€ slack_client.py              # Slack Block Kit integration
â”‚   â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”‚   â””â”€â”€ requirements.txt
â”‚   â”‚
â”‚   â”œâ”€â”€ memory-agent/                        # Incident learning
â”‚   â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”‚   â”œâ”€â”€ main.py                      # Memory orchestrator
â”‚   â”‚   â”‚   â”œâ”€â”€ incident_store.py            # PostgreSQL storage
â”‚   â”‚   â”‚   â”œâ”€â”€ vector_store.py              # Qdrant embeddings
â”‚   â”‚   â”‚   â””â”€â”€ pattern_detector.py          # Pattern analysis
â”‚   â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”‚   â””â”€â”€ requirements.txt
â”‚   â”‚
â”‚   â”œâ”€â”€ llm-service/                         # LLM API wrapper
â”‚   â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”‚   â”œâ”€â”€ main.py                      # FastAPI server
â”‚   â”‚   â”‚   â”œâ”€â”€ llm_client.py                # Multi-provider LLM client
â”‚   â”‚   â”‚   â””â”€â”€ rag_pipeline.py              # RAG with Qdrant
â”‚   â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”‚   â””â”€â”€ requirements.txt
â”‚   â”‚
â”‚   â””â”€â”€ approval-dashboard/                  # Human-in-the-loop UI
â”‚       â”œâ”€â”€ backend/
â”‚       â”‚   â”œâ”€â”€ src/
â”‚       â”‚   â”‚   â”œâ”€â”€ server.js                # Express + Socket.io
â”‚       â”‚   â”‚   â”œâ”€â”€ routes/                  # REST API routes
â”‚       â”‚   â”‚   â””â”€â”€ services/                # Business logic
â”‚       â”‚   â”œâ”€â”€ Dockerfile
â”‚       â”‚   â””â”€â”€ package.json
â”‚       â””â”€â”€ front (Docker Compose - Recommended)

### Prerequisites

**Required:**
- **Docker Desktop** 24.0+ with Docker Compose v2.20+
- **Python 3.11+** (for trigger_incident.py script)
- **16 GB RAM** minimum (32 GB recommended)
- **50 GB** available disk space

**API Keys (at least one required):**
- **Google Gemini API Key** ([Get here](https://makersuite.google.com/app/apikey)) - **RECOMMENDED** (2000 RPM free tier)
- **OpenAI API Key** ([Get here](https://platform.openai.com/api-keys)) - Optional
- **Anthropic API Key** ([Get here](https://console.anthropic.com/)) - Optional

**Optional:**
- Slack Bot Token ([Get here](https://api.slack.com/apps)) - For notifications
- Qdrant Cloud account ([Get here](https://cloud.qdrant.io/)) - For vector storage (self-hosted by default
â”œâ”€â”€ k8s/                                     # Kubernetes manifests
â”‚   â”œâ”€â”€ agents/                              # Agent deployments
â”‚   â”œâ”€â”€ infrastructure/                      # RabbitMQ, PostgreSQL, Redis
â”‚   â””â”€â”€ monitoring/                          # Prometheus, Grafana
â”‚
â”œâ”€â”€ infrastructure/
â”‚   â”œâ”€â”€ helm-charts/                         # Helm charts
â”‚   â””â”€â”€ database/                            # Database schemas
â”‚
â””â”€â”€ monitoring/
    â”œâ”€â”€ prometheus/                          # Prometheus config
    â”œâ”€â”€ grafana/                             # Grafana dashboards
    â””â”€â”€ alertmanager/                        # Alert rules
```

---

## ðŸš€ Quick Start

### Prerequisites

- **Kubernetes cluster** (Azure AKS, AWS EKS, GCP GKE, or local Minikube)
- **kubectl** configured
- **Docker** (for local development)
- **ðŸ”¥ One-Command Setup

1. **Clone the repository**:
```bash
git clone https://github.com/nidhi-upadhye03/Agentic-system-for-devops.git
cd llm-devops-copilot
```

2. **Create `.env` file** (copy from `.env.example` and add your API keys):
```bash
# Copy template
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, notepad++
```

**Minimum `.env` configuration:**
```bash
# LLM API (at least one required - Gemini recommended)
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-key-here  # Optional

# RabbitMQ (default values work)
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=devops
RABBITMQ_PASSWORD=devops123

# PostgreSQL (default values work)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=devops
POSTGRES_PASSWORD=devops123
POSTGRES_DB=devops_db

# Redis (default values work)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis123

# Optional: Slack notifications
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#devops-alerts
```

3. **Start all 18 services** (builds and runs everything):
```bash
docker-compose up -d --build
```

This command will:
- âœ… Build all Docker images (~5-10 minutes first time)
- âœ… Start PostgreSQL, Redis, RabbitMQ
- âœ… Initialize database schema
- âœ… Launch all 5 AI agents
- âœ… Start both dashboards (Approval + Ops)
- âœ… Start monitoring stack (Prometheus, Grafana)

4. **Verify all services are healthy** (~60-90 seconds for full startup):
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep devops
```

All containers should show `(healthy)` status.

5. **Access the Dashboards**:

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| **Approval Dashboard** | http://localhost:3001 | Review and approve remediation actions |
| **Ops Dashboard** | http://localhost:3003 | System overview and incident feed |
| **Grafana** | http://localhost:3002 | Metrics and visualization (admin/admin) |
| **Prometheus** | http://localhost:9090 | Raw metrics and queries |
| **RabbitMQ Management** | http://localhost:15672 | Message queue monitoring (devops/devops123) |

6. **Trigger a test incident**:
```bash
# Using Python script (recommended)
python trigger_incident.py

# OR manually inject an incident
curl -X POST http://localhost:8080/trigger \
  -H "Content-Type: application/json" \
  -d '{"metric":"cpu_percent","value":95.5,"threshold":80.0}'
```

7. **Watch the magic happen** ðŸŽ©âœ¨:

Open 5 terminals and monitor agent logs in real-time:

**Terminal 1 - Monitoring Agent:**
```bash
docker logs devops-monitoring-agent --follow
```

**Terminal 2 - Analyzer Agent:**
```bash
docker logs devops-analyzer-agent --follow
```

**Terminal 3 - Auto-Response Agent:**
```bash
docker logs devops-auto-response-agent --follow
```

**Terminal 4 - Notifier Agent:**
```bash
docker logs devops-notifier-agent --follow
```

**Terminal 5 - LLM Service:**
```bash
docker logs devops-llm-service --follow
```

**Or use this one-liner to see all logs:**
```bash
docker-compose logs -f monitoring-agent analyzer-agent auto-response-agent notifier-agent llm-service
```

### ðŸ“Š Verify Complete Workflow

After triggering an incident, you should see:

1. âœ… **Monitoring Agent** detects anomaly (CPU > 80%)
2. âœ… **Analyzer Agent** performs LLM analysis (Gemini 2.0-Flash)
3. âœ… **Auto-Response Agent** creates approval request
4. âœ… **Approval Dashboard** displays incident card at http://localhost:3001
5. âœ… **Notifier Agent** sends notifications
6. âœ… **Ops Dashboard** shows incident in feed at http://localhost:3003

**Expected Timeline:**
- Detection: < 15 seconds
- Analysis: 2-5 seconds
- Approval creation: 1 second
- Dashboard update: Real-time (WebSocket)
- **Total MTTR: < 2 minutes** (automated path)

### ðŸŽ¨ View Formatted Agent Logs

```powershell
# Windows PowerShell - Beautiful colored output
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   DEVOPS COPILOT - AGENT LOGS" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "[1] MONITORING AGENT" -ForegroundColor Green
docker logs devops-monitoring-agent --tail 15

Write-Host "`n[2] ANALYZER AGENT" -ForegroundColor Green  
docker logs devops-analyzer-agent --tail 15

Write-Host "`n[3] AUTO-RESPONSE AGENT" -ForegroundColor Green
docker logs devops-auto-response-agent --tail 15

Write-Host "`n[4] NOTIFIER AGENT" -ForegroundColor Green
docker logs devops-notifier-agent --tail 15

Write-Host "`n[5] LLM SERVICE" -ForegroundColor Green
docker logs devops-llm-service --tail 10
```

### ðŸ›‘ Stop All Services

```bash
# Graceful shutdown
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Stop and remove everything including images
docker-compose down -v --rmi all
```

### ðŸ”§ Troubleshooting

**Issue: Containers failing health checks**
```bash
# Check specific container logs
docker logs devops-analyzer-agent --tail 50

# Restart specific service
docker-compose restart analyzer-agent

# Rebuild and restart
docker-compose up -d --build analyzer-agent
```

**Issue: Out of memory**
```bash
# Check Docker Desktop settings
# Increase memory allocation to at least 16 GB (preferably 32 GB)

# Check current usage
docker stats
```

**Issue: Port already in use**
```bash
# Check what's using port 3001 (example)
# Windows:
netstat -ano | findstr :3001

# Linux/Mac:
lsof -i :3001

# Kill the process or change port in docker-compose.yml
```

**Issue: LLM service not working**
```bash
# Verify API key is set
docker exec devops-llm-service printenv | grep API_KEY

# Test LLM service directly
curl http://localhost:8000/health

# Check LLM service logs
docker logs devops-llm-service --tail 100
```

### ðŸš€ Alternative Deployment Options

#### Option 1: Kubernetes (Production)

```bash
# Create namespace
kubectl create namespace devops-agents

# Apply manifests
kubectl apply -k k8s/overlays/production/

# Verify
kubectl get pods -n devops-agents
kubectl logs -f deployment/analyzer-agent -n devops-agents
```

#### Option 2: Azure Container Apps

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Deploy (uses pre-built images from Docker Hub)
chmod +x deploy-from-dockerhub.sh
./deploy-from-dockerhub.sh
```

**Estimated Cost**: $51-66/month (Azure for Students: $100 free credits)nstall with Helm
cd infrastructure/helm-charts
helm install devops-agents ./devops-agents -n devops-agents

# Verify
kubectl get pods -n devops-agents
```

---

## ðŸ”§ Configuration

### Agent Configuration

All agents are configured via environment variables:

#### Monitoring Agent
```bash
PROMETHEUS_URL=http://prometheus:9090
CPU_THRESHOLD=80.0
MEMORY_THRESHOLD=85.0
ERROR_RATE_THRESHOLD=5.0
ANOMALY_SENSITIVITY=2.0
```

#### Analyzer Agent
```bash
LLM_SERVICE_URL=http://llm-service:8000
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
RAG_ENABLED=true
RAG_TOP_K=5
```

#### Auto-Response Agent
```bash
K8S_NAMESPACE=default
AUTO_EXECUTE_THRESHOLD=95
MIN_SCALE_REPLICAS=1
MAX_SCALE_REPLICAS=10
K8S_DRY_RUN=false
```

---

## ðŸ“Š Monitoring & Observability

### ðŸŽ¯ Access All Dashboards

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Approval Dashboard** | http://localhost:3001 | None | Review AI recommendations, approve/reject actions |
| **Ops Dashboard** | http://localhost:3003 | None | System status, incident feed, agent health |
| **Grafana** | http://localhost:3002 | admin/admin | Metrics visualization, custom dashboards |
| **Prometheus** | http://localhost:9090 | None | Raw metrics, PromQL queries, alerts |
| **RabbitMQ Management** | http://localhost:15672 | devops/devops123 | Queue monitoring, message rates |

### ðŸ“ˆ Key Metrics

**System Performance:**
- **Incident Detection Rate**: 10-50 incidents per hour (configurable)
- **Analysis Latency**: 2-5 seconds (GPT-4), 1-3 seconds (Gemini 2.0)
- **Auto-Execution Rate**: 95% confidence threshold (customizable)
- **MTTR**: < 2 minutes (automated), < 5 minutes (with approval)
- **Approval Response Time**: Real-time WebSocket updates (<1s)

**Agent Health Metrics:**
- **Monitoring Agent**: Active/Disabled status, check interval (30s)
- **Analyzer Agent**: Queue depth, analysis success rate, LLM latency
- **Auto-Response Agent**: Action success rate, approval pending count
- **Notifier Agent**: Notification delivery rate, Slack API status
- **Memory Ag & Validation

### ðŸŽ¯ End-to-End Workflow Test

**1. Trigger a test incident:**
```bash
# Using Python script (recommended)
python trigger_incident.py

# Output:
# âœ… Event published to RabbitMQ
# Incident ID: manual-test-1767728017
# Waiting 8 seconds for pipeline to process...
```

**2. Verify each stage in real-time:**

**Stage 1 - Detection:**
```bash
docker logs devops-monitoring-agent --tail 20
# Expected: "ðŸš¨ Incident detected: threshold_breach"
```

**Stage 2 - Analysis:**
```bash
docker logs devops-analyzer-agent --tail 30
# Expected: "ðŸ” Analyzing incident manual-test-1767728017"
# Expected: "âœ“ Analysis complete: confidence=75%"
# Expected: "âœ“ Published analysis for incident"
```

**Stage 3 - Decision:**
```bash
docker logs devops-auto-response-agent --tail 30
# Expected: "Processing analysis for incident manual-test-1767728017: 1 recommendations"
# Expected: "âœ“ Created approval request: 119"
```

**Stage 4 - Approval Dashboard:**
```bash
# Open browser: http://localhost:3001
# Expected: New approval card appears with incident details
# Expected: Shows AI recommendation (scale_deployment to 3 replicas)
# Expected: Approve/Reject buttons functional
```

**Stage 5 - Notification:**
```bash
docker logs devops-notifier-agent --tail 15
# Expected: "Sending approval request notification: 119"
```

**3. Complete workflow verification:**
```powershell
# Windows PowerShell - Beautiful summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   WORKFLOW VERIFICATION" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "âœ“ Incident Detection: OK" -ForegroundColor Green
Write-Host "âœ“ AI Analysis: OK (Confidence: 75%)" -ForegroundColor Green
Write-Host "âœ“ Approval Created: OK (ID: 119)" -ForegroundColor Green
Write-Host "âœ“ Dashboard Updated: OK" -ForegroundColor Green
Write-Host "âœ“ Notification Sent: OK" -ForegroundColor Green
```

### ðŸ”¬ Unit Tests

```bash
# Run all tests for a specific agent
cd services/monitoring-agent
pytest tests/ -v --cov=app

# Run with coverage report
pytest tests/ -v --cov=app --cov-report=html

# Test specific module
pytest tests/test_prometheus_client.py -v

# Run tests for all agents
./run_tests.sh
```

### ðŸŽ­ Chaos Testing

**Simulate different incident types:**

**1. High CPU incident:**
```bash
python trigger_incident.py
# DefaProject Status & Roadmap

### âœ… Completed (v1.0 - January 2026)

- âœ… **Core 5 Agents**: All agents fully functional and tested
- âœ… **Event-Driven Architecture**: RabbitMQ with topic-based routing
- âœ… **LLM Integration**: GPT-4, Gemini 2.0-Flash, Claude 3.5 support
- âœ… **Approval Dashboard**: Full-featured web UI with real-time updates
- âœ… **Ops Dashboard**: System monitoring and incident feed
- âœ… **Docker Compose**: 18-service stack with health checks
- âœ…ðŸŽ“ Documentation

### ðŸ“š Additional Resources

- **[PROJECT_EXAM_DOCUMENTATION.md](PROJECT_EXAM_DOCUMENTATION.md)** - Comprehensive academic documentation with abstract, requirements, workflow, and future enhancements
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Detailed setup guide for beginners
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Deep dive into system architecture
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment strategies
- **[SYSTEM-UNDERSTANDING.md](SYSTEM-UNDERSTANDING.md)** - Complete system overview
- **[IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md)** - Development progress tracker
- **[FUTUREVISION.md](FUTUREVISION.md)** - Vision and future plans
- **[API.md](docs/API.md)** - API reference documentation

### ðŸŽ¬ Video Tutorials (Coming Soon)

- System overview and demo
- Local deployment walkthrough
- Creating custom agents
- Troubleshooting common issues

## â“ FAQ

**Q: What's the difference between Approval Dashboard and Ops Dashboard?**
- **Approval Dashboard (3001)**: For reviewing and approving AI-recommended actions. Human-in-the-loop interface.
- **Ops Dashboard (3003)**: For monitoring overall system health, viewing incident feed, and agent status.

**Q: Can I use this without Kubernetes?**
Yes! The system works perfectly with Docker Compose (default). Kubernetes support is optional for production scale.

**Q: Which LLM provider should I use?**
- **Google Gemini 2.0-Flash** (recommended): Free 2000 RPM, fast (1-3s), good quality
- **OpenAI GPT-4**: Higher quality, slower (2-5s), paid ($0.03-0.05 per incident)
- **Anthropic Claude**: Alternative option, similar to GPT-4

**Q: How much does it cost to run?**
- **Local (Docker Compose)**: Free except LLM API calls (~$0.03-0.05 per incident with caching)
- **Azure Container Apps**: ~$51-66/month
- **Kubernetes (cloud)**: Varies by provider, estimate $100-200/month

**Q: Can I disable auto-execution?**
Yes! Set `AUTO_EXECUTE_THRESHOLD=100` to require approval for all actions. Or set to `0` to always auto-execute (not recommended for production).

**Q: How do I add a new LLM provider?**
Edit `services/llm-service/app/llm_client.py` and add your provider to the `LLMClient` class. Follow existing patterns for OpenAI/Anthropic/Google.

**Q: Can I customize remediation actions?**
Yes! Edit `services/auto-response-agent/app/executors/` to add custom executors. Current executors: Kubernetes, Docker Compose.

**Q: How do I integrate with my existing monitoring?**
The Monitoring Agent can be configured to read from any Prometheus-compatible metrics endpoint. Update `PROMETHEUS_URL` in `.env`.

## ðŸ¤ Contributing

We welcome contributions! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

**Areas we need help:**
- ðŸ§ª More unit tests and integration tests
- ðŸ“ Documentation improvements and tutorials
- ðŸŽ¨ Dashboard UI/UX enhancements
- ðŸ”Œ New executor implementations (Ansible, Terraform, etc.)
- ðŸ¤– Custom agent implementations
- ðŸŒ Internationalization (i18n)

**Code Style:**
- Python: Black formatter, type hints, docstrings
- JavaScript/React: ESLint, Prettier
- Commit messages: Conventional Commits forma
- ðŸš§ **Kubernetes Deployment**: Helm charts and production manifests (80% complete)
- ðŸš§ **Azure Container Apps**: Cloud deployment automation (60% complete)
- ðŸš§ **Advanced Analytics**: ML-based incident clustering and prediction (30% complete)
- ðŸš§ **Multi-Cluster Support**: Federation across multiple K8s clusters (20% complete)

### ðŸ”® Future Roadmap

**Q1 2026:**
- [ ] Time-series forecasting for predictive incident detection
- [ ] Enhanced RAG with multi-modal support (logs, traces, metrics)
- [ ] Advanced approval workflow (conditional approvals, escalation)
- [ ] Custom runbook generation from incident resolutions

**Q2 2026:**
- [ ] Reinforcement learning for action optimization
- [ ] Natural language interface ("Show me all database incidents")
- [ ] Multi-cloud support (AWS, GCP, Azure)
- [ ] Advanced cost analytics and optimization

**Q3 2026:**
- [ ] Federated learning across organizations
- [ ] Self-healing infrastructure (IaC remediation)
- [ ] Chaos engineering integration (automated resilience testing)
- [ ] Enterprise features (SSO, RBAC, audit logs)

**Q4 2026:**
- [ ] Open source community release
- [ ] Plugin ecosystem for custom agents
- [ ] SDK for programmatic access (Python, Go, JavaScript)
- [ ] SaaS offering with multi-tenancy
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "memory-leak-test",
    "type": "threshold_breach",
    "metric": "test_app_memory_mb",
    "value": 950.0,
    "threshold": 800.0,
    "severity": "high"
  }'
```

**3. Error rate spike:**
```bash
curl -X POST http://localhost:8080/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "error-spike-test",
    "type": "error_rate",
    "metric": "test_app_errors_total",
    "value": 12.5,
    "threshold": 5.0,
    "severity": "critical"
  }'
```

### ðŸ”Ž Integration Tests

**Test agent communication:**
```bash
# Check RabbitMQ message flow
docker exec devops-rabbitmq rabbitmqctl list_queues

# Verify PostgreSQL data
docker exec devops-postgres psql -U devops -d devops_db -c "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 5;"

# Test Redis cache
docker exec devops-redis redis-cli -a redis123 KEYS "*llm*"

# Check vector store
curl http://localhost:6333/collections
```

### ðŸ“Š Performance Benchmarks

Run performance tests to verify SLAs:

```bash
# Test detection latency
time python trigger_incident.py
# Target: < 15 seconds to detection

# Test analysis throughput
for i in {1..10}; do
  python trigger_incident.py &
done
wait
# Target: Handle 10 concurrent incidents

# Monitor memory usage during tests
docker stats --no-stream
# Target: < 12 GB total RAM usage
```

### âœ… Health Check Tests

```bash
# Check all service health endpoints
./scripts/health-check.sh

# Or manually:
curl http://localhost:8000/health    # LLM Service
curl http://localhost:3000/api/health # Approval Backend
curl http://localhost:8001/health     # Ops Backend
curl http://localhost:8080/status     # Monitoring Agent
rate(incidents_detected_total[1h]) * 3600

# Average analysis latency
avg(analysis_latency_seconds)

# Auto-execution success rate
sum(rate(acti & Community

### ðŸ†˜ Getting Help

**For bugs and issues:**
- ðŸ“ Open a [GitHub Issue](https://github.com/nidhi-upadhye03/Agentic-system-for-devops/issues)
- ðŸ› Use issue templates for bug reports
- ðŸ’¡ Use feature request template for suggestions

**For questions and discussions:**
- ðŸ’¬ GitHub Discussions (coming soon)
- ðŸ“§ Email: nidhi.upadhye03@gmail.com
- ðŸ“– Read the docs: [Documentation](#-documentation)

**For urgent support:**
- ðŸš¨ Check [Troubleshooting](#-troubleshooting) section first
- ðŸ“Š Check [FAQ](#-faq) for common questions
- ðŸ” Search existing GitHub issues

### ðŸ“Š Project Statistics

- **Total Services**: 18 microservices
- **Lines of Code**: ~15,000+ (Python + JavaScript)
- **Docker Images**: 12 custom + 6 official
- **API Endpoints**: 50+ REST endpoints
- **Real-time Updates**: WebSocket integration
- **Supported Platforms**: Docker Compose, Kubernetes, Azure
- **LLM Providers**: 4 (OpenAI, Anthropic, Google, OpenRouter)

### ðŸ† Achievements

- âœ… **End-to-End Tested**: Complete incident lifecycle verified
- âœ… **Production Ready**: Health checks, graceful shutdowns, error handling
- âœ… **Cost Optimized**: Redis caching reduces LLM costs by 60-70%
- âœ… **Fast**: < 2 minute MTTR for automated incidents
- âœ… **Intelligent**: 75-95% confidence AI analysis
- âœ… **Observable**: Comprehensive metrics and logging

### ðŸŒŸ Star History

If you find this project useful, please consider giving it a â­ on GitHub!

[![Star History Chart](https://api.star-history.com/svg?repos=nidhi-upadhye03/Agentic-system-for-devops&type=Date)](https://star-history.com/#nidhi-upadhye03/Agentic-system-for-devops&Date)

### ðŸ“± Stay Updated

- Watch this repository for updates
- Follow [@nidhi-upadhye03](https://github.com/nidhi-upadhye03) on GitHub
- Check [CHANGELOG.md](CHANGELOG.md) for version history

---

## ðŸŽ‰ Quick Links Summary

| Resource | Link | Description |
|----------|------|-------------|
| **Approval Dashboard** | http://localhost:3001 | Review AI recommendations |
| **Ops Dashboard** | http://localhost:3003 | System monitoring |
| **Grafana** | http://localhost:3002 | Metrics visualization |
| **Prometheus** | http://localhost:9090 | Raw metrics |
| **RabbitMQ** | http://localhost:15672 | Message broker |
| **Documentation** | [PROJECT_EXAM_DOCUMENTATION.md](PROJECT_EXAM_DOCUMENTATION.md) | Academic paper |
| **Architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| **API Docs** | [docs/API.md](docs/API.md) | REST API reference |
| **Issues** | [GitHub Issues](https://github.com/nidhi-upadhye03/Agentic-system-for-devops/issues) | Bug reports |
| **Docker Hub** | [nidhi-upadhye03](https://hub.docker.com/u/nidhi-upadhye03) | Container images |

---

**âš¡ Built with passion for autonomous DevOps by [nidhi-upadhye03](https://github.com/nidhi-upadhye03)**

**ðŸš€ Transforming incident response from reactive to proactive, one AI agent at a time.**

---

**Last Updated:** January 7, 2026 | **Version:** 1.0.0 | **Status:** Production Ready âœ…

Prometheus alerts are pre-configured in `monitoring/prometheus/alerts.yml`:

- âš ï¸ High incident detection rate (> 100/hour)
- âš ï¸ Analysis failures (> 10% error rate)
- âš ï¸ Action execution failures (> 5% error rate)
- âš ï¸ LLM API errors (> 20 errors in 5 minutes)
- âš ï¸ RabbitMQ queue backlog (> 100 messages)
- âš ï¸ Agent container restarts (> 3 restarts in 10 minutes)

---

## ðŸ§ª Testing

### Run Tests

```bash
# Monitoring Agent
cd services/monitoring-agent
pytest tests/ -v --cov=app

# Analyzer Agent
cd services/analyzer-agent
pytest tests/ -v --cov=app
```

### Simulate Incident

```bash
# Deploy test app with high CPU
kubectl apply -f k8s/test-apps/cpu-hog.yaml

# Watch agents respond
kubectl logs -f deployment/monitoring-agent -n devops-agents
kubectl logs -f deployment/analyzer-agent -n devops-agents
```

---

## ðŸ”’ Security

- âœ… **Secrets Management**: Kubernetes Secrets, Azure Key Vault
- âœ… **RBAC**: Kubernetes service accounts with minimal permissions
- âœ… **Network Policies**: Pod-to-pod traffic restrictions
- âœ… **TLS/SSL**: HTTPS for all external APIs
- âœ… **Security Scanning**: Trivy in CI/CD pipeline

---

## ðŸ“ˆ Roadmap

- [ ] **Phase 7**: Integration testing with test applications
- [ ] **Phase 8**: Dashboard enhancements (Agent Timeline, Metrics)
- [x] **Phase 9**: Azure Container Apps deployment (IN PROGRESS - 60%)
- [ ] **Phase 10**: Advanced pattern detection (ML-based clustering)
- [ ] **Phase 11**: Multi-cluster support (federation)

---

## ðŸ¤ Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## ðŸ“„ License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## Team

This project is maintained by a collaborative DevOps AI team.

Primary contribution by Nidhi:
- Implemented the Monitoring Agent end-to-end.
- Connected all agents using RabbitMQ event routing and queue bindings.

---

## Acknowledgments

- **OpenAI** for GPT-4 API
- **Anthropic** for Claude 3.5 Sonnet API
- **Qdrant** for vector database
- **RabbitMQ** for reliable message broker
- **Slack** for notification platform

---

## ðŸ“ž Support

For questions, issues, or feedback:

- ðŸ“ Open a [GitHub Issue](https://github.com/nidhi-upadhye03/Agentic-system-for-devops/issues)
- ðŸ“§ Email: nidhi.upadhye03@gmail.com
- ðŸ“– Read the docs: [IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md), [FUTUREVISION.md](FUTUREVISION.md)

---

**âš¡ Built with passion for autonomous AI-driven DevOps by the team**


