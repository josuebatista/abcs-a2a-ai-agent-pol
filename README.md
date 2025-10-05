# A2A AI Agent POC

Agent2Agent Protocol compliant AI agent for Google Cloud Platform, designed to be discoverable and orchestrated by primary agents like ServiceNow.

## Overview

This proof-of-concept implements Google's A2A protocol specification with:
- **3 AI Capabilities**: Text summarization (Gemini), sentiment analysis (Natural Language API), and data extraction (Entity Recognition)
- **JSON-RPC 2.0**: Standard protocol for task requests
- **Server-Sent Events**: Real-time status updates
- **Agent Discovery**: Standard `.well-known/agent.json` endpoint
- **Cloud Run Ready**: Optimized for GCP deployment
- **Real AI Integration**: Uses Vertex AI and Google Cloud Natural Language API

## Prerequisites

- Python 3.9+
- Google Cloud Platform account with billing enabled
- GCP Project with the following APIs enabled:
  - Vertex AI API
  - Cloud Natural Language API
- Service account with permissions:
  - Vertex AI User
  - Cloud Natural Language API User

## Quick Start

### 1. GCP Setup

Enable required APIs:
```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable language.googleapis.com
```

Set up authentication (choose one method):

**Option A: Service Account Key (Local Development)**
```bash
gcloud iam service-accounts create a2a-agent-sa
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:a2a-agent-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:a2a-agent-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudlanguage.admin"
gcloud iam service-accounts keys create key.json \
  --iam-account=a2a-agent-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/key.json"
```

**Option B: Application Default Credentials**
```bash
gcloud auth application-default login
```

### 2. Local Development

1. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and set your GCP_PROJECT_ID
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application**:
   ```bash
   python main.py
   ```

4. **Access the application**:
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

### 3. Test Text Summarization (Real Gemini API)
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "text.summarize", "params": {"text": "This is a long text that needs to be summarized. It contains multiple sentences and provides detailed information about various topics. The goal is to create a concise summary that captures the main points without losing important details. This text processing capability will be very useful for A2A protocol compliance and ServiceNow integration."}, "id": "test-summary"}' | jq .

# Check result (wait 5 seconds for Gemini processing)
sleep 5 && curl -s http://localhost:8080/tasks/test-summary | jq .
```

### 4. Test Sentiment Analysis (Real Natural Language API)
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "text.analyze_sentiment", "params": {"text": "I am very excited about this A2A implementation! It looks great and will work perfectly with ServiceNow."}, "id": "test-sentiment"}' | jq .

# Check result
sleep 3 && curl -s http://localhost:8080/tasks/test-sentiment | jq .
```

### 5. Test Data Extraction (Real Entity Recognition)
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "data.extract", "params": {"text": "Contact John Smith at john.smith@example.com, phone: 555-1234. Meeting scheduled for 2025-09-22 at Google Cloud offices."}, "id": "test-extract"}' | jq .

# Check result
sleep 3 && curl -s http://localhost:8080/tasks/test-extract | jq .
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
- ✅ **v0.2**: Working A2A agent with mock capabilities
- ✅ **v0.3**: Real AI integration with Vertex AI and Natural Language API
- 🔄 **Next**: Production Cloud Run deployment with authentication

## ServiceNow Integration

Once deployed to Cloud Run, ServiceNow can discover this agent by:

1. **Discovery**: GET `https://your-cloudrun-url/.well-known/agent.json`
2. **Task Submission**: POST `https://your-cloudrun-url/rpc` with JSON-RPC payload
3. **Status Monitoring**: GET `https://your-cloudrun-url/tasks/{task_id}` or SSE stream

## Security Notes

- Authentication currently disabled for development (`"required": false` in agent.json)
- Production deployment should enable Bearer token authentication
- Service account credentials required for Vertex AI and Natural Language API access
- Keep service account keys secure - never commit to version control
- For Cloud Run deployment, use Cloud Run service accounts instead of keys

## AI Capabilities

### Text Summarization
- **Model**: Gemini 1.5 Flash
- **Max Input**: 10,000 characters
- **Processing Time**: ~3-5 seconds
- **Features**: Configurable summary length, compression metrics

### Sentiment Analysis
- **API**: Google Cloud Natural Language API
- **Max Input**: 5,000 characters
- **Processing Time**: ~1-3 seconds
- **Output**: Sentiment label (positive/negative/neutral), confidence scores

### Data Extraction
- **API**: Google Cloud Natural Language API (Entity Recognition)
- **Max Input**: 10,000 characters
- **Processing Time**: ~1-3 seconds
- **Entities**: Persons, locations, organizations, dates, events, phone numbers, emails

## License

This is a proof-of-concept project for A2A protocol compliance testing.