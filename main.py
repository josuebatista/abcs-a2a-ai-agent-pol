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
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gemini AI imports
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {str(e)}")
        logger.warning("Application will start but AI capabilities may not work without proper API key")
else:
    logger.warning("GEMINI_API_KEY not set. AI capabilities will not work.")

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
        "task_id": task_id,
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

# Capability handlers using Gemini API
async def handle_text_summarization(params: Dict[str, Any]) -> Dict[str, Any]:
    """Text summarization using Gemini API"""
    text = params.get("text", "")
    max_length = params.get("max_length", 100)

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) < 10:
        raise ValueError("Text must be at least 10 characters long")

    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-pro-latest')

        # Create prompt
        prompt = f"""Summarize the following text in approximately {max_length} words or less:

{text}"""

        # Generate summary
        response = model.generate_content(prompt)
        summary = response.text.strip()

        return {
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": round(len(summary) / len(text), 2)
        }

    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        raise ValueError(f"Failed to generate summary: {str(e)}")

async def handle_sentiment_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sentiment analysis using Gemini API"""
    text = params.get("text", "")

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) > 5000:
        raise ValueError("Text must be 5000 characters or less")

    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-pro-latest')

        # Create prompt for structured sentiment analysis
        prompt = f"""Analyze the sentiment of the following text and respond with ONLY a JSON object in this exact format:
{{
    "sentiment": "positive" or "negative" or "neutral",
    "confidence": a number between 0 and 1,
    "scores": {{
        "positive": a number between 0 and 1,
        "negative": a number between 0 and 1,
        "neutral": a number between 0 and 1
    }}
}}

Text: {text}"""

        # Generate analysis
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Clean up JSON response (remove markdown code blocks if present)
        result_text = result_text.replace('```json', '').replace('```', '').strip()

        # Parse JSON response
        result = json.loads(result_text)

        return result

    except Exception as e:
        logger.error(f"Sentiment analysis failed: {str(e)}")
        raise ValueError(f"Failed to analyze sentiment: {str(e)}")

async def handle_data_extraction(params: Dict[str, Any]) -> Dict[str, Any]:
    """Data extraction using Gemini API entity recognition"""
    text = params.get("text", "")
    schema = params.get("schema", {})

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) > 10000:
        raise ValueError("Text must be 10000 characters or less")

    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-pro-latest')

        # Create prompt for entity extraction
        prompt = f"""Extract the entities from the following text.
Recognize the following entity types:
- Persons
- Locations
- Organizations
- Dates
- Events
- Phone numbers
- Emails

Return the result as a JSON object with keys matching the entity types above (lowercase, plural).
Each entity should have "name" and "salience" (a number between 0 and 1 indicating importance).

Example format:
{{
    "persons": [{{"name": "John Doe", "salience": 0.8}}],
    "locations": [{{"name": "New York", "salience": 0.6}}],
    "organizations": [{{"name": "Acme Inc.", "salience": 0.7}}]
}}

Text: {text}"""

        # Generate entity extraction
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Clean up JSON response (remove markdown code blocks if present)
        result_text = result_text.replace('```json', '').replace('```', '').strip()

        # Parse JSON response
        extracted_data = json.loads(result_text)

        # Calculate entity count and average confidence
        entity_count = 0
        total_salience = 0.0

        for entity_type, entities in extracted_data.items():
            if isinstance(entities, list):
                entity_count += len(entities)
                for entity in entities:
                    if isinstance(entity, dict) and 'salience' in entity:
                        total_salience += entity.get('salience', 0)

        avg_confidence = round(total_salience / entity_count, 2) if entity_count > 0 else 0.0

        return {
            "extracted_data": extracted_data,
            "entity_count": entity_count,
            "confidence": avg_confidence
        }

    except Exception as e:
        logger.error(f"Data extraction failed: {str(e)}")
        raise ValueError(f"Failed to extract data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)