#!/bin/bash

# Local Testing Script for A2A Agent v0.9.0
# This script sets up the environment and starts the server for local testing

echo "=========================================="
echo "A2A Agent v0.9.0 - Local Test Environment"
echo "=========================================="
echo

# Check for Gemini API key in .env
if ! grep -q "GEMINI_API_KEY=.*[^=]$" .env 2>/dev/null || grep -q "GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE" .env 2>/dev/null; then
    echo "❌ ERROR: GEMINI_API_KEY not configured in .env"
    echo
    echo "Please update .env with your Gemini API key:"
    echo "  1. Get your key from: https://makersuite.google.com/app/apikey"
    echo "  2. Edit .env file and replace YOUR_GEMINI_KEY_HERE with your actual key"
    echo
    exit 1
fi

# Export authentication keys for local testing
export API_KEYS='{"fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=":{"name":"Local Test Key","created":"2025-11-06","expires":null,"notes":"From api-keys-abcs-test-ai-agent-001"}}'

echo "✓ Environment configured"
echo "  - Gemini API key loaded from .env"
echo "  - Authentication key: fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
echo "  - Port: 8080"
echo

echo "Starting server..."
echo "=========================================="
echo

# Start the server
python main.py
