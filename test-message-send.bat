@echo off
REM Test script for A2A Protocol v0.3.0 message/send implementation (Windows)
REM Tests the new natural language interface

setlocal enabledelayedexpansion

set "BASE_URL=%~1"
set "API_KEY=%~2"

if "%BASE_URL%"=="" set "BASE_URL=http://localhost:8080"
if "%API_KEY%"=="" (
    echo ERROR: API_KEY required
    echo Usage: %0 ^<base_url^> ^<api_key^>
    echo Example: %0 http://localhost:8080 your-api-key
    exit /b 1
)

echo ==========================================
echo A2A Protocol message/send Test Suite
echo Service: %BASE_URL%
echo ==========================================
echo.

set PASS=0
set FAIL=0

echo === Test 1: message/send - Summarization Intent ===
echo Testing: Summarization via natural language...
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Summarize this text: AI is transforming industries worldwide. Machine learning models are becoming more sophisticated every day.\"}]}},\"id\":\"test-1\"}" > temp_response.json
type temp_response.json
echo.

REM Extract taskId from response
for /f "tokens=2 delims=:," %%a in ('findstr "taskId" temp_response.json') do set TASK_ID=%%a
set TASK_ID=%TASK_ID:"=%
set TASK_ID=%TASK_ID: =%

echo Waiting for task to complete...
timeout /t 5 /nobreak >nul
curl -s "%BASE_URL%/tasks/%TASK_ID%" -H "Authorization: Bearer %API_KEY%"
echo.
echo.

echo === Test 2: message/send - Sentiment Analysis Intent ===
echo Testing: Sentiment analysis via natural language...
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"What's the sentiment of this review: This product is absolutely fantastic! I love it!\"}]}},\"id\":\"test-2\"}"
echo.

timeout /t 3 /nobreak >nul
curl -s "%BASE_URL%/tasks/test-2" -H "Authorization: Bearer %API_KEY%"
echo.
echo.

echo === Test 3: message/send - Entity Extraction Intent ===
echo Testing: Entity extraction via natural language...
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Extract entities: Microsoft CEO Satya Nadella spoke in Seattle on January 15th. Contact: info@microsoft.com\"}]}},\"id\":\"test-3\"}"
echo.

timeout /t 3 /nobreak >nul
curl -s "%BASE_URL%/tasks/test-3" -H "Authorization: Bearer %API_KEY%"
echo.
echo.

echo === Test 4: Legacy Method (Backwards Compatibility) ===
echo Testing: Legacy text.summarize...
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"text.summarize\",\"params\":{\"text\":\"Test text\",\"max_length\":20},\"id\":\"legacy-test\"}"
echo.
echo.

echo ==========================================
echo Testing complete! Check results above.
echo ==========================================
