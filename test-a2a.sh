#!/bin/bash
# Note: Using root endpoint / (legacy /rpc still supported)

BASE_URL="https://a2a-agent-298609520814.us-central1.run.app"

echo "🧪 Testing A2A Agent..."

# Function to test and display results
test_method() {
    local method=$1
    local params=$2
    local task_id=$3
    local description=$4

    echo ""
    echo "📝 Testing: $description"

    # Submit task
    response=$(curl -s -X POST "$BASE_URL/" \
        -H "Content-Type: application/json" \
        -d "{\"method\": \"$method\", \"params\": $params, \"id\": \"$task_id\"}")
    
    echo "Task submitted: $task_id"
    
    # Wait for completion
    sleep 3
    
    # Get results
    result=$(curl -s "$BASE_URL/tasks/$task_id")
    echo "$result" | jq .
}

# Test all methods
test_method "text.summarize" \
    '{"text": "Artificial intelligence is rapidly transforming industries. Machine learning models are becoming more sophisticated. Companies are investing heavily in AI research.", "max_length": 20}' \
    "test-summary-$(date +%s)" \
    "Text Summarization"

test_method "text.analyze_sentiment" \
    '{"text": "This product is fantastic! I love it!"}' \
    "test-sentiment-$(date +%s)" \
    "Sentiment Analysis"

test_method "data.extract" \
    '{"text": "Google announced their new Pixel phone in Mountain View on October 4th. CEO Sundar Pichai presented the features."}' \
    "test-extract-$(date +%s)" \
    "Entity Extraction"

echo ""
echo "✅ All tests completed!"