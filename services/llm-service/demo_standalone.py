"""
Standalone LLM Service Demo - Runs without Docker!
Works without databases - just OpenAI/Gemini integration
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
from openai import OpenAI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="LLM Service - Standalone Demo",
    description="Simplified LLM service that works without Docker",
    version="1.0.0-demo"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not OPENAI_API_KEY and not GEMINI_API_KEY:
    logger.warning("⚠️  No API keys configured! Set OPENAI_API_KEY or GEMINI_API_KEY environment variable.")

openai_client = None
gemini_client = None

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("✅ OpenAI client initialized")

if GEMINI_API_KEY:
    gemini_client = OpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    logger.info("✅ Gemini client initialized")

# Pydantic models
class Message(BaseModel):
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    messages: List[Message]
    provider: Optional[str] = "openai"
    max_tokens: Optional[int] = 2000
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    response: str
    provider: str

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM Service - Standalone Demo",
        "version": "1.0.0-demo",
        "status": "running",
        "note": "This is a simplified version that works without Docker!",
        "configured_providers": {
            "openai": openai_client is not None,
            "gemini": gemini_client is not None
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chat": "/api/v1/chat"
        }
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "providers": {
            "openai": "configured" if openai_client else "not configured",
            "gemini": "configured" if gemini_client else "not configured"
        }
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat completion endpoint

    Simple chat with OpenAI or Gemini without database dependencies
    """
    try:
        # Select client
        if request.provider == "gemini" and gemini_client:
            client = gemini_client
            model = "gemini-2.0-flash-exp"
            provider = "gemini"
        elif openai_client:
            client = openai_client
            model = "gpt-4o-mini"  # Cheaper model for demo
            provider = "openai"
        else:
            raise HTTPException(
                status_code=503,
                detail="No LLM provider configured. Set OPENAI_API_KEY or GEMINI_API_KEY environment variable."
            )

        # Convert messages
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Call LLM
        logger.info(f"Calling {provider} with {len(messages)} messages")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        content = response.choices[0].message.content or ""
        logger.info(f"Got response from {provider}: {len(content)} characters")

        return ChatResponse(
            response=content,
            provider=provider
        )

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/demo")
async def demo_page():
    """Simple HTML demo page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LLM Service Demo</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .chat-box { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
            input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .response { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; white-space: pre-wrap; }
            .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <h1>🤖 LLM Service - Demo</h1>
        <div class="status success">
            ✅ Service is running! (Standalone mode - no Docker required)
        </div>

        <div class="chat-box">
            <h2>Chat with AI</h2>
            <textarea id="prompt" rows="4" placeholder="Enter your message here...">Hello! Tell me about Kubernetes in one sentence.</textarea>
            <button onclick="sendChat()">Send Message</button>
            <div id="response"></div>
        </div>

        <div class="chat-box">
            <h2>API Documentation</h2>
            <p>Interactive API docs: <a href="/docs" target="_blank">/docs</a></p>
            <p>Health check: <a href="/health" target="_blank">/health</a></p>
        </div>

        <script>
            async function sendChat() {
                const prompt = document.getElementById('prompt').value;
                const responseDiv = document.getElementById('response');

                responseDiv.innerHTML = '<div class="response">⏳ Thinking...</div>';

                try {
                    const response = await fetch('/api/v1/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            messages: [{ role: 'user', content: prompt }]
                        })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        responseDiv.innerHTML = `
                            <div class="response">
                                <strong>🤖 AI Response (${data.provider}):</strong><br><br>
                                ${data.response}
                            </div>
                        `;
                    } else {
                        responseDiv.innerHTML = `<div class="status error">❌ Error: ${data.detail}</div>`;
                    }
                } catch (error) {
                    responseDiv.innerHTML = `<div class="status error">❌ Error: ${error.message}</div>`;
                }
            }
        </script>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*60)
    print("🚀 LLM Service - Standalone Demo")
    print("="*60)
    print("\n📝 SETUP:")
    print("   Set your API key first:")
    print("   PowerShell:  $env:OPENAI_API_KEY='your-key-here'")
    print("   CMD:         set OPENAI_API_KEY=your-key-here")
    print("\n🌐 Access:")
    print("   Demo Page:    http://localhost:8000/demo")
    print("   API Docs:     http://localhost:8000/docs")
    print("   Health:       http://localhost:8000/health")
    print("\n💡 Features:")
    print("   ✅ Chat with OpenAI/Gemini")
    print("   ✅ Simple web interface")
    print("   ✅ No Docker required!")
    print("   ❌ No RAG (needs Qdrant)")
    print("   ❌ No async tasks (needs RabbitMQ)")
    print("\n" + "="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
