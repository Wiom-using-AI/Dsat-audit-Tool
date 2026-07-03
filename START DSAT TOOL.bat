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
echo  [1/4] Flask server starting...
timeout /t 5 /nobreak >nul

:: Start Cloudflare tunnel - write ALL output to log
set LOGFILE=C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool\tunnel.log
if exist "%LOGFILE%" del /Q "%LOGFILE%"
start "" /B cmd /c ""C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool\cloudflared.exe" tunnel --url http://localhost:5001 >> "%LOGFILE%" 2>&1"
echo  [2/4] Creating public link (waiting 25 seconds)...
timeout /t 25 /nobreak >nul

:: Use PowerShell to extract URL reliably with regex
echo  [3/4] Reading tunnel URL...
for /f "usebackq delims=" %%U in (`powershell -NoProfile -Command "$c=Get-Content '%LOGFILE%' -Raw -ErrorAction SilentlyContinue; $m=[regex]::Matches($c,'https://[a-z0-9-]+\.trycloudflare\.com'); if($m.Count -gt 0){$m[$m.Count-1].Value}else{''}"`  ) do set TUNNEL_URL=%%U

if "%TUNNEL_URL%"=="" (
    echo  WARNING: Could not detect tunnel URL. Retrying...
    timeout /t 10 /nobreak >nul
    for /f "usebackq delims=" %%U in (`powershell -NoProfile -Command "$c=Get-Content '%LOGFILE%' -Raw -ErrorAction SilentlyContinue; $m=[regex]::Matches($c,'https://[a-z0-9-]+\.trycloudflare\.com'); if($m.Count -gt 0){$m[$m.Count-1].Value}else{''}"`  ) do set TUNNEL_URL=%%U
)

:: Update current_url.json and push to GitHub
echo  [4/4] Publishing permanent link...
cd /d "C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool"
powershell -NoProfile -Command "Set-Content -Path 'current_url.json' -Value ('{\"url\": \"' + $env:TUNNEL_URL + '\"}')"
git add "current_url.json" >nul 2>&1
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
if not "%TUNNEL_URL%"=="" (
echo  Current tunnel: %TUNNEL_URL%
)
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
