# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ IMPORTANT: A2A Protocol Compliance Status

**Current Status**: Phase 1 Complete - 80% Compliant (v0.9.1) ✅ **PRODUCTION VERIFIED**

This implementation has achieved **major A2A Protocol v0.3.0 compliance** with Phase 1 complete. See **[FULL-COMPLIANCE-ASSESSMENT.md](./FULL-COMPLIANCE-ASSESSMENT.md)** for complete roadmap.

**✅ Completed (Phase 1 - v0.9.1)**:
1. ✅ Skills rewritten with human-friendly descriptions and examples
2. ✅ Complete task state lifecycle (all 8 required states)
3. ✅ Protocol metadata fields (preferredTransport, supportsAuthenticatedExtendedCard)
4. ✅ Message/Part data structures (TextPart, FilePart, DataPart)
5. ✅ `message/send` handler with natural language processing
6. ✅ Intent detection (summarization, sentiment-analysis, entity-extraction)
7. ✅ Message-based task routing
8. ✅ 100% backwards compatibility with legacy methods

**Production Deployment**:
- ✅ Deployed to Cloud Run: https://a2a-agent-298609520814.us-central1.run.app
- ✅ Local testing: All tests passed
- ✅ Production testing: All tests passed
- ✅ Authentication: Bearer token working
- ✅ AI Processing: Gemini 2.5 Flash operational
- ✅ **NEW: tasks/list** - Paginated task listing with filtering

**🔄 Remaining for Full Compliance (Phase 2)**:
1. 🔄 `tasks/cancel` - Cancel running tasks
2. 🔄 File/Data part handling (currently TextPart only)

**Current Compliance**: 90% (up from 80%)
**Estimated to 100%**: 1 week (Phase 2 completion)

---

## Project Overview

An Agent2Agent (A2A) protocol secondary agent implementing custom AI capabilities with Google's Gemini 2.5 Flash API. Production-ready proof-of-concept deployed on GCP Cloud Run with FastAPI. **Secured with Bearer Token authentication for privacy and cost protection.**

**Note**: While functional and production-ready, the current architecture requires refactoring to fully comply with A2A Protocol v0.3.0 specifications.

## Development Commands

### Local Testing (Windows/Linux/Mac)

**Windows**:
```cmd
REM 1. Update .env with your Gemini API key from https://makersuite.google.com/app/apikey
REM 2. Start server
start-local-test.bat

REM 3. In new terminal, run tests
test-message-send.bat http://localhost:8080 "fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

REM Quick manual test
quick-test.bat
```

**Linux/Mac**:
```bash
# 1. Update .env with your Gemini API key
# 2. Start server
./start-local-test.sh

# 3. In new terminal, run tests
./test-message-send.sh http://localhost:8080 fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=
```

**See [LOCAL-TESTING-GUIDE.md](./LOCAL-TESTING-GUIDE.md) for complete testing instructions.**

### Cloud Run Deployment

```bash
# Deploy to production
gcloud run deploy a2a-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --update-secrets API_KEYS=api-keys-abcs-test-ai-agent-001:latest,GEMINI_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --timeout 300
```

### Testing Endpoints

**Local**:
```bash
# Health check
curl http://localhost:8080/health

# Agent card
curl http://localhost:8080/.well-known/agent-card.json

# New A2A message/send method
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"type":"text","text":"Summarize: AI is transforming industries"}]}},"id":"test"}'

# Legacy method (still works)
curl -X POST http://localhost:8080/rpc \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"text.summarize","params":{"text":"Test","max_length":20},"id":"test-1"}'
```

