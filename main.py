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

# Google Cloud AI imports
from google.cloud import aiplatform
from google.cloud import language_v1
import vertexai
from vertexai.preview.generative_models import GenerativeModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Vertex AI
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-project-id")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    logger.info(f"Vertex AI initialized for project: {PROJECT_ID}, location: {LOCATION}")
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI: {str(e)}")
    logger.warning("Application will start but AI capabilities may not work without proper GCP credentials")

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

# Capability handlers using Vertex AI
async def handle_text_summarization(params: Dict[str, Any]) -> Dict[str, Any]:
    """Text summarization using Natural Language API"""
    text = params.get("text", "")
    max_length = params.get("max_length", 100)

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) < 10:
        raise ValueError("Text must be at least 10 characters long")

    try:
        # Use a simple extractive summarization approach
        # For a production system, use a dedicated summarization model
        sentences = text.split('. ')

        # Calculate how many sentences to keep based on max_length
        words_per_sentence = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        target_sentences = max(1, int(max_length / words_per_sentence)) if words_per_sentence > 0 else 1
        target_sentences = min(target_sentences, len(sentences))

        # Take first N sentences as summary
        summary = '. '.join(sentences[:target_sentences])
        if not summary.endswith('.'):
            summary += '.'

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
    """Sentiment analysis using Google Cloud Natural Language API"""
    text = params.get("text", "")

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) > 5000:
        raise ValueError("Text must be 5000 characters or less")

    try:
        # Initialize Natural Language client
        client = language_v1.LanguageServiceClient()

        # Prepare the document
        document = language_v1.Document(
            content=text,
            type_=language_v1.Document.Type.PLAIN_TEXT
        )

        # Analyze sentiment
        response = client.analyze_sentiment(document=document)
        sentiment = response.document_sentiment

        # Determine overall sentiment classification
        if sentiment.score > 0.25:
            sentiment_label = "positive"
        elif sentiment.score < -0.25:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        # Calculate score distribution (normalized)
        positive_score = max(0, sentiment.score)
        negative_score = max(0, -sentiment.score)
        neutral_score = 1 - abs(sentiment.score)

        return {
            "sentiment": sentiment_label,
            "confidence": round(sentiment.magnitude, 2),
            "scores": {
                "positive": round(positive_score, 2),
                "negative": round(negative_score, 2),
                "neutral": round(neutral_score, 2)
            }
        }

    except Exception as e:
        logger.error(f"Sentiment analysis failed: {str(e)}")
        raise ValueError(f"Failed to analyze sentiment: {str(e)}")

async def handle_data_extraction(params: Dict[str, Any]) -> Dict[str, Any]:
    """Data extraction using Google Cloud Natural Language API entity recognition"""
    text = params.get("text", "")
    schema = params.get("schema", {})

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) > 10000:
        raise ValueError("Text must be 10000 characters or less")

    try:
        # Initialize Natural Language client
        client = language_v1.LanguageServiceClient()

        # Prepare the document
        document = language_v1.Document(
            content=text,
            type_=language_v1.Document.Type.PLAIN_TEXT
        )

        # Analyze entities
        response = client.analyze_entities(document=document)

        # Organize entities by type
        entities_by_type = {
            "persons": [],
            "locations": [],
            "organizations": [],
            "events": [],
            "dates": [],
            "phone_numbers": [],
            "emails": [],
            "other": []
        }

        total_salience = 0
        for entity in response.entities:
            entity_data = {
                "name": entity.name,
                "type": language_v1.Entity.Type(entity.type_).name,
                "salience": round(entity.salience, 3)
            }

            total_salience += entity.salience

            # Categorize entities
            entity_type = language_v1.Entity.Type(entity.type_).name
            if entity_type == "PERSON":
                entities_by_type["persons"].append(entity_data)
            elif entity_type == "LOCATION":
                entities_by_type["locations"].append(entity_data)
            elif entity_type == "ORGANIZATION":
                entities_by_type["organizations"].append(entity_data)
            elif entity_type == "EVENT":
                entities_by_type["events"].append(entity_data)
            elif entity_type == "DATE":
                entities_by_type["dates"].append(entity_data)
            elif entity_type == "PHONE_NUMBER":
                entities_by_type["phone_numbers"].append(entity_data)
            elif entity_type == "ADDRESS":
                entities_by_type["emails"].append(entity_data)
            else:
                entities_by_type["other"].append(entity_data)

        # Calculate average confidence
        entity_count = len(response.entities)
        avg_confidence = round(total_salience / entity_count, 2) if entity_count > 0 else 0.0

        # Remove empty categories
        extracted_data = {k: v for k, v in entities_by_type.items() if v}

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