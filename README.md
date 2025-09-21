# A2A AI Agent POC

Agent2Agent Protocol compliant AI agent for Google Cloud Platform, designed to be discoverable and orchestrated by primary agents like ServiceNow.

## Overview

This proof-of-concept implements Google's A2A protocol specification with:
- **3 AI Capabilities**: Text summarization, sentiment analysis, and data extraction
- **JSON-RPC 2.0**: Standard protocol for task requests
- **Server-Sent Events**: Real-time status updates
- **Agent Discovery**: Standard `.well-known/agent.json` endpoint
- **Cloud Run Ready**: Optimized for GCP deployment

## Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the application**:
   ```bash
   python main.py
   ```

3. **Access the application**:
   - API Documentation: http://localhost:8080/docs
   - Health Check: http://localhost:8080/health
   - Agent Card: http://localhost:8080/.well-known/agent.json

## Testing the A2A Agent

### 1. Health Check
```bash
curl -s http://localhost:8080/health | jq .
```

### 2. Agent Discovery
```bash
curl -s http://localhost:8080/.well-known/agent.json | jq .
```

### 3. Test Text Summarization
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "text.summarize", "params": {"text": "This is a long text that needs to be summarized. It contains multiple sentences and provides detailed information about various topics. The goal is to create a concise summary that captures the main points without losing important details. This text processing capability will be very useful for A2A protocol compliance and ServiceNow integration."}, "id": "test-summary"}' | jq .

# Check result (wait 3 seconds for processing)
sleep 3 && curl -s http://localhost:8080/tasks/test-summary | jq .
```

### 4. Test Sentiment Analysis
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "text.analyze_sentiment", "params": {"text": "I am very excited about this A2A implementation! It looks great and will work perfectly with ServiceNow."}, "id": "test-sentiment"}' | jq .

# Check result
sleep 2 && curl -s http://localhost:8080/tasks/test-sentiment | jq .
```

### 5. Test Data Extraction
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "data.extract", "params": {"text": "Contact John Smith at john.smith@example.com, phone: 555-1234. Meeting scheduled for 2025-09-22 at Google Cloud offices."}, "id": "test-extract"}' | jq .

# Check result
sleep 2 && curl -s http://localhost:8080/tasks/test-extract | jq .
```

### 6. Test Error Handling
```bash
# Create invalid task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "unsupported.method", "params": {"test": "data"}, "id": "test-error"}' | jq .

# Check error result
sleep 2 && curl -s http://localhost:8080/tasks/test-error | jq .
```

### 7. Test Server-Sent Events (SSE)
```bash
# Stream updates for a completed task (will exit after showing final status)
timeout 5s curl -s http://localhost:8080/tasks/test-summary/stream
```

## A2A Protocol Compliance

### Endpoints

- **Discovery**: `GET /.well-known/agent.json` - Agent capabilities and metadata
- **RPC**: `POST /rpc` - JSON-RPC 2.0 task submission
- **Status**: `GET /tasks/{task_id}` - Task status and results
- **Stream**: `GET /tasks/{task_id}/stream` - Real-time updates via SSE

### Capabilities

1. **text.summarize**
   - Input: `{"text": "string"}`
   - Output: `{"summary": "string", "original_length": int, "summary_length": int, "compression_ratio": float}`

2. **text.analyze_sentiment**
   - Input: `{"text": "string"}`
   - Output: `{"sentiment": "positive|negative|neutral", "confidence": float, "scores": {...}}`

3. **data.extract**
   - Input: `{"text": "string", "schema": {} }`
   - Output: `{"extracted_data": {}, "confidence": float}`

### Status Codes

- `pending`: Task queued for processing
- `running`: Task currently being processed
- `completed`: Task completed successfully
- `failed`: Task processing failed

## Architecture

```
├── main.py              # FastAPI application with A2A protocol
├── requirements.txt     # Python dependencies
├── Dockerfile          # Cloud Run container
├── .well-known/
│   └── agent.json      # Agent discovery card
└── CLAUDE.md           # Development guidelines
```

## Deployment

### Local Testing
```bash
python main.py
```

### Docker Build
```bash
docker build -t a2a-agent .
docker run -p 8080:8080 a2a-agent
```

### Cloud Run Deployment
```bash
gcloud run deploy a2a-agent --source . --platform managed --region us-central1 --allow-unauthenticated
```

## Development Status

- ✅ **v0.1**: Initial project structure
- ✅ **v0.1.1**: Working A2A agent with tested endpoints
- 🔄 **Next**: Vertex AI integration for real AI capabilities
- 🔄 **Next**: Production Cloud Run deployment

## ServiceNow Integration

Once deployed to Cloud Run, ServiceNow can discover this agent by:

1. **Discovery**: GET `https://your-cloudrun-url/.well-known/agent.json`
2. **Task Submission**: POST `https://your-cloudrun-url/rpc` with JSON-RPC payload
3. **Status Monitoring**: GET `https://your-cloudrun-url/tasks/{task_id}` or SSE stream

## Security Notes

- Currently configured for development (authentication disabled)
- Production deployment should enable Bearer token authentication
- IAM roles and service accounts needed for Vertex AI integration

## License

This is a proof-of-concept project for A2A protocol compliance testing.