**Production** (https://a2a-agent-298609520814.us-central1.run.app):
```bash
SERVICE_URL="https://a2a-agent-298609520814.us-central1.run.app"
API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

# Health check
curl -s $SERVICE_URL/health | jq .

# Test message/send
curl -X POST $SERVICE_URL/rpc \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"type":"text","text":"Summarize in 20 words: AI is revolutionizing industries"}]}},"id":"prod-test"}'

# Check result (get taskId from above response)
curl -s $SERVICE_URL/tasks/TASK_ID_HERE \
  -H "Authorization: Bearer $API_KEY" | jq .
```

## Architecture

**Core Application (main.py)**
- Single FastAPI app implementing A2A protocol specification
- In-memory task storage (`tasks: Dict[str, Dict]`) - replace with persistent storage for production
- Background task processing using FastAPI's `BackgroundTasks`
- Three capability handlers using Gemini 2.5 Flash API
- Environment credential conflict resolution for Cloud Run deployment

**A2A Protocol Flow**
1. **Discovery**: Primary agents fetch `/.well-known/agent-card.json` (served via StaticFiles)
2. **Task Submission**: JSON-RPC 2.0 POST to `/rpc` creates task with unique ID
3. **Background Processing**: `process_task()` routes to capability handlers based on method
4. **Status Updates**: Clients poll `/tasks/{task_id}` or stream via SSE `/tasks/{task_id}/stream`
5. **Task States**: `pending` → `running` → `completed`/`failed`

**Key Components**
- Pydantic models for JSON-RPC request/response
- `process_task()`: Background processor routing tasks to handlers
- Real AI capability handlers using Gemini 2.5 Flash
- Static file mount for `.well-known/agent-card.json` (with legacy agent.json support)
- Debug endpoints: `/debug/config` for troubleshooting
- Environment cleanup to prevent credential conflicts

**Capabilities (All powered by Gemini 2.5 Flash)**
- `text.summarize`: Text summarization with configurable length
- `text.analyze_sentiment`: Sentiment analysis with confidence scores
- `data.extract`: Entity extraction with fallback regex parsing

## Authentication System (v0.8.0+)

**Multi-Key Bearer Token Authentication** protects all endpoints from unauthorized access.

### Quick Setup

1. **Generate API keys**:
```bash
# Generate a secure random key
openssl rand -base64 32
```

2. **Create API keys JSON** (see `api-keys-example.json`):
```json
{
  "your-generated-key-here": {
    "name": "Primary User",
    "created": "2025-10-11",
    "expires": null,
    "notes": "Main access key"
  }
}
```

3. **Store in Secret Manager**:
```bash
# Minify and store (IMPORTANT: use echo -n to avoid newlines!)
echo -n '{"your-key":{"name":"User1","created":"2025-10-11","expires":null}}' | \
  gcloud secrets create api-keys --data-file=-

# Grant service account access
PROJECT_ID=$(gcloud config get-value project)
gcloud secrets add-iam-policy-binding api-keys \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

4. **Deploy with both secrets**:
```bash
gcloud run deploy a2a-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --update-secrets API_KEYS=api-keys:latest,GEMINI_API_KEY=gemini-api-key:latest
```

5. **Test authentication**:
```bash
SERVICE_URL="https://a2a-agent-298609520814.us-central1.run.app"
API_KEY="your-key-here"

curl -X POST ${SERVICE_URL}/rpc \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"method":"text.summarize","params":{"text":"Test"},"id":"1"}'
```

### Key Features

- **Protected Endpoints**: `/rpc`, `/tasks/{task_id}`, `/tasks/{task_id}/stream`
- **Public Endpoints**: `/health`, `/.well-known/agent-card.json` (no auth required)
- **User Tracking**: Logs show which key created each task
- **Expiry Support**: Optional expiration dates for temporary keys
- **Graceful Fallback**: If `API_KEYS` not set, authentication is disabled (with warnings)

**Complete Documentation**: See `AUTHENTICATION.md` for detailed setup, key management, and troubleshooting.

## Critical Deployment Knowledge

### Gemini API Setup
1. **API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Model**: Uses `gemini-2.5-flash` (NOT `gemini-pro-latest`)
3. **Validation**: Always test API key with curl before deployment

### Secret Manager Configuration
```bash
# Create secret WITHOUT newline (critical!)
echo -n "YOUR_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# Or use printf (more reliable)
printf "YOUR_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
```

### Known Issues and Solutions

**Issue**: "Illegal metadata" or "API_KEY_INVALID" errors in Cloud Run
**Cause**: Credential conflict between Cloud Run's automatic auth and Gemini API key
**Solution**: Code clears Google Cloud credentials on startup:
```python
# Clear Google Cloud credentials to prevent conflicts
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
```

**Issue**: Data extraction JSON parse errors
**Solution**: Implemented with fallback regex extraction for emails/phones

**Issue**: Secret not loading in Cloud Run
**Solution**: Use `--update-secrets` flag (not `--set-secrets`) and grant service account access:
```bash
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

