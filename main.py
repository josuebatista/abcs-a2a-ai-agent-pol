"""
A2A Protocol Compliant AI Agent
Main FastAPI application for Google Cloud Run deployment
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Literal, Union
from enum import Enum
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

# ============================================================================
# BEARER TOKEN AUTHENTICATION SETUP
# ============================================================================

# Initialize security scheme
security = HTTPBearer()

# Load and parse API keys from environment variable
API_KEYS: Dict[str, Dict[str, Any]] = {}
raw_api_keys = os.getenv("API_KEYS")

if raw_api_keys:
    try:
        # Parse JSON structure: {"key1": {"name": "User 1", "created": "...", "expires": null}, ...}
        API_KEYS = json.loads(raw_api_keys.strip())
        logger.info(f"✓ Loaded {len(API_KEYS)} API key(s) for authentication")

        # Log key names (not the actual keys)
        for key_token, key_info in API_KEYS.items():
            key_name = key_info.get('name', 'Unknown')
            key_prefix = key_token[:8] if len(key_token) >= 8 else key_token[:4]
            expires = key_info.get('expires', 'never')
            logger.info(f"  - Key for '{key_name}' ({key_prefix}...) expires: {expires}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse API_KEYS JSON: {e}")
        logger.warning("Authentication will be DISABLED due to invalid API_KEYS format")
        API_KEYS = {}
else:
    logger.warning("API_KEYS environment variable not set - authentication DISABLED")
    logger.warning("This is a security risk for production. Set API_KEYS to enable authentication.")

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    Verify Bearer token against configured API keys.
    Returns key metadata if valid, raises HTTPException if invalid.
    """
    token = credentials.credentials

    # Check if token exists in our API_KEYS
    if token not in API_KEYS:
        logger.warning(f"Authentication failed: Invalid token ({token[:8]}...)")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_info = API_KEYS[token]
    key_name = key_info.get('name', 'Unknown')

    # Check if key has expired
    expires = key_info.get('expires')
    if expires:
        try:
            from datetime import datetime
            expiry_date = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if datetime.utcnow() > expiry_date:
                logger.warning(f"Authentication failed: Expired token for '{key_name}'")
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            logger.error(f"Invalid expiry date format for key '{key_name}': {expires}")

    # Log successful authentication
    logger.info(f"✓ Authenticated request from: {key_name}")

    return key_info

