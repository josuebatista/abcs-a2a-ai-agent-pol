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
- Lines 56-66: Pydantic models for JSON-RPC request/response
- Lines 141-173: `process_task()` - background processor routing tasks to handlers
- Lines 175-323: Real AI capability handlers using Gemini API
- Line 50: Static file mount for `.well-known/agent.json`

**Capabilities Defined (All powered by Gemini API)**
- `text.summarize`: Text summarization using Gemini Pro
- `text.analyze_sentiment`: Sentiment analysis with structured JSON output from Gemini
- `data.extract`: Entity extraction with salience scoring via Gemini

## Agent Discovery Card

`.well-known/agent.json` declares:
- 3 capabilities with complete JSON schemas (input/output)
- RPC endpoints following A2A specification
- Status codes (pending/running/completed/failed)
- Authentication config (currently disabled for development)
- Metadata for ServiceNow discovery

## Current Status

**Working (v0.4)**
- ✅ Complete A2A protocol implementation
- ✅ All endpoints tested and functional locally
- ✅ JSON-RPC 2.0 + SSE working
- ✅ Real AI capabilities using Gemini API
- ✅ All three handlers tested with live Gemini API calls
- ✅ Simplified authentication (single API key)

**Version History**
- v0.1: Initial project structure
- v0.2: Working A2A agent with mock capabilities
- v0.3: Real AI integration with Vertex AI and Natural Language API
- v0.4: Migrated to Gemini API for all capabilities (current)

**Next Phase Options**
- **Cloud Run Deployment**: Deploy containerized app with authentication
- **Testing**: Add pytest suite for A2A compliance validation
- **Authentication**: Add bearer token authentication for production

## AI Capabilities Architecture

All three capabilities use **Google Gemini API** (`gemini-pro-latest` model):

1. **Text Summarization** (`handle_text_summarization()` - line ~175):
   - Accepts text and max_length parameters
   - Uses prompt engineering to request summary of specific length
   - Returns summary with compression metrics

2. **Sentiment Analysis** (`handle_sentiment_analysis()` - line ~210):
   - Prompts Gemini for structured JSON sentiment output
   - Returns sentiment label, confidence, and score breakdown
   - JSON cleaning to handle markdown code blocks

3. **Data Extraction** (`handle_data_extraction()` - line ~254):
   - Prompts Gemini to extract entities by type
   - Returns structured entities with salience scores
   - Supports: persons, locations, organizations, dates, events, phone numbers, emails

## Deployment Notes

- User has GCP account with Cloud Run access and billing enabled
- Dockerfile optimized for Cloud Run (non-root user, healthcheck, slim base)
- Port 8080 hardcoded for Cloud Run compatibility
- Authentication currently disabled (`"required": false` in agent.json) - enable for production
- **Environment Setup**: Requires `GEMINI_API_KEY` environment variable
- For Cloud Run: Use Secret Manager to store Gemini API key securely
- No service account or IAM roles needed (Gemini API uses API key authentication)

## A2A Protocol Requirements

Must maintain:
- Agent card at `/.well-known/agent.json` with proper capability schemas
- JSON-RPC 2.0 format: `{"method": "text.summarize", "params": {...}, "id": "..."}`
- Status reporting: pending → running → completed/failed
- Artifact returns in result object
- SSE support for real-time updates
- ServiceNow-compatible discovery mechanism
