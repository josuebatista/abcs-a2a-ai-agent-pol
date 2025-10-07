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
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gemini AI imports
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CRITICAL: Clear Google Cloud credentials to prevent conflicts with API key auth
# This must be done BEFORE importing or using the Gemini SDK
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    logger.info("Clearing GOOGLE_APPLICATION_CREDENTIALS to prevent auth conflicts")
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

# Also clear other potential credential sources
for env_var in ["GOOGLE_CLOUD_PROJECT", "GCP_PROJECT", "GCLOUD_PROJECT"]:
    if env_var in os.environ:
        logger.info(f"Clearing {env_var}")
        del os.environ[env_var]

# Initialize Gemini API
raw_api_key = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = None
GEMINI_MODEL = None  # Will be set after successful initialization

# Aggressively clean the API key
if raw_api_key:
    # Log the raw state
    logger.info(f"Raw API key length: {len(raw_api_key)}")
    logger.info(f"Raw API key repr: {repr(raw_api_key[:10])}...")
    
    # Strip all whitespace and control characters
    cleaned_key = raw_api_key.strip().replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '')
    
    # Remove any non-ASCII characters
    cleaned_key = ''.join(c for c in cleaned_key if ord(c) < 128 and c.isprintable())
    
    # Final validation - API keys should be 39 chars
    if len(cleaned_key) == 39 and cleaned_key.startswith('AIza'):
        GEMINI_API_KEY = cleaned_key
        logger.info(f"✓ API key cleaned successfully (length: {len(GEMINI_API_KEY)})")
        logger.info(f"API key pattern: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:]}")
    else:
        logger.error(f"API key validation failed. Length: {len(cleaned_key)}, Starts with: {cleaned_key[:4] if len(cleaned_key) > 4 else 'too short'}")
        logger.error(f"Expected length: 39, got: {len(cleaned_key)}")
else:
    logger.error("GEMINI_API_KEY not found in environment variables")
    logger.error(f"Available env vars: {list(os.environ.keys())}")

if GEMINI_API_KEY:
    try:
        # IMPORTANT: Force REST transport to avoid gRPC metadata conflicts in Cloud Run
        logger.info("Configuring Gemini API with REST transport...")
        
        # Try configuring with REST transport (if supported in your SDK version)
        try:
            genai.configure(
                api_key=GEMINI_API_KEY,
                transport="rest"  # This forces REST instead of gRPC
            )
            logger.info("Configured with REST transport")
        except TypeError:
            # Fallback if transport parameter not supported
            logger.info("REST transport not supported, using default")
            genai.configure(api_key=GEMINI_API_KEY)
        
        # Test with a simple model
        test_model_name = "gemini-2.5-flash"
        logger.info(f"Testing with {test_model_name}...")
        
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": 2048,
        }
        
        test_model = genai.GenerativeModel(
            test_model_name,
            generation_config=generation_config
        )
        test_response = test_model.generate_content("Say OK")
        
        if test_response and test_response.text:
            GEMINI_MODEL = test_model_name
            logger.info(f"✓ SUCCESS: Gemini API working with {GEMINI_MODEL}")
            logger.info(f"Test response: {test_response.text[:50]}")
        else:
            logger.error("Model returned empty response")
            GEMINI_API_KEY = None
            
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        if "API_KEY_INVALID" in str(e) or "403" in str(e):
            logger.error("Authentication failed - likely credential conflict with Cloud Run")
        GEMINI_API_KEY = None
        GEMINI_MODEL = None
