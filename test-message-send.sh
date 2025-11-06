#!/bin/bash

# Test script for A2A Protocol v0.3.0 message/send implementation
# Tests the new natural language interface

set -e

BASE_URL="${1:-http://localhost:8080}"
API_KEY="${2}"

if [ -z "$API_KEY" ]; then
    echo "❌ Error: API_KEY required"
    echo "Usage: $0 <base_url> <api_key>"
    echo "Example: $0 http://localhost:8080 your-api-key"
    exit 1
fi

echo "=========================================="
echo "A2A Protocol message/send Test Suite"
echo "Service: $BASE_URL"
echo "=========================================="
echo

PASS=0
FAIL=0

test_case() {
    local name="$1"
    local method="$2"
    local message="$3"
    local expected_skill="$4"

    echo -n "Testing: $name... "

    response=$(curl -s -X POST "$BASE_URL/rpc" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "method": "'"$method"'",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {"type": "text", "text": "'"$message"'"}
                    ]
                }
            },
            "id": "test-'"$(date +%s)"'"
        }')

    task_id=$(echo "$response" | jq -r '.result.taskId // empty')

    if [ -n "$task_id" ]; then
        echo "✓ PASS (Task ID: $task_id)"
        ((PASS++))

        # Wait for processing
        sleep 3

        # Check result
        result=$(curl -s "$BASE_URL/tasks/$task_id" \
            -H "Authorization: Bearer $API_KEY")

        status=$(echo "$result" | jq -r '.status')
        echo "  Status: $status"
    else
        echo "✗ FAIL"
        echo "  Response: $response"
        ((FAIL++))
    fi
}

echo "=== Test 1: message/send - Summarization Intent ==="
test_case \
    "Summarization via natural language" \
    "message/send" \
    "Summarize this text: AI is transforming industries worldwide. Machine learning models are becoming more sophisticated every day." \
    "summarization"

echo
echo "=== Test 2: message/send - Sentiment Analysis Intent ==="
test_case \
    "Sentiment analysis via natural language" \
    "message/send" \
    "What's the sentiment of this review: This product is absolutely fantastic! I love it!" \
    "sentiment-analysis"

echo
echo "=== Test 3: message/send - Entity Extraction Intent ==="
test_case \
    "Entity extraction via natural language" \
    "message/send" \
    "Extract entities: Microsoft CEO Satya Nadella spoke in Seattle on January 15th. Contact: info@microsoft.com" \
    "entity-extraction"

echo
echo "=== Test 4: message/send - With Length Specification ==="
test_case \
    "Summarization with length in message" \
    "message/send" \
    "Summarize this in 20 words: Artificial intelligence and machine learning are revolutionizing industries. Companies are investing heavily in AI research and development." \
    "summarization"

echo
echo "=== Test 5: Legacy Method (Backwards Compatibility) ==="
echo -n "Testing: Legacy text.summarize... "

legacy_response=$(curl -s -X POST "$BASE_URL/rpc" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "text.summarize",
        "params": {
            "text": "Test text",
            "max_length": 20
        },
        "id": "legacy-test"
    }')

legacy_task_id=$(echo "$legacy_response" | jq -r '.result.task_id // empty')

if [ -n "$legacy_task_id" ]; then
    echo "✓ PASS (Legacy method still works)"
    ((PASS++))
else
    echo "✗ FAIL"
    ((FAIL++))
fi

echo
echo "=== Test 6: Invalid Method ==="
echo -n "Testing: Invalid method handling... "

invalid_response=$(curl -s -X POST "$BASE_URL/rpc" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "invalid.method",
        "params": {},
        "id": "invalid-test"
    }')

error_code=$(echo "$invalid_response" | jq -r '.error.code // empty')

if [ "$error_code" = "-32601" ]; then
    echo "✓ PASS (Correctly returns 'Method not found')"
    ((PASS++))
else
    echo "✗ FAIL (Expected error code -32601)"
    ((FAIL++))
fi

echo
echo "=========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "=========================================="

if [ $FAIL -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi
