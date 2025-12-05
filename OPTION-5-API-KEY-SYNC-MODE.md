# Option 5: API Key-Based Synchronous Mode - RECOMMENDED ⭐

**Date**: 2025-12-05
**Version**: v0.10.3 (planned)
**Status**: Implementation Ready

---

## Executive Summary

**Problem**: ServiceNow cannot use A2A agents running in async mode, only sync mode. ServiceNow cannot be modified to send a `synchronous: true` parameter.

**Solution**: Store sync/async preference **in the API key metadata** itself. When ServiceNow authenticates, the agent automatically detects the mode from the API key and behaves accordingly.

**Key Benefit**: **Zero ServiceNow changes needed** - all configuration is server-side.

---

## Why Option 5 is Best

### Comparison with Other Options

| Option | ServiceNow Changes | Implementation | Maintainability |
|--------|-------------------|----------------|-----------------|
| 1. Parameter | ❌ Requires parameter | Medium | Good |
| 2. Separate Endpoint | ❌ Requires URL change | Medium | Fair |
| 3. User-Agent Detection | ❌ Fragile/implicit | Low | Poor |
| 4. Timeout Hybrid | ❌ Unreliable | Low | Poor |
| **5. API Key Mode** | ✅ **Zero changes** | **Medium** | **Excellent** |

### Advantages

1. **Zero ServiceNow Changes**: ServiceNow just needs a different API key - no code changes
2. **Explicit Configuration**: Mode is clearly defined per client
3. **Flexible**: Can configure timeout per API key
4. **Backwards Compatible**: Existing keys default to async mode
5. **Easy Management**: Change mode by updating Secret Manager
6. **A2A Aligned**: Authentication-based configuration is secure pattern

---

## How It Works

### Current API Key Structure

```json
{
  "key1": {
    "name": "ServiceNow Production",
    "created": "2025-12-05",
    "expires": "2026-12-05",
    "notes": "ServiceNow A2A integration"
  }
}
```

### Enhanced API Key Structure (Option 5)

```json
{
  "key1": {
    "name": "ServiceNow Production",
    "created": "2025-12-05",
    "expires": "2026-12-05",
    "notes": "ServiceNow A2A integration",
    "mode": "sync",
    "timeout": 60
  },
  "key2": {
    "name": "Legacy Client",
    "created": "2025-12-01",
    "expires": "2026-12-01",
    "notes": "Existing async client",
    "mode": "async"
  }
}
```

### New Fields

- **`mode`** (optional): `"sync"` or `"async"` (defaults to `"async"`)
- **`timeout`** (optional): Timeout in seconds for sync mode (defaults to 60)

---

## Implementation Details

### 1. Enhanced API Key Parsing

**File**: `main.py` (lines 135-155)

**Before**:
```python
# Load API keys from environment
raw_api_keys = os.getenv("API_KEYS", "{}")
API_KEYS = json.loads(raw_api_keys.strip())
logger.info(f"✓ Loaded {len(API_KEYS)} API key(s) for authentication")
```

**After**:
```python
# Load API keys from environment with enhanced validation
raw_api_keys = os.getenv("API_KEYS", "{}")
API_KEYS = json.loads(raw_api_keys.strip())

# Validate and normalize API key configurations
for key_hash, config in API_KEYS.items():
    # Set defaults for new fields
    if "mode" not in config:
        config["mode"] = "async"  # Default to async for backwards compatibility
    if "timeout" not in config:
        config["timeout"] = 60  # Default 60 second timeout for sync mode

    # Validate mode
    if config["mode"] not in ["sync", "async"]:
        logger.warning(f"Invalid mode '{config['mode']}' for key '{config.get('name', 'unknown')}', defaulting to 'async'")
        config["mode"] = "async"

    # Validate timeout
    if not isinstance(config["timeout"], (int, float)) or config["timeout"] <= 0:
        logger.warning(f"Invalid timeout {config['timeout']} for key '{config.get('name', 'unknown')}', defaulting to 60")
        config["timeout"] = 60

    logger.info(f"✓ API key '{config.get('name', 'unknown')}': mode={config['mode']}, timeout={config['timeout']}s")

logger.info(f"✓ Loaded {len(API_KEYS)} API key(s) for authentication")
```

