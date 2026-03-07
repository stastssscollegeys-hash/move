@echo off
cd /d "%~dp0.."

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>nul
)
timeout /t 1 /nobreak >nul

echo Building...
call npx tsc -p tsconfig.yt.json
if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   http://localhost:3000/lp-nanobanana
echo ==========================================
echo   Close this window to stop the server.
echo.

node dist-yt/server.js
pause