# Optional: Dependency that only enforces auth if API_KEYS are configured
async def verify_token_optional(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - only enforces if API_KEYS are configured.
    Use this during migration period if needed.
    """
    # If no API keys configured, allow unauthenticated access
    if not API_KEYS:
        logger.debug("No API keys configured - allowing unauthenticated access")
        return None

    # If API keys are configured, require authentication
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await verify_token(credentials)

app = FastAPI(
    title="A2A AI Agent",
    description="Agent2Agent Protocol Compliant AI Agent",
    version="0.1.0"
)

# Mount static files for .well-known directory
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="well-known")

# In-memory task storage (for POC - use proper storage in production)
tasks: Dict[str, Dict] = {}

# A2A Protocol v0.3.0 Task States
class TaskState(str, Enum):
    """Complete task lifecycle states per A2A Protocol v0.3.0"""
    PENDING = "pending"              # Awaiting processing
    RUNNING = "running"              # Active execution
    INPUT_REQUIRED = "input-required"  # Awaiting user/client input (human-in-the-loop)
    AUTH_REQUIRED = "auth-required"    # Secondary credentials needed
    COMPLETED = "completed"          # Successful terminal state
    CANCELED = "canceled"            # User-terminated state
    REJECTED = "rejected"            # Agent declined execution
    FAILED = "failed"                # Error terminal state

# Pydantic models for A2A protocol
class TaskRequest(BaseModel):
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str  # All 8 TaskState values supported: pending, running, input-required, auth-required, completed, canceled, rejected, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None

# A2A Protocol v0.3.0 Message/Part Data Structures
class TextPart(BaseModel):
    """Text content part of a message"""
    type: Literal["text"] = "text"
    text: str

class FileWithUri(BaseModel):
    """File reference by URI"""
    uri: str
    mimeType: str

class FileWithBytes(BaseModel):
    """File with base64-encoded content"""
    bytes: str  # base64 encoded
    mimeType: str

class FilePart(BaseModel):
    """File part of a message"""
    type: Literal["file"] = "file"
    file: Union[FileWithUri, FileWithBytes]

class DataPart(BaseModel):
    """Structured data part of a message"""
    type: Literal["data"] = "data"
    data: Dict[str, Any]

# Union type for all part types
Part = Union[TextPart, FilePart, DataPart]

class Message(BaseModel):
    """A2A Protocol message with role and parts"""
    role: Literal["user", "agent"]
    parts: List[Dict[str, Any]]  # Using Dict for flexibility in parsing

class SendMessageParams(BaseModel):
    """Parameters for message/send RPC method"""
    message: Message
    taskId: Optional[str] = None
    streamingConfig: Optional[Dict[str, Any]] = None

class JsonRpcRequest(BaseModel):
    """Standard JSON-RPC 2.0 request"""
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Dict[str, Any]
    id: Union[str, int]

class JsonRpcResponse(BaseModel):
    """Standard JSON-RPC 2.0 response"""
    jsonrpc: Literal["2.0"] = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Union[str, int]

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

# A2A Discovery endpoint - Agent Card (v0.3.0 compliant)
@app.get("/.well-known/agent-card.json")
async def get_agent_card():
    # This will be served by static files, but keeping as fallback
    try:
        with open(".well-known/agent-card.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent card not found")

# Legacy endpoint for backwards compatibility (v0.2.1)
@app.get("/.well-known/agent.json")
async def get_agent_card_legacy():
    # Redirect to new endpoint
    try:
        with open(".well-known/agent-card.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent card not found")

# ============================================================================
# A2A Protocol v0.3.0 Core Methods
# ============================================================================

def determine_skill_from_message(text: str) -> str:
    """
    Determine which skill to invoke based on natural language message content.
    Uses keyword matching - could be enhanced with LLM-based intent classification.
    """
    text_lower = text.lower()

    # Summarization keywords
    summarization_keywords = [
        "summarize", "summary", "overview", "brief",
        "condense", "key points", "main points", "tldr",
        "give me a", "what are the"
    ]
    if any(keyword in text_lower for keyword in summarization_keywords):
        return "summarization"

    # Sentiment analysis keywords
    sentiment_keywords = [
        "sentiment", "tone", "emotion", "feeling",
        "positive", "negative", "analyze", "opinion",
        "how do", "what's the feeling"
    ]
    if any(keyword in text_lower for keyword in sentiment_keywords):
        return "sentiment-analysis"

    # Entity extraction keywords
    extraction_keywords = [
        "extract", "find", "identify", "entities",
        "names", "people", "organizations", "locations",
        "contacts", "pull out", "what organizations"
    ]
    if any(keyword in text_lower for keyword in extraction_keywords):
        return "entity-extraction"

    # Default to summarization if unclear
    logger.info(f"Could not determine skill from: '{text[:50]}...', defaulting to summarization")
    return "summarization"

def extract_max_length_from_text(text: str) -> Optional[int]:
    """Extract max_length parameter from natural language if specified"""
    import re

    patterns = [
        r'(?:in|maximum|max|up to|under)\s+(\d+)\s+words?',
        r'(\d+)\s+words?\s+(?:or less|maximum|max)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))

    return None  # Use default

async def handle_message_send(
    params: Dict[str, Any],
    auth: Dict[str, Any],
    background_tasks: BackgroundTasks,
    request_id: Union[str, int]
) -> Dict[str, Any]:
    """
    Handle message/send RPC method - the main entry point for A2A protocol.
    Accepts natural language messages and routes to appropriate skills.
    """
    try:
        # Parse and validate params
        send_params = SendMessageParams(**params)
        message = send_params.message
        task_id = send_params.taskId or str(uuid.uuid4())

        # Check Gemini configuration
        if not GEMINI_API_KEY or not GEMINI_MODEL:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error: AI capabilities not configured"
                },
                "id": request_id
            }

        # Extract text content from message parts
        text_content = ""
        for part in message.parts:
            if isinstance(part, dict):
                part_type = part.get("type")
                if part_type == "text":
                    text_content += part.get("text", "") + "\n"
                elif part_type == "file":
                    # TODO: Handle file parts (download URI or decode bytes)
                    logger.warning(f"File part handling not yet implemented")
                elif part_type == "data":
                    # TODO: Handle structured data parts
                    logger.warning(f"Data part handling not yet implemented")

        text_content = text_content.strip()

        if not text_content:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Invalid params: No text content found in message"
                },
                "id": request_id
            }

        # Determine skill/intent from message
        skill = determine_skill_from_message(text_content)

        # Create task
        tasks[task_id] = {
            "task_id": task_id,
            "status": TaskState.PENDING,
            "skill": skill,
            "message": text_content,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": auth.get('name', 'Unknown'),
            "result": None,
            "error": None,
            "progress": 0
        }

        logger.info(f"Task {task_id} created by '{auth.get('name')}' - Skill: {skill} (via message/send)")

        # Start background processing
        background_tasks.add_task(process_message_task, task_id)

        return {
            "jsonrpc": "2.0",
            "result": {
                "taskId": task_id,
                "status": TaskState.PENDING
            },
            "id": request_id
        }

    except Exception as e:
        logger.error(f"Error in handle_message_send: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": request_id
        }

async def process_message_task(task_id: str):
    """Process message-based task by routing to appropriate skill handler"""
    task = tasks[task_id]

    try:
        task["status"] = TaskState.RUNNING
        task["progress"] = 10

        skill = task["skill"]
        text = task["message"]

        # Route to existing handlers (these remain unchanged!)
        if skill == "summarization":
            max_length = extract_max_length_from_text(text) or 100
            result = await handle_text_summarization(
                {"text": text, "max_length": max_length},
                task
            )
        elif skill == "sentiment-analysis":
            result = await handle_sentiment_analysis({"text": text}, task)
        elif skill == "entity-extraction":
            result = await handle_data_extraction({"text": text}, task)
        else:
            raise ValueError(f"Unknown skill: {skill}")

        # Update task with result
        task["status"] = TaskState.COMPLETED
        task["progress"] = 100
        task["result"] = result
        task["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        task["status"] = TaskState.FAILED
        task["error"] = str(e)
        task["failed_at"] = datetime.utcnow().isoformat()

# ============================================================================
# A2A Protocol v0.3.0: tasks/list Method
# ============================================================================

async def handle_tasks_list(
    params: Dict[str, Any],
    auth: Dict[str, Any],
    request_id: Union[str, int]
) -> Dict[str, Any]:
    """
    Handle tasks/list RPC method - return paginated tasks for authenticated user.

    A2A Protocol v0.3.0 Specification:
    - Returns paginated list of tasks owned by the authenticated user
    - Supports filtering by status, skill
    - Default: 20 tasks per page, max 100
    """
    try:
        # Parse pagination parameters
        page = params.get("page", 1)
        limit = params.get("limit", 20)
        status_filter = params.get("status")  # Optional: "pending", "running", "completed", "failed", etc.
        skill_filter = params.get("skill")     # Optional: "summarization", "sentiment-analysis", "entity-extraction"

        # Validate pagination parameters
        if page < 1:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Invalid params: page must be >= 1"
                },
                "id": request_id
            }

        if limit < 1 or limit > 100:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Invalid params: limit must be between 1 and 100"
                },
                "id": request_id
            }

        # Get user's API key name for filtering
        user_name = auth.get('name', 'Unknown')

        # Filter tasks by user (only show tasks created by this user)
        user_tasks = [
            task for task in tasks.values()
            if task.get("created_by") == user_name
        ]

        # Apply status filter if provided
        if status_filter:
            user_tasks = [
                task for task in user_tasks
                if task.get("status") == status_filter
            ]

        # Apply skill filter if provided
        if skill_filter:
            user_tasks = [
                task for task in user_tasks
                if task.get("skill") == skill_filter or task.get("method") == skill_filter
            ]

        # Sort by creation time (newest first)
        user_tasks.sort(
            key=lambda t: t.get("created_at", ""),
            reverse=True
        )

        # Calculate pagination
        total_tasks = len(user_tasks)
        total_pages = (total_tasks + limit - 1) // limit  # Ceiling division
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit

        # Get paginated slice
        paginated_tasks = user_tasks[start_idx:end_idx]

        # Build response
        return {
            "jsonrpc": "2.0",
            "result": {
                "tasks": paginated_tasks,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "totalTasks": total_tasks,
                    "totalPages": total_pages,
                    "hasNextPage": page < total_pages,
                    "hasPreviousPage": page > 1
                },
                "filters": {
                    "status": status_filter,
                    "skill": skill_filter
                }
            },
            "id": request_id
        }

    except Exception as e:
        logger.error(f"Error in handle_tasks_list: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": request_id
        }

# ============================================================================
# JSON-RPC 2.0 Processing Logic (Shared by Root and Legacy Endpoints)
# ============================================================================

async def _process_rpc_request(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Core RPC request processing logic shared by both endpoints.

    Supports:
    - A2A Protocol v0.3.0 methods (message/send, tasks/list, tasks/get)
    - Legacy custom methods (text.summarize, text.analyze_sentiment, data.extract)

    Args:
        request: FastAPI Request object
        background_tasks: FastAPI BackgroundTasks for async processing
        auth: Authentication dictionary from verify_token

    Returns:
        JSON-RPC 2.0 response dictionary
    """
    # Log endpoint usage for monitoring
    endpoint_path = request.url.path
    logger.info(f"RPC request via {endpoint_path} from '{auth.get('name', 'Unknown')}'")

    try:
        # Parse JSON-RPC request
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        # Route to A2A Protocol v0.3.0 methods
        if method == "message/send":
            return await handle_message_send(params, auth, background_tasks, request_id)

        elif method == "tasks/get":
            # Implemented by /tasks/{task_id} endpoint but also available via RPC
            task_id = params.get("taskId")
            if not task_id or task_id not in tasks:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Invalid taskId"},
                    "id": request_id
                }
            return {
                "jsonrpc": "2.0",
                "result": tasks[task_id],
                "id": request_id
            }

        elif method == "tasks/list":
            # A2A Protocol v0.3.0: List paginated tasks for authenticated user
            return await handle_tasks_list(params, auth, request_id)

        # Legacy custom methods (backwards compatibility)
        elif method in ["text.summarize", "text.analyze_sentiment", "data.extract"]:
            logger.warning(f"⚠️  Using deprecated method '{method}'. Consider using 'message/send' per A2A v0.3.0")

            # Check if Gemini is configured
            if not GEMINI_API_KEY or not GEMINI_MODEL:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error: AI capabilities not configured"
                    },
                    "id": request_id
                }

            task_id = request_id or str(uuid.uuid4())

            # Initialize legacy task
            tasks[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "method": method,
                "params": params,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": auth.get('name', 'Unknown'),
                "result": None,
                "error": None,
                "progress": 0
            }

            logger.info(f"Task {task_id} created by '{auth.get('name')}' - Method: {method} (LEGACY)")

            # Start background task processing (legacy)
            background_tasks.add_task(process_task, task_id)

            return {
                "jsonrpc": "2.0",
                "result": {
                    "task_id": task_id,
                    "status": "pending"
                },
                "id": request_id
            }

        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }

    except json.JSONDecodeError:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": "Parse error: Invalid JSON"
            },
            "id": None
        }
    except Exception as e:
        logger.error(f"RPC error: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": body.get("id") if 'body' in locals() else None
        }

