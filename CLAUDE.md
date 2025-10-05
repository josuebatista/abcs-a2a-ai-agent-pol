# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An Agent2Agent (A2A) protocol compliant secondary agent implementing Google's A2A specification for discovery and orchestration by primary agents like ServiceNow. Built as a proof-of-concept for GCP Cloud Run deployment with FastAPI.

## Development Commands

```bash
# Local development
pip install -r requirements.txt
python main.py  # Runs on http://localhost:8080

# Docker
docker build -t a2a-agent .
docker run -p 8080:8080 a2a-agent

# Cloud Run deployment
gcloud run deploy a2a-agent --source . --platform managed --region us-central1

# Testing endpoints (see README.md for complete curl examples)
curl -s http://localhost:8080/health | jq .
curl -s http://localhost:8080/.well-known/agent.json | jq .
```

## Architecture

**Core Application (main.py)**
- Single FastAPI app implementing A2A protocol specification
- In-memory task storage (`tasks: Dict[str, Dict]`) - replace with persistent storage for production
- Background task processing using FastAPI's `BackgroundTasks`
- Three capability handlers: `handle_text_summarization()`, `handle_sentiment_analysis()`, `handle_data_extraction()`

**A2A Protocol Flow**
1. **Discovery**: Primary agents fetch `/.well-known/agent.json` (served via StaticFiles)
2. **Task Submission**: JSON-RPC 2.0 POST to `/rpc` creates task with unique ID
3. **Background Processing**: `process_task()` routes to capability handlers based on method
4. **Status Updates**: Clients poll `/tasks/{task_id}` or stream via SSE `/tasks/{task_id}/stream`
5. **Task States**: `pending` → `running` → `completed`/`failed`

**Key Components**
- Lines 31-45: Pydantic models for JSON-RPC request/response
- Lines 119-151: `process_task()` - background processor routing tasks to handlers
- Lines 154-212: Mock capability implementations (replace with Vertex AI)
- Line 28: Static file mount for `.well-known/agent.json`

**Capabilities Defined**
- `text.summarize`: Text summarization (mock: returns first 100 chars + metrics)
- `text.analyze_sentiment`: Sentiment analysis (mock: returns hardcoded positive sentiment)
- `data.extract`: Extract structured data (mock: returns static entity list)

## Agent Discovery Card

`.well-known/agent.json` declares:
- 3 capabilities with complete JSON schemas (input/output)
- RPC endpoints following A2A specification
- Status codes (pending/running/completed/failed)
- Authentication config (currently disabled for development)
- Metadata for ServiceNow discovery

## Current Status

**Working (v0.2)**
- ✅ Complete A2A protocol implementation
- ✅ All endpoints tested and functional locally
- ✅ JSON-RPC 2.0 + SSE working
- ✅ Mock AI capabilities return proper structure

**Next Phase Options**
- **Vertex AI Integration**: Replace mock handlers (lines 154-212) with real Google Cloud AI calls
- **Cloud Run Deployment**: Deploy containerized app with authentication
- **Testing**: Add pytest suite for A2A compliance validation

## Modifying AI Capabilities

To replace mock implementations with real AI:

1. Update capability handlers in `main.py`:
   - `handle_text_summarization()` at line 154
   - `handle_sentiment_analysis()` at line 173
   - `handle_data_extraction()` at line 193

2. Add Vertex AI dependencies to `requirements.txt`:
   ```
   google-cloud-aiplatform==1.38.1  # Already present
   ```

3. Update `.well-known/agent.json` with real processing limits (max_length, timeout)

4. Add GCP credentials handling for Vertex AI authentication

## Deployment Notes

- User has GCP account with Cloud Run access and billing enabled
- Dockerfile optimized for Cloud Run (non-root user, healthcheck, slim base)
- Port 8080 hardcoded for Cloud Run compatibility
- Authentication currently disabled (`"required": false` in agent.json) - enable for production
- IAM roles needed: Cloud Run Invoker, Vertex AI User (for real AI integration)

## A2A Protocol Requirements

Must maintain:
- Agent card at `/.well-known/agent.json` with proper capability schemas
- JSON-RPC 2.0 format: `{"method": "text.summarize", "params": {...}, "id": "..."}`
- Status reporting: pending → running → completed/failed
- Artifact returns in result object
- SSE support for real-time updates
- ServiceNow-compatible discovery mechanism
