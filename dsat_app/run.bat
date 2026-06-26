@echo off
title DSAT Audit Tool - Wiom Quality
color 1F
echo.
echo  ================================================
echo    DSAT Audit Tool - Wiom Quality Management
echo  ================================================
echo.

:: Install Flask if needed
pip install flask --quiet 2>nul

:: Kill any old instances
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5001"') do taskkill /F /PID %%a >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1

:: Start Flask server
echo  [1/2] Starting Flask server...
start /B python app.py > ..\flask.log 2>&1
timeout /t 4 /nobreak >nul

:: Start Cloudflare tunnel
echo  [2/2] Creating public link (this takes ~15 seconds)...
start /B ..\cloudflared.exe tunnel --url http://localhost:5001 > ..\tunnel.log 2>&1
timeout /t 15 /nobreak >nul

:: Extract the tunnel URL from log
set TUNNEL_URL=
for /f "tokens=*" %%a in ('findstr "trycloudflare.com" ..\tunnel.log 2^>nul') do (
    set LINE=%%a
)

:: Display the URL
cls
color 1F
echo.
echo  ================================================
echo    DSAT Audit Tool - Wiom Quality Management
echo  ================================================
echo.
echo  STATUS: RUNNING
echo.
echo  *** SHARE THIS LINK WITH YOUR QA TEAM ***
echo.
findstr "trycloudflare.com" ..\tunnel.log 2>nul | findstr "https"
echo.
echo  ================================================
echo  Admin login : admin / admin123
echo  QA login    : (name) / Wiom@123
echo  ================================================
echo.
echo  Keep this window OPEN while team is working.
echo  Close it to stop the server.
echo.
pause