## Current Status

**Production Deployment (v0.9.1)** ✅ **80% A2A COMPLIANT - PRODUCTION VERIFIED**
- ✅ **Live on Cloud Run**: `https://a2a-agent-298609520814.us-central1.run.app`
- ✅ **Phase 1 Complete**: Core A2A Protocol v0.3.0 methods implemented
- ✅ **message/send**: Natural language interface working in production
- ✅ **Intent Detection**: Accurately routes to appropriate skills
- ✅ **Bearer Token Authentication**: Multi-key auth with expiry support
- ✅ **3 AI Skills**: Text summarization, sentiment analysis, data extraction
- ✅ **Gemini 2.5 Flash**: All capabilities powered by latest model
- ✅ **Streaming Support**: SSE enabled for real-time updates
- ✅ **Secret Manager**: Secure API key management (Gemini + API keys)
- ✅ **Health Monitoring**: `/health` endpoint operational
- ✅ **Discovery Ready**: A2A v0.3.0 compliant agent card at `/.well-known/agent-card.json`
- ✅ **Complete Task States**: All 8 A2A-required states
- ✅ **Backwards Compatible**: Legacy methods still work with deprecation warnings
- ✅ **Usage Tracking**: Logs show which user/key created each task
- ✅ **Privacy & Cost Protection**: All API endpoints secured with Bearer tokens

**Compliance Status (v0.9.1)**:
- ✅ Agent card format: Fully compliant (human-friendly skills with examples)
- ✅ Task states: Fully compliant (all 8 states)
- ✅ Protocol metadata: Fully compliant (preferredTransport, etc.)
- ✅ RPC methods: **Compliant** (`message/send` implemented!)
- ✅ Message structure: **Compliant** (Message/Part implementation)
- ✅ Intent detection: **Implemented** (natural language routing)
- ✅ **tasks/list: IMPLEMENTED (v0.10.0)** - Paginated listing with filters
- 🔄 tasks/cancel: Not implemented (Phase 2 final step)
- 🔄 File/Data parts: TextPart only (Phase 2 optional)

**Overall Compliance**: 90% (up from 80%) - **PHASE 2.1 COMPLETE**

**Deployment Date**: 2025-10-11
**Latest Update**: 2025-11-06 (v0.10.0 - tasks/list implemented)
**Secret Name**: `api-keys-abcs-test-ai-agent-001`
**Service Account**: `298609520814-compute@developer.gserviceaccount.com`

**Version History**
- v0.1: Initial project structure
- v0.2: Working A2A agent with mock capabilities
- v0.3: Real AI integration with Vertex AI
- v0.4: Migrated to Gemini API
- v0.5: Production Cloud Run deployment with Secret Manager
- v0.6: A2A v0.3.0 filename compliance (agent-card.json migration)
- v0.7: Full A2A v0.3.0 protocol compliance - deployed to production
- v0.8.0: Bearer token authentication with multi-key support
- v0.8.1: Plan A Quick Wins - Skills rewrite, complete task states
- v0.9.0: Phase 1 - Core A2A Protocol implementation
- v0.9.1: Bug fixes + Windows testing support
- v0.9.2: Documentation updates for Phase 1
- v0.10.0: tasks/list implementation with pagination and filtering (current)

**Phase 1 Complete (v0.9.1)** ✅
- ✅ **Message/Part Data Structures**: Standard A2A message format implemented
- ✅ **message/send Handler**: Core protocol method working in production
- ✅ **Intent Detection**: Natural language routing operational
- ✅ **Message-based Task Processing**: Integrated with existing AI handlers
- ✅ **Backwards Compatible**: Legacy methods still functional

