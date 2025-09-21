"""
A2A Protocol Compliant AI Agent
Main FastAPI application for Google Cloud Run deployment
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import uuid
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="A2A AI Agent",
    description="Agent2Agent Protocol Compliant AI Agent",
    version="0.1.0"
)

# Mount static files for .well-known directory
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="well-known")

# In-memory task storage (for POC - use proper storage in production)
tasks: Dict[str, Dict] = {}

# Pydantic models for A2A protocol
class TaskRequest(BaseModel):
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# A2A Discovery endpoint - Agent Card
@app.get("/.well-known/agent.json")
async def get_agent_card():
    # This will be served by static files, but keeping as fallback
    try:
        with open(".well-known/agent.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent card not found")

# JSON-RPC endpoint for task requests
@app.post("/rpc")
async def handle_rpc_request(request: TaskRequest, background_tasks: BackgroundTasks):
    task_id = request.id or str(uuid.uuid4())

    # Initialize task
    tasks[task_id] = {
        "id": task_id,
        "status": "pending",
        "method": request.method,
        "params": request.params,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
        "progress": 0
    }

    # Start background task processing
    background_tasks.add_task(process_task, task_id)

    return {
        "jsonrpc": "2.0",
        "result": {
            "task_id": task_id,
            "status": "pending"
        },
        "id": request.id
    }

# Task status endpoint
@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(**tasks[task_id])

# Server-Sent Events for real-time updates
@app.get("/tasks/{task_id}/stream")
async def stream_task_updates(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_stream():
        while True:
            if task_id in tasks:
                task = tasks[task_id]
                data = json.dumps(task)
                yield f"data: {data}\n\n"

                if task["status"] in ["completed", "failed"]:
                    break

            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Background task processor
async def process_task(task_id: str):
    """Process tasks based on their method"""
    task = tasks[task_id]

    try:
        # Update status to running
        task["status"] = "running"
        task["progress"] = 10

        method = task["method"]
        params = task["params"]

        # Route to appropriate capability handler
        if method == "text.summarize":
            result = await handle_text_summarization(params)
        elif method == "text.analyze_sentiment":
            result = await handle_sentiment_analysis(params)
        elif method == "data.extract":
            result = await handle_data_extraction(params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        # Update task with result
        task["status"] = "completed"
        task["progress"] = 100
        task["result"] = result
        task["completed_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        task["status"] = "failed"
        task["error"] = str(e)
        task["failed_at"] = datetime.utcnow().isoformat()

# Capability handlers (mock implementations for POC)
async def handle_text_summarization(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock text summarization - replace with Vertex AI integration"""
    text = params.get("text", "")
    if not text:
        raise ValueError("Text parameter is required")

    # Simulate processing time
    await asyncio.sleep(2)

    # Mock summarization (replace with actual Vertex AI call)
    summary = f"Summary of {len(text)} characters: {text[:100]}..."

    return {
        "summary": summary,
        "original_length": len(text),
        "summary_length": len(summary),
        "compression_ratio": len(summary) / len(text)
    }

async def handle_sentiment_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock sentiment analysis - replace with Vertex AI integration"""
    text = params.get("text", "")
    if not text:
        raise ValueError("Text parameter is required")

    # Simulate processing time
    await asyncio.sleep(1.5)

    # Mock sentiment analysis
    return {
        "sentiment": "positive",
        "confidence": 0.85,
        "scores": {
            "positive": 0.85,
            "negative": 0.10,
            "neutral": 0.05
        }
    }

async def handle_data_extraction(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock data extraction - replace with Vertex AI integration"""
    text = params.get("text", "")
    schema = params.get("schema", {})

    if not text:
        raise ValueError("Text parameter is required")

    # Simulate processing time
    await asyncio.sleep(1)

    # Mock data extraction
    return {
        "extracted_data": {
            "entities": ["mock_entity_1", "mock_entity_2"],
            "dates": ["2025-09-21"],
            "locations": ["Google Cloud"]
        },
        "confidence": 0.92
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)