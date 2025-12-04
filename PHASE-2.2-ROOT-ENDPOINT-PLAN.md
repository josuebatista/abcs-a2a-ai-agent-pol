# Phase 2.2: Root Endpoint Support - Implementation Plan

**Phase**: 2.2 - ServiceNow Compatibility
**Date**: 2025-12-03
**Version**: v0.10.2 (planned)
**Status**: 📝 **PLANNING**

---

## Problem Statement

**Issue**: ServiceNow's A2A implementation expects the JSON-RPC endpoint at the **root URL** (`https://a2a-agent-298609520814.us-central1.run.app`) without the `/rpc` suffix.

**Current Implementation**:
- JSON-RPC endpoint: `/rpc` (line 710 in main.py)
- Declared in agent-card.json: `"rpc": "/rpc"` (line 79)

**Impact**:
- ServiceNow cannot connect to the agent
- Other A2A clients may also expect root endpoint
- Not following emerging A2A best practices

---

## Solution: Option 1 - Dual Endpoint Support ⭐

Implement **BOTH** endpoints for maximum compatibility:
1. **Primary**: `/` (root) - for ServiceNow and A2A standard
2. **Legacy**: `/rpc` - for backwards compatibility with existing clients

### Benefits
✅ Solves ServiceNow integration issue
✅ Maintains 100% backwards compatibility
✅ Follows A2A Protocol best practices
✅ No breaking changes for existing clients
✅ Future-proof architecture

---

## Implementation Steps

### Step 1: Code Changes in main.py

#### 1.1 Extract RPC Handler Logic (Refactoring)
**Location**: `main.py:710-823`

**Action**: Extract the core RPC handling logic into a shared function

**Before**:
```python
@app.post("/rpc")
async def handle_rpc_request(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_token)
):
    # All logic here (113 lines)
```

**After**:
```python
async def _process_rpc_request(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Core RPC request processing logic shared by both endpoints.
    Supports A2A Protocol v0.3.0 and legacy methods.
    """
    # All processing logic moved here
    # Returns JSON-RPC response dict

@app.post("/rpc")
async def handle_rpc_request_legacy(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_token)
):
    """
    Legacy JSON-RPC 2.0 endpoint (backwards compatibility).
    Use root endpoint / for new integrations.
    """
    logger.info("Request received on legacy /rpc endpoint")
    return await _process_rpc_request(request, background_tasks, auth)

@app.post("/")
async def handle_rpc_request_root(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_token)
):
    """
    Primary JSON-RPC 2.0 endpoint (A2A Protocol v0.3.0 standard).
    Supports: message/send, tasks/list, tasks/get, and legacy methods.
    """
    logger.info("Request received on root / endpoint")
    return await _process_rpc_request(request, background_tasks, auth)
```

**Rationale**:
- DRY principle - single source of truth for RPC logic
- Easy to maintain - changes apply to both endpoints
- Clear logging - know which endpoint clients are using
- Minimal code duplication

---

#### 1.2 Add Logging for Endpoint Usage Tracking
**Location**: Inside `_process_rpc_request` function

**Action**: Add logging to track which endpoint clients use

```python
async def _process_rpc_request(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any]
) -> Dict[str, Any]:
    """Core RPC request processing logic"""

    # Determine which endpoint was called
    endpoint_path = request.url.path
    logger.info(f"RPC request via {endpoint_path} from '{auth.get('name', 'Unknown')}'")

    # Rest of processing logic...
```

**Rationale**:
- Visibility into client migration from /rpc to /
- Usage analytics for deprecation planning
- Debugging support

---

### Step 2: Update agent-card.json

**Location**: `.well-known/agent-card.json:79`

**Current**:
```json
"endpoints": {
  "rpc": "/rpc",
  "status": "/tasks/{task_id}",
  "stream": "/tasks/{task_id}/stream"
}
```

**Updated**:
```json
"endpoints": {
  "rpc": "/",
  "rpcLegacy": "/rpc",
  "status": "/tasks/{task_id}",
  "stream": "/tasks/{task_id}/stream"
}
```

**Rationale**:
- Declares `/` as primary endpoint per A2A v0.3.0
- Maintains `/rpc` as legacy for discoverability
- Clear naming: `rpc` (primary) vs `rpcLegacy` (backwards compat)

**Alternative** (if ServiceNow strict parser):
```json
"endpoints": {
  "rpc": "/",
  "status": "/tasks/{task_id}",
  "stream": "/tasks/{task_id}/stream"
}
```
- Omit `rpcLegacy` if not part of A2A spec
- `/rpc` still works, just not advertised

---

### Step 3: Update All Test Scripts

**Files to Update**:
1. `test-message-send.sh` - line 35
2. `test-message-send.bat` - similar line
3. `test-tasks-list.sh` - multiple references
4. `test-tasks-list.bat` - multiple references
5. `test-a2a.sh` - line ~421
6. `send-and-wait.sh` - multiple references
7. `send-and-wait.bat` - multiple references
8. `quick-test.bat` - RPC call
9. `quick-test-tasks-list.bat` - RPC call
10. `prod-test-tasks-list.bat` - RPC call

