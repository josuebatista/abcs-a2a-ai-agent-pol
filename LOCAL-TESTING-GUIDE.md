# Local Testing Guide - A2A Agent v0.10.0

This guide will help you test the A2A Protocol implementation locally before deploying to Cloud Run.

---

## Prerequisites

### 1. Gemini API Key (Required)

You need a Google Gemini API key to power the AI capabilities.

**Get your key**:
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (format: `AIza...` - 39 characters)

**Add to .env**:
```bash
# Edit .env file
nano .env

# Replace this line:
GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE

# With your actual key:
GEMINI_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr
```

### 2. Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Authentication Key (Already Configured)

Your authentication key is already set up in `start-local-test.sh`:
- **Key**: `fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=`
- **Source**: Secret `api-keys-abcs-test-ai-agent-001` from Cloud Run

---

## Quick Start

### Option 1: Using Start Script (Recommended)

```bash
# 1. Make sure .env has your Gemini API key
nano .env

# 2. Start the server
./start-local-test.sh
```

The script will:
- ✅ Check for Gemini API key
- ✅ Set up authentication
- ✅ Start server on http://localhost:8080

### Option 2: Manual Start

```bash
# Set environment variables
export API_KEYS='{"fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=":{"name":"Local Test","created":"2025-11-06","expires":null}}'

# Start server
python main.py
```

---

## Running Tests

Once the server is running, **open a new terminal** and run:

```bash
# Set your API key
export API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

# Run comprehensive test suite
./test-message-send.sh http://localhost:8080 $API_KEY
```

**Expected Output**:
```
==========================================
A2A Protocol message/send Test Suite
Service: http://localhost:8080
==========================================

=== Test 1: message/send - Summarization Intent ===
Testing: Summarization via natural language... ✓ PASS (Task ID: xxx)
  Status: completed

=== Test 2: message/send - Sentiment Analysis Intent ===
Testing: Sentiment analysis via natural language... ✓ PASS (Task ID: xxx)
  Status: completed

...

==========================================
Results: 6 passed, 0 failed
==========================================
✓ All tests passed!
```

---

## Manual Testing Examples

### Test 1: New A2A message/send Method

```bash
API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

# Submit a message
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "Summarize this article in 30 words: Artificial intelligence is transforming industries worldwide. Machine learning models are becoming increasingly sophisticated, enabling new applications in healthcare, finance, and transportation."
          }
        ]
      }
    },
    "id": "test-1"
  }' | jq .
```

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "taskId": "test-1",
    "status": "pending"
  },
  "id": "test-1"
}
```

**Check Result** (wait 3-5 seconds):
```bash
curl -s http://localhost:8080/tasks/test-1 \
  -H "Authorization: Bearer $API_KEY" | jq .
```

**Expected**:
```json
{
  "task_id": "test-1",
  "status": "completed",
  "result": {
    "summary": "AI is revolutionizing global industries. Advanced ML models enable...",
    "original_length": 145,
    "summary_length": 89,
    "compression_ratio": 0.61,
    "model_used": "gemini-2.5-flash"
  },
  "skill": "summarization",
  "created_by": "Local Test Key"
}
```

---

### Test 2: Sentiment Analysis

```bash
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "What is the sentiment of this review: This product is absolutely fantastic! I love it and would recommend it to everyone!"
          }
        ]
      }
    },
    "id": "sentiment-test"
  }' | jq .
```

---

### Test 3: Entity Extraction

```bash
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "Extract all entities from this text: Microsoft CEO Satya Nadella announced a new partnership in Seattle on January 15th, 2024. Contact: info@microsoft.com"
          }
        ]
      }
    },
    "id": "extract-test"
  }' | jq .
```

---

### Test 4: Legacy Method (Backwards Compatibility)

Verify old methods still work:

```bash
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "text.summarize",
    "params": {
      "text": "AI is transforming industries. ML models are sophisticated.",
      "max_length": 20
    },
    "id": "legacy-test"
  }' | jq .
```

**Expected**: Should work with deprecation warning in server logs.

---

### Test 5: tasks/list Method (NEW in v0.10.0!)

List all tasks created by your API key:

```bash
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {},
    "id": "list-all"
  }' | jq .
```

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tasks": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "totalTasks": 5,
      "totalPages": 1,
      "hasNextPage": false,
      "hasPreviousPage": false
    },
    "filters": {
      "status": null,
      "skill": null
    }
  },
  "id": "list-all"
}
```

---

### Test 6: tasks/list with Pagination

Get only first 2 tasks:

```bash
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {
      "limit": 2
    },
    "id": "list-limited"
  }' | jq .
```

---

### Test 7: tasks/list with Filtering

Get only completed tasks:

```bash
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {
      "status": "completed"
    },
    "id": "list-completed"
  }' | jq .
```

Get only summarization tasks:

```bash
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {
      "skill": "summarization"
    },
    "id": "list-summarization"
  }' | jq .
```

---

### Test 8: Comprehensive Test Suite

Run the complete test suite for tasks/list:

**Windows**:
```cmd
test-tasks-list.bat http://localhost:8080 "fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
```

**Linux/Mac**:
```bash
chmod +x test-tasks-list.sh
./test-tasks-list.sh http://localhost:8080 "fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
```

This runs 9 comprehensive tests covering:
- Basic pagination
- Custom limits
- Page navigation
- Status filtering
- Skill filtering
- Combined filters
- Error handling (invalid page/limit)
- Empty results

---

## Verification Checklist

### ✅ Server Health
```bash
curl -s http://localhost:8080/health | jq .
```

