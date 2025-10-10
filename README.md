# A2A AI Agent Proof-of-Life for Google Cloud Platform

Agent2Agent Protocol compliant AI agent for Google Cloud Platform, designed to be discoverable and orchestrated by primary agents like ServiceNow.

## Overview

This proof-of-concept implements Google's A2A protocol specification with:
- **3 AI Capabilities**: Text summarization, sentiment analysis, and data extraction - all powered by Gemini API
- **JSON-RPC 2.0**: Standard protocol for task requests
- **Server-Sent Events**: Real-time status updates
- **Agent Discovery**: Standard `.well-known/agent-card.json` endpoint (A2A v0.3.0 compliant)
- **Cloud Run Ready**: Optimized for GCP deployment with Secret Manager integration
- **Real AI Integration**: Uses Google Gemini 2.5 Flash API for all AI capabilities

## Prerequisites

- Python 3.9+
- Google Cloud SDK (`gcloud`)
- Docker (for containerized deployment)
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- GCP Project with Cloud Run and Secret Manager enabled

## Quick Start

### 1. API Key Setup

1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Verify your API key works:
   ```bash
   # Replace YOUR_API_KEY with your actual key
   curl -X POST \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents": [{"parts": [{"text": "Say hello"}]}]}'
   ```

### 2. Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd a2a-ai-agent
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and set your GEMINI_API_KEY
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the application**:
   ```bash
   python main.py
   ```

5. **Access the application**:
   - API Documentation: http://localhost:8080/docs
   - Health Check: http://localhost:8080/health
   - Agent Card: http://localhost:8080/.well-known/agent-card.json

## Google Cloud Run Deployment

### Prerequisites
1. Enable required APIs:
   ```bash
   gcloud services enable run.googleapis.com secretmanager.googleapis.com
   ```

2. Create and store API key in Secret Manager:
   ```bash
   # Create secret (use echo -n to avoid newline issues)
   echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
   
   # Verify secret was created correctly
   gcloud secrets versions access latest --secret="gemini-api-key" | wc -c
   # Should return 39 (typical API key length)
   ```

### Deployment Steps

1. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy a2a-agent \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --update-secrets GEMINI_API_KEY=gemini-api-key:latest \
     --memory 512Mi \
     --timeout 300
   ```

2. **Verify deployment**:
   ```bash
   # Get the service URL
   SERVICE_URL=$(gcloud run services describe a2a-agent --region us-central1 --format 'value(status.url)')
   
   # Check health
   curl -s $SERVICE_URL/health | jq .
   ```

## Docker Deployment

### Local Docker Testing

1. **Build the Docker image**:
   ```bash
   docker build -t a2a-agent .
   ```

2. **Run locally with Docker**:
   ```bash
   # Stop any existing containers on port 8080
   docker stop $(docker ps -q --filter "publish=8080")
   
   # Run on port 8080 (or use 8081 if port is busy)
   docker run -p 8080:8080 --rm \
     -e GEMINI_API_KEY="YOUR_API_KEY" \
     --name a2a-test \
     a2a-agent
   ```

3. **Test the containerized application**:
   ```bash
   curl http://localhost:8080/health | jq .
   ```

## Complete Testing Suite

### 1. Health and Discovery
```bash
# Replace SERVICE_URL with your Cloud Run URL or http://localhost:8080 for local

# Health check
curl -s $SERVICE_URL/health | jq .

# Agent discovery (A2A v0.3.0 compliant)
curl -s $SERVICE_URL/.well-known/agent-card.json | jq .
```

### 2. Text Summarization
```bash
# Submit summarization task
curl -s -X POST $SERVICE_URL/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "text.summarize",
    "params": {
      "text": "The James Webb Space Telescope has captured unprecedented images of distant galaxies, revealing star formations that occurred just 300 million years after the Big Bang. These observations challenge existing models of early universe evolution and suggest that galaxy formation began much earlier than previously thought.",
      "max_length": 40
    },
    "id": "summary-test"
  }' | jq .

