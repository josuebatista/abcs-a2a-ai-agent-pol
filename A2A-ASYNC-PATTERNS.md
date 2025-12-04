# A2A Protocol Asynchronous Patterns Guide

**Version**: v0.10.0
**Date**: 2025-11-06
**Protocol**: A2A Protocol v0.3.0

---

## Table of Contents

1. [Overview](#overview)
2. [Why Asynchronous?](#why-asynchronous)
3. [Pattern 1: message/send + Polling](#pattern-1-messagesend--polling)
4. [Pattern 2: message/send + SSE Streaming](#pattern-2-messagesend--sse-streaming)
5. [Pattern 3: message/send + tasks/list](#pattern-3-messagesend--taskslist)
6. [Complete Examples](#complete-examples)
7. [Best Practices](#best-practices)
8. [Error Handling](#error-handling)

---

## Overview

The A2A Protocol uses an **asynchronous request-response pattern** to handle long-running AI operations without blocking HTTP connections.

### The Async Flow

```
Client                    A2A Agent                  AI Service
  |                          |                           |
  |-- 1. message/send ------>|                           |
  |<-- taskId + pending -----|                           |
  |                          |-- 2. Process ------------>|
  |                          |<-- AI Response ----------|
  |-- 3. tasks/get --------->|                           |
  |<-- result + completed ---|                           |
```

**Key Concepts**:
- `message/send` returns **immediately** with a `taskId`
- Task status: `pending` → `running` → `completed`/`failed`
- Client **polls** or **streams** to get the final result

---

## Why Asynchronous?

### Problem: Synchronous AI Calls

```
❌ BLOCKED for 2-10 seconds
Client --[HTTP Request]---> Agent --[AI Processing]---> Response
       (waiting... waiting... timeout risk!)
```

### Solution: Asynchronous Pattern

```
✅ Immediate Response
Client --[message/send]---> Agent
       <--[taskId]----------

Later...
Client --[tasks/get]------> Agent
       <--[result]----------
```

**Benefits**:
- No HTTP timeout issues (AI processing can take minutes)
- Client can do other work while waiting
- Multiple tasks can be submitted in parallel
- Real-time progress updates via SSE

---

## Pattern 1: message/send + Polling

**Use Case**: Simple client, willing to poll for results

### Step 1: Submit Task

**Request**:
```bash
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "Summarize this article in 50 words: Artificial intelligence is transforming industries worldwide. Machine learning models are becoming increasingly sophisticated, enabling new applications in healthcare, finance, and education. The impact of AI on society continues to grow exponentially."
          }
        ]
      }
    },
    "id": "req-1"
  }'
```

**Response** (Immediate - <100ms):
```json
{
  "jsonrpc": "2.0",
  "result": {
    "taskId": "abc123-def456-ghi789",
    "status": "pending"
  },
  "id": "req-1"
}
```

### Step 2: Wait (AI Processing)

```bash
# Wait 3-5 seconds for AI to process
sleep 5
```

**What's happening**:
- Task status changes: `pending` → `running`
- AI model (Gemini) processes the request
- Result is stored in task object

### Step 3: Retrieve Result via tasks/get (RPC Method)

**Request**:
```bash
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {
      "taskId": "abc123-def456-ghi789"
    },
    "id": "get-1"
  }'
```

**Response** (When completed):
```json
{
  "jsonrpc": "2.0",
  "result": {
    "task_id": "abc123-def456-ghi789",
    "status": "completed",
    "skill": "summarization",
    "message": "Summarize this article in 50 words: ...",
    "created_at": "2025-11-06T12:30:00.000Z",
    "created_by": "Primary Key",
    "result": {
      "summary": "AI is transforming healthcare, finance, and education through increasingly sophisticated machine learning models. The technology's societal impact grows exponentially as new applications emerge across industries worldwide.",
      "original_length": 256,
      "summary_length": 185,
      "compression_ratio": 1.38,
      "model_used": "gemini-2.5-flash"
    },
    "error": null,
    "progress": 100,
    "completed_at": "2025-11-06T12:30:03.456Z"
  },
  "id": "get-1"
}
```

### Step 3 (Alternative): Retrieve Result via REST Endpoint

**Request** (Simpler!):
```bash
curl https://a2a-agent-298609520814.us-central1.run.app/tasks/abc123-def456-ghi789 \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
```

**Response**: Same as above (without JSON-RPC wrapper)

### Polling Loop Pattern

**JavaScript Example**:
```javascript
async function submitAndWait(message) {
  // Step 1: Submit task
  const submitResponse = await fetch('https://a2a-agent-298609520814.us-central1.run.app/', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'message/send',
      params: { message },
      id: 'submit-1'
    })
  });

  const { result } = await submitResponse.json();
  const taskId = result.taskId;

  // Step 2: Poll for result
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds

    const taskResponse = await fetch(
      `https://a2a-agent-298609520814.us-central1.run.app/tasks/${taskId}`,
      {
        headers: {
          'Authorization': 'Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA='
        }
      }
    );

    const task = await taskResponse.json();

    if (task.status === 'completed') {
      return task.result;
    } else if (task.status === 'failed') {
      throw new Error(task.error);
    }
    // Continue polling if pending/running
  }
}

// Usage
const result = await submitAndWait({
  role: 'user',
  parts: [{ type: 'text', text: 'Summarize: AI is transforming industries.' }]
});
console.log(result.summary);
```

**Python Example**:
```python
import requests
import time
import json

def submit_and_wait(message_text):
    base_url = "https://a2a-agent-298609520814.us-central1.run.app"
    headers = {
        "Authorization": "Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=",
        "Content-Type": "application/json"
    }

    # Step 1: Submit task
    submit_payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message_text}]
            }
        },
        "id": "submit-1"
    }

    response = requests.post(f"{base_url}/rpc", headers=headers, json=submit_payload)
    task_id = response.json()["result"]["taskId"]

    # Step 2: Poll for result
    while True:
        time.sleep(2)  # Wait 2 seconds

        task_response = requests.get(f"{base_url}/tasks/{task_id}", headers=headers)
        task = task_response.json()

        if task["status"] == "completed":
            return task["result"]
        elif task["status"] == "failed":
            raise Exception(task["error"])
        # Continue polling if pending/running

