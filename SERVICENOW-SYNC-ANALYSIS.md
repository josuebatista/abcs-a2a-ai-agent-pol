# ServiceNow Synchronous Mode Support - Analysis & Options

**Date**: 2025-12-05
**Issue**: ServiceNow cannot use A2A agents running in async mode, only sync mode
**Current Version**: v0.10.2 (async-only)

---

## Current Implementation Analysis

### How It Works Now (Async-Only)

**Flow**:
1. Client calls `message/send` → Returns **immediately** with `taskId` and `status: "pending"`
2. Task processes in **background** (via `BackgroundTasks`)
3. Client must **poll** `/tasks/{taskId}` or use **SSE streaming** to get result
4. AI processing takes 2-10 seconds

**Code Structure**:
```python
# Current: handle_message_send (main.py:458-550)
async def handle_message_send(...):
    # Create task
    tasks[task_id] = {"status": "pending", ...}

    # Process in background ← ASYNC
    background_tasks.add_task(process_message_task, task_id)

    # Return immediately ← CLIENT GETS PENDING TASK
    return {
        "result": {
            "taskId": task_id,
            "status": "pending"
        }
    }
```

**ServiceNow Problem**:
- ServiceNow expects the **result immediately** in the same response
- Cannot handle polling or SSE streaming
- Needs synchronous (blocking) response with completed result

---

## Options for ServiceNow Compatibility

### ⭐ Option 1: Add Synchronous Mode Parameter (RECOMMENDED)

**Concept**: Support both async and sync modes via optional parameter

**Implementation**:
```python
# Request with sync mode
{
  "method": "message/send",
  "params": {
    "message": {...},
    "synchronous": true  ← NEW PARAMETER
  }
}

# Response (sync mode) - waits for completion
{
  "result": {
    "taskId": "abc-123",
    "status": "completed",
    "result": {
      "summary": "AI generated content here...",
      ...
    }
  }
}
```

**Pros**:
- ✅ Backwards compatible (default async behavior unchanged)
- ✅ Single endpoint for both modes
- ✅ Clear opt-in via parameter
- ✅ ServiceNow sets `synchronous: true`
- ✅ Other clients continue using async mode

**Cons**:
- ⚠️ Sync requests block HTTP connection (2-10 seconds)
- ⚠️ Risk of timeout if AI takes too long
- ⚠️ Need to handle timeouts gracefully

**Implementation Effort**: Medium (2-3 hours)

---

### Option 2: Separate Synchronous Endpoint

**Concept**: Create dedicated endpoint for sync mode

**Implementation**:
```python
# New endpoint: /sync or /message/send/sync
POST /sync
{
  "method": "message/send",
  "params": {
    "message": {...}
  }
}

# Response - includes completed result
{
  "result": {
    "taskId": "abc-123",
    "status": "completed",
    "result": {...}
  }
}
```

**Pros**:
- ✅ Clear separation of sync vs async
- ✅ No risk of breaking existing clients
- ✅ Easy to configure different timeouts per endpoint
- ✅ ServiceNow uses `/sync`, others use `/`

**Cons**:
- ⚠️ Code duplication (similar logic in two places)
- ⚠️ More endpoints to maintain
- ⚠️ Agent card needs to advertise both endpoints

**Implementation Effort**: Medium (2-3 hours)

---

### Option 3: Auto-Detect Sync Mode (User-Agent Based)

**Concept**: Detect ServiceNow client and automatically use sync mode

**Implementation**:
```python
async def handle_message_send(..., request: Request):
    user_agent = request.headers.get("user-agent", "")

    # Auto-detect ServiceNow
    is_servicenow = "servicenow" in user_agent.lower()
    synchronous = is_servicenow

    if synchronous:
        # Wait for result
        await process_and_wait(task_id)
    else:
        # Background task
        background_tasks.add_task(...)
```

**Pros**:
- ✅ No client changes needed
- ✅ Automatic behavior based on client
- ✅ Transparent to ServiceNow

**Cons**:
- ❌ Fragile (relies on User-Agent header)
- ❌ Hard to debug/troubleshoot
- ❌ Not explicit in API contract
- ❌ Not A2A protocol compliant

**Implementation Effort**: Low (1 hour) but **NOT RECOMMENDED**

---

### Option 4: Timeout-Based Hybrid Mode

**Concept**: Wait briefly for fast completions, return async for slow ones

