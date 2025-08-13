@echo off
echo 🚀 Starting Employee Management Backend Server...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python.
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "app.py" (
    echo ❌ app.py not found. Make sure you're in the backend directory.
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist ".venv" (
    echo ✅ Virtual environment found. Activating...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️  No virtual environment found. Using system Python.
)

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Test the server configuration
echo 🧪 Testing server configuration...
python test_server.py
if %errorlevel% neq 0 (
    echo ❌ Server configuration test failed!
    pause
    exit /b 1
)

echo ✅ Server configuration test passed!
echo 🌐 Starting server on http://localhost:5000...
echo Press Ctrl+C to stop the server
python app.py