---

### 2. Modified `handle_message_send()` - Sync/Async Branching

**File**: `main.py` (lines 458-550)

**Current Logic**:
```python
# Create task
tasks[task_id] = {
    "taskId": task_id,
    "status": TaskState.PENDING,
    # ... other fields
}

# Always process in background (async)
background_tasks.add_task(process_message_task, task_id)

# Return pending status
return {
    "jsonrpc": "2.0",
    "result": {
        "taskId": task_id,
        "status": TaskState.PENDING
    },
    "id": request_id
}
```

**New Logic**:
```python
# Create task
tasks[task_id] = {
    "taskId": task_id,
    "status": TaskState.PENDING,
    # ... other fields
}

# Check mode from authenticated API key
api_key_mode = auth.get("mode", "async")
api_key_timeout = auth.get("timeout", 60)

if api_key_mode == "sync":
    # SYNCHRONOUS MODE: Wait for completion
    logger.info(f"Processing task {task_id} in SYNC mode (timeout={api_key_timeout}s) for client '{auth.get('name', 'unknown')}'")

    try:
        # Wait for task completion with timeout
        await asyncio.wait_for(
            process_message_task(task_id),
            timeout=float(api_key_timeout)
        )

        # Return completed result
        task_result = tasks[task_id]
        logger.info(f"Task {task_id} completed synchronously in {task_result.get('processingTime', 0):.2f}s")

        return {
            "jsonrpc": "2.0",
            "result": task_result,
            "id": request_id
        }

    except asyncio.TimeoutError:
        # Timeout occurred - task still processing
        logger.error(f"Task {task_id} timed out after {api_key_timeout}s in sync mode")

        # Mark task as failed
        tasks[task_id]["status"] = TaskState.FAILED
        tasks[task_id]["error"] = {
            "code": -32603,
            "message": f"Request timeout - task exceeded {api_key_timeout}s limit. Task remains processing in background."
        }

        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Request timeout - task exceeded {api_key_timeout}s limit",
                "data": {
                    "taskId": task_id,
                    "timeout": api_key_timeout,
                    "suggestion": "Consider increasing timeout in API key configuration or using async mode"
                }
            },
            "id": request_id
        }

    except Exception as e:
        # Unexpected error during sync processing
        logger.error(f"Error in sync processing for task {task_id}: {str(e)}", exc_info=True)

        tasks[task_id]["status"] = TaskState.FAILED
        tasks[task_id]["error"] = {
            "code": -32603,
            "message": f"Internal error during sync processing: {str(e)}"
        }

        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error during sync processing: {str(e)}",
                "data": {"taskId": task_id}
            },
            "id": request_id
        }

else:
    # ASYNCHRONOUS MODE: Background processing (current behavior)
    logger.info(f"Processing task {task_id} in ASYNC mode for client '{auth.get('name', 'unknown')}'")

    background_tasks.add_task(process_message_task, task_id)

    # Return pending status
    return {
        "jsonrpc": "2.0",
        "result": {
            "taskId": task_id,
            "status": TaskState.PENDING
        },
        "id": request_id
    }
```

---

### 3. Updated Legacy Methods Handler

**File**: `main.py` (lines 765-806)

Apply same sync/async logic to legacy methods (`text.summarize`, `text.analyze_sentiment`, `data.extract`):

```python
# Inside handle_legacy_method() after task creation:

api_key_mode = auth.get("mode", "async")
api_key_timeout = auth.get("timeout", 60)

if api_key_mode == "sync":
    # Process synchronously for legacy methods
    try:
        await asyncio.wait_for(
            process_message_task(task_id),
            timeout=float(api_key_timeout)
        )
        return {"jsonrpc": "2.0", "result": tasks[task_id], "id": request_id}
    except asyncio.TimeoutError:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Legacy method timeout after {api_key_timeout}s"
            },
            "id": request_id
        }
else:
    # Async processing for legacy methods
    background_tasks.add_task(process_message_task, task_id)
    return {
        "jsonrpc": "2.0",
        "result": {"taskId": task_id, "status": TaskState.PENDING},
        "id": request_id
    }
```