**Implementation**:
```python
async def handle_message_send(...):
    # Create task
    tasks[task_id] = {...}

    # Start processing
    background_tasks.add_task(process_message_task, task_id)

    # Wait up to 2 seconds
    for i in range(20):
        await asyncio.sleep(0.1)
        if tasks[task_id]["status"] == "completed":
            # Return result if completed quickly
            return {"result": tasks[task_id]}

    # Return pending if still processing
    return {"result": {"taskId": task_id, "status": "pending"}}
```

**Pros**:
- ✅ Fast tasks complete synchronously
- ✅ No breaking changes
- ✅ Gracefully falls back to async

**Cons**:
- ⚠️ Inconsistent behavior (sometimes sync, sometimes async)
- ⚠️ ServiceNow might not handle mixed mode well
- ⚠️ Hard to predict which mode will be used

**Implementation Effort**: Low (1-2 hours) but **NOT RELIABLE**

---

## Recommended Solution: Option 1 (Sync Mode Parameter)

### Why Option 1 is Best

1. **Clear & Explicit**: Client chooses mode via parameter
2. **Backwards Compatible**: Existing clients unaffected
3. **A2A Aligned**: Parameter-based behavior is common pattern
4. **ServiceNow Friendly**: ServiceNow can set `synchronous: true`
5. **Future-Proof**: Easy to extend with more options

### Implementation Plan

#### 1. Update Data Models

**File**: `main.py` (around line 290)

Add optional `synchronous` field to `SendMessageParams`:
```python
class SendMessageParams(BaseModel):
    message: Message
    taskId: Optional[str] = None
    streamingConfig: Optional[Dict[str, Any]] = None
    synchronous: Optional[bool] = False  ← NEW
```

#### 2. Modify `handle_message_send()`

**File**: `main.py:458-550`

**Current Logic**:
```python
# Create task
tasks[task_id] = {...}

# Process in background
background_tasks.add_task(process_message_task, task_id)

# Return pending
return {"result": {"taskId": task_id, "status": "pending"}}
```

**New Logic**:
```python
# Create task
tasks[task_id] = {...}

# Check if synchronous mode requested
if send_params.synchronous:
    # SYNC MODE: Wait for completion
    await process_message_task(task_id)

    # Return completed result
    return {
        "jsonrpc": "2.0",
        "result": tasks[task_id],  # Full task with result
        "id": request_id
    }
else:
    # ASYNC MODE: Background processing
    background_tasks.add_task(process_message_task, task_id)

    # Return pending
    return {
        "jsonrpc": "2.0",
        "result": {
            "taskId": task_id,
            "status": "pending"
        },
        "id": request_id
    }
```

#### 3. Add Timeout Protection

Wrap sync processing with timeout:
```python
if send_params.synchronous:
    try:
        # Wait max 60 seconds for completion
        await asyncio.wait_for(
            process_message_task(task_id),
            timeout=60.0
        )
        return {"result": tasks[task_id]}
    except asyncio.TimeoutError:
        # Graceful degradation
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Request timeout - task taking longer than 60s. Use async mode for long-running tasks."
            },
            "id": request_id
        }
```

#### 4. Update Agent Card

**File**: `.well-known/agent-card.json`

Add capabilities declaration:
```json
"capabilities": {
  "streaming": true,
  "pushNotifications": false,
  "stateTransitionHistory": false,
  "synchronousMode": true  ← NEW
}
```

#### 5. Update Documentation

**Files to Update**:
- `README.md` - Add synchronous mode examples
- `A2A-ASYNC-PATTERNS.md` - Add "Pattern 4: Synchronous Mode"
- Create `SERVICENOW-INTEGRATION-GUIDE.md`

---

## Implementation Details

### Code Changes Summary

**Files to Modify**:
1. `main.py` (3 changes):
   - Line 294: Add `synchronous` field to `SendMessageParams`
   - Line 458-550: Update `handle_message_send()` with sync/async branching
   - Add timeout handling for sync mode

2. `.well-known/agent-card.json`:
   - Add `synchronousMode: true` capability

3. Documentation (3 files):
   - `README.md` - Examples
   - `A2A-ASYNC-PATTERNS.md` - Pattern 4
   - New: `SERVICENOW-INTEGRATION-GUIDE.md`

**Estimated Lines Changed**: ~50 lines

---

## Testing Strategy