# Usage
result = submit_and_wait("Summarize: AI is transforming industries.")
print(result["summary"])
```

---

## Pattern 2: message/send + SSE Streaming

**Use Case**: Real-time updates, progress monitoring

### Step 1: Submit Task (Same as Pattern 1)

```bash
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Analyze sentiment: This product is amazing!"}]
      }
    },
    "id": "req-1"
  }'
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "taskId": "xyz789-abc123",
    "status": "pending"
  },
  "id": "req-1"
}
```

### Step 2: Open SSE Stream

**Request**:
```bash
curl -N https://a2a-agent-298609520814.us-central1.run.app/tasks/xyz789-abc123/stream \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
```

**Response** (Server-Sent Events):
```
data: {"status": "pending", "progress": 0}

data: {"status": "running", "progress": 50}

data: {"status": "completed", "progress": 100, "result": {"sentiment": "positive", "confidence": 0.95}}
```

### JavaScript SSE Example

```javascript
function streamTask(taskId) {
  const eventSource = new EventSource(
    `https://a2a-agent-298609520814.us-central1.run.app/tasks/${taskId}/stream`,
    {
      headers: {
        'Authorization': 'Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA='
      }
    }
  );

  eventSource.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log(`Status: ${update.status}, Progress: ${update.progress}%`);

    if (update.status === 'completed') {
      console.log('Result:', update.result);
      eventSource.close();
    } else if (update.status === 'failed') {
      console.error('Error:', update.error);
      eventSource.close();
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
    eventSource.close();
  };
}

// Usage
streamTask('xyz789-abc123');
```

### Python SSE Example

```python
import requests
import json

def stream_task(task_id):
    url = f"https://a2a-agent-298609520814.us-central1.run.app/tasks/{task_id}/stream"
    headers = {
        "Authorization": "Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
    }

    with requests.get(url, headers=headers, stream=True) as response:
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                    print(f"Status: {data['status']}, Progress: {data.get('progress', 0)}%")

                    if data['status'] == 'completed':
                        print(f"Result: {data['result']}")
                        break
                    elif data['status'] == 'failed':
                        print(f"Error: {data['error']}")
                        break

# Usage
stream_task('xyz789-abc123')
```

---

## Pattern 3: message/send + tasks/list

**Use Case**: Batch processing, checking multiple tasks

### Step 1: Submit Multiple Tasks

```bash
# Task 1: Summarization
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Summarize: Document 1"}]
      }
    },
    "id": "batch-1"
  }'

