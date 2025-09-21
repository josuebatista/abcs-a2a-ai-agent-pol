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