**Phase 2.1 Complete (v0.10.0)** ✅ **NEW!**
- ✅ **tasks/list Method**: Paginated task listing with filters
  - Pagination: page, limit (1-100), totalTasks, totalPages
  - Filtering: by status (pending/running/completed/failed), by skill
  - Per-user isolation: users only see their own tasks
  - Comprehensive test suite included

**Next Phase (Phase 2 - Remaining for 95%+ Compliance)**
- 🔄 **tasks/cancel**: Cancel running tasks (Priority: High)
- 🔄 **File/Data Part Handling**: Currently TextPart only (Priority: Medium)
- 🔄 **Primary Agent Integration**: Test with ServiceNow or Google Agent Engine
- 🔄 **Rate Limiting**: Add per-key request throttling and quotas
- 🔄 **Monitoring**: Integrate Cloud Monitoring and alerting

See **[FULL-COMPLIANCE-ASSESSMENT.md](./FULL-COMPLIANCE-ASSESSMENT.md)** for detailed roadmap.
See **[PHASE-1-IMPLEMENTATION.md](./PHASE-1-IMPLEMENTATION.md)** for Phase 1 details.
See **[LOCAL-TESTING-GUIDE.md](./LOCAL-TESTING-GUIDE.md)** for testing instructions.

## AI Capabilities Architecture

All three capabilities use **Google Gemini 2.5 Flash API**:

1. **Text Summarization** (`handle_text_summarization()`):
   - Accepts text and max_length parameters
   - Prompt engineering for specific length summaries
   - Returns summary with compression metrics
   - 30-second timeout with async processing

2. **Sentiment Analysis** (`handle_sentiment_analysis()`):
   - Structured JSON output from Gemini
   - Returns sentiment label, confidence, and score breakdown
   - Automatic JSON cleaning for markdown artifacts

3. **Data Extraction** (`handle_data_extraction()`):
   - Extracts: persons, locations, organizations, dates, events, phones, emails
   - Fallback regex extraction if Gemini JSON is malformed
   - Returns entities with salience scores

## Deployment Architecture

### Docker Configuration
- Base image: `python:3.9-slim`
- Non-root user for security
- Environment variables cleared to prevent conflicts
- Healthcheck endpoint configured
- Port 8080 exposed for Cloud Run

### Cloud Run Configuration
- Region: `us-central1`
- Memory: 512Mi minimum
- Timeout: 300 seconds
- Auto-scaling enabled
- Unauthenticated access (for POC)

### Environment Variables
- `GEMINI_API_KEY`: Required, loaded from Secret Manager
- `PORT`: Set to 8080 by Cloud Run
- Google credentials explicitly cleared on startup

## Testing Strategy

### Local Testing
```bash
# Test with Docker
docker run -p 8081:8080 --rm \
  -e GEMINI_API_KEY="YOUR_KEY" \
  a2a-agent

# Verify all capabilities
./test-a2a.sh http://localhost:8081
```

### Cloud Run Testing

**Production URL**: `https://a2a-agent-298609520814.us-central1.run.app`

```bash
# Quick verification
curl -s https://a2a-agent-298609520814.us-central1.run.app/health | jq .

# Test A2A v0.3.0 discovery
curl -s https://a2a-agent-298609520814.us-central1.run.app/.well-known/agent-card.json | jq '{protocolVersion, url, skills: (.skills | length)}'

# Complete test suite
SERVICE_URL=$(gcloud run services describe a2a-agent --region us-central1 --format 'value(status.url)')
./test-a2a.sh $SERVICE_URL
```

### Quick Task Test

Test text summarization end-to-end:
```bash
# Submit task
TASK_ID="test-$(date +%s)"
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/rpc \
  -H "Content-Type: application/json" \
  -d "{
    \"method\": \"text.summarize\",
    \"params\": {
      \"text\": \"Artificial intelligence is transforming industries worldwide through machine learning.\",
      \"max_length\": 20
    },
    \"id\": \"$TASK_ID\"
  }" | jq .

# Wait and retrieve result
sleep 5
curl -s https://a2a-agent-298609520814.us-central1.run.app/tasks/$TASK_ID | jq .
```

## Debug Tools

### Diagnostic Endpoints
- `/health`: Check API configuration status
- `/debug/config`: View environment and configuration
- `/test/direct`: Test Gemini directly (if implemented)