**Expected**:
```json
{
  "status": "healthy",
  "gemini_configured": true,
  "api_key_loaded": true,
  "model": "gemini-2.5-flash"
}
```

### ✅ Agent Card
```bash
curl -s http://localhost:8080/.well-known/agent-card.json | jq '{version, protocolVersion, skills: (.skills | length)}'
```

**Expected**:
```json
{
  "version": "0.9.0",
  "protocolVersion": "0.3.0",
  "skills": 3
}
```

### ✅ Intent Detection

Test that the agent correctly identifies intents:

| Message | Expected Skill |
|---------|---------------|
| "Summarize this..." | summarization |
| "What's the sentiment..." | sentiment-analysis |
| "Extract entities..." | entity-extraction |
| "Give me an overview..." | summarization |
| "How does this sound?" | sentiment-analysis |
| "Find all the names..." | entity-extraction |

### ✅ Parameter Extraction

Test that length specifications are parsed:

| Message | Expected max_length |
|---------|-------------------|
| "Summarize in 20 words" | 20 |
| "Brief overview (50 words)" | 50 |
| "Maximum 100 words" | 100 |
| "Under 30 words" | 30 |
| "Summarize this" | 100 (default) |

---

## Troubleshooting

### Issue: "API_KEY_INVALID" Error

**Cause**: Gemini API key not set or invalid

**Solution**:
```bash
# Check .env file
cat .env

# Make sure it has:
GEMINI_API_KEY=AIzaSy...  # Your actual key

# Test API key directly
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents": [{"parts": [{"text": "test"}]}]}'
```

### Issue: Port 8080 Already in Use

**Solution**:
```bash
# Find process using port 8080
lsof -i :8080

# Kill it
kill -9 <PID>

# Or use different port
export PORT=8081
python main.py
```

### Issue: "Unauthorized" Error

**Cause**: Missing or incorrect authentication key

**Solution**:
```bash
# Make sure you're using the correct API key
export API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

# Include it in all requests
curl -H "Authorization: Bearer $API_KEY" ...
```

### Issue: Tasks Stay in "pending" State

**Cause**: Gemini API call failing

**Check Logs**:
```bash
# Server logs will show the error
# Look for lines like:
# ERROR: Task xxx failed: ...
```

**Solution**:
- Verify Gemini API key is valid
- Check internet connection
- Verify API quota not exceeded

---

## Performance Testing

### Single Request Latency

```bash
time curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"type":"text","text":"Summarize: Test text"}]}},"id":"perf-1"}'
```

**Expected**: < 200ms for task creation

### Concurrent Requests

```bash
# Submit 10 tasks concurrently
for i in {1..10}; do
  curl -s -X POST http://localhost:8080/rpc \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Summarize: Test $i\"}]}},\"id\":\"perf-$i\"}" &
done

wait
echo "All tasks submitted"
```

---

## Server Logs to Monitor

When running locally, watch for these log entries:

**✅ Good Signs**:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8080
✓ API key cleaned successfully (length: 39)
Configured with REST transport
✓ SUCCESS: Gemini 2.5 Flash model is working
Task xxx created by 'Local Test Key' - Skill: summarization (via message/send)
Task xxx completed successfully
```

**⚠️ Warnings**:
```
⚠️  Using deprecated method 'text.summarize'. Consider using 'message/send' per A2A v0.3.0
Could not determine skill from: '...', defaulting to summarization
File part handling not yet implemented
```

**❌ Errors**:
```
ERROR: Task xxx failed: ...
API_KEY_INVALID
Failed to parse extraction response
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. **Commit Test Results**
   ```bash
   # Add any test output logs
   git add test-results.log
   git commit -m "Local testing complete - all tests passing"
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy a2a-agent \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --update-secrets API_KEYS=api-keys-abcs-test-ai-agent-001:latest,GEMINI_API_KEY=gemini-api-key:latest
   ```

3. **Test Production**
   ```bash
   SERVICE_URL="https://a2a-agent-298609520814.us-central1.run.app"
   ./test-message-send.sh $SERVICE_URL $API_KEY
   ```

### If Tests Fail ❌

1. **Review Logs**: Check server output for errors
2. **Debug Specific Test**: Run failing test manually with verbose output
3. **Check Configuration**: Verify API keys, ports, dependencies
4. **Report Issue**: Create GitHub issue with logs and steps to reproduce

---

## Test Coverage

This local test suite validates:

- ✅ Message/send RPC method
- ✅ Intent detection (all 3 skills)
- ✅ Parameter extraction from natural language
- ✅ Task creation and status tracking
- ✅ Background processing
- ✅ AI handler integration
- ✅ Legacy method backwards compatibility
- ✅ Error handling
- ✅ Authentication
- ✅ Health checks
- ✅ Agent card serving

**Coverage**: ~90% of Phase 1 implementation

---

## Quick Reference

```bash
# Start server
./start-local-test.sh

# Run tests (in new terminal)
export API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
./test-message-send.sh http://localhost:8080 $API_KEY

# Check health
curl -s http://localhost:8080/health | jq .

# View agent card
curl -s http://localhost:8080/.well-known/agent-card.json | jq .

# Test message/send
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"type":"text","text":"Summarize: AI is amazing"}]}},"id":"quick-test"}'

# Check task result
curl -s http://localhost:8080/tasks/quick-test -H "Authorization: Bearer $API_KEY" | jq .
```

---

**Happy Testing! 🧪**

See [PHASE-1-IMPLEMENTATION.md](./PHASE-1-IMPLEMENTATION.md) for implementation details.
