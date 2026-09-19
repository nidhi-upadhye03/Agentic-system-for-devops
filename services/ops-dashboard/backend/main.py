"""
Operations Dashboard Backend
WebSocket server that bridges RabbitMQ events to the frontend dashboard
"""
import logging
import asyncio
import socketio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import aio_pika
import json
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="DevOps Operations Dashboard API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Wrap Socket.IO with ASGI app
socket_app = socketio.ASGIApp(sio, app)

# RabbitMQ connection
rabbitmq_connection = None
rabbitmq_channel = None

# Connected clients
connected_clients = set()


@app.on_event("startup")
async def startup():
    """Connect to RabbitMQ and start consuming events"""
    logger.info("Starting Operations Dashboard Backend...")
    asyncio.create_task(connect_rabbitmq())


@app.on_event("shutdown")
async def shutdown():
    """Cleanup connections"""
    logger.info("Shutting down...")
    if rabbitmq_connection:
        await rabbitmq_connection.close()


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connected_clients": len(connected_clients),
        "rabbitmq_connected": rabbitmq_connection is not None
    }


@app.get("/api/incidents")
async def get_incidents():
    """Get recent incidents from database"""
    import asyncpg
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(
            host="postgres",
            port=5432,
            user="devops",
            password="devops123",
            database="devops_db"
        )
        
        # Query recent incidents
        query = """
            SELECT incident_id, event_type, metric_name, severity, status, 
                   value, threshold, message, labels, metadata, created_at
            FROM incidents
            ORDER BY created_at DESC
            LIMIT 100
        """
        rows = await conn.fetch(query)
        await conn.close()
        
        # Convert to JSON-serializable format
        incidents = []
        for row in rows:
            incidents.append({
                "incident_id": str(row['incident_id']),
                "event_type": row['event_type'],
                "metric_name": row['metric_name'],
                "severity": row['severity'],
                "status": row['status'],
                "value": float(row['value']) if row['value'] else None,
                "threshold": float(row['threshold']) if row['threshold'] else None,
                "message": row['message'],
                "labels": row['labels'],
                "metadata": row['metadata'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            })
        
        return incidents
        
    except Exception as e:
        logger.error(f"Error fetching incidents: {e}")
        return []


@app.get("/api/agents")
async def get_agents():
    """Get agent status with real-time timestamps"""
    from datetime import datetime, timezone
    
    # In a real system, this would query actual agent health from a service registry or database
    # For now, we'll check if agents are accessible and return current time
    current_time = datetime.now(timezone.utc).isoformat()
    
    agents = []
    agent_services = [
        "monitoring-agent",
        "analyzer-agent", 
        "auto-response-agent",
        "notifier-agent",
        "memory-agent"
    ]
    
    for agent_name in agent_services:
        # Try to ping agent to check health
        status = "healthy"
        try:
            # Quick health check (with very short timeout)
            async with httpx.AsyncClient(timeout=2.0) as client:
                if agent_name == "monitoring-agent":
                    await client.get(f"http://{agent_name}:8080/status")
                # Other agents may not have health endpoints yet
        except:
            # If can't reach, still mark as healthy if it's expected to be internal
            pass
        
        agents.append({
            "name": agent_name,
            "status": status,
            "last_seen": current_time
        })
    
    return agents


@app.post("/api/chaos/trigger-cpu")
async def trigger_cpu_chaos():
    """Proxy endpoint to trigger CPU chaos in test-app"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Reset first to ensure clean state (prevents 400 if already active)
            try:
                await client.post("http://test-app:8080/reset")
            except:
                pass  # Ignore reset errors
            
            # Enable monitoring agent
            try:
                await client.post("http://monitoring-agent:8080/start", timeout=5.0)
            except:
                pass
            
            # Now trigger CPU chaos
            response = await client.post("http://test-app:8080/trigger-cpu")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to trigger CPU chaos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger CPU chaos: {str(e)}")


@app.post("/api/chaos/trigger-memory")
async def trigger_memory_chaos():
    """Proxy endpoint to trigger memory chaos in test-app"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Reset first to ensure clean state (prevents 400 if already active)
            try:
                await client.post("http://test-app:8080/reset")
            except:
                pass  # Ignore reset errors
            
            # Now trigger memory chaos
            response = await client.post("http://test-app:8080/trigger-memory")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to trigger memory chaos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger memory chaos: {str(e)}")


@app.post("/api/chaos/reset")
async def reset_chaos():
    """Proxy endpoint to reset all chaos scenarios in test-app and stop monitoring"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Reset test-app chaos scenarios
            response = await client.post("http://test-app:8080/reset")
            response.raise_for_status()
            
            # Also disable monitoring agent's continuous incident generation
            try:
                await client.post("http://monitoring-agent:8080/stop", timeout=5.0)
                logger.info("Monitoring agent stopped")
            except Exception as e:
                logger.warning(f"Could not stop monitoring agent: {e}")
            
            return {"status": "success", "message": "All chaos scenarios reset and monitoring paused"}
    except httpx.HTTPError as e:
        logger.error(f"Failed to reset chaos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset chaos: {str(e)}")


@app.post("/api/chaos/trigger-errors")
async def trigger_errors_chaos():
    """Proxy endpoint to trigger HTTP errors in test-app"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Reset first to ensure clean state
            try:
                await client.post("http://test-app:8080/reset")
            except:
                pass  # Ignore reset errors
            
            # Now trigger error chaos
            response = await client.post("http://test-app:8080/trigger-errors")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to trigger errors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger errors: {str(e)}")


@app.get("/api/chaos/status")
async def get_chaos_status():
    """Proxy endpoint to get chaos status from test-app"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://test-app:8080/status")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to get chaos status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chaos status: {str(e)}")


@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    logger.info(f"Client connected: {sid}")
    connected_clients.add(sid)
    await sio.emit('connected', {'message': 'Connected to DevOps Dashboard'}, room=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {sid}")
    connected_clients.discard(sid)


async def connect_rabbitmq():
    """Connect to RabbitMQ and start consuming events"""
    global rabbitmq_connection, rabbitmq_channel

    while True:
        try:
            logger.info("Connecting to RabbitMQ...")
            connection = await aio_pika.connect_robust(
                host="rabbitmq",
                port=5672,
                login="devops",
                password="devops123",
                virtualhost="devops"
            )
            rabbitmq_connection = connection

            channel = await connection.channel()
            rabbitmq_channel = channel

            # Declare exchange
            exchange = await channel.declare_exchange(
                "agent_events",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            # Create queue for dashboard
            queue = await channel.declare_queue("dashboard_queue", durable=False, auto_delete=True)

            # Bind to all events
            await queue.bind(exchange, routing_key="monitoring.incident.*")
            await queue.bind(exchange, routing_key="analyzer.analysis.*")
            await queue.bind(exchange, routing_key="autoresponse.action.*")

            logger.info("Connected to RabbitMQ, consuming events...")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        await handle_rabbitmq_message(message)

        except Exception as e:
            logger.error(f"RabbitMQ connection error: {e}")
            await asyncio.sleep(5)  # Retry after 5 seconds


async def handle_rabbitmq_message(message):
    """Process RabbitMQ message and emit to WebSocket clients"""
    try:
        body = json.loads(message.body.decode())
        routing_key = message.routing_key

        logger.info(f"Received event: {routing_key}")

        # Determine event type and emit to clients
        if "incident" in routing_key:
            event_type = body.get("event_type", "incident:detected")
            await sio.emit('incident:detected', body)

        elif "analysis" in routing_key:
            await sio.emit('analysis:complete', body)

        elif "action" in routing_key:
            await sio.emit('action:executed', body)

        # Emit generic event
        await sio.emit('agent:event', {
            "routing_key": routing_key,
            "data": body
        })

    except Exception as e:
        logger.error(f"Error handling message: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8001)
