#!/bin/bash
# Test script for Option 5: API Key-Based Synchronous Mode

SERVICE_URL="${1:-http://localhost:8080}"
ASYNC_KEY="${2:-fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=}"
SYNC_KEY="${3:-sync-test-key-12345}"

echo "=========================================="
echo "Testing Option 5: API Key-Based Sync Mode"
echo "=========================================="
echo ""
echo "Service URL: $SERVICE_URL"
echo ""

# Test 1: Async Mode (Default)
echo "[Test 1] Async Mode (default behavior)"
echo "----------------------------------------"
echo "Using API Key: $ASYNC_KEY (async mode)"
echo ""

RESPONSE=$(curl -s -X POST "$SERVICE_URL/" \
  -H "Authorization: Bearer $ASYNC_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Summarize: AI is transforming technology"}]
      }
    },
    "id": "test-async-1"
  }')

echo "Response (should be immediate with status: pending):"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""
echo ""

# Test 2: Sync Mode
echo "[Test 2] Sync Mode (new behavior)"
echo "----------------------------------------"
echo "Using API Key: $SYNC_KEY (sync mode)"
echo "This will take 2-5 seconds to complete..."
echo ""

START_TIME=$(date +%s)

RESPONSE=$(curl -s -X POST "$SERVICE_URL/" \
  -H "Authorization: Bearer $SYNC_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Summarize: AI is transforming technology"}]
      }
    },
    "id": "test-sync-1"
  }')

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Response (should include completed result after ~${DURATION}s):"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""
echo "Request duration: ${DURATION}s"
echo ""
echo ""

# Test 3: Legacy Method with Async
echo "[Test 3] Legacy Method (text.summarize) - Async Mode"
echo "------------------------------------------------------"
echo "Using API Key: $ASYNC_KEY (async mode)"
echo ""

RESPONSE=$(curl -s -X POST "$SERVICE_URL/" \
  -H "Authorization: Bearer $ASYNC_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "text.summarize",
    "params": {
      "text": "Artificial intelligence is rapidly transforming industries worldwide."
    },
    "id": "test-legacy-async"
  }')

echo "Response (should be immediate with status: pending):"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""
echo ""

# Test 4: Legacy Method with Sync
echo "[Test 4] Legacy Method (text.summarize) - Sync Mode"
echo "----------------------------------------------------"
echo "Using API Key: $SYNC_KEY (sync mode)"
echo "This will take 2-5 seconds to complete..."
echo ""

START_TIME=$(date +%s)

RESPONSE=$(curl -s -X POST "$SERVICE_URL/" \
  -H "Authorization: Bearer $SYNC_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "text.summarize",
    "params": {
      "text": "Artificial intelligence is rapidly transforming industries worldwide."
    },
    "id": "test-legacy-sync"
  }')

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Response (should include completed result after ~${DURATION}s):"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""
echo "Request duration: ${DURATION}s"
echo ""
echo ""

echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Expected Results:"
echo "  - Test 1 & 3: Immediate response with 'pending' status (async)"
echo "  - Test 2 & 4: Delayed response with 'completed' status (sync)"
echo ""