**Strategy**:
- **Phase A**: Update all scripts to use `/` (root endpoint)
- **Phase B**: Add comments noting `/rpc` still works for compatibility

**Example Change** (test-message-send.sh:35):
```bash
# Before:
response=$(curl -s -X POST "$BASE_URL/rpc" \

# After:
response=$(curl -s -X POST "$BASE_URL/" \
    # Note: /rpc endpoint still supported for backwards compatibility
```

**Alternative Strategy** (Dual Testing):
- Keep some scripts using `/rpc` to verify backwards compatibility
- Update production scripts to use `/`
- Mark legacy scripts with `# (LEGACY /rpc endpoint)` comment

---

### Step 4: Update Documentation

**Files to Update**:

#### 4.1 README.md
**Sections**:
- Line ~48: Quick Production Test example
- Line ~84-97: A2A-ASYNC-PATTERNS.md examples
- Line 265-279: Text Summarization examples
- Line 282-312: Sentiment Analysis examples
- Line 315-330: Data Extraction examples
- Line 334-353: Stream Task Updates examples
- Line 420-432: test-a2a.sh script example

**Changes**:
```bash
# Update all curl examples from:
curl -X POST $SERVICE_URL/rpc \

# To:
curl -X POST $SERVICE_URL/ \
  # Note: Legacy /rpc endpoint still supported
```

#### 4.2 A2A-ASYNC-PATTERNS.md
**Sections**:
- All curl examples (~10 occurrences)
- Pattern 1, 2, 3 examples

**Changes**: Same as README.md

#### 4.3 LOCAL-TESTING-GUIDE.md
**Sections**:
- All test examples

**Changes**: Update endpoint references

#### 4.4 PHASE-1-IMPLEMENTATION.md & PHASE-2.1-IMPLEMENTATION.md
**Sections**:
- Code examples showing RPC calls
- Testing sections

**Changes**: Update for consistency

#### 4.5 test-payloads-examples.json
**Change**: Add note in description
```json
{
  "description": "JSON payload examples for A2A Agent v0.10.2",
  "note": "Send to root endpoint / (or legacy /rpc for backwards compatibility)",
  ...
}
```

---

### Step 5: Create Implementation Documentation

**New File**: `PHASE-2.2-IMPLEMENTATION.md`

**Structure**:
```markdown
# Phase 2.2: Root Endpoint Support - COMPLETE ✅

## Summary
Added dual endpoint support for maximum compatibility

## What Was Implemented
1. ✅ Root endpoint `/` as primary
2. ✅ Legacy `/rpc` for backwards compatibility
3. ✅ Shared processing logic (DRY)
4. ✅ Updated agent-card.json
5. ✅ Updated all test scripts
6. ✅ Updated all documentation

## Testing
- [x] Root endpoint works with all methods
- [x] Legacy /rpc still works
- [x] ServiceNow integration verified
- [x] All test scripts pass

## Backwards Compatibility
100% maintained - no breaking changes
```

---

## Testing Strategy

### Phase 1: Local Testing

#### Test 1: Root Endpoint - Basic Methods
```bash
# Set environment
export API_KEY="your-test-key"
export SERVICE_URL="http://localhost:8080"

# Test message/send via root
curl -X POST $SERVICE_URL/ \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Summarize: AI is transforming industries"}]
      }
    },
    "id": "test-root-1"
  }'

# Expected: Returns taskId with pending status
```

#### Test 2: Root Endpoint - tasks/list
```bash
curl -X POST $SERVICE_URL/ \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {"page": 1, "limit": 10},
    "id": "test-list-1"
  }'

# Expected: Returns paginated task list
```

#### Test 3: Legacy /rpc Endpoint - Backwards Compatibility
```bash
# Same tests but with /rpc
curl -X POST $SERVICE_URL/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Test legacy endpoint"}]
      }
    },
    "id": "test-legacy-1"
  }'

# Expected: Works identically to root endpoint
```

#### Test 4: Agent Card Discovery
```bash
# Verify agent-card.json reflects new endpoint
curl -s $SERVICE_URL/.well-known/agent-card.json | jq '.endpoints'

# Expected:
# {
#   "rpc": "/",
#   "rpcLegacy": "/rpc",  # or omitted
#   "status": "/tasks/{task_id}",
#   "stream": "/tasks/{task_id}/stream"
# }
```

#### Test 5: Run Updated Test Scripts
```bash
# Run all test scripts to verify they work with root endpoint
./test-message-send.sh http://localhost:8080 $API_KEY
./test-tasks-list.sh http://localhost:8080 $API_KEY
./send-and-wait.sh http://localhost:8080 $API_KEY
```

### Phase 2: Cloud Run Testing

