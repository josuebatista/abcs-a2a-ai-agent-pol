@echo off
REM Helper script: Send message and automatically wait for result
REM Usage: send-and-wait.bat "Your message here"
REM Note: Using root endpoint / (legacy /rpc still supported)

set "API_KEY=fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
set "BASE_URL=https://a2a-agent-298609520814.us-central1.run.app"
set "MESSAGE=%~1"

if "%MESSAGE%"=="" (
    echo Usage: %0 "Your message here"
    echo Example: %0 "Summarize: AI is transforming industries"
    exit /b 1
)

echo ==========================================
echo Sending message to A2A Agent...
echo ==========================================
echo Message: %MESSAGE%
echo.

REM Send message
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"%MESSAGE%\"}]}},\"id\":\"cli-test\"}" > temp_task.json

echo Response:
type temp_task.json
echo.
echo.

REM Extract taskId (basic parsing for Windows)
for /f "tokens=2 delims=:," %%a in ('findstr "taskId" temp_task.json') do set TASK_ID=%%a
set TASK_ID=%TASK_ID:"=%
set TASK_ID=%TASK_ID: =%

echo Task ID: %TASK_ID%
echo.
echo Waiting 5 seconds for AI processing...
timeout /t 5 /nobreak >nul
echo.

echo ==========================================
echo Fetching Result...
echo ==========================================
curl -s "%BASE_URL%/tasks/%TASK_ID%" -H "Authorization: Bearer %API_KEY%"
echo.
echo.

del temp_task.json
echo ==========================================
echo Done!
echo ==========================================