# Task 2: Sentiment Analysis
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Sentiment: Review text"}]
      }
    },
    "id": "batch-2"
  }'

# Task 3: Entity Extraction
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Extract entities: Text"}]
      }
    },
    "id": "batch-3"
  }'
```

### Step 2: Wait for Processing

```bash
sleep 5
```

### Step 3: List All Tasks

**Request** (Get all tasks):
```bash
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {},
    "id": "list-all"
  }'
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tasks": [
      {
        "task_id": "task-3-id",
        "status": "completed",
        "skill": "entity-extraction",
        "created_at": "2025-11-06T12:35:02.000Z",
        "result": {...}
      },
      {
        "task_id": "task-2-id",
        "status": "completed",
        "skill": "sentiment-analysis",
        "created_at": "2025-11-06T12:35:01.000Z",
        "result": {...}
      },
      {
        "task_id": "task-1-id",
        "status": "completed",
        "skill": "summarization",
        "created_at": "2025-11-06T12:35:00.000Z",
        "result": {...}
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "totalTasks": 3,
      "totalPages": 1,
      "hasNextPage": false,
      "hasPreviousPage": false
    }
  },
  "id": "list-all"
}
```

### Step 4: Filter Completed Tasks Only

**Request**:
```bash
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {
      "status": "completed"
    },
    "id": "list-completed"
  }'
```

### Step 5: Filter by Skill

**Request** (Get only summarization tasks):
```bash
curl -X POST https://a2a-agent-298609520814.us-central1.run.app/ \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {
      "skill": "summarization"
    },
    "id": "list-summarization"
  }'
```

### Python Batch Processing Example

```python
import requests
import time
import json

base_url = "https://a2a-agent-298609520814.us-central1.run.app"
headers = {
    "Authorization": "Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=",
    "Content-Type": "application/json"
}

# Submit batch of tasks
messages = [
    "Summarize: Document 1 content...",
    "Summarize: Document 2 content...",
    "Summarize: Document 3 content..."
]

task_ids = []
for i, msg in enumerate(messages):
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": msg}]
            }
        },
        "id": f"batch-{i}"
    }
    response = requests.post(f"{base_url}/rpc", headers=headers, json=payload)
    task_id = response.json()["result"]["taskId"]
    task_ids.append(task_id)
    print(f"Submitted task {i+1}: {task_id}")

# Wait for all to complete
print("\nWaiting 10 seconds for processing...")
time.sleep(10)

# Get all completed tasks
list_payload = {
    "jsonrpc": "2.0",
    "method": "tasks/list",
    "params": {"status": "completed"},
    "id": "list-1"
}
response = requests.post(f"{base_url}/rpc", headers=headers, json=list_payload)
tasks = response.json()["result"]["tasks"]

print(f"\nCompleted tasks: {len(tasks)}")
for task in tasks:
    print(f"- {task['task_id']}: {task['skill']}")
    if task.get('result'):
        print(f"  Summary: {task['result'].get('summary', 'N/A')[:100]}...")
```

---

## Complete Examples

### Example 1: Full Summarization Flow

**Windows (PowerShell)**:
```powershell
$apiKey = "fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
$baseUrl = "https://a2a-agent-298609520814.us-central1.run.app"
$headers = @{
    "Authorization" = "Bearer $apiKey"
    "Content-Type" = "application/json"
}

# Step 1: Submit task
$body = @{
    jsonrpc = "2.0"
    method = "message/send"
    params = @{
        message = @{
            role = "user"
            parts = @(
                @{
                    type = "text"
                    text = "Summarize in 30 words: AI is revolutionizing industries."
                }
            )
        }
    }
    id = "ps-test"
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod -Uri "$baseUrl/rpc" -Method Post -Headers $headers -Body $body
$taskId = $response.result.taskId
Write-Host "Task ID: $taskId"

# Step 2: Wait
Write-Host "Waiting 5 seconds..."
Start-Sleep -Seconds 5

# Step 3: Get result
$result = Invoke-RestMethod -Uri "$baseUrl/tasks/$taskId" -Method Get -Headers @{"Authorization"="Bearer $apiKey"}
Write-Host "Status: $($result.status)"
Write-Host "Summary: $($result.result.summary)"
```

### Example 2: Sentiment Analysis with Error Handling

**Bash**:
```bash
#!/bin/bash
API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
BASE_URL="https://a2a-agent-298609520814.us-central1.run.app"

# Submit task
response=$(curl -s -X POST "$BASE_URL/rpc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Sentiment: This is terrible!"}]
      }
    },
    "id": "sentiment-1"
  }')