---

## Testing Strategy

### Test 1: Async Mode (Default - Existing Behavior)

**API Key** (async mode - default):
```json
{
  "test-async-key": {
    "name": "Test Async Client",
    "created": "2025-12-05",
    "expires": "2026-12-05"
  }
}
```

**Test Command**:
```bash
curl -X POST http://localhost:8080/ \
  -H "Authorization: Bearer test-async-key" \
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
    "id": "test-async-1"
  }'
```

**Expected Response** (immediate):
```json
{
  "jsonrpc": "2.0",
  "result": {
    "taskId": "abc-123",
    "status": "pending"
  },
  "id": "test-async-1"
}
```

---

### Test 2: Sync Mode (New Behavior)

**API Key** (sync mode):
```json
{
  "test-sync-key": {
    "name": "Test Sync Client (ServiceNow Simulation)",
    "created": "2025-12-05",
    "expires": "2026-12-05",
    "mode": "sync",
    "timeout": 60
  }
}
```

**Test Command**:
```bash
curl -X POST http://localhost:8080/ \
  -H "Authorization: Bearer test-sync-key" \
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
    "id": "test-sync-1"
  }'
```

**Expected Response** (after 2-5 seconds):
```json
{
  "jsonrpc": "2.0",
  "result": {
    "taskId": "def-456",
    "status": "completed",
    "result": {
      "summary": "AI is transformative technology...",
      "processingTime": 3.45
    }
  },
  "id": "test-sync-1"
}
```

---

### Test 3: Sync Mode Timeout

**API Key** (short timeout):
```json
{
  "test-timeout-key": {
    "name": "Test Timeout",
    "mode": "sync",
    "timeout": 2
  }
}
```

**Test Command**:
```bash
# Request that takes > 2 seconds
curl -X POST http://localhost:8080/ \
  -H "Authorization: Bearer test-timeout-key" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Write a very long detailed analysis"}]
      }
    },
    "id": "test-timeout-1"
  }'
```

**Expected Response** (after 2 seconds):
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Request timeout - task exceeded 2s limit",
    "data": {
      "taskId": "ghi-789",
      "timeout": 2,
      "suggestion": "Consider increasing timeout in API key configuration or using async mode"
    }
  },
  "id": "test-timeout-1"
}
```

---

## ServiceNow Configuration

### Step 1: Create ServiceNow API Key

**Secret Manager Entry**:
```json
{
  "servicenow-prod": {
    "name": "ServiceNow Production",
    "created": "2025-12-05",
    "expires": "2026-12-05",
    "notes": "ServiceNow A2A integration - sync mode required",
    "mode": "sync",
    "timeout": 60
  }
}
```

### Step 2: Update Secret Manager

```bash
# Get current API keys
gcloud secrets versions access latest --secret="api-keys-abcs-test-ai-agent-001" > api-keys.json

# Edit api-keys.json to add ServiceNow key with mode: "sync"

# Update secret
gcloud secrets versions add api-keys-abcs-test-ai-agent-001 --data-file=api-keys.json

# Verify
gcloud secrets versions access latest --secret="api-keys-abcs-test-ai-agent-001"

# Clean up
rm api-keys.json
```

### Step 3: Deploy Updated Agent

```bash
# Deploy with updated secrets
gcloud run deploy a2a-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --update-secrets API_KEYS=api-keys-abcs-test-ai-agent-001:latest,GEMINI_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --timeout 300
```

### Step 4: Configure ServiceNow

**ServiceNow A2A Configuration**:
- **Agent URL**: `https://a2a-agent-298609520814.us-central1.run.app`
- **API Key**: `servicenow-prod` (the key with `mode: "sync"`)
- **Agent Card URL**: `https://a2a-agent-298609520814.us-central1.run.app/.well-known/agent-card.json`

ServiceNow will:
1. Discover agent via agent-card.json
2. Use root endpoint `/`
3. Send standard A2A requests
4. **Automatically get sync responses** (agent detects from API key)

