"""
LLM Service - FastAPI REST API for AI interactions
Provides endpoints for chat completions, RAG queries, and document ingestion
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import asyncio
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import pika
import json
import os

from app.llm_client import LLMClient, LLMConfig, LLMProvider
from app.rag_pipeline import RAGPipeline, RAGConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI LLM Service",
    description="Production-grade LLM service with RAG capabilities",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
request_counter = Counter('llm_requests_total', 'Total LLM requests', ['endpoint', 'provider'])
request_duration = Histogram('llm_request_duration_seconds', 'Request duration', ['endpoint'])
error_counter = Counter('llm_errors_total', 'Total errors', ['endpoint', 'error_type'])

# Initialize LLM client and RAG pipeline
llm_config = LLMConfig()
rag_config = RAGConfig()
llm_client = LLMClient(llm_config)
rag_pipeline = None  # Initialize lazily when needed

def get_rag_pipeline():
    """Get or create RAG pipeline instance"""
    global rag_pipeline
    if rag_pipeline is None:
        try:
            rag_pipeline = RAGPipeline(llm_client, rag_config)
            logger.info("RAG pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {e}")
            raise HTTPException(status_code=503, detail="RAG service unavailable - Qdrant not accessible")
    return rag_pipeline

# RabbitMQ connection (optional for task queue)
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672")

# Pydantic models
class Message(BaseModel):
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    messages: List[Message]
    provider: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    provider: str
    tokens_used: Optional[int] = None

class DocumentIngestRequest(BaseModel):
    text: str = Field(..., description="Document text to ingest")
    metadata: Optional[Dict[str, Any]] = None

class DocumentIngestResponse(BaseModel):
    chunks_created: int
    collection_name: str
    status: str

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="User question")
    system_prompt: Optional[str] = None
    top_k: Optional[int] = 5

class RAGQueryResponse(BaseModel):
    answer: str
    context_used: int
    provider: str

class RetrievalRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class RetrievalResponse(BaseModel):
    documents: List[Dict[str, Any]]
    count: int

class TaskRequest(BaseModel):
    task_type: str = Field(..., description="Type of async task")
    payload: Dict[str, Any] = Field(..., description="Task payload")

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# Dependency for RabbitMQ publishing
def get_rabbitmq_connection():
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue='llm_tasks', durable=True)
        return channel
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        return None

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness probe"""
    return {
        "status": "healthy",
        "service": "llm-service",
        "version": "1.0.0",
        "providers": {
            "openai": "configured" if LLMProvider.OPENAI in llm_client.available_providers else "not configured",
            "anthropic": "configured" if LLMProvider.ANTHROPIC in llm_client.available_providers else "not configured",
            "gemini": "configured" if LLMProvider.GEMINI in llm_client.available_providers else "not configured"
        }
    }

