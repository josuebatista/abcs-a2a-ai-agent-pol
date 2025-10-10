# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An Agent2Agent (A2A) protocol compliant secondary agent implementing Google's A2A specification for discovery and orchestration by primary agents like ServiceNow. Production-ready proof-of-concept deployed on GCP Cloud Run with FastAPI and Gemini 2.5 Flash API.

## Development Commands

```bash
# Local development
pip install -r requirements.txt
python main.py  # Runs on http://localhost:8080

# Docker (use port 8081 if 8080 is busy)
docker build -t a2a-agent .
docker run -p 8080:8080 --rm \
  -e GEMINI_API_KEY="YOUR_KEY" \
  --name a2a-test \
  a2a-agent

# Cloud Run deployment with Secret Manager
gcloud run deploy a2a-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --update-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --timeout 300

# Testing endpoints (see README.md for complete curl examples)
curl -s http://localhost:8080/health | jq .
curl -s http://localhost:8080/.well-known/agent-card.json | jq .
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

**Working (v0.5)**
- ✅ Production deployment on Cloud Run
- ✅ Secret Manager integration
- ✅ Credential conflict resolution
- ✅ All three AI capabilities with Gemini 2.5 Flash
- ✅ Comprehensive error handling and fallbacks
- ✅ Docker containerization with proper environment isolation
- ✅ Complete test suite and documentation

**Version History**
- v0.1: Initial project structure
- v0.2: Working A2A agent with mock capabilities
- v0.3: Real AI integration with Vertex AI
- v0.4: Migrated to Gemini API
- v0.5: Production Cloud Run deployment with Secret Manager
- v0.6: A2A v0.3.0 filename compliance (agent-card.json migration)
- v0.7: Full A2A v0.3.0 protocol compliance (schema migration complete) (current)

**Next Phase Options**
- **Authentication**: Add bearer token authentication for production
- **Rate Limiting**: Implement request throttling
- **Monitoring**: Add Cloud Monitoring and alerting
- **Database**: Replace in-memory storage with Firestore

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
```bash
SERVICE_URL=$(gcloud run services describe a2a-agent --region us-central1 --format 'value(status.url)')
./test-a2a.sh $SERVICE_URL
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

1. **Security**: Enable authentication in agent-card.json for production
2. **Persistence**: Replace in-memory task storage with Firestore/Cloud SQL
3. **Monitoring**: Add Cloud Monitoring metrics and alerts
4. **Rate Limiting**: Implement quotas to prevent abuse
5. **Error Tracking**: Integrate with Cloud Error Reporting
6. **Scaling**: Configure auto-scaling parameters based on load testing