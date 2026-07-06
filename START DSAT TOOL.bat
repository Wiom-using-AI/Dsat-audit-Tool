@echo off
title DSAT Audit Tool - Wiom Quality
color 1F
cls
echo.
echo  ============================================
echo    DSAT Audit Tool - Wiom Quality
echo    Please wait, starting up...
echo  ============================================
echo.

:: Kill old processes
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start Flask
cd /d "C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool\dsat_app"
start /B python app.py > "%TEMP%\flask_dsat.log" 2>&1
echo  [1/2] Flask server starting...
timeout /t 5 /nobreak >nul

:: Start tunnel watchdog (auto-restarts tunnel if it drops + pushes new URL)
echo  [2/2] Starting tunnel watchdog...
start "Tunnel Watchdog" powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool\tunnel_watchdog.ps1"

:: Wait for URL to be live
echo  Waiting for public link to be ready...
timeout /t 35 /nobreak >nul

:: Done
cls
color 1F
echo.
echo  ============================================
echo    DSAT Audit Tool - RUNNING
echo  ============================================
echo.
echo  PERMANENT LINK (share this always):
echo.
echo  https://wiom-using-ai.github.io/Dsat-audit-Tool/
echo.
echo  ============================================
echo  Admin login : admin / admin123
echo  QA login    : firstname / Wiom@123
echo  ============================================
echo.
echo  Tunnel watchdog is running - auto-recovers if connection drops.
echo  Keep this window OPEN while team is working.
echo.

:: Copy permanent link to clipboard
echo https://wiom-using-ai.github.io/Dsat-audit-Tool/ | clip
echo  (Permanent link copied to clipboard!)
echo.
pause