---

## Benefits Summary

### For ServiceNow
- ✅ **Zero code changes** - just use different API key
- ✅ Works with standard A2A protocol
- ✅ Gets immediate sync responses
- ✅ No polling/SSE needed

### For Other Clients
- ✅ Existing async clients unaffected
- ✅ Can opt-in to sync mode by API key
- ✅ Flexible timeout configuration
- ✅ Easy to switch modes

### For Maintenance
- ✅ Single codebase for both modes
- ✅ Configuration via Secret Manager
- ✅ Clear logging per mode
- ✅ Easy to debug (mode visible in logs)

---

## Implementation Checklist

### Code Changes
- [ ] **main.py:135-155** - Enhanced API key parsing with validation
- [ ] **main.py:458-550** - Modified `handle_message_send()` with sync/async branching
- [ ] **main.py:765-806** - Updated legacy methods handler

### Testing
- [ ] Test async mode with existing key (default behavior)
- [ ] Test sync mode with `mode: "sync"` key
- [ ] Test timeout with short timeout value
- [ ] Verify legacy methods work in both modes

### Deployment
- [ ] Test locally with both sync and async keys
- [ ] Update Secret Manager with ServiceNow key
- [ ] Deploy to Cloud Run
- [ ] Verify agent-card.json accessible

### Documentation
- [ ] Update README.md with API key mode examples
- [ ] Create SERVICENOW-INTEGRATION-GUIDE.md
- [ ] Update test scripts if needed

---

## Estimated Effort

- **Implementation**: 2-3 hours
- **Local Testing**: 1 hour
- **Secret Manager Update**: 30 minutes
- **Production Deployment**: 30 minutes
- **ServiceNow Verification**: User-dependent
- **Total**: 4-5 hours

---

## Risks & Mitigations

### Risk 1: Timeout Too Short
**Issue**: ServiceNow requests timeout before AI completes
**Mitigation**:
- Default 60s timeout (generous)
- Configurable per API key
- Clear timeout error messages
- Suggest increasing timeout in error response

### Risk 2: Resource Exhaustion
**Issue**: Many sync requests block connections
**Mitigation**:
- FastAPI async/await handles efficiently
- Cloud Run auto-scales
- Monitor concurrency metrics
- Set reasonable max timeout (60s)

### Risk 3: Backwards Compatibility
**Issue**: Breaking existing clients
**Mitigation**:
- Default mode is "async" (current behavior)
- Existing keys without "mode" field default to async
- No breaking changes
- Extensive validation and logging

---

## Monitoring & Debugging

### Log Messages

**Startup**:
```
✓ API key 'ServiceNow Production': mode=sync, timeout=60s
✓ API key 'Legacy Client': mode=async, timeout=60s
✓ Loaded 2 API key(s) for authentication
```

**Request Processing**:
```
INFO: Processing task abc-123 in SYNC mode (timeout=60s) for client 'ServiceNow Production'
INFO: Task abc-123 completed synchronously in 3.45s
```

```
INFO: Processing task def-456 in ASYNC mode for client 'Legacy Client'
```

**Timeouts**:
```
ERROR: Task ghi-789 timed out after 60s in sync mode
```

### Cloud Run Logs Query

```bash
# View mode usage
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 100 | grep "Processing task"

# View sync completions
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 100 | grep "completed synchronously"

# View timeouts
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 100 | grep "timed out"
```

---

## Rollback Plan

If issues arise:

```bash
# Revert code changes
git revert HEAD
gcloud run deploy a2a-agent --source . --region us-central1

# Or rollback to previous revision
gcloud run services update-traffic a2a-agent \
  --region us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Remove sync mode from API key in Secret Manager
# (keeps key working in async mode)
```

---

## Conclusion

Option 5 provides the **ideal solution** for ServiceNow compatibility:

✅ **Zero ServiceNow changes** - just use sync-mode API key
✅ **Backwards compatible** - existing clients unaffected
✅ **Flexible** - easy to configure per client
✅ **Maintainable** - single codebase, clear configuration
✅ **Secure** - authentication-based configuration

**Ready for implementation.**