### Log Analysis
```bash
# View initialization logs
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 50 | grep -E "API key|SUCCESS|ERROR"

# Real-time monitoring
gcloud alpha run services logs tail a2a-agent --region us-central1
```

## A2A Protocol Compliance

### Current Status: ✅ FULL COMPLIANCE (v0.3.0)

**Last Reviewed**: 2025-10-10
**Compliance Achieved**: v0.7.0

### ✅ Compliant Elements
- JSON-RPC 2.0 format implementation (`/rpc` endpoint)
- Task lifecycle states: `pending` → `running` → `completed`/`failed`
- SSE streaming support (`/tasks/{task_id}/stream`)
- Standard endpoints: `/rpc`, `/tasks/{task_id}`, `/tasks/{task_id}/stream`
- Background task processing
- HTTPS requirement (Cloud Run deployment)

### ✅ Priority 1 Fixes (COMPLETED)

#### 1. Well-Known URI Path ✅
- **Status**: FIXED
- **Changes Made**:
  - Renamed `/.well-known/agent.json` → `/.well-known/agent-card.json`
  - Updated main.py endpoints (lines 218-235)
  - Added legacy `/agent.json` endpoint for backward compatibility
  - Updated all documentation references

### ✅ Priority 2 Fixes (COMPLETED)

#### 2. Agent Card Schema Migration ✅
- **Status**: FIXED
- **Changes Made**:
  - Added `protocolVersion: "0.3.0"` (separate from agent version)
  - Added `url` field with Cloud Run endpoint
  - Converted `capabilities` array → `skills` array with proper structure
  - Added new `capabilities` object: `{streaming: true, pushNotifications: false, stateTransitionHistory: false}`
  - Added `defaultInputModes`: `["text/plain", "application/json"]`
  - Added `defaultOutputModes`: `["application/json"]`
  - Migrated authentication to `securitySchemes` per OpenAPI 3.0 spec
  - Updated all skills to use `input`/`output` instead of `input_schema`/`output_schema`
  - Added descriptive `tags` to each skill for better discoverability

### 📋 Required Actions for Full Compliance

**Priority 1: File Migration** ✅ COMPLETED (v0.6.0)

**Priority 2: Agent Card Schema** ✅ COMPLETED (v0.7.0)

**All Compliance Requirements Met**:
- ✅ Well-known URI: `/.well-known/agent-card.json`
- ✅ Protocol version declared: `"protocolVersion": "0.3.0"`
- ✅ Primary URL specified with Cloud Run endpoint
- ✅ Skills array with proper schema structure
- ✅ Capabilities object with boolean flags
- ✅ Input/output MIME types declared
- ✅ OpenAPI 3.0 compliant security schemes
- ✅ Complete transport and endpoint specifications

### A2A Protocol v0.3.0 Specification Reference

**Required Compliance Points**:
- Agent card location: `/.well-known/agent-card.json` (RFC 8615)
- Transport: HTTPS required
- Protocol: JSON-RPC 2.0 (implemented ✅)
- Task ID: Server-generated unique identifier (implemented ✅)
- Authentication: Standard HTTP transport layer auth
- Security: TLS 1.3+ recommended

**Version History**:
- v0.2.1: Used `agent.json` filename
- v0.3.0: Changed to `agent-card.json`, added signatures, added mTLS to SecuritySchemes

## Production Considerations

1. **Security**: ✅ Bearer token authentication implemented (v0.8.0)
   - Store API keys in Secret Manager
   - Rotate keys every 90-180 days
   - Monitor authentication logs for suspicious activity
2. **Persistence**: Replace in-memory task storage with Firestore/Cloud SQL
3. **Monitoring**: Add Cloud Monitoring metrics and alerts
   - Track per-key usage patterns
   - Alert on authentication failures
4. **Rate Limiting**: Implement per-key quotas to prevent abuse
5. **Error Tracking**: Integrate with Cloud Error Reporting
6. **Scaling**: Configure auto-scaling parameters based on load testing
7. **Key Management**: Consider admin API for key lifecycle management