### Test 1: Async Mode (Default - Existing Behavior)
```bash
curl -X POST $SERVICE_URL/ \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Summarize: AI is great"}]
      }
    },
    "id": "test-async"
  }'

# Expected: {"result": {"taskId": "...", "status": "pending"}}
```

### Test 2: Sync Mode (New Behavior)
```bash
curl -X POST $SERVICE_URL/ \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Summarize: AI is great"}]
      },
      "synchronous": true
    },
    "id": "test-sync"
  }'

# Expected (after 2-5 seconds):
# {
#   "result": {
#     "taskId": "...",
#     "status": "completed",
#     "result": {
#       "summary": "AI is transformative...",
#       ...
#     }
#   }
# }
```

### Test 3: Sync Mode Timeout
```bash
# Test with request that takes > 60 seconds
# Expected: Timeout error with code -32603
```

---

## ServiceNow Configuration

Once implemented, ServiceNow should:

1. **Discovery**: Use agent card at `/.well-known/agent-card.json`
2. **Endpoint**: POST to `/` (root endpoint)
3. **Request Format**:
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Natural language request from ServiceNow"
        }
      ]
    },
    "synchronous": true  ← CRITICAL FOR SERVICENOW
  },
  "id": "servicenow-request-123"
}
```

4. **Response**: Will receive completed result immediately in response

---

## Risks & Mitigations

### Risk 1: HTTP Timeout
**Issue**: Client HTTP timeout < AI processing time
**Mitigation**:
- Set reasonable timeout (60s)
- Document timeout behavior
- Provide fallback error message
- Suggest async mode for long tasks

### Risk 2: Resource Exhaustion
**Issue**: Many sync requests block server threads
**Mitigation**:
- FastAPI handles async/await efficiently
- Cloud Run auto-scales
- Monitor concurrency metrics
- Set max timeout to prevent indefinite blocks

### Risk 3: Backwards Compatibility
**Issue**: Breaking existing clients
**Mitigation**:
- Default behavior unchanged (async)
- Sync is opt-in only
- Extensive testing before deployment

---

## Alternative: Option 2 (Separate Endpoint)

If Option 1 has issues, implement Option 2:

### Pros of Option 2
- Clearer separation
- Different timeout configs per endpoint
- No risk to existing async endpoint

### Implementation
```python
@app.post("/sync")
async def handle_sync_message(
    request: Request,
    auth: Dict[str, Any] = Depends(verify_token)
):
    """Synchronous message processing for ServiceNow compatibility"""
    body = await request.json()
    params = body.get("params", {})
    request_id = body.get("id")

    # Process synchronously
    send_params = SendMessageParams(**params)
    task_id = send_params.taskId or str(uuid.uuid4())

    # Create and process task
    tasks[task_id] = {...}

    try:
        await asyncio.wait_for(
            process_message_task(task_id),
            timeout=60.0
        )
        return {"jsonrpc": "2.0", "result": tasks[task_id], "id": request_id}
    except asyncio.TimeoutError:
        return {"jsonrpc": "2.0", "error": {...}, "id": request_id}
```

---

## Recommendation Summary

**Implement Option 1** (Synchronous Mode Parameter):
- ✅ Most flexible
- ✅ Backwards compatible
- ✅ Clear API contract
- ✅ Easy for ServiceNow to configure
- ✅ Aligns with A2A protocol patterns

**Timeline**:
- Implementation: 2-3 hours
- Testing: 1 hour
- Documentation: 1 hour
- **Total**: 4-5 hours

**Next Steps**:
1. Get user approval for Option 1
2. Implement synchronous mode parameter
3. Test locally with both modes
4. Deploy to Cloud Run
5. Provide ServiceNow configuration guide

---

## Questions for User

1. **Preference**: Do you prefer Option 1 (parameter) or Option 2 (separate endpoint)?
2. **Timeout**: Is 60 seconds reasonable for sync mode timeout?
3. **ServiceNow Testing**: Do you have access to ServiceNow test environment?
4. **Priority**: Should this be implemented immediately or can it wait?

---

## Conclusion

The current implementation is **async-only** which is incompatible with ServiceNow. Adding **synchronous mode support via parameter** (Option 1) is the best solution that:
- Solves ServiceNow's requirement
- Maintains backwards compatibility
- Follows A2A protocol patterns
- Is relatively easy to implement

Ready to proceed with implementation upon approval.