#### Deploy to Cloud Run
```bash
# Deploy with updated code
gcloud run deploy a2a-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --update-secrets API_KEYS=api-keys-abcs-test-ai-agent-001:latest,GEMINI_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --timeout 300
```

#### Test Production
```bash
export SERVICE_URL="https://a2a-agent-298609520814.us-central1.run.app"
export API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

# Test root endpoint
curl -X POST $SERVICE_URL/ \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Production test"}]
      }
    },
    "id": "prod-test-1"
  }'

# Test legacy /rpc still works
curl -X POST $SERVICE_URL/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Legacy test"}]
      }
    },
    "id": "legacy-test-1"
  }'
```

### Phase 3: ServiceNow Integration Testing

**Prerequisites**:
- ServiceNow instance configured with A2A
- Agent URL: `https://a2a-agent-298609520814.us-central1.run.app`
- API key configured in ServiceNow

**Test Cases**:
1. ✅ ServiceNow discovers agent via agent-card.json
2. ✅ ServiceNow sends message/send to root endpoint
3. ✅ Agent responds with taskId
4. ✅ ServiceNow polls for task completion
5. ✅ Agent returns completed result

**Success Criteria**:
- ServiceNow successfully sends requests to root endpoint
- All A2A protocol methods work correctly
- No errors in ServiceNow logs
- No errors in Cloud Run logs

---

## Risk Assessment

### Low Risk Items ✅
- Adding new root endpoint `/` - no impact on existing clients
- Keeping `/rpc` endpoint - maintains backwards compatibility
- Refactoring to shared function - internal change only
- Documentation updates - no functional impact

### Medium Risk Items ⚠️
- Test script updates - may break if not careful
  - **Mitigation**: Test each script after update
  - **Rollback**: Git revert if needed

- Agent card changes - clients parse this
  - **Mitigation**: Add `rpcLegacy` instead of removing `rpc`
  - **Alternative**: Just change value of `rpc` to `/`

### No High Risk Items ✅

---

## Rollback Plan

If issues arise after deployment:

### Immediate Rollback (< 5 minutes)
```bash
# Revert to previous Cloud Run revision
gcloud run services update-traffic a2a-agent \
  --region us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Or via git
git revert HEAD
gcloud run deploy a2a-agent --source . --region us-central1
```

### Partial Rollback
- If only test scripts broken: Revert test files only
- If agent-card.json issue: Revert only that file
- Code is modular - can revert specific components

---

## Success Metrics

### Functional Metrics
- [ ] Root endpoint `/` handles all RPC methods correctly
- [ ] Legacy `/rpc` endpoint still works (backwards compat)
- [ ] Agent card correctly declares endpoints
- [ ] All test scripts pass with new endpoint
- [ ] ServiceNow successfully connects to agent

### Non-Functional Metrics
- [ ] No performance degradation (response times < 200ms for RPC routing)
- [ ] No increase in error rates
- [ ] Logs show clear endpoint usage (root vs legacy)
- [ ] 100% backwards compatibility maintained

---

## Timeline Estimate

**Total Time**: 2-3 hours

### Breakdown
- **Code changes** (main.py): 30 minutes
  - Refactor to shared function: 15 min
  - Add root endpoint: 5 min
  - Add logging: 10 min

- **Agent card update**: 5 minutes

- **Test script updates**: 45 minutes
  - 10 test scripts × ~4 minutes each

- **Documentation updates**: 45 minutes
  - 9 documentation files × ~5 minutes each

- **Testing**: 30 minutes
  - Local testing: 15 min
  - Production testing: 15 min

- **Buffer**: 15 minutes

---

## Post-Implementation

### Monitoring
- Watch Cloud Run logs for endpoint usage patterns
- Track ratio of `/` vs `/rpc` usage over time
- Monitor for any ServiceNow integration issues

### Future Deprecation (Optional)
**Timeline**: 6-12 months after deployment

If all clients migrate to root endpoint:
1. Add deprecation warning to `/rpc` endpoint logs
2. Update documentation to mark `/rpc` as deprecated
3. After sufficient notice, consider removing `/rpc`

**Not Recommended**: Keep both endpoints indefinitely (low maintenance cost)

---

## Dependencies

### Required
- ✅ Git repository access
- ✅ gcloud CLI configured
- ✅ Cloud Run deployment permissions
- ✅ API keys for testing

### Optional
- ServiceNow instance for integration testing (user will test)
- Monitoring/observability tools

---

## Questions to Clarify with User

None - implementation is straightforward with low risk.

---

## Conclusion

This implementation plan provides:
1. **Clear solution**: Dual endpoint support (root + legacy)
2. **Zero breaking changes**: 100% backwards compatible
3. **Comprehensive testing**: Multi-phase validation
4. **Complete documentation**: All files updated
5. **Risk mitigation**: Rollback plan included
6. **Reasonable timeline**: 2-3 hours total

The refactoring to a shared `_process_rpc_request()` function ensures maintainability while the dual endpoints provide maximum compatibility with ServiceNow and existing clients.

Ready for user approval and implementation.