# ============================================================================
# JSON-RPC 2.0 Endpoints (Root + Legacy for Backwards Compatibility)
# ============================================================================

@app.post("/")
async def handle_rpc_request_root(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_token)
):
    """
    Primary JSON-RPC 2.0 endpoint at root path (A2A Protocol v0.3.0 standard).

    This is the primary endpoint for A2A Protocol compliance and ServiceNow integration.

    Supports:
    - A2A Protocol v0.3.0 methods: message/send, tasks/list, tasks/get
    - Legacy methods: text.summarize, text.analyze_sentiment, data.extract

    See: https://agent2agent.ai/protocol
    """
    return await _process_rpc_request(request, background_tasks, auth)

@app.post("/rpc")
async def handle_rpc_request_legacy(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_token)
):
    """
    Legacy JSON-RPC 2.0 endpoint (backwards compatibility only).

    ⚠️ DEPRECATED: Use root endpoint / for new integrations.
    This endpoint is maintained for backwards compatibility with existing clients.

    Supports:
    - A2A Protocol v0.3.0 methods: message/send, tasks/list, tasks/get
    - Legacy methods: text.summarize, text.analyze_sentiment, data.extract
    """
    return await _process_rpc_request(request, background_tasks, auth)

# Task status endpoint
@app.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    auth: Dict[str, Any] = Depends(verify_token)
):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(**tasks[task_id])

# Server-Sent Events for real-time updates
@app.get("/tasks/{task_id}/stream")
async def stream_task_updates(
    task_id: str,
    auth: Dict[str, Any] = Depends(verify_token)
):
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