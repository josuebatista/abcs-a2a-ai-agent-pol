@echo off
REM Local Testing Script for A2A Agent v0.9.0 (Windows)
REM This script sets up the environment and starts the server for local testing

echo ==========================================
echo A2A Agent v0.9.0 - Local Test Environment
echo ==========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found
    echo Please create .env file with your GEMINI_API_KEY
    exit /b 1
)

REM Check if GEMINI_API_KEY is configured
findstr /C:"GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE" .env >nul
if %errorlevel%==0 (
    echo ERROR: GEMINI_API_KEY not configured in .env
    echo.
    echo Please update .env with your Gemini API key:
    echo   1. Get your key from: https://makersuite.google.com/app/apikey
    echo   2. Edit .env file and replace YOUR_GEMINI_KEY_HERE with your actual key
    echo.
    exit /b 1
)

REM Export authentication keys for local testing
set API_KEYS={"fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=":{"name":"Local Test Key","created":"2025-11-06","expires":null,"notes":"From api-keys-abcs-test-ai-agent-001"}}

echo Environment configured
echo   - Gemini API key loaded from .env
echo   - Authentication key: fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA=
echo   - Port: 8080
echo.

echo Starting server...
echo ==========================================
echo.

REM Start the server
python main.py