# Check result
sleep 3 && curl -s $SERVICE_URL/tasks/summary-test | jq .
```

### 3. Sentiment Analysis
```bash
# Positive sentiment test
curl -s -X POST $SERVICE_URL/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "text.analyze_sentiment",
    "params": {
      "text": "This restaurant exceeded all my expectations! The food was absolutely delicious, the service was impeccable, and the atmosphere was perfect."
    },
    "id": "positive-test"
  }' | jq .

sleep 3 && curl -s $SERVICE_URL/tasks/positive-test | jq .

# Negative sentiment test
curl -s -X POST $SERVICE_URL/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "text.analyze_sentiment",
    "params": {
      "text": "Terrible experience. The product broke after two days and customer service was unhelpful."
    },
    "id": "negative-test"
  }' | jq .

sleep 3 && curl -s $SERVICE_URL/tasks/negative-test | jq .
```

### 4. Data Extraction
```bash
# Extract entities
curl -s -X POST $SERVICE_URL/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "data.extract",
    "params": {
      "text": "Microsoft CEO Satya Nadella announced a partnership with OpenAI in San Francisco on January 15th, 2024. Contact: john.smith@microsoft.com or 555-0123."
    },
    "id": "extract-test"
  }' | jq .

sleep 3 && curl -s $SERVICE_URL/tasks/extract-test | jq .
```

### 5. Stream Task Updates (SSE)
```bash
# Submit a task and stream updates
TASK_ID="stream-test-$(date +%s)"

# Submit task
curl -s -X POST https://a2a-agent-298609520814.us-central1.run.app/rpc \
  -H "Content-Type: application/json" \
  -d "{
    \"method\": \"text.summarize\",
    \"params\": {
      \"text\": \"Long text here...\",
      \"max_length\": 50
    },
    \"id\": \"$TASK_ID\"
  }" | jq .

# Stream updates (will show real-time progress)
curl -N https://a2a-agent-298609520814.us-central1.run.app/tasks/$TASK_ID/stream
```

### 6. Check Agent Discovery (A2A Protocol v0.3.0)
```bash
# Get agent capabilities
curl -s https://a2a-agent-298609520814.us-central1.run.app/.well-known/agent-card.json | jq .

# Check health
curl -s https://a2a-agent-298609520814.us-central1.run.app/health | jq .
```

### 7. Performance Test
```bash
# Submit multiple tasks simultaneously
for i in {1..5}; do
  curl -s -X POST https://a2a-agent-298609520814.us-central1.run.app/rpc \
    -H "Content-Type: application/json" \
    -d "{
      \"method\": \"text.analyze_sentiment\",
      \"params\": {
        \"text\": \"Test message $i - This is a great product!\"
      },
      \"id\": \"perf-test-$i\"
    }" &
done

wait
echo "All tasks submitted"

# Check all results
sleep 3
for i in {1..5}; do
  echo "Task perf-test-$i:"
  curl -s https://a2a-agent-298609520814.us-central1.run.app/tasks/perf-test-$i | jq '.status'
done
```

### 8. Batch Testing Script

Save as `test-a2a.sh`:
```bash
#!/bin/bash

BASE_URL="${1:-http://localhost:8080}"

echo "🧪 Testing A2A Agent at $BASE_URL"

test_method() {
    local method=$1
    local params=$2
    local task_id=$3
    local description=$4
    
    echo ""
    echo "📝 Testing: $description"
    
    # Submit task
    response=$(curl -s -X POST "$BASE_URL/rpc" \
        -H "Content-Type: application/json" \
        -d "{\"method\": \"$method\", \"params\": $params, \"id\": \"$task_id\"}")
    
    echo "Task submitted: $task_id"
    sleep 3
    
    # Get results
    result=$(curl -s "$BASE_URL/tasks/$task_id")
    echo "$result" | jq .
}

# Test all methods
test_method "text.summarize" \
    '{"text": "AI is transforming industries. ML models are sophisticated. Companies invest in research.", "max_length": 20}' \
    "test-$(date +%s)-summary" \
    "Text Summarization"

test_method "text.analyze_sentiment" \
    '{"text": "This product is fantastic! I love it!"}' \
    "test-$(date +%s)-sentiment" \
    "Sentiment Analysis"

test_method "data.extract" \
    '{"text": "Google CEO Sundar Pichai presented in Mountain View. Contact: info@google.com"}' \
    "test-$(date +%s)-extract" \
    "Entity Extraction"

