@echo off
REM Quick manual test for A2A Agent

set "API_KEY=fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

echo ==========================================
echo Quick A2A Agent Test
echo ==========================================
echo.

echo [1/4] Health Check...
curl -s http://localhost:8080/health
echo.
echo.

echo [2/4] Agent Card...
curl -s http://localhost:8080/.well-known/agent-card.json | findstr "version protocolVersion"
echo.
echo.

echo [3/4] Testing message/send (Summarization)...
curl -s -X POST http://localhost:8080/rpc -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Summarize in 20 words: Artificial intelligence is transforming industries worldwide. Machine learning models are becoming increasingly sophisticated.\"}]}},\"id\":\"quick-test\"}"
echo.
echo.
echo Waiting 5 seconds for processing...
timeout /t 5 /nobreak >nul
echo.

echo [4/4] Checking most recent task...
echo Note: Copy the taskId from above and check manually with:
echo curl http://localhost:8080/tasks/TASK_ID_HERE -H "Authorization: Bearer %API_KEY%"
echo.

echo ==========================================
echo Tests Complete!
echo ==========================================
echo.
echo Check server logs to see:
echo   - Task created and completed successfully
echo   - Intent detection working (summarization)
echo   - AI summary generated
