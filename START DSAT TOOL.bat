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
echo  [1/3] Flask server starting...
timeout /t 5 /nobreak >nul

:: Start Cloudflare tunnel
set LOGFILE=C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool\tunnel.log
if exist "%LOGFILE%" del /Q "%LOGFILE%"
start /B "C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool\cloudflared.exe" tunnel --url http://localhost:5001 2>"%LOGFILE%"
echo  [2/3] Creating public link...
timeout /t 15 /nobreak >nul

:: Extract the tunnel URL from log
set TUNNEL_URL=
for /f "tokens=*" %%a in ('findstr /i "trycloudflare.com" "%LOGFILE%" 2^>nul') do (
    for %%b in (%%a) do (
        echo %%b | findstr /i "https://" >nul 2>&1 && set TUNNEL_URL=%%b
    )
)

:: Update current_url.json and push to GitHub
echo  [3/3] Publishing permanent link...
cd /d "C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool"
echo {"url": "%TUNNEL_URL%"} > current_url.json
git add current_url.json >nul 2>&1
git commit -m "Update tunnel URL" >nul 2>&1
git push origin main >nul 2>&1

:: Done — show the permanent link
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
echo  The permanent link auto-redirects to server.
echo  Keep this window OPEN while team is working.
echo.

:: Copy permanent link to clipboard
echo https://wiom-using-ai.github.io/Dsat-audit-Tool/ | clip
echo  (Permanent link copied to clipboard!)
echo.
pause