echo ""
echo "✅ All tests completed!"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. API Key Issues

**Symptom**: `API_KEY_INVALID` error

**Diagnosis**:
```bash
# Test API key directly
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents": [{"parts": [{"text": "test"}]}]}'
```

**Solutions**:
- Ensure you're using a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Verify the key has no trailing spaces or newlines
- Regenerate the key if needed

#### 2. Cloud Run Secret Not Loading

**Symptom**: Health check shows `"api_key_loaded": false`

**Diagnosis**:
```bash
# Check service configuration
gcloud run services describe a2a-agent \
  --region us-central1 \
  --format="json" | jq '.spec.template.spec.containers[0].env'

# Verify secret access
SERVICE_ACCOUNT=$(gcloud run services describe a2a-agent \
  --region us-central1 \
  --format='value(spec.template.spec.serviceAccountName)')

gcloud secrets get-iam-policy gemini-api-key
```

**Solutions**:
```bash
# Grant service account access to secret
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

# Redeploy with --update-secrets flag
gcloud run deploy a2a-agent \
  --source . \
  --region us-central1 \
  --update-secrets GEMINI_API_KEY=gemini-api-key:latest
```

#### 3. Docker Port Already in Use

**Diagnosis**:
```bash
# Find what's using port 8080
lsof -i :8080
docker ps --filter "publish=8080"
```

**Solutions**:
```bash
# Option 1: Stop conflicting containers
docker stop $(docker ps -q --filter "publish=8080")

# Option 2: Use different port
docker run -p 8081:8080 --rm \
  -e GEMINI_API_KEY="YOUR_KEY" \
  a2a-agent
```

#### 4. Data Extraction JSON Parse Errors

**Symptom**: `Failed to parse extraction response` error

**Solution**: The application includes fallback regex extraction for emails and phones. If Gemini returns malformed JSON, basic entities will still be extracted.

### Debug Endpoints

The application includes debug endpoints for troubleshooting:

```bash
# Debug configuration (remove in production)
curl -s $SERVICE_URL/debug/config | jq .

# Direct Gemini test
curl -s $SERVICE_URL/test/direct | jq .
```

### Cloud Run Logs

View application logs for detailed debugging:
```bash
# View recent logs
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 50

# Filter for errors
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 100 | grep -E "ERROR|Failed|Exception"

# Monitor logs in real-time
gcloud alpha run services logs tail a2a-agent --region us-central1
```

## Architecture

```
├── main.py              # FastAPI application with A2A protocol
├── requirements.txt     # Python dependencies  
├── Dockerfile          # Cloud Run container with environment fixes
├── .well-known/
│   └── agent-card.json # Agent discovery card (A2A v0.3.0)
├── .env.example        # Environment variable template
└── README.md           # This file
```

## Key Features

### Gemini 2.5 Flash Integration
- Uses latest `gemini-2.5-flash` model for optimal performance
- REST transport to avoid gRPC metadata conflicts in Cloud Run
- Automatic retry logic for transient failures
- Comprehensive error handling with fallbacks

### Security
- API keys stored in Google Secret Manager
- Environment variable isolation in Docker
- No credentials in code or logs
- Automatic credential conflict resolution

### Performance
- Async task processing with progress tracking
- 30-second timeout for AI operations
- Automatic scaling with Cloud Run
- Health checks and monitoring endpoints

## Development Status

- ✅ **v0.1**: Initial project structure
- ✅ **v0.2**: Working A2A agent with mock capabilities
- ✅ **v0.3**: Real AI integration with Vertex AI
- ✅ **v0.4**: Migrated to Gemini API
- ✅ **v0.5**: Production Cloud Run deployment with Secret Manager
- ✅ **v0.6**: A2A Protocol v0.3.0 compliance - agent-card.json migration
- ✅ **v0.7**: Full A2A Protocol v0.3.0 compliance - complete schema migration (current)
- 🔄 **Next**: Enhanced authentication and rate limiting for production

## Contributing
- Fork the repository
- Create your feature branch (git checkout -b feature/amazing-feature)
- Commit your changes (git commit -m 'Add some amazing feature')
- Push to the branch (git push origin feature/amazing-feature)
- Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.