else:
    logger.warning("GEMINI_API_KEY not available. AI capabilities will not work.")
    GEMINI_MODEL = None

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
    # More detailed health check for debugging
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "gemini_configured": bool(GEMINI_API_KEY and GEMINI_MODEL),
        "model": GEMINI_MODEL,
        "api_key_loaded": bool(GEMINI_API_KEY),
        "model_selected": bool(GEMINI_MODEL)
    }
    
    # Add warning if not fully configured
    if not health_status["gemini_configured"]:
        health_status["warning"] = "AI capabilities not available"
        if not health_status["api_key_loaded"]:
            health_status["issue"] = "API key not loaded or invalid"
        elif not health_status["model_selected"]:
            health_status["issue"] = "Model initialization failed"
    
    return health_status

# Debug endpoint (remove in production)
@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration - REMOVE IN PRODUCTION"""
    return {
        "env_vars_present": {
            "GEMINI_API_KEY": "GEMINI_API_KEY" in os.environ,
            "GOOGLE_APPLICATION_CREDENTIALS": "GOOGLE_APPLICATION_CREDENTIALS" in os.environ,
            "PORT": os.environ.get("PORT", "not set"),
            "K_SERVICE": os.environ.get("K_SERVICE", "not set"),
            "K_REVISION": os.environ.get("K_REVISION", "not set"),
        },
        "api_key_cleaned": GEMINI_API_KEY is not None,
        "api_key_length": len(GEMINI_API_KEY) if GEMINI_API_KEY else 0,
        "model": GEMINI_MODEL,
        "model_initialized": GEMINI_MODEL is not None,
        "all_env_vars": list(os.environ.keys())
    }

# Test endpoint for Gemini
@app.get("/test/gemini")
async def test_gemini():
    """Test Gemini API directly"""
    try:
        if not GEMINI_MODEL:
            return {
                "success": False,
                "error": "Gemini not initialized",
                "model": None
            }
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content("Say 'Hello World'")
        
        return {
            "success": True,
            "model": GEMINI_MODEL,
            "response": response.text[:100] if response and response.text else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "model": GEMINI_MODEL,
            "error_type": type(e).__name__
        }

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
    # Check if Gemini is configured
    if not GEMINI_API_KEY or not GEMINI_MODEL:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error: AI capabilities not configured"
            },
            "id": request.id
        }
    
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
            result = await handle_text_summarization(params, task)
        elif method == "text.analyze_sentiment":
            result = await handle_sentiment_analysis(params, task)
        elif method == "data.extract":
            result = await handle_data_extraction(params, task)
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
async def handle_text_summarization(params: Dict[str, Any], task: Dict = None) -> Dict[str, Any]:
    """Text summarization using Gemini API"""
    text = params.get("text", "")
    max_length = params.get("max_length", 100)

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) < 10:
        raise ValueError("Text must be at least 10 characters long")

    try:
        if task:
            task["progress"] = 30
        
        # Initialize Gemini model - using cached configuration
        model = genai.GenerativeModel(GEMINI_MODEL)

        # Create prompt
        prompt = f"""Summarize the following text in approximately {max_length} words or less:

