# PowerShell script to start the Flask backend server
Write-Host "🚀 Starting Employee Management Backend Server..." -ForegroundColor Green

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "app.py")) {
    Write-Host "❌ app.py not found. Make sure you're in the backend directory." -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
if (Test-Path ".venv") {
    Write-Host "✅ Virtual environment found. Activating..." -ForegroundColor Green
    & ".venv\Scripts\Activate.ps1"
} else {
    Write-Host "⚠️  No virtual environment found. Using system Python." -ForegroundColor Yellow
}

# Install dependencies if needed
Write-Host "📦 Checking dependencies..." -ForegroundColor Blue
pip install -r requirements.txt --quiet

# Test the server configuration
Write-Host "🧪 Testing server configuration..." -ForegroundColor Blue
python test_server.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Server configuration test passed!" -ForegroundColor Green
    Write-Host "🌐 Starting server on http://localhost:5000..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    python app.py
} else {
    Write-Host "❌ Server configuration test failed!" -ForegroundColor Red
    exit 1
}
