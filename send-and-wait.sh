#!/bin/bash
# Helper script: Send message and automatically wait for result
# Usage: ./send-and-wait.sh "Your message here"
# Note: Using root endpoint / (legacy /rpc still supported)

API_KEY="fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
BASE_URL="https://a2a-agent-298609520814.us-central1.run.app"
MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
    echo "Usage: $0 \"Your message here\""
    echo "Example: $0 \"Summarize: AI is transforming industries\""
    exit 1
fi

echo "=========================================="
echo "Sending message to A2A Agent..."
echo "=========================================="
echo "Message: $MESSAGE"
echo

# Send message
RESPONSE=$(curl -s -X POST "$BASE_URL/" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"message/send\",
    \"params\": {
      \"message\": {
        \"role\": \"user\",
        \"parts\": [{
          \"type\": \"text\",
          \"text\": \"$MESSAGE\"
        }]
      }
    },
    \"id\": \"cli-test\"
  }")

echo "Response:"
echo "$RESPONSE"
echo
echo

# Extract taskId
if command -v jq &> /dev/null; then
    TASK_ID=$(echo "$RESPONSE" | jq -r '.result.taskId')
else
    # Fallback without jq
    TASK_ID=$(echo "$RESPONSE" | grep -o '"taskId":"[^"]*"' | cut -d'"' -f4)
fi

echo "Task ID: $TASK_ID"
echo
echo "Waiting 5 seconds for AI processing..."
sleep 5
echo

echo "=========================================="
echo "Fetching Result..."
echo "=========================================="
if command -v jq &> /dev/null; then
    curl -s "$BASE_URL/tasks/$TASK_ID" \
      -H "Authorization: Bearer $API_KEY" | jq .
else
    curl -s "$BASE_URL/tasks/$TASK_ID" \
      -H "Authorization: Bearer $API_KEY"
fi
echo
echo

echo "=========================================="
echo "Done!"
echo "=========================================="
