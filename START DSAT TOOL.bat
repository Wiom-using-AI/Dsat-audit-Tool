@echo off
title DSAT Audit Tool - Starting...
color 1F

:: Kill old processes silently
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Launch watchdog hidden (starts Flask + tunnel automatically, no window)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$psi=New-Object System.Diagnostics.ProcessStartInfo; ^
   $psi.FileName='powershell.exe'; ^
   $psi.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool\tunnel_watchdog.ps1""'; ^
   $psi.WindowStyle=[System.Diagnostics.ProcessWindowStyle]::Hidden; ^
   $psi.CreateNoWindow=$true; ^
   [System.Diagnostics.Process]::Start($psi) | Out-Null"

cls
color 1F
echo.
echo  ============================================
echo    DSAT Audit Tool - RUNNING IN BACKGROUND
echo  ============================================
echo.
echo  Tool is starting silently in background.
echo  It will be ready in about 30 seconds.
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
echo https://wiom-using-ai.github.io/Dsat-audit-Tool/ | clip
echo  (Link copied to clipboard!)
echo.
echo  You can close this window now.
echo.
pause
