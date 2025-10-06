# A2A AI Agent POC

Agent2Agent Protocol compliant AI agent for Google Cloud Platform, designed to be discoverable and orchestrated by primary agents like ServiceNow.

## Overview

This proof-of-concept implements Google's A2A protocol specification with:
- **3 AI Capabilities**: Text summarization, sentiment analysis, and data extraction - all powered by Gemini API
- **JSON-RPC 2.0**: Standard protocol for task requests
- **Server-Sent Events**: Real-time status updates
- **Agent Discovery**: Standard `.well-known/agent.json` endpoint
- **Cloud Run Ready**: Optimized for GCP deployment
- **Real AI Integration**: Uses Google Gemini API for all AI capabilities

## Prerequisites

- Python 3.9+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Quick Start

### 1. API Key Setup

Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### 2. Local Development

1. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and set your GEMINI_API_KEY
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

### 3. Test Text Summarization (Gemini API)
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "text.summarize", "params": {"text": "Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass one-thousandth that of the Sun, but two-and-a-half times that of all the other planets in the Solar System combined.", "max_length": 50}, "id": "test-summary"}' | jq .

# Check result (wait 5 seconds for Gemini processing)
sleep 5 && curl -s http://localhost:8080/tasks/test-summary | jq .
```

### 4. Test Sentiment Analysis (Gemini API)
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "text.analyze_sentiment", "params": {"text": "I am very happy with the new product. It is amazing"}, "id": "test-sentiment"}' | jq .

# Check result
sleep 5 && curl -s http://localhost:8080/tasks/test-sentiment | jq .
```

### 5. Test Data Extraction (Gemini API)
```bash
# Create task
curl -s -X POST http://localhost:8080/rpc -H "Content-Type: application/json" -d '{"method": "data.extract", "params": {"text": "John Doe, the CEO of Acme Inc., will be in New York on Monday, October 28, 2025 for the annual Acme conference. He can be reached at john.doe@acmeinc.com or at 555-123-4567."}, "id": "test-extract"}' | jq .

# Check result
sleep 5 && curl -s http://localhost:8080/tasks/test-extract | jq .
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
- ✅ **v0.4**: Migrated to Gemini API for all AI capabilities (simplified architecture)
- 🔄 **Next**: Production Cloud Run deployment with authentication

## ServiceNow Integration

Once deployed to Cloud Run, ServiceNow can discover this agent by:

1. **Discovery**: GET `https://your-cloudrun-url/.well-known/agent.json`
2. **Task Submission**: POST `https://your-cloudrun-url/rpc` with JSON-RPC payload
3. **Status Monitoring**: GET `https://your-cloudrun-url/tasks/{task_id}` or SSE stream

## Security Notes

- Authentication currently disabled for development (`"required": false` in agent.json)
- Production deployment should enable Bearer token authentication
- **IMPORTANT**: Never commit `.env` file with your actual `GEMINI_API_KEY` to version control
- Store API keys securely using environment variables or secret management services
- For Cloud Run deployment, use Secret Manager to store the Gemini API key

## AI Capabilities

All three capabilities are powered by **Google Gemini API** (`gemini-pro-latest` model):

### Text Summarization
- **Model**: Gemini Pro (via Gemini API)
- **Max Input**: Configurable (default: 100 words)
- **Processing Time**: ~3-5 seconds
- **Features**: Configurable summary length, compression metrics

### Sentiment Analysis
- **Model**: Gemini Pro (via Gemini API)
- **Max Input**: 5,000 characters
- **Processing Time**: ~3-5 seconds
- **Output**: Sentiment label (positive/negative/neutral), confidence scores with detailed breakdown

### Data Extraction
- **Model**: Gemini Pro (via Gemini API)
- **Max Input**: 10,000 characters
- **Processing Time**: ~3-5 seconds
- **Entities**: Persons, locations, organizations, dates, events, phone numbers, emails
- **Output**: Structured JSON with entity names and salience scores

## License

This is a proof-of-concept project for A2A protocol compliance testing.