{text}"""

        if task:
            task["progress"] = 50
        
        # Generate summary with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=30.0
        )
        
        summary = response.text.strip()

        if task:
            task["progress"] = 90

        return {
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": round(len(summary) / len(text), 2),
            "model_used": GEMINI_MODEL
        }

    except asyncio.TimeoutError:
        raise ValueError("Request timed out after 30 seconds")
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        if "API_KEY_INVALID" in str(e):
            raise ValueError("API key authentication failed - possible credential conflict")
        raise ValueError(f"Failed to generate summary: {str(e)}")

async def handle_sentiment_analysis(params: Dict[str, Any], task: Dict = None) -> Dict[str, Any]:
    """Sentiment analysis using Gemini API"""
    text = params.get("text", "")

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) > 5000:
        raise ValueError("Text must be 5000 characters or less")

    try:
        if task:
            task["progress"] = 30
        
        # Initialize Gemini model with correct name
        model = genai.GenerativeModel(GEMINI_MODEL)

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

        if task:
            task["progress"] = 50

        # Generate analysis with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=30.0
        )
        
        result_text = response.text.strip()

        if task:
            task["progress"] = 70

        # Clean up JSON response (remove markdown code blocks if present)
        result_text = result_text.replace('```json', '').replace('```', '').strip()

        # Parse JSON response
        result = json.loads(result_text)
        result["model_used"] = GEMINI_MODEL

        if task:
            task["progress"] = 90

        return result

    except asyncio.TimeoutError:
        raise ValueError("Request timed out after 30 seconds")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {result_text}")
        raise ValueError(f"Failed to parse sentiment analysis response: {str(e)}")
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {str(e)}")
        raise ValueError(f"Failed to analyze sentiment: {str(e)}")

async def handle_data_extraction(params: Dict[str, Any], task: Dict = None) -> Dict[str, Any]:
    """Data extraction using Gemini API entity recognition"""
    text = params.get("text", "")
    schema = params.get("schema", {})

    if not text:
        raise ValueError("Text parameter is required")

    if len(text) > 10000:
        raise ValueError("Text must be 10000 characters or less")

    try:
        if task:
            task["progress"] = 30
        
        # Initialize Gemini model with correct name
        model = genai.GenerativeModel(GEMINI_MODEL)

        # More explicit prompt for valid JSON
        prompt = f"""Extract entities from the following text and return ONLY valid JSON.

Text: {text}

Return a JSON object with these keys (use empty arrays if no entities found):
- persons: array of {{"name": "...", "salience": 0.0-1.0}}
- locations: array of {{"name": "...", "salience": 0.0-1.0}}
- organizations: array of {{"name": "...", "salience": 0.0-1.0}}
- dates: array of {{"name": "...", "salience": 0.0-1.0}}
- events: array of {{"name": "...", "salience": 0.0-1.0}}
- phones: array of {{"name": "...", "salience": 0.0-1.0}}
- emails: array of {{"name": "...", "salience": 0.0-1.0}}

Example response format:
{{
  "persons": [{{"name": "John Doe", "salience": 0.9}}],
  "locations": [{{"name": "New York", "salience": 0.7}}],
  "organizations": [],
  "dates": [],
  "events": [],
  "phones": [],
  "emails": []
}}

Important: Return ONLY the JSON object, no markdown, no explanation, no code blocks."""

        if task:
            task["progress"] = 50

        # Generate entity extraction with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=30.0
        )
        
        result_text = response.text.strip()

        if task:
            task["progress"] = 70

        # Clean up JSON response more aggressively
        # Remove markdown code blocks if present
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        # Remove any text before the first {
        if '{' in result_text:
            result_text = result_text[result_text.index('{'):]
        
        # Remove any text after the last }
        if '}' in result_text:
            result_text = result_text[:result_text.rindex('}')+1]
        
        # Log the response for debugging
        logger.info(f"Gemini response (first 200 chars): {result_text[:200]}")

        try:
            # Parse JSON response
            extracted_data = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {result_text[:500]}")
            # Fallback: try to extract with regex or return empty structure
            extracted_data = {
                "persons": [],
                "locations": [],
                "organizations": [],
                "dates": [],
                "events": [],
                "phones": [],
                "emails": []
            }
            
            # Simple extraction fallback
            import re
            
            # Extract emails
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            if emails:
                extracted_data["emails"] = [{"name": email, "salience": 0.8} for email in emails]
            
            # Extract phone numbers
            phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
            if phones:
                extracted_data["phones"] = [{"name": phone, "salience": 0.7} for phone in phones]

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

        if task:
            task["progress"] = 90

        return {
            "extracted_data": extracted_data,
            "entity_count": entity_count,
            "confidence": avg_confidence,
            "model_used": GEMINI_MODEL
        }

    except asyncio.TimeoutError:
        raise ValueError("Request timed out after 30 seconds")
    except Exception as e:
        logger.error(f"Data extraction failed: {str(e)}")
        raise ValueError(f"Failed to extract data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)