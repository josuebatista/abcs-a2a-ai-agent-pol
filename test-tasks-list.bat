@echo off
REM Test script for tasks/list method (Windows)
REM Tests pagination, filtering, and error handling

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
echo A2A Protocol tasks/list Test Suite
echo Service: %BASE_URL%
echo ==========================================
echo.

REM First, create some test tasks to list
echo [Setup] Creating test tasks...
echo.

REM Task 1: Summarization
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Summarize: Test 1\"}]}},\"id\":\"setup-1\"}" > nul
echo Created task 1 (summarization)

REM Task 2: Sentiment
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Sentiment: Test 2\"}]}},\"id\":\"setup-2\"}" > nul
echo Created task 2 (sentiment-analysis)

REM Task 3: Entity extraction
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Extract entities: Test 3\"}]}},\"id\":\"setup-3\"}" > nul
echo Created task 3 (entity-extraction)

echo.
echo Waiting 2 seconds for tasks to process...
timeout /t 2 /nobreak >nul
echo.

echo === Test 1: Basic tasks/list (no params) ===
echo Should return first 20 tasks (default pagination)
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{},\"id\":\"test-1\"}"
echo.
echo.

echo === Test 2: tasks/list with custom limit ===
echo Should return first 2 tasks only
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"limit\":2},\"id\":\"test-2\"}"
echo.
echo.

echo === Test 3: tasks/list with pagination (page 2) ===
echo Should return next page with limit=1
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"page\":2,\"limit\":1},\"id\":\"test-3\"}"
echo.
echo.

echo === Test 4: tasks/list filtered by status=completed ===
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"status\":\"completed\"},\"id\":\"test-4\"}"
echo.
echo.

echo === Test 5: tasks/list filtered by skill=summarization ===
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"skill\":\"summarization\"},\"id\":\"test-5\"}"
echo.
echo.

echo === Test 6: tasks/list with combined filters ===
echo Should filter by status=completed AND skill=sentiment-analysis
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"status\":\"completed\",\"skill\":\"sentiment-analysis\"},\"id\":\"test-6\"}"
echo.
echo.

echo === Test 7: Error handling - Invalid page (negative) ===
echo Should return error
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"page\":-1},\"id\":\"test-7\"}"
echo.
echo.

echo === Test 8: Error handling - Invalid limit (too large) ===
echo Should return error (limit > 100)
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"limit\":200},\"id\":\"test-8\"}"
echo.
echo.

echo === Test 9: Empty results (non-existent status) ===
echo Should return empty task list
curl -s -X POST "%BASE_URL%/" -H "Authorization: Bearer %API_KEY%" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/list\",\"params\":{\"status\":\"nonexistent\"},\"id\":\"test-9\"}"
echo.
echo.

echo ==========================================
echo Test Results Summary
echo ==========================================
echo.
echo Expected Results:
echo Test 1: Should show pagination metadata with totalTasks, totalPages
echo Test 2: Should show max 2 tasks in array
echo Test 3: Should show page=2 in pagination
echo Test 4: Should show only completed tasks
echo Test 5: Should show only summarization tasks
echo Test 6: Should show only completed sentiment-analysis tasks
echo Test 7: Should show error "page must be >= 1"
echo Test 8: Should show error "limit must be between 1 and 100"
echo Test 9: Should show empty tasks array []
echo.
echo ==========================================
echo Testing complete!
echo ==========================================
