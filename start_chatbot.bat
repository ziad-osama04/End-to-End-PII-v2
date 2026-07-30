@echo off
echo ===================================================
echo Starting End-to-End PII v2 Chatbot
echo ===================================================

echo.
echo [1/2] Starting Backend (FastAPI)...
start "PII Backend" cmd /k "cd backend && call venv\Scripts\activate && python main.py"

echo.
echo [2/2] Starting Frontend (React)...
start "PII Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo ===================================================
echo Both services are starting in separate windows!
echo Once the frontend says "ready in ... ms", 
echo open http://localhost:5173 in your browser.
echo ===================================================
pause
