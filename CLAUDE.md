# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI/ML Solution Architect's proof-of-concept project to build a fully compliant Agent2Agent (A2A) protocol secondary agent in Google Cloud Platform. The agent implements Google's A2A protocol specification (introduced April 2025) and can be discovered and orchestrated by primary agents like ServiceNow.

## Project Requirements

**Create a Cloud Run application that:**
- Implements Google's A2A protocol specification using their Agent Development Kit (ADK) for Python
- Exposes an agent card at `/.well-known/agent.json` with proper metadata
- Provides at least 2-3 basic AI capabilities (e.g., text summarization, sentiment analysis, data extraction)
- Uses JSON-RPC and Server-Sent Events (SSE) as required by A2A
- Implements proper authentication (Bearer Token or OAuth)
- Returns structured responses with artifacts as per A2A spec
- Includes proper error handling and logging

**Technical Stack:**
- Python 3.9+ with Google's ADK
- FastAPI or Flask for the web framework
- Cloud Run for deployment
- Cloud Build for CI/CD
- Vertex AI for the actual AI capabilities
- Proper containerization with Dockerfile

## Key Deliverables

1. **Complete project structure** with all necessary files
2. **Dockerfile** optimized for Cloud Run
3. **requirements.txt** with all dependencies including Google's ADK
4. **Main application code** implementing A2A protocol
5. **Agent card template** (`agent.json`) with proper capability declarations
6. **Cloud Run deployment configuration** (YAML or gcloud commands)
7. **Testing scripts** to validate A2A compliance
8. **Documentation** explaining the architecture and how to extend capabilities

## A2A Protocol Implementation Requirements

The agent must:
- Register capabilities in the agent card with proper skill definitions
- Handle task requests via JSON-RPC format
- Implement the A2A handshake and discovery mechanism
- Use proper status reporting (pending, running, completed, failed)
- Return artifacts in the expected A2A format
- Support agent-to-agent authentication patterns

## Example Use Case

The secondary agent should be able to:
- Receive a text summarization request from a primary agent (like ServiceNow)
- Process the request using Vertex AI
- Return the summarized text as an artifact
- Handle multiple concurrent requests
- Provide proper status updates during processing

## Development Commands

Since this is a new project, common commands will include:

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally for development
python main.py

# Build Docker image
docker build -t a2a-agent .

# Deploy to Cloud Run
gcloud run deploy a2a-agent --source .

# Run tests
python -m pytest tests/

# Validate A2A compliance
python scripts/test_a2a_compliance.py
```

## Architecture Notes

- The application must expose the agent card at `/.well-known/agent.json` for discovery
- JSON-RPC endpoints handle task requests from primary agents
- Server-Sent Events (SSE) provide real-time status updates
- Vertex AI integration provides the actual AI capabilities
- Authentication layer handles Bearer Token or OAuth validation
- Cloud Run provides scalable, serverless deployment

## Deployment Considerations

- Requires proper IAM roles and service account configurations
- Must include security considerations for production deployment
- Should handle multiple concurrent requests efficiently
- Needs proper error handling and logging for production monitoring
- Agent discovery mechanism must be accessible to primary agents like ServiceNow

## Project Context

The user has a GCP paid account with billing enabled and experience deploying to Cloud Run, with necessary permissions and tooling already set up. The focus should be on step-by-step deployment instructions and explaining how primary agents discover and interact with this secondary agent.

## Current Development Status (Updated: 2025-09-21)

### ✅ COMPLETED - Phase 1: Working A2A Agent (v0.2)

**What's Working:**
- ✅ Complete FastAPI application with A2A protocol compliance
- ✅ All 3 AI capabilities implemented (mock implementations):
  - Text summarization with compression metrics
  - Sentiment analysis with confidence scores
  - Data extraction from unstructured text
- ✅ JSON-RPC 2.0 compliant endpoints
- ✅ Server-Sent Events (SSE) for real-time updates
- ✅ Agent card at `/.well-known/agent.json` for ServiceNow discovery
- ✅ Comprehensive error handling and status management
- ✅ Local testing completed - all endpoints verified working
- ✅ Complete README.md with curl testing commands
- ✅ Version control with tags: v0.1, v0.1.1, v0.2
- ✅ Repository synced to: https://github.com/josuebatista/abcs-a2a-ai-agent-pol.git

**Repository Structure:**
```
├── main.py              # FastAPI app with A2A protocol (WORKING)
├── requirements.txt     # All dependencies specified
├── Dockerfile          # Cloud Run optimized container
├── .well-known/
│   └── agent.json      # Agent discovery card (ServiceNow compatible)
├── README.md           # Complete documentation & test commands
└── CLAUDE.md           # This guidance file
```

**Testing Commands (All Verified Working):**
```bash
# Start application
python main.py

# Test all capabilities - see README.md for complete curl commands
curl -s http://localhost:8080/health | jq .
curl -s http://localhost:8080/.well-known/agent.json | jq .
# Full test suite documented in README.md
```

### 🔄 NEXT STEPS - Phase 2 Options:

**Option A: Testing Infrastructure**
- Add pytest test suite for automated testing
- Create test scripts for CI/CD pipeline
- Add integration tests for A2A protocol compliance

**Option B: Real AI Integration (Recommended Next)**
- Replace mock implementations with actual Vertex AI calls
- Integrate Google Cloud AI Platform for:
  - Real text summarization using PaLM/Gemini
  - Actual sentiment analysis
  - Proper data extraction with NER
- Update agent card with real capability limits

**Option C: Cloud Run Deployment**
- Deploy to Cloud Run with proper IAM setup
- Configure authentication (Bearer tokens)
- Set up monitoring and logging
- Test ServiceNow integration end-to-end

### 🎯 IMMEDIATE NEXT SESSION GOALS:

1. **Choose integration path**: Vertex AI (recommended) or deployment first
2. **For Vertex AI Integration:**
   - Set up Google Cloud AI Platform credentials
   - Replace mock functions in main.py with real AI calls
   - Update capability schemas in agent.json with real limits
   - Test with actual AI processing

3. **For Cloud Run Deployment:**
   - Build and deploy container
   - Configure proper authentication
   - Test from ServiceNow or external primary agent

### 🔧 TECHNICAL NOTES FOR CONTINUATION:

**Current Mock Implementation Locations:**
- `handle_text_summarization()` in main.py:180
- `handle_sentiment_analysis()` in main.py:196
- `handle_data_extraction()` in main.py:210

**Key Files to Modify for Real AI:**
- `main.py`: Replace mock functions with Vertex AI calls
- `requirements.txt`: Add google-cloud-aiplatform specific versions
- `.well-known/agent.json`: Update with real processing limits

**Known Working Endpoints (Ready for ServiceNow):**
- Agent Discovery: `GET /.well-known/agent.json`
- Task Submission: `POST /rpc` (JSON-RPC 2.0)
- Status Check: `GET /tasks/{task_id}`
- Real-time Updates: `GET /tasks/{task_id}/stream` (SSE)

The agent is **fully functional** and **ServiceNow-ready** with mock capabilities. Next phase is to make it production-ready with real AI or deploy as-is for initial integration testing.