# Check for errors in submission
if echo "$response" | grep -q "error"; then
  echo "Error submitting task:"
  echo "$response" | jq .
  exit 1
fi

# Extract task ID
task_id=$(echo "$response" | jq -r '.result.taskId')
echo "Task ID: $task_id"

# Poll with timeout
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
  sleep 2
  attempt=$((attempt + 1))

  result=$(curl -s "$BASE_URL/tasks/$task_id" \
    -H "Authorization: Bearer $API_KEY")

  status=$(echo "$result" | jq -r '.status')
  echo "Attempt $attempt: Status = $status"

  if [ "$status" = "completed" ]; then
    echo "Success!"
    echo "$result" | jq '.result'
    exit 0
  elif [ "$status" = "failed" ]; then
    echo "Task failed:"
    echo "$result" | jq '.error'
    exit 1
  fi
done

echo "Timeout: Task did not complete in time"
exit 1
```

### Example 3: Batch Processing with Filtering

**Node.js**:
```javascript
const fetch = require('node-fetch');

const API_KEY = 'fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=';
const BASE_URL = 'https://a2a-agent-298609520814.us-central1.run.app';

async function batchProcess() {
  const headers = {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  };

  // Submit 5 tasks
  const messages = [
    'Summarize: Article 1',
    'Summarize: Article 2',
    'Sentiment: Review 1',
    'Sentiment: Review 2',
    'Extract entities: Document 1'
  ];

  console.log('Submitting tasks...');
  const submissions = messages.map((text, i) =>
    fetch(`${BASE_URL}/rpc`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'message/send',
        params: {
          message: {
            role: 'user',
            parts: [{ type: 'text', text }]
          }
        },
        id: `batch-${i}`
      })
    }).then(r => r.json())
  );

  const results = await Promise.all(submissions);
  console.log(`Submitted ${results.length} tasks`);

  // Wait for processing
  console.log('Waiting 10 seconds...');
  await new Promise(resolve => setTimeout(resolve, 10000));

  // Get all completed summarization tasks
  const listResponse = await fetch(`${BASE_URL}/rpc`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'tasks/list',
      params: {
        status: 'completed',
        skill: 'summarization'
      },
      id: 'list-1'
    })
  });

  const { result } = await listResponse.json();
  console.log(`\nCompleted summarization tasks: ${result.tasks.length}`);

  result.tasks.forEach(task => {
    console.log(`\nTask: ${task.task_id}`);
    console.log(`Summary: ${task.result?.summary?.substring(0, 100)}...`);
  });
}

batchProcess().catch(console.error);
```

---

## Best Practices

### 1. **Always Handle Async Nature**

❌ **Wrong** (assuming synchronous):
```javascript
const response = await fetch('/rpc', { method: 'message/send', ... });
const summary = response.result.summary; // undefined! No summary yet
```

✅ **Correct** (handle async):
```javascript
// Submit
const submitResponse = await fetch('/rpc', { method: 'message/send', ... });
const taskId = submitResponse.result.taskId;

// Wait and retrieve
await sleep(3000);
const taskResponse = await fetch(`/tasks/${taskId}`);
const summary = taskResponse.result.summary; // ✓ Available
```

### 2. **Use Appropriate Wait Times**

| Task Type | Typical Time | Recommended Wait |
|-----------|--------------|------------------|
| Summarization (short) | 2-5 seconds | 3 seconds |
| Summarization (long) | 5-10 seconds | 7 seconds |
| Sentiment Analysis | 1-3 seconds | 2 seconds |
| Entity Extraction | 2-4 seconds | 3 seconds |

### 3. **Implement Timeout Logic**

```javascript
async function pollWithTimeout(taskId, timeoutMs = 30000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const task = await getTask(taskId);

    if (task.status === 'completed') return task.result;
    if (task.status === 'failed') throw new Error(task.error);

    await sleep(2000);
  }

  throw new Error('Task timeout');
}
```

### 4. **Use SSE for Long-Running Tasks**

If task > 10 seconds, prefer SSE over polling:
- **Polling**: Multiple HTTP requests, higher latency
- **SSE**: Single connection, real-time updates

### 5. **Batch Similar Tasks**

Submit multiple tasks at once, then use `tasks/list` with filters:
```javascript
// Submit 100 summarization tasks
const taskIds = await submitBatch(documents);

