@echo off
REM Quick Start Script for Windows - Babbelfish MVP
REM This script helps you get started quickly

echo ========================================
echo 🐠 Babbelfish Quick Start (Windows)
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.9+ first
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Check if virtual environment exists
if not exist "backend\venv" (
    echo 📦 Creating virtual environment...
    cd backend
    python -m venv venv
    cd ..
    echo ✅ Virtual environment created
    echo.
) else (
    echo ✅ Virtual environment exists
    echo.
)

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found
    echo.
    echo Please create a .env file with your OpenAI API key:
    echo.
    echo 1. Copy backend\.env.example to .env in project root
    echo 2. Edit .env and add: OPENAI_API_KEY=sk-proj-...
    echo.
    echo After that, run this script again.
    pause
    exit /b 1
)

echo ✅ .env file found
echo.

REM Install dependencies
echo 📦 Installing dependencies...
cd backend
call venv\Scripts\activate.bat
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
cd ..
echo ✅ Dependencies installed
echo.

REM Test API connection
echo 🧪 Testing OpenAI connection...
python test_connection.py
if errorlevel 1 (
    echo.
    echo ❌ API connection test failed
    echo    Check your .env file and API key
    pause
    exit /b 1
)
echo.

echo ========================================
echo 🎉 Setup Complete!
echo ========================================
echo.
echo Next steps:
echo.
echo 1. Start backend:
echo    cd backend
echo    venv\Scripts\activate
echo    uvicorn main:app --reload
echo.
echo 2. In a NEW terminal, start frontend:
echo    cd frontend
echo    python -m http.server 3000
echo.
echo 3. Open browser: http://localhost:3000
echo.
echo ========================================
pause

