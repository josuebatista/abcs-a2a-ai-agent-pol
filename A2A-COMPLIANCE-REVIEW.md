# A2A Protocol v0.3.0 Compliance Review

**Review Date**: 2025-11-05
**Reviewer**: Claude (Sonnet 4.5)
**Protocol Version**: A2A v0.3.0
**Implementation Version**: v0.8.0
**Overall Status**: ⚠️ **PARTIAL COMPLIANCE - MAJOR GAPS**

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Critical Findings](#critical-findings)
3. [Compliance Matrix](#compliance-matrix)
4. [Detailed Analysis](#detailed-analysis)
5. [Recommendations by Priority](#recommendations-by-priority)
6. [Migration Path](#migration-path)
7. [Architectural Corrections](#architectural-corrections)

---

## Executive Summary

The current implementation is a **production-ready proof-of-concept** with excellent foundational work in authentication, deployment, and AI integration. However, it **significantly deviates from the official A2A Protocol v0.3.0 specification** in fundamental ways.

### Key Strengths ✅
- Excellent Bearer token authentication with multi-key support
- Proper agent discovery at `.well-known/agent-card.json`
- Production-ready Cloud Run deployment
- Real AI integration with Gemini 2.5 Flash
- Comprehensive documentation

### Critical Gaps 🔴
- **Custom RPC methods instead of standard A2A methods** (`message/send`, `message/stream`, etc.)
- **Missing Message/Part data structures** required by the protocol
- **Incomplete task state lifecycle** (4 of 8 required states)
- **Skills misused as RPC methods** instead of capability metadata

### Bottom Line
The implementation treats A2A as a **capability advertisement framework** with custom RPC methods. A2A is actually a **standardized messaging protocol** where all communication goes through `message/send` and `message/stream`, with skills being metadata for discovery only.

**Estimated effort for full compliance**: 3-4 weeks

---

## Critical Findings

### 🔴 CRITICAL ISSUE #1: Custom Methods Instead of Standard A2A RPC Methods

**Status**: Non-Compliant
**Location**: `main.py:332-376`
**Severity**: Critical - Breaks interoperability

#### What the Spec Requires

The A2A protocol defines **specific standard RPC methods** that all compliant agents must implement:

| Method | Purpose | Status |
|--------|---------|--------|
| `message/send` | Synchronous message transmission | ✗ Missing |
| `message/stream` | Streaming responses via SSE | ✗ Missing |
| `tasks/get` | Fetch task status | ✓ Partial |
| `tasks/list` | List paginated tasks | ✗ Missing |
| `tasks/cancel` | Terminate task execution | ✗ Missing |
| `tasks/resubscribe` | Resume streaming after disconnect | ✗ Missing |
| `agent/getAuthenticatedExtendedCard` | Retrieve authenticated card | ✗ Missing |

#### What the Implementation Does

Uses **custom skill-based methods**:
- `text.summarize`
- `text.analyze_sentiment`
- `data.extract`

#### Why This Is Wrong

The A2A protocol is **NOT** a framework for advertising custom AI capabilities as RPC methods. It's a **standard communication protocol** where:

1. **All communication** goes through `message/send` or `message/stream`
2. **Skills in agent card** are metadata for discovery (not method names)
3. **Primary agents** send natural language messages
4. **Secondary agents** interpret messages and route internally

#### Example of Correct Flow

```
Primary Agent (ServiceNow):
  1. Discovers agent via /.well-known/agent-card.json
  2. Sees "summarization" skill in capabilities
  3. Sends: POST /rpc
     {
       "jsonrpc": "2.0",
       "method": "message/send",
       "params": {
         "message": {
           "role": "user",
           "parts": [
             {"type": "text", "text": "Summarize this article: [content]"}
           ]
         }
       },
       "id": "req-1"
     }

Secondary Agent (Your Agent):
  1. Receives message/send
  2. Parses message parts
  3. Determines intent (summarization)
  4. Routes to Gemini handler internally
  5. Returns response with result
```

#### Required Fix

```python
# main.py - BEFORE (Wrong)
@app.post("/rpc")
async def handle_rpc_request(request: TaskRequest, ...):
    method = request.method  # "text.summarize", "text.analyze_sentiment", etc.
    if method == "text.summarize":
        result = await handle_text_summarization(params, task)
    # ...

# main.py - AFTER (Correct)
@app.post("/rpc")
async def handle_rpc_request(request: JsonRpcRequest, ...):
    method = request.method

    if method == "message/send":
        return await handle_message_send(request.params)
    elif method == "message/stream":
        return await handle_message_stream(request.params)
    elif method == "tasks/get":
        return await handle_tasks_get(request.params)
    elif method == "tasks/list":
        return await handle_tasks_list(request.params)
    elif method == "tasks/cancel":
        return await handle_tasks_cancel(request.params)
    else:
        return error_response(-32601, "Method not found")
```

---

### 🔴 CRITICAL ISSUE #2: Message/Part Structure Not Implemented

**Status**: Missing
**Location**: `main.py:229-232`
**Severity**: Critical - Required by spec

#### What the Spec Requires

All messages must use the **Message/Parts** structure:

```python
class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: List[Part]

# Part Types
class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str

class FilePart(BaseModel):
    type: Literal["file"] = "file"
    file: FileBase  # FileWithBytes or FileWithUri

class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: Dict[str, Any]
```

Example message:
```json
{
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "text",
        "text": "Analyze the sentiment of this review"
      },
      {
        "type": "file",
        "file": {
          "uri": "https://example.com/review.txt",
          "mimeType": "text/plain"
        }
      }
    ]
  }
}
```

#### What the Implementation Does

Accepts arbitrary `params` dictionaries:
```python
class TaskRequest(BaseModel):
    method: str
    params: Dict[str, Any]  # No structure validation
    id: Optional[str] = None
```

#### Required Fix

```python
# Add to main.py

from typing import Union, Literal
from pydantic import BaseModel, Field

# Part types
class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str

class FileWithUri(BaseModel):
    uri: str
    mimeType: str

class FileWithBytes(BaseModel):
    bytes: str  # base64 encoded
    mimeType: str

class FilePart(BaseModel):
    type: Literal["file"] = "file"
    file: Union[FileWithUri, FileWithBytes]

class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: Dict[str, Any]

Part = Union[TextPart, FilePart, DataPart]

class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: List[Part]

class SendMessageParams(BaseModel):
    message: Message
    taskId: Optional[str] = None

class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Dict[str, Any]
    id: Union[str, int]

# Handler
async def handle_message_send(params: SendMessageParams, auth: Dict):
    """Handle message/send RPC method"""
    message = params.message
    task_id = params.taskId or str(uuid.uuid4())

    # Extract text from parts
    text_content = ""
    for part in message.parts:
        if part.type == "text":
            text_content += part.text + "\n"
        elif part.type == "file":
            # Handle file part (download URI or decode bytes)
            pass
        elif part.type == "data":
            # Handle structured data
            pass

    # Determine intent and route to appropriate skill
    skill = determine_skill_from_message(text_content)

    # Create task
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "skill": skill,
        "message": text_content,
        "created_by": auth.get('name'),
        "result": None
    }

    # Process in background
    background_tasks.add_task(process_message_task, task_id)

    return {
        "jsonrpc": "2.0",
        "result": {
            "taskId": task_id,
            "status": "pending"
        },
        "id": request.id
    }
```

---

### 🔴 CRITICAL ISSUE #3: Skills Misused as RPC Method Names

**Status**: Non-Compliant
**Location**: `.well-known/agent-card.json:23-253`
**Severity**: High - Architectural misunderstanding

#### What the Spec Requires

Skills are **metadata for discovery** that describe capabilities:

```json
{
  "skills": [
    {
      "id": "summarization",
      "name": "Text Summarization",
      "description": "I can summarize long documents, articles, and reports into concise overviews",
      "tags": ["nlp", "text-processing", "summarization"],
      "examples": [
        "Summarize this article",
        "Give me a brief overview of this document",
        "What are the key points?"
      ]
    }
  ]
}
```

Skills are **NOT** invoked directly as RPC methods. They help primary agents understand what the secondary agent can do.

#### What the Implementation Does

Uses skill IDs as RPC method names:
```json
{
  "skills": [
    {
      "id": "text.summarize",  // Used as RPC method name - WRONG
      "name": "Text Summarization",
      "input": { /* schema */ },
      "output": { /* schema */ }
    }
  ]
}
```

Then invokes directly:
```bash
curl -X POST /rpc -d '{"method": "text.summarize", ...}'
```

#### Required Fix

**Agent Card** - Skills as capabilities:
```json
{
  "skills": [
    {
      "id": "summarization",
      "name": "Text Summarization",
      "description": "I can summarize text content of any length into concise overviews. Just ask me to 'summarize' or 'give an overview' of any text.",
      "tags": ["nlp", "text", "summarization", "content-analysis"],
      "examples": [
        "Summarize this article for me",
        "Give me a brief overview",
        "What are the main points?",
        "Condense this into a paragraph"
      ]
    },
    {
      "id": "sentiment-analysis",
      "name": "Sentiment Analysis",
      "description": "I can analyze the emotional tone and sentiment of text, identifying whether it's positive, negative, or neutral with confidence scores.",
      "tags": ["nlp", "sentiment", "emotion", "text-analysis"],
      "examples": [
        "What's the sentiment of this review?",
        "Analyze the tone of this message",
        "Is this feedback positive or negative?"
      ]
    },
    {
      "id": "entity-extraction",
      "name": "Entity Extraction",
      "description": "I can identify and extract key entities from text including people, organizations, locations, dates, events, and contact information.",
      "tags": ["nlp", "ner", "extraction", "entities"],
      "examples": [
        "Extract the names from this document",
        "What organizations are mentioned?",
        "Find all the contact details"
      ]
    }
  ]
}
```

**Code** - Intent detection:
```python
async def determine_skill_from_message(text: str) -> str:
    """Determine which skill to use based on message content"""
    text_lower = text.lower()

    # Simple keyword matching (could use LLM for better intent detection)
    if any(word in text_lower for word in ["summarize", "summary", "overview", "brief"]):
        return "summarization"
    elif any(word in text_lower for word in ["sentiment", "tone", "emotion", "feeling"]):
        return "sentiment-analysis"
    elif any(word in text_lower for word in ["extract", "find", "identify", "entities", "names"]):
        return "entity-extraction"
    else:
        # Default or use LLM to determine intent
        return "summarization"

async def process_message_task(task_id: str):
    """Process message-based task"""
    task = tasks[task_id]
    skill = task["skill"]
    text = task["message"]

    try:
        task["status"] = "running"

        if skill == "summarization":
            result = await handle_text_summarization({"text": text}, task)
        elif skill == "sentiment-analysis":
            result = await handle_sentiment_analysis({"text": text}, task)
        elif skill == "entity-extraction":
            result = await handle_data_extraction({"text": text}, task)

        task["status"] = "completed"
        task["result"] = result

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)
```

---

### 🟡 MAJOR ISSUE #4: Task State Lifecycle Incomplete

**Status**: Partially Compliant
**Location**: `main.py:236`
**Severity**: Medium - Missing required states

#### What the Spec Requires

Task states per `TaskState` enum:
- `pending` - Awaiting processing
- `running` - Active execution
- `input-required` - Awaiting user/client input (human-in-the-loop)
- `auth-required` - Secondary credentials needed
- `completed` - Successful terminal state
- `canceled` - User-terminated state
- `rejected` - Agent declined execution
- `failed` - Error terminal state

#### What the Implementation Has

```python
class TaskStatus(BaseModel):
    task_id: str
    status: str  # Only: "pending", "running", "completed", "failed"
```

**Missing**: `input-required`, `auth-required`, `canceled`, `rejected`

#### Required Fix

```python
# main.py

from typing import Literal

class TaskStatus(BaseModel):
    task_id: str
    status: Literal[
        "pending",
        "running",
        "input-required",
        "auth-required",
        "completed",
        "canceled",
        "rejected",
        "failed"
    ]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None

# Add tasks/cancel handler
async def handle_tasks_cancel(params: Dict, auth: Dict):
    """Handle tasks/cancel RPC method"""
    task_id = params.get("taskId")

    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    # Only allow canceling non-terminal states
    if task["status"] not in ["completed", "failed", "canceled", "rejected"]:
        task["status"] = "canceled"
        task["canceled_at"] = datetime.utcnow().isoformat()
        logger.info(f"Task {task_id} canceled by '{auth.get('name')}'")

    return {
        "jsonrpc": "2.0",
        "result": {
            "taskId": task_id,
            "status": task["status"]
        },
        "id": request.id
    }

# Add to RPC router
@app.post("/rpc")
async def handle_rpc_request(request: JsonRpcRequest, ...):
    # ...
    elif request.method == "tasks/cancel":
        return await handle_tasks_cancel(request.params, auth)
```

---

### 🟡 MAJOR ISSUE #5: Missing Core RPC Methods

**Status**: Non-Compliant
**Location**: `main.py:332`
**Severity**: High - Required for compliance

#### Missing Methods

| Method | Purpose | Difficulty |
|--------|---------|-----------|
| `message/stream` | SSE streaming responses | Medium |
| `tasks/list` | Paginated task listing | Low |
| `tasks/resubscribe` | Resume SSE after disconnect | Medium |
| `agent/getAuthenticatedExtendedCard` | Extended discovery | Low |

#### Required Implementation

```python
# tasks/list
async def handle_tasks_list(params: Dict, auth: Dict):
    """Handle tasks/list RPC method"""
    page = params.get("page", 1)
    limit = params.get("limit", 20)

    # Filter tasks by authenticated user
    user_tasks = [
        task for task in tasks.values()
        if task.get("created_by") == auth.get("name")
    ]

    # Paginate
    start = (page - 1) * limit
    end = start + limit
    paginated = list(user_tasks)[start:end]

    return {
        "jsonrpc": "2.0",
        "result": {
            "tasks": paginated,
            "page": page,
            "total": len(user_tasks)
        },
        "id": request.id
    }

# message/stream
async def handle_message_stream(params: Dict, auth: Dict):
    """Handle message/stream RPC method (SSE)"""
    message = Message(**params.get("message"))
    task_id = params.get("taskId") or str(uuid.uuid4())

    # Create task
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "message": extract_text_from_parts(message.parts),
        "created_by": auth.get("name")
    }

    # Start processing
    asyncio.create_task(process_message_task(task_id))

    # Return streaming response
    async def event_generator():
        while True:
            task = tasks.get(task_id)
            if not task:
                break

            # Send task update
            event_data = {
                "jsonrpc": "2.0",
                "result": {
                    "taskId": task_id,
                    "status": task["status"],
                    "progress": task.get("progress", 0),
                    "result": task.get("result")
                }
            }
            yield f"data: {json.dumps(event_data)}\n\n"

            if task["status"] in ["completed", "failed", "canceled"]:
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# agent/getAuthenticatedExtendedCard
async def handle_get_authenticated_extended_card(params: Dict, auth: Dict):
    """Handle agent/getAuthenticatedExtendedCard RPC method"""
    # Return extended agent card with user-specific info
    with open(".well-known/agent-card.json", "r") as f:
        agent_card = json.load(f)

    # Add authenticated user info
    agent_card["authenticatedUser"] = {
        "name": auth.get("name"),
        "created": auth.get("created")
    }

    return {
        "jsonrpc": "2.0",
        "result": agent_card,
        "id": request.id
    }
```

---

### 🟡 MAJOR ISSUE #6: Agent Card Schema Gaps

**Status**: Mostly Compliant with Gaps
**Location**: `.well-known/agent-card.json`
**Severity**: Medium - Missing recommended fields

#### What's Missing

1. **`preferredTransport`** field (recommended):
   ```json
   "preferredTransport": "JSONRPC"
   ```

2. **`supportsAuthenticatedExtendedCard`** (recommended):
   ```json
   "supportsAuthenticatedExtendedCard": false
   ```

3. **`additionalInterfaces`** (for multi-transport):
   ```json
   "additionalInterfaces": [
     {
       "transport": "REST",
       "url": "https://a2a-agent-hs6athqpoa-uc.a.run.app/v1"
     }
   ]
   ```

4. **`iconUrl`** (nice to have):
   ```json
   "iconUrl": "https://example.com/agent-icon.png"
   ```

#### Required Fix

Update `.well-known/agent-card.json:2-5`:
```json
{
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "supportsAuthenticatedExtendedCard": false,
  "name": "A2A AI Agent POC",
  "description": "Agent2Agent Protocol compliant AI agent with Gemini 2.5 Flash API capabilities for text summarization, sentiment analysis, and data extraction. Requires Bearer token authentication.",
  "url": "https://a2a-agent-hs6athqpoa-uc.a.run.app",
  ...
}
```

---

## Compliance Matrix

| Category | Requirement | Spec | Current | Status | Priority |
|----------|-------------|------|---------|--------|----------|
| **Core RPC Methods** | | | | | |
| | `message/send` | Required | ✗ Missing | 🔴 | P1 |
| | `message/stream` | Required | ✗ Missing | 🔴 | P1 |
| | `tasks/get` | Required | ✓ Partial (via /tasks/{id}) | 🟡 | P2 |
| | `tasks/list` | Required | ✗ Missing | 🔴 | P2 |
| | `tasks/cancel` | Required | ✗ Missing | 🔴 | P2 |
| | `tasks/resubscribe` | Optional | ✗ Missing | 🟡 | P3 |
| | `agent/getAuthenticatedExtendedCard` | Optional | ✗ Missing | 🟡 | P3 |
| **Data Structures** | | | | | |
| | Message | Required | ✗ Missing | 🔴 | P1 |
| | Parts (Text/File/Data) | Required | ✗ Missing | 🔴 | P1 |
| | Task States (8 types) | Required | Partial (4 of 8) | 🟡 | P2 |
| | JSON-RPC Request | Required | ✓ Present | 🟢 | - |
| | JSON-RPC Response | Required | ✓ Present | 🟢 | - |
| | JSON-RPC Error | Required | ✓ Present | 🟢 | - |
| **Agent Card** | | | | | |
| | `protocolVersion` | Required | ✓ 0.3.0 | 🟢 | - |
| | `name` | Required | ✓ Present | 🟢 | - |
| | `description` | Required | ✓ Present | 🟢 | - |
| | `url` | Required | ✓ Present | 🟢 | - |
| | `preferredTransport` | Recommended | ✗ Missing | 🟡 | P2 |
| | `version` | Required | ✓ Present | 🟢 | - |
| | `skills` | Required | ✓ Present (wrong usage) | 🟡 | P1 |
| | `capabilities` | Required | ✓ Present | 🟢 | - |
| | `securitySchemes` | Recommended | ✓ Present | 🟢 | - |
| | `endpoints` | Required | ✓ Present | 🟢 | - |
| | `supportsAuthenticatedExtendedCard` | Optional | ✗ Missing | 🟡 | P3 |
| **Transport** | | | | | |
| | JSON-RPC 2.0 | One required | ✓ Partial | 🟡 | P1 |
| | REST endpoints | Optional | ✗ Missing | ⚪ | P4 |
| | gRPC | Optional | ✗ Missing | ⚪ | - |
| **Security** | | | | | |
| | HTTPS/TLS | Required | ✓ Cloud Run | 🟢 | - |
| | Authentication | Required | ✓ Bearer tokens | 🟢 | - |
| | Authorization | Recommended | ✓ Per-key | 🟢 | - |
| | Credential in headers | Required | ✓ Authorization header | 🟢 | - |
| **Discovery** | | | | | |
| | `/.well-known/agent-card.json` | Required | ✓ Present | 🟢 | - |
| | Public access (no auth) | Required | ✓ Public | 🟢 | - |
| | RFC 8615 compliance | Required | ✓ Compliant | 🟢 | - |

**Legend**: 🟢 Compliant | 🟡 Partial | 🔴 Non-Compliant | ⚪ Optional/Not Applicable

**Compliance Score**: 14/28 Required (50%) | 8/28 Partial (29%) | 6/28 Missing (21%)

---

## Detailed Analysis

### What You Did Well ✅

#### 1. Bearer Token Authentication (v0.8.0)
**Location**: `main.py:123-214`

Excellent implementation with:
- Multi-key support with metadata (name, created, expires, notes)
- Proper OpenAPI 3.0 security schemes in agent card
- Per-key user tracking in logs
- Expiry date validation
- Graceful fallback when API_KEYS not set
- Secure storage in Google Cloud Secret Manager

**Example**:
```python
async def verify_token(credentials: HTTPAuthorizationCredentials):
    token = credentials.credentials
    if token not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid token")

    key_info = API_KEYS[token]
    # Check expiry
    expires = key_info.get('expires')
    if expires and datetime.utcnow() > datetime.fromisoformat(expires):
        raise HTTPException(status_code=401, detail="Token expired")

    logger.info(f"✓ Authenticated request from: {key_info.get('name')}")
    return key_info
```

This is **production-grade** security implementation.

---

#### 2. Agent Discovery
**Location**: `.well-known/agent-card.json`, `main.py:312-329`

Correct implementation:
- Proper RFC 8615 location: `/.well-known/agent-card.json`
- No authentication required (public discovery)
- Legacy endpoint for backward compatibility (`/agent.json`)
- Static file mounting with FastAPI

**Example**:
```python
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="well-known")

@app.get("/.well-known/agent.json")  # Legacy support
async def get_agent_card_legacy():
    with open(".well-known/agent-card.json", "r") as f:
        return json.load(f)
```

Perfect implementation of discovery pattern.

---

#### 3. Cloud Run Deployment
**Location**: `Dockerfile`, deployment docs

Excellent production practices:
- Non-root user for security
- Secret Manager integration for both Gemini API and auth keys
- Environment variable cleanup to prevent credential conflicts
- Health check endpoint
- Proper memory and timeout configuration
- Comprehensive troubleshooting documentation

**Example credential cleanup**:
```python
# CRITICAL: Clear Google Cloud credentials to prevent conflicts
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    logger.info("Clearing GOOGLE_APPLICATION_CREDENTIALS")
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

for env_var in ["GOOGLE_CLOUD_PROJECT", "GCP_PROJECT", "GCLOUD_PROJECT"]:
    if env_var in os.environ:
        del os.environ[env_var]
```

This shows deep understanding of Cloud Run deployment challenges.

---

#### 4. Gemini 2.5 Flash Integration
**Location**: `main.py:447-697`

Solid AI implementation:
- Latest model (`gemini-2.5-flash`)
- REST transport to avoid gRPC conflicts
- Async processing with timeouts
- Error handling with fallbacks
- Structured output with JSON parsing
- Regex fallback for entity extraction

**Example**:
```python
async def handle_sentiment_analysis(params: Dict, task: Dict = None):
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""Analyze sentiment and respond with ONLY JSON:
    {{"sentiment": "positive|negative|neutral", "confidence": 0.0-1.0, ...}}
    Text: {text}"""

    response = await asyncio.wait_for(
        asyncio.to_thread(model.generate_content, prompt),
        timeout=30.0
    )

    result_text = response.text.strip()
    result_text = result_text.replace('```json', '').replace('```', '').strip()
    result = json.loads(result_text)
    return result
```

Well-engineered with proper error handling.

---

#### 5. Documentation
**Location**: `README.md`, `AUTHENTICATION.md`, `CLAUDE.md`

Comprehensive documentation:
- Clear setup instructions
- Complete testing examples
- Troubleshooting guides
- Architecture explanations
- Security best practices
- Version history

This is **exemplary** for a proof-of-concept project.

---

### What Needs Fixing 🔧

#### 1. Protocol Architecture Misunderstanding

**The Core Problem**: The implementation treats A2A as a **capability advertisement framework** where each skill is a callable RPC method. This is incorrect.

**What A2A Actually Is**: A **messaging protocol** where:
- Primary agents send messages via standard `message/send`
- Skills are metadata for discovery only
- Secondary agents interpret messages and route internally
- All communication uses Message/Parts structure

**Visual Comparison**:

```
CURRENT IMPLEMENTATION (Wrong):
Primary Agent → [discovers skills] → calls custom method "text.summarize"
                                    → calls custom method "text.analyze_sentiment"

CORRECT A2A PROTOCOL:
Primary Agent → [discovers skills] → calls "message/send" with text
                                    → Secondary agent determines intent
                                    → Routes to appropriate handler
```

---

#### 2. Missing Standard Methods

The implementation needs these methods:

**message/send**:
```python
async def handle_message_send(params: SendMessageParams, auth: Dict):
    """Process user message and return task"""
    message = params.message
    task_id = params.taskId or str(uuid.uuid4())

    # Extract text from parts
    text = extract_text_from_parts(message.parts)

    # Determine skill from message
    skill = determine_skill_from_message(text)

    # Create and process task
    # ... (implementation details above)
```

**tasks/list**:
```python
async def handle_tasks_list(params: Dict, auth: Dict):
    """Return paginated task list for authenticated user"""
    # Filter by user, paginate, return
```

**tasks/cancel**:
```python
async def handle_tasks_cancel(params: Dict, auth: Dict):
    """Cancel running task"""
    task_id = params.get("taskId")
    if tasks[task_id]["status"] not in ["completed", "failed"]:
        tasks[task_id]["status"] = "canceled"
```

---

#### 3. Skills Rewrite

**Current** (`.well-known/agent-card.json:24-73`):
```json
{
  "id": "text.summarize",  // Wrong - used as RPC method
  "name": "Text Summarization",
  "input": { /* detailed schema */ },
  "output": { /* detailed schema */ }
}
```

**Should Be**:
```json
{
  "id": "summarization",
  "name": "Text Summarization",
  "description": "I can summarize long documents, articles, and reports into concise overviews. Simply ask me to 'summarize' or 'give an overview' of any text content.",
  "tags": ["nlp", "text-processing", "summarization", "content-analysis"],
  "examples": [
    "Summarize this article for me",
    "Give me a brief overview of this document",
    "What are the key points in this report?",
    "Condense this text into a few sentences"
  ]
}
```

Skills should be **human-readable capability descriptions**, not technical API specifications.

---

## Recommendations by Priority

### 🎯 Priority 1: Core Protocol Compliance (Critical)

**Estimated Effort**: 2-3 weeks
**Impact**: Critical - Required for A2A interoperability

#### Task 1.1: Implement Message/Part Data Structures

**Files**: `main.py:10-20` (new models)

```python
from typing import Union, Literal, List
from pydantic import BaseModel

class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str

class FileWithUri(BaseModel):
    uri: str
    mimeType: str

class FileWithBytes(BaseModel):
    bytes: str  # base64
    mimeType: str

class FilePart(BaseModel):
    type: Literal["file"] = "file"
    file: Union[FileWithUri, FileWithBytes]

class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: Dict[str, Any]

Part = Union[TextPart, FilePart, DataPart]

class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: List[Part]

class SendMessageParams(BaseModel):
    message: Message
    taskId: Optional[str] = None
    streamingConfig: Optional[Dict] = None
```

---

#### Task 1.2: Implement message/send Method

**Files**: `main.py:332-377` (refactor), new handler

```python
@app.post("/rpc")
async def handle_rpc_request(
    request: JsonRpcRequest,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_token)
):
    """Route JSON-RPC requests to appropriate handlers"""

    method = request.method
    params = request.params

    try:
        if method == "message/send":
            result = await handle_message_send(params, auth, background_tasks)
        elif method == "message/stream":
            return await handle_message_stream(params, auth)
        elif method == "tasks/get":
            result = await handle_tasks_get(params, auth)
        elif method == "tasks/list":
            result = await handle_tasks_list(params, auth)
        elif method == "tasks/cancel":
            result = await handle_tasks_cancel(params, auth)
        elif method == "tasks/resubscribe":
            result = await handle_tasks_resubscribe(params, auth)
        elif method == "agent/getAuthenticatedExtendedCard":
            result = await handle_get_authenticated_extended_card(params, auth)
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request.id
            }

        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request.id
        }

    except HTTPException as e:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": e.status_code,
                "message": e.detail
            },
            "id": request.id
        }
    except Exception as e:
        logger.error(f"RPC error: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {"detail": str(e)}
            },
            "id": request.id
        }

async def handle_message_send(
    params: Dict,
    auth: Dict,
    background_tasks: BackgroundTasks
) -> Dict:
    """Handle message/send RPC method"""

    # Validate and parse params
    send_params = SendMessageParams(**params)
    message = send_params.message
    task_id = send_params.taskId or str(uuid.uuid4())

    # Check Gemini configuration
    if not GEMINI_API_KEY or not GEMINI_MODEL:
        raise HTTPException(
            status_code=503,
            detail="AI capabilities not configured"
        )

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
        raise HTTPException(
            status_code=400,
            detail="No text content found in message"
        )

    # Determine skill/intent from message
    skill = determine_skill_from_message(text_content)

    # Create task
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "skill": skill,
        "message": text_content,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": auth.get('name', 'Unknown'),
        "result": None,
        "error": None,
        "progress": 0
    }

    logger.info(f"Task {task_id} created by '{auth.get('name')}' - Skill: {skill}")

    # Start background processing
    background_tasks.add_task(process_message_task, task_id)

    return {
        "taskId": task_id,
        "status": "pending"
    }

def determine_skill_from_message(text: str) -> str:
    """
    Determine which skill to use based on message content.
    Simple keyword matching - could be enhanced with LLM-based intent detection.
    """
    text_lower = text.lower()

    # Summarization keywords
    if any(word in text_lower for word in [
        "summarize", "summary", "overview", "brief",
        "condense", "key points", "main points", "tldr"
    ]):
        return "summarization"

    # Sentiment analysis keywords
    elif any(word in text_lower for word in [
        "sentiment", "tone", "emotion", "feeling",
        "positive", "negative", "analyze", "opinion"
    ]):
        return "sentiment-analysis"

    # Entity extraction keywords
    elif any(word in text_lower for word in [
        "extract", "find", "identify", "entities",
        "names", "people", "organizations", "locations", "contacts"
    ]):
        return "entity-extraction"

    else:
        # Default to summarization if unclear
        logger.info(f"Could not determine skill, defaulting to summarization")
        return "summarization"

async def process_message_task(task_id: str):
    """Process message-based task by routing to appropriate skill handler"""
    task = tasks[task_id]

    try:
        task["status"] = "running"
        task["progress"] = 10

        skill = task["skill"]
        text = task["message"]

        # Route to existing skill handlers
        if skill == "summarization":
            # Parse max_length from message if specified, else default
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
        task["status"] = "completed"
        task["progress"] = 100
        task["result"] = result
        task["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        task["status"] = "failed"
        task["error"] = str(e)
        task["failed_at"] = datetime.utcnow().isoformat()

def extract_max_length_from_text(text: str) -> Optional[int]:
    """Extract max_length parameter from natural language if specified"""
    import re

    # Look for patterns like "in 50 words", "maximum 100 words", etc.
    patterns = [
        r'(?:in|maximum|max|up to|under)\s+(\d+)\s+words?',
        r'(\d+)\s+words?\s+(?:or less|maximum|max)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))

    return None
```

---

#### Task 1.3: Rewrite Agent Card Skills

**Files**: `.well-known/agent-card.json:23-253`

Replace detailed input/output schemas with human-friendly descriptions:

```json
{
  "skills": [
    {
      "id": "summarization",
      "name": "Text Summarization",
      "description": "I can summarize long documents, articles, reports, and any text content into concise overviews. Simply ask me to 'summarize' or 'give an overview' and optionally specify a length (e.g., 'in 50 words').",
      "tags": ["nlp", "text-processing", "summarization", "content-analysis"],
      "examples": [
        "Summarize this article for me",
        "Give me a brief overview of this document in 100 words",
        "What are the key points in this report?",
        "Condense this text into a few sentences",
        "TL;DR of this content"
      ]
    },
    {
      "id": "sentiment-analysis",
      "name": "Sentiment Analysis",
      "description": "I can analyze the emotional tone and sentiment of text content, identifying whether it's positive, negative, or neutral. I provide confidence scores and detailed sentiment breakdowns.",
      "tags": ["nlp", "sentiment", "emotion", "text-analysis", "opinion-mining"],
      "examples": [
        "What's the sentiment of this review?",
        "Analyze the tone of this customer feedback",
        "Is this message positive or negative?",
        "How do people feel about this?",
        "Determine the emotional tone"
      ]
    },
    {
      "id": "entity-extraction",
      "name": "Entity Extraction",
      "description": "I can identify and extract key entities from text including people, organizations, locations, dates, events, phone numbers, and email addresses. Useful for processing documents and extracting structured information.",
      "tags": ["nlp", "ner", "named-entity-recognition", "extraction", "information-extraction"],
      "examples": [
        "Extract all the names from this document",
        "What organizations are mentioned here?",
        "Find all contact details in this email",
        "Identify people and places mentioned",
        "Pull out dates and events from this text"
      ]
    }
  ]
}
```

**Remove**: The detailed `input` and `output` schemas - these are not part of A2A spec for skills.

---

#### Task 1.4: Update Agent Card Metadata

**Files**: `.well-known/agent-card.json:2-16`

```json
{
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "supportsAuthenticatedExtendedCard": false,
  "name": "A2A AI Agent POC",
  "description": "Agent2Agent Protocol v0.3.0 compliant AI agent powered by Google Gemini 2.5 Flash. Provides natural language processing capabilities including text summarization, sentiment analysis, and entity extraction. Secured with Bearer token authentication.",
  "url": "https://a2a-agent-hs6athqpoa-uc.a.run.app",
  "version": "0.9.0",
  "provider": {
    "name": "ABCS A2A Agent POC",
    "url": "https://github.com/josuebatista/abcs-a2a-ai-agent-pol"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  ...
}
```

---

### 🎯 Priority 2: Complete Required Methods (High)

**Estimated Effort**: 1 week
**Impact**: High - Required for full compliance

#### Task 2.1: Implement tasks/list

```python
async def handle_tasks_list(params: Dict, auth: Dict) -> Dict:
    """Handle tasks/list RPC method - return paginated tasks for user"""

    page = params.get("page", 1)
    limit = params.get("limit", 20)
    status_filter = params.get("status")  # Optional filter

    # Filter tasks by authenticated user
    user_tasks = [
        task for task in tasks.values()
        if task.get("created_by") == auth.get("name")
    ]

    # Apply status filter if provided
    if status_filter:
        user_tasks = [t for t in user_tasks if t["status"] == status_filter]

    # Sort by creation time (newest first)
    user_tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)

    # Paginate
    start = (page - 1) * limit
    end = start + limit
    paginated = user_tasks[start:end]

    return {
        "tasks": paginated,
        "page": page,
        "limit": limit,
        "total": len(user_tasks),
        "hasMore": end < len(user_tasks)
    }
```

---

#### Task 2.2: Implement tasks/cancel

```python
async def handle_tasks_cancel(params: Dict, auth: Dict) -> Dict:
    """Handle tasks/cancel RPC method"""

    task_id = params.get("taskId")

    if not task_id:
        raise HTTPException(status_code=400, detail="taskId required")

    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    # Verify user owns this task
    if task.get("created_by") != auth.get("name"):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")

    # Only allow canceling non-terminal states
    terminal_states = ["completed", "failed", "canceled", "rejected"]
    if task["status"] in terminal_states:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in {task['status']} state"
        )

    # Cancel the task
    task["status"] = "canceled"
    task["canceled_at"] = datetime.utcnow().isoformat()

    logger.info(f"Task {task_id} canceled by '{auth.get('name')}'")

    return {
        "taskId": task_id,
        "status": "canceled"
    }
```

---

#### Task 2.3: Add All Task States

**Files**: `main.py:234-239`

```python
from enum import Enum

class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    INPUT_REQUIRED = "input-required"
    AUTH_REQUIRED = "auth-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    REJECTED = "rejected"
    FAILED = "failed"

class TaskStatus(BaseModel):
    task_id: str
    status: TaskState
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
```

---

### 🎯 Priority 3: Advanced Features (Medium)

**Estimated Effort**: 1-2 weeks
**Impact**: Medium - Improves functionality

#### Task 3.1: Implement message/stream (SSE)

```python
async def handle_message_stream(params: Dict, auth: Dict) -> StreamingResponse:
    """Handle message/stream RPC method - return SSE stream"""

    send_params = SendMessageParams(**params)
    message = send_params.message
    task_id = send_params.taskId or str(uuid.uuid4())

    # Extract text
    text = extract_text_from_parts(message.parts)
    skill = determine_skill_from_message(text)

    # Create task
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "skill": skill,
        "message": text,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": auth.get('name'),
        "result": None,
        "progress": 0
    }

    # Start processing in background
    asyncio.create_task(process_message_task(task_id))

    # Stream updates
    async def event_generator():
        last_status = None

        while True:
            if task_id not in tasks:
                break

            task = tasks[task_id]

            # Only send updates when task changes
            if task["status"] != last_status or task.get("progress") != task.get("last_progress"):
                event_data = {
                    "jsonrpc": "2.0",
                    "result": {
                        "taskId": task_id,
                        "status": task["status"],
                        "progress": task.get("progress", 0)
                    }
                }

                # Include result on completion
                if task["status"] == "completed" and task.get("result"):
                    event_data["result"]["result"] = task["result"]

                # Include error on failure
                if task["status"] == "failed" and task.get("error"):
                    event_data["result"]["error"] = task["error"]

                yield f"data: {json.dumps(event_data)}\n\n"

                last_status = task["status"]
                task["last_progress"] = task.get("progress")

            # Stop streaming on terminal states
            if task["status"] in ["completed", "failed", "canceled", "rejected"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

---

#### Task 3.2: Implement tasks/resubscribe

```python
async def handle_tasks_resubscribe(params: Dict, auth: Dict) -> StreamingResponse:
    """Handle tasks/resubscribe - resume streaming for existing task"""

    task_id = params.get("taskId")

    if not task_id:
        raise HTTPException(status_code=400, detail="taskId required")

    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    # Verify ownership
    if task.get("created_by") != auth.get("name"):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Stream from current state
    async def event_generator():
        # Send current state immediately
        event_data = {
            "jsonrpc": "2.0",
            "result": {
                "taskId": task_id,
                "status": task["status"],
                "progress": task.get("progress", 0)
            }
        }

        if task["status"] == "completed" and task.get("result"):
            event_data["result"]["result"] = task["result"]
        if task["status"] == "failed" and task.get("error"):
            event_data["result"]["error"] = task["error"]

        yield f"data: {json.dumps(event_data)}\n\n"

        # If terminal state, close immediately
        if task["status"] in ["completed", "failed", "canceled", "rejected"]:
            return

        # Otherwise continue streaming updates
        last_progress = task.get("progress")
        while True:
            await asyncio.sleep(0.5)

            if task_id not in tasks:
                break

            current_task = tasks[task_id]
            current_progress = current_task.get("progress", 0)

            if current_progress != last_progress or current_task["status"] != task["status"]:
                event_data = {
                    "jsonrpc": "2.0",
                    "result": {
                        "taskId": task_id,
                        "status": current_task["status"],
                        "progress": current_progress
                    }
                }

                if current_task["status"] == "completed":
                    event_data["result"]["result"] = current_task.get("result")
                if current_task["status"] == "failed":
                    event_data["result"]["error"] = current_task.get("error")

                yield f"data: {json.dumps(event_data)}\n\n"

                last_progress = current_progress
                task = current_task

            if current_task["status"] in ["completed", "failed", "canceled", "rejected"]:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

---

#### Task 3.3: Implement agent/getAuthenticatedExtendedCard

```python
async def handle_get_authenticated_extended_card(params: Dict, auth: Dict) -> Dict:
    """
    Handle agent/getAuthenticatedExtendedCard RPC method.
    Returns agent card with user-specific information.
    """

    # Load base agent card
    with open(".well-known/agent-card.json", "r") as f:
        agent_card = json.load(f)

    # Add authenticated user context
    agent_card["authenticatedUser"] = {
        "name": auth.get("name"),
        "keyCreated": auth.get("created"),
        "keyExpires": auth.get("expires")
    }

    # Add user-specific usage stats
    user_tasks = [
        task for task in tasks.values()
        if task.get("created_by") == auth.get("name")
    ]

    agent_card["userStats"] = {
        "totalTasks": len(user_tasks),
        "completedTasks": len([t for t in user_tasks if t["status"] == "completed"]),
        "failedTasks": len([t for t in user_tasks if t["status"] == "failed"])
    }

    return agent_card
```

Update agent card to indicate support:
```json
{
  "supportsAuthenticatedExtendedCard": true,
  ...
}
```

---

### 🎯 Priority 4: Optional Enhancements (Low)

**Estimated Effort**: 2-3 weeks
**Impact**: Low - Nice to have

#### Task 4.1: Add REST Transport Support

For clients that prefer REST over JSON-RPC:

```python
# Add REST-style endpoints
from fastapi import Query

@app.post("/v1/message:send")
async def rest_message_send(
    message: Message,
    taskId: Optional[str] = None,
    auth: Dict = Depends(verify_token)
):
    """REST endpoint for message/send"""
    return await handle_message_send(
        {"message": message, "taskId": taskId},
        auth,
        BackgroundTasks()
    )

@app.get("/v1/tasks/{task_id}")
async def rest_get_task(
    task_id: str,
    auth: Dict = Depends(verify_token)
):
    """REST endpoint for tasks/get"""
    return await handle_tasks_get({"taskId": task_id}, auth)

@app.get("/v1/tasks")
async def rest_list_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    auth: Dict = Depends(verify_token)
):
    """REST endpoint for tasks/list"""
    return await handle_tasks_list(
        {"page": page, "limit": limit, "status": status},
        auth
    )

@app.post("/v1/tasks/{task_id}:cancel")
async def rest_cancel_task(
    task_id: str,
    auth: Dict = Depends(verify_token)
):
    """REST endpoint for tasks/cancel"""
    return await handle_tasks_cancel({"taskId": task_id}, auth)

@app.get("/v1/card")
async def rest_get_card(auth: Dict = Depends(verify_token)):
    """REST endpoint for authenticated card"""
    return await handle_get_authenticated_extended_card({}, auth)
```

Update agent card:
```json
{
  "additionalInterfaces": [
    {
      "transport": "REST",
      "url": "https://a2a-agent-hs6athqpoa-uc.a.run.app/v1",
      "description": "RESTful HTTP+JSON interface"
    }
  ]
}
```

---

#### Task 4.2: Add Push Notification Support

For enterprise scenarios requiring webhooks:

```python
# Webhook configuration storage (use DB in production)
webhook_configs: Dict[str, Dict] = {}

async def handle_push_notification_config_set(params: Dict, auth: Dict) -> Dict:
    """Set webhook configuration for task notifications"""

    task_id = params.get("taskId")
    webhook_url = params.get("webhookUrl")
    events = params.get("events", ["completed", "failed"])

    if not task_id or not webhook_url:
        raise HTTPException(status_code=400, detail="taskId and webhookUrl required")

    config_id = str(uuid.uuid4())
    webhook_configs[config_id] = {
        "configId": config_id,
        "taskId": task_id,
        "webhookUrl": webhook_url,
        "events": events,
        "userId": auth.get("name"),
        "created": datetime.utcnow().isoformat()
    }

    return {
        "configId": config_id,
        "status": "active"
    }

async def notify_webhook(task_id: str):
    """Send webhook notification when task updates"""

    # Find webhooks for this task
    configs = [
        cfg for cfg in webhook_configs.values()
        if cfg["taskId"] == task_id
    ]

    if not configs:
        return

    task = tasks.get(task_id)
    if not task:
        return

    # Send to each webhook
    import httpx
    async with httpx.AsyncClient() as client:
        for config in configs:
            # Check if this event should trigger webhook
            if task["status"] in config["events"]:
                try:
                    await client.post(
                        config["webhookUrl"],
                        json={
                            "taskId": task_id,
                            "status": task["status"],
                            "result": task.get("result"),
                            "error": task.get("error")
                        },
                        timeout=10.0
                    )
                    logger.info(f"Webhook notified: {config['webhookUrl']}")
                except Exception as e:
                    logger.error(f"Webhook failed: {e}")

# Call from process_message_task when status changes
async def process_message_task(task_id: str):
    # ... existing code ...

    task["status"] = "completed"
    await notify_webhook(task_id)  # Add this
```

Update agent card:
```json
{
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,  // Changed
    "stateTransitionHistory": false
  }
}
```

---

## Migration Path

### Phase 1: Quick Wins (Week 1)

**Goal**: Fix agent card and add missing states

1. Add `preferredTransport: "JSONRPC"` to agent card
2. Add `supportsAuthenticatedExtendedCard: false`
3. Rewrite skills with human-friendly descriptions
4. Add all 8 task states to `TaskStatus` model
5. Update version to `0.9.0`

**Testing**:
```bash
# Verify agent card structure
curl -s $SERVICE_URL/.well-known/agent-card.json | \
  jq '{protocolVersion, preferredTransport, skills: (.skills | map(.id))}'
```

---

### Phase 2: Core Refactor (Weeks 2-3)

**Goal**: Implement standard A2A methods

1. Add Message/Part Pydantic models
2. Implement `message/send` handler
3. Implement skill detection logic
4. Update RPC router to handle standard methods
5. Implement `tasks/list` and `tasks/cancel`
6. Add comprehensive tests

**Testing**:
```bash
# Test message/send
curl -X POST $SERVICE_URL/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"type": "text", "text": "Summarize: AI is transforming industries."}
        ]
      }
    },
    "id": "test-1"
  }'

# Test tasks/list
curl -X POST $SERVICE_URL/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {"page": 1, "limit": 10},
    "id": "list-1"
  }'
```

---

### Phase 3: Advanced Features (Weeks 4-5)

**Goal**: Add streaming and extended card

1. Implement `message/stream` with SSE
2. Implement `tasks/resubscribe`
3. Implement `agent/getAuthenticatedExtendedCard`
4. Add file part handling (basic)
5. Update documentation

**Testing**:
```bash
# Test streaming
curl -N -X POST $SERVICE_URL/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Analyze sentiment: Great product!"}]
      }
    },
    "id": "stream-1"
  }'
```

---

### Phase 4: Polish & Deploy (Week 6)

**Goal**: Production deployment of v0.9.0

1. Update all documentation
2. Create compliance test suite
3. Deploy to Cloud Run
4. Run full test suite
5. Update README and CLAUDE.md

---

## Architectural Corrections

### Understanding the A2A Protocol

#### What A2A Is

A **standard messaging protocol** for agent-to-agent communication that:

1. **Provides interoperability** - Any primary agent can communicate with any secondary agent
2. **Uses standard methods** - All agents speak the same language (`message/send`, etc.)
3. **Enables discovery** - Agent cards describe capabilities in human-readable format
4. **Supports async operations** - Long-running tasks with status polling or streaming
5. **Secures communication** - Standard HTTPS + authentication schemes

#### What A2A Is NOT

- ❌ A framework for exposing custom RPC methods per capability
- ❌ An API gateway with skill-specific endpoints
- ❌ A capability advertisement system with technical schemas
- ❌ A replacement for internal routing logic

### The Correct Flow

```
┌─────────────────┐
│ Primary Agent   │
│ (ServiceNow)    │
└────────┬────────┘
         │ 1. Discover capabilities
         ├──GET─→ /.well-known/agent-card.json
         │
         │ 2. Send natural language message
         ├──POST→ /rpc (method: "message/send")
         │        {
         │          "message": {
         │            "role": "user",
         │            "parts": [
         │              {"type": "text", "text": "Summarize this..."}
         │            ]
         │          }
         │        }
         ▼
┌─────────────────┐
│ Your Agent      │
│                 │
│  ┌───────────┐  │
│  │ RPC Router│  │ 3. Route to message/send handler
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼──────┐ │ 4. Determine intent/skill
│  │   Intent   │ │    ("summarize" → summarization)
│  │  Detection │ │
│  └─────┬──────┘ │
│        │        │
│  ┌─────▼──────┐ │ 5. Route to internal handler
│  │  Gemini    │ │    (existing handle_text_summarization)
│  │  Handler   │ │
│  └─────┬──────┘ │
│        │        │
│  ┌─────▼──────┐ │ 6. Return result
│  │   Task     │ │
│  │   Store    │ │
│  └────────────┘ │
└─────────────────┘
```

### Key Principles

1. **One entry point** - All messages come through `message/send` or `message/stream`
2. **Internal routing** - Your agent determines which skill to use based on message content
3. **Skills = metadata** - They describe capabilities for discovery, not RPC method names
4. **Standard responses** - All responses follow JSON-RPC 2.0 format with taskId

---

## Testing & Validation

### A2A Compliance Test Suite

Create `test-a2a-compliance.sh`:

```bash
#!/bin/bash

SERVICE_URL="${1:-http://localhost:8080}"
API_KEY="${2}"

if [ -z "$API_KEY" ]; then
    echo "Usage: $0 <service_url> <api_key>"
    exit 1
fi

echo "=========================================="
echo "A2A Protocol v0.3.0 Compliance Test Suite"
echo "Service: $SERVICE_URL"
echo "=========================================="
echo

PASS=0
FAIL=0

test_case() {
    local name="$1"
    local command="$2"
    local validation="$3"

    echo -n "Testing: $name... "

    result=$(eval "$command" 2>&1)

    if echo "$result" | eval "$validation" > /dev/null 2>&1; then
        echo "✓ PASS"
        ((PASS++))
    else
        echo "✗ FAIL"
        echo "  Command: $command"
        echo "  Result: $result"
        ((FAIL++))
    fi
}

# Test 1: Agent Card Discovery
test_case \
    "Agent card at /.well-known/agent-card.json" \
    "curl -s $SERVICE_URL/.well-known/agent-card.json" \
    "jq -e '.protocolVersion == \"0.3.0\"'"

# Test 2: Protocol version
test_case \
    "Protocol version is 0.3.0" \
    "curl -s $SERVICE_URL/.well-known/agent-card.json" \
    "jq -e '.protocolVersion == \"0.3.0\"'"

# Test 3: Preferred transport
test_case \
    "Preferred transport declared" \
    "curl -s $SERVICE_URL/.well-known/agent-card.json" \
    "jq -e '.preferredTransport'"

# Test 4: Skills present
test_case \
    "Skills array present" \
    "curl -s $SERVICE_URL/.well-known/agent-card.json" \
    "jq -e '.skills | length > 0'"

# Test 5: Security schemes
test_case \
    "Security schemes declared" \
    "curl -s $SERVICE_URL/.well-known/agent-card.json" \
    "jq -e '.securitySchemes.bearerAuth'"

# Test 6: message/send method
test_case \
    "message/send method implemented" \
    "curl -s -X POST $SERVICE_URL/rpc \
        -H 'Authorization: Bearer $API_KEY' \
        -H 'Content-Type: application/json' \
        -d '{
            \"jsonrpc\": \"2.0\",
            \"method\": \"message/send\",
            \"params\": {
                \"message\": {
                    \"role\": \"user\",
                    \"parts\": [{\"type\": \"text\", \"text\": \"Hello\"}]
                }
            },
            \"id\": \"test-1\"
        }'" \
    "jq -e '.result.taskId'"

# Test 7: tasks/get method
TASK_ID=$(curl -s -X POST $SERVICE_URL/rpc \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Test"}]
            }
        },
        "id": "setup"
    }' | jq -r '.result.taskId')

test_case \
    "tasks/get method implemented" \
    "curl -s -X POST $SERVICE_URL/rpc \
        -H 'Authorization: Bearer $API_KEY' \
        -H 'Content-Type: application/json' \
        -d '{
            \"jsonrpc\": \"2.0\",
            \"method\": \"tasks/get\",
            \"params\": {\"taskId\": \"$TASK_ID\"},
            \"id\": \"test-get\"
        }'" \
    "jq -e '.result.taskId == \"$TASK_ID\"'"

# Test 8: tasks/list method
test_case \
    "tasks/list method implemented" \
    "curl -s -X POST $SERVICE_URL/rpc \
        -H 'Authorization: Bearer $API_KEY' \
        -H 'Content-Type: application/json' \
        -d '{
            \"jsonrpc\": \"2.0\",
            \"method\": \"tasks/list\",
            \"params\": {\"page\": 1, \"limit\": 10},
            \"id\": \"test-list\"
        }'" \
    "jq -e '.result.tasks'"

# Test 9: tasks/cancel method
test_case \
    "tasks/cancel method implemented" \
    "curl -s -X POST $SERVICE_URL/rpc \
        -H 'Authorization: Bearer $API_KEY' \
        -H 'Content-Type: application/json' \
        -d '{
            \"jsonrpc\": \"2.0\",
            \"method\": \"tasks/cancel\",
            \"params\": {\"taskId\": \"$TASK_ID\"},
            \"id\": \"test-cancel\"
        }'" \
    "jq -e '.result.status == \"canceled\"'"

# Test 10: Authentication required
test_case \
    "Authentication enforced on /rpc" \
    "curl -s -X POST $SERVICE_URL/rpc \
        -H 'Content-Type: application/json' \
        -d '{
            \"jsonrpc\": \"2.0\",
            \"method\": \"message/send\",
            \"params\": {\"message\": {\"role\": \"user\", \"parts\": []}},
            \"id\": \"unauth\"
        }'" \
    "jq -e '.error or .detail'"

echo
echo "=========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "=========================================="

if [ $FAIL -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi
```

Usage:
```bash
chmod +x test-a2a-compliance.sh
./test-a2a-compliance.sh https://your-agent.run.app your-api-key
```

---

## Summary & Next Steps

### Current State

**Strengths**:
- Production-ready infrastructure (Cloud Run, Secret Manager, authentication)
- Real AI capabilities with Gemini 2.5 Flash
- Excellent documentation and security practices

**Gaps**:
- Non-compliant RPC method structure
- Missing standard A2A methods
- Skills misused as RPC endpoints
- Incomplete task state machine

### Recommended Approach

**Option A: Full Compliance (Recommended)**
- Implement all Priority 1 & 2 tasks
- 3-4 weeks effort
- Full A2A v0.3.0 compliance
- Interoperable with any A2A primary agent

**Option B: Minimal Compliance**
- Implement only Priority 1 tasks
- 2 weeks effort
- Basic compliance with message/send
- May have limited interoperability

**Option C: Keep Current Architecture**
- Update agent card only
- 1 week effort
- Not A2A compliant but functional
- Custom integration required for each client

### Next Steps

1. **Review this assessment** with stakeholders
2. **Choose compliance level** based on requirements
3. **Create implementation plan** with timeline
4. **Set up development branch** for refactoring
5. **Implement changes incrementally** with testing
6. **Deploy v0.9.0** when ready

### Success Criteria

✅ All standard A2A methods implemented
✅ Message/Part structures working
✅ Skills used correctly as metadata
✅ All task states supported
✅ Compliance test suite passing 100%
✅ Documentation updated
✅ Deployed to production

---

**Questions or need clarification?** Reference specific sections by task number (e.g., "Task 1.2") for focused discussion.
