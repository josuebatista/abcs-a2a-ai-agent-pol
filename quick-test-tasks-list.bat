@echo off
REM Quick test for tasks/list method

set "API_KEY=fILbeUXt2PbZQ7LhXOFiHwK3oc9iLvQCyby7rYDpNZA="

echo ==========================================
echo Quick tasks/list Test
echo ==========================================
echo.

echo [1] Creating a test task...
curl -s -X POST http://localhost:8080/rpc -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Summarize: Test\"}]}},\"id\":\"quick-1\"}"
echo.
echo.

echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo [2] Listing all tasks...
curl -s -X POST http://localhost:8080/rpc -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{},\"id\":\"list-1\"}"
echo.
echo.

echo [3] Listing with limit=1...
curl -s -X POST http://localhost:8080/rpc -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"limit\":1},\"id\":\"list-2\"}"
echo.
echo.

echo [4] Testing error handling (invalid limit)...
curl -s -X POST http://localhost:8080/rpc -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"limit\":200},\"id\":\"list-error\"}"
echo.
echo.

echo ==========================================
echo Test Complete!
echo ==========================================