// Check completion status
const { tasks } = await listTasks({ skill: 'summarization', status: 'completed' });
console.log(`${tasks.length}/100 completed`);
```

### 6. **Handle All Task States**

```javascript
switch (task.status) {
  case 'pending':
  case 'running':
    // Continue waiting
    break;
  case 'completed':
    // Success - use task.result
    break;
  case 'failed':
    // Error - show task.error
    break;
  case 'canceled':
    // User canceled - handle gracefully
    break;
  case 'input-required':
    // Need more input from user
    break;
  default:
    console.warn('Unknown status:', task.status);
}
```

---

## Error Handling

### Common Error Scenarios

#### 1. Invalid Task ID

**Request**:
```bash
curl https://a2a-agent-298609520814.us-central1.run.app/tasks/invalid-id \
  -H "Authorization: Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
```

**Response**:
```json
{
  "error": "Task not found",
  "taskId": "invalid-id"
}
```

#### 2. Task Failed During Processing

**Response**:
```json
{
  "task_id": "abc123",
  "status": "failed",
  "error": "AI model timeout",
  "failed_at": "2025-11-06T12:30:15.000Z"
}
```

#### 3. Authentication Error

**Response**:
```json
{
  "detail": "Invalid authentication token"
}
```

**Fix**: Check your API key is correct

#### 4. Rate Limiting (Future)

**Response**:
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

### Error Handling Code

```javascript
async function safeGetTask(taskId) {
  try {
    const response = await fetch(
      `https://a2a-agent-298609520814.us-central1.run.app/tasks/${taskId}`,
      {
        headers: {
          'Authorization': 'Bearer fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA='
        }
      }
    );

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Authentication failed - check API key');
      } else if (response.status === 404) {
        throw new Error(`Task ${taskId} not found`);
      } else if (response.status === 429) {
        throw new Error('Rate limit exceeded - retry later');
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const task = await response.json();

    if (task.status === 'failed') {
      throw new Error(`Task failed: ${task.error}`);
    }

    return task;
  } catch (error) {
    console.error('Error fetching task:', error.message);
    throw error;
  }
}
```

---

## Quick Reference

### All Available Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `message/send` | Submit AI task | `taskId` + `pending` |
| `tasks/get` | Get single task | Full task object |
| `tasks/list` | List user's tasks | Paginated task array |
| `GET /tasks/{id}` | Get task (REST) | Full task object |
| `GET /tasks/{id}/stream` | Stream updates (SSE) | Real-time events |

### Task Statuses

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `pending` | Queued | Wait or stream |
| `running` | Processing | Wait or stream |
| `completed` | Done ✓ | Get result |
| `failed` | Error ✗ | Check error field |
| `canceled` | User canceled | N/A |
| `input-required` | Need input | Provide input |
| `auth-required` | Need auth | Authenticate |
| `rejected` | Rejected | Check reason |

### Helper Scripts

Quick commands available in this repo:

```bash
# Send and wait automatically
./send-and-wait.sh "Your message here"
./send-and-wait.bat "Your message here"  # Windows

# Run comprehensive tests
./test-message-send.sh http://localhost:8080 API_KEY
./test-tasks-list.sh http://localhost:8080 API_KEY
```

---

## Summary

The A2A Protocol's asynchronous pattern enables:
- ✅ Non-blocking AI operations
- ✅ Long-running task support (minutes/hours)
- ✅ Real-time progress updates
- ✅ Batch processing capabilities
- ✅ Reliable delivery without timeouts

**Key Takeaway**: Always use the two-step pattern:
1. `message/send` → Get `taskId`
2. `tasks/get` or SSE → Get result

---

**Questions?** See:
- [LOCAL-TESTING-GUIDE.md](./LOCAL-TESTING-GUIDE.md) - Complete testing examples
- [PHASE-1-IMPLEMENTATION.md](./PHASE-1-IMPLEMENTATION.md) - Implementation details
- [PHASE-2.1-IMPLEMENTATION.md](./PHASE-2.1-IMPLEMENTATION.md) - tasks/list details
- [test-payloads-examples.json](./test-payloads-examples.json) - All JSON payloads

**Production URL**: https://a2a-agent-298609520814.us-central1.run.app
**Current Version**: v0.10.0 (90% A2A Protocol v0.3.0 compliant)
