@echo off
REM Production test for tasks/list

set "API_KEY=fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="
set "URL=https://a2a-agent-298609520814.us-central1.run.app"

echo ==========================================
echo Production tasks/list Test
echo ==========================================
echo.

echo [1] Creating test tasks...
curl -s -X POST "%URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Summarize: Test 1\"}]}},\"id\":\"test-1\"}"
echo.
curl -s -X POST "%URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Sentiment: Test 2\"}]}},\"id\":\"test-2\"}"
echo.
echo.

echo Waiting 3 seconds for processing...
timeout /t 3 /nobreak >nul

echo [2] Testing tasks/list (all tasks)...
curl -s -X POST "%URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{},\"id\":\"list-all\"}"
echo.
echo.

echo [3] Testing tasks/list with limit=1...
curl -s -X POST "%URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"limit\":1},\"id\":\"list-limited\"}"
echo.
echo.

echo [4] Testing tasks/list filtered by status=completed...
curl -s -X POST "%URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"status\":\"completed\"},\"id\":\"list-completed\"}"
echo.
echo.

echo [5] Testing error handling (invalid limit)...
curl -s -X POST "%URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"limit\":200},\"id\":\"list-error\"}"
echo.
echo.

echo ==========================================
echo Production Test Complete!
echo ==========================================