# Readiness check
@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes readiness probe"""
    try:
        # Test LLM client
        if not llm_client.available_providers:
            raise HTTPException(status_code=503, detail="No LLM providers configured")

        return {"status": "ready", "providers": len(llm_client.available_providers)}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Chat completion endpoint
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Get chat completion from LLM

    Supports both OpenAI and Gemini with automatic failover
    """
    try:
        with request_duration.labels(endpoint='chat').time():
            # Convert messages to dict format
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

            # Determine provider
            provider = None
            if request.provider:
                provider = LLMProvider(request.provider.lower())

            # Get completion
            response = llm_client.chat_completion(
                messages=messages,
                provider=provider,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            used_provider = provider or llm_config.preferred_provider
            request_counter.labels(endpoint='chat', provider=used_provider.value).inc()

            return ChatResponse(
                response=response.content,
                provider=used_provider.value,
                tokens_used=response.total_tokens
            )

    except Exception as e:
        error_counter.labels(endpoint='chat', error_type=type(e).__name__).inc()
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Streaming chat endpoint
@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat completion from LLM

    Returns Server-Sent Events (SSE) for real-time streaming
    """
    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        provider = LLMProvider(request.provider.lower()) if request.provider else None

        async def event_generator():
            try:
                async for chunk in llm_client.stream_completion(messages, provider):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        request_counter.labels(endpoint='chat_stream', provider='streaming').inc()
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        error_counter.labels(endpoint='chat_stream', error_type=type(e).__name__).inc()
        logger.error(f"Chat stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Document ingestion endpoint
@app.post("/api/v1/documents/ingest", response_model=DocumentIngestResponse)
async def ingest_document(request: DocumentIngestRequest):
    """
    Ingest a document into the vector store for RAG

    Chunks the document and creates embeddings
    """
    try:
        with request_duration.labels(endpoint='ingest').time():
            pipeline = get_rag_pipeline()
            chunks_created = pipeline.ingest_document(
                text=request.text,
                metadata=request.metadata
            )

            request_counter.labels(endpoint='ingest', provider='qdrant').inc()

            return DocumentIngestResponse(
                chunks_created=chunks_created,
                collection_name=rag_config.collection_name,
                status="success"
            )

    except Exception as e:
        error_counter.labels(endpoint='ingest', error_type=type(e).__name__).inc()
        logger.error(f"Document ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# RAG query endpoint
@app.post("/api/v1/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """
    Perform RAG query: retrieve context and generate answer

    Uses semantic search to find relevant documents before answering
    """
    try:
        with request_duration.labels(endpoint='rag_query').time():
            pipeline = get_rag_pipeline()
            answer = pipeline.rag_query(
                query=request.query,
                system_prompt=request.system_prompt,
                top_k=request.top_k
            )

            # Get documents for context count
            docs = pipeline.retrieve(request.query, request.top_k)

            request_counter.labels(endpoint='rag_query', provider='rag').inc()

            return RAGQueryResponse(
                answer=answer,
                context_used=len(docs),
                provider=llm_config.preferred_provider.value
            )

    except Exception as e:
        error_counter.labels(endpoint='rag_query', error_type=type(e).__name__).inc()
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Retrieval endpoint
@app.post("/api/v1/rag/retrieve", response_model=RetrievalResponse)
async def retrieve_documents(request: RetrievalRequest):
    """
    Retrieve relevant documents without generating an answer

    Useful for debugging or custom processing
    """
    try:
        with request_duration.labels(endpoint='retrieve').time():
            pipeline = get_rag_pipeline()
            documents = pipeline.retrieve(
                query=request.query,
                top_k=request.top_k
            )

            request_counter.labels(endpoint='retrieve', provider='qdrant').inc()

            return RetrievalResponse(
                documents=documents,
                count=len(documents)
            )

    except Exception as e:
        error_counter.labels(endpoint='retrieve', error_type=type(e).__name__).inc()
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Async task submission endpoint
@app.post("/api/v1/tasks/submit", response_model=TaskResponse)
async def submit_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Submit an async task to the message queue

    Tasks are processed by worker services
    """
    try:
        # Generate task ID
        import uuid
        task_id = str(uuid.uuid4())

        # Prepare task message
        task_message = {
            "task_id": task_id,
            "task_type": request.task_type,
            "payload": request.payload,
            "status": "pending"
        }

        # Publish to RabbitMQ
        channel = get_rabbitmq_connection()
        if channel:
            channel.basic_publish(
                exchange='',
                routing_key='llm_tasks',
                body=json.dumps(task_message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            channel.close()

            request_counter.labels(endpoint='submit_task', provider='rabbitmq').inc()

            return TaskResponse(
                task_id=task_id,
                status="queued",
                message=f"Task {task_id} submitted successfully"
            )
        else:
            raise HTTPException(status_code=503, detail="Task queue unavailable")

    except Exception as e:
        error_counter.labels(endpoint='submit_task', error_type=type(e).__name__).inc()
        logger.error(f"Task submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Collection management endpoints
@app.delete("/api/v1/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """
    Delete a vector collection (use with caution)

    Admin endpoint for collection management
    """
    try:
        if collection_name == rag_config.collection_name:
            pipeline = get_rag_pipeline()
            pipeline.delete_collection()
            return {"status": "success", "message": f"Collection {collection_name} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Collection not found")

    except Exception as e:
        logger.error(f"Collection deletion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/collections/info")
async def collection_info():
    """Get information about the current collection"""
    try:
        pipeline = get_rag_pipeline()
        collections = pipeline.qdrant_client.get_collections().collections
        current_collection = next(
            (c for c in collections if c.name == rag_config.collection_name),
            None
        )

        if current_collection:
            collection_info = pipeline.qdrant_client.get_collection(rag_config.collection_name)
            return {
                "name": rag_config.collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }
        else:
            return {"name": rag_config.collection_name, "status": "not_found"}

    except Exception as e:
        logger.error(f"Collection info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "AI LLM Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "chat": "/api/v1/chat",
            "chat_stream": "/api/v1/chat/stream",
            "ingest": "/api/v1/documents/ingest",
            "rag_query": "/api/v1/rag/query",
            "retrieve": "/api/v1/rag/retrieve",
            "submit_task": "/api/v1/tasks/submit"
        },
        "documentation": "/docs"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting LLM Service...")
    logger.info(f"Configured providers: {[p.value for p in llm_client.available_providers]}")
    logger.info(f"RAG pipeline will be initialized on first RAG request")
    logger.info("LLM Service ready!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down LLM Service...")

# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
