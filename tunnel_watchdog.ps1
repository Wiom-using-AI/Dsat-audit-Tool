# DSAT Tool Watchdog - auto-restarts Flask + tunnel if they die, pushes new URL to GitHub
$baseDir  = "C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool"
$appDir   = "$baseDir\dsat_app"
$cfExe    = "$baseDir\cloudflared.exe"
$logFile  = "$baseDir\tunnel.log"
$jsonFile = "$baseDir\current_url.json"

function Write-Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] $msg"
}

function Start-Flask {
    $existing = Get-Process python -ErrorAction SilentlyContinue
    if ($existing) { $existing | Stop-Process -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
    $p = Start-Process -FilePath "python" -ArgumentList "app.py" `
         -WorkingDirectory $appDir -NoNewWindow -PassThru
    Write-Log "Flask started (PID $($p.Id))"
    return $p
}

function Start-Tunnel {
    $existing = Get-Process cloudflared -ErrorAction SilentlyContinue
    if ($existing) { $existing | Stop-Process -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
    if (Test-Path $logFile) { Remove-Item $logFile -Force -ErrorAction SilentlyContinue }
    $p = Start-Process -FilePath $cfExe `
         -ArgumentList "tunnel --url http://localhost:5001" `
         -RedirectStandardError $logFile -NoNewWindow -PassThru
    Write-Log "Tunnel started (PID $($p.Id))"
    return $p
}

function Get-TunnelUrl {
    $deadline = (Get-Date).AddSeconds(40)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-Path $logFile) {
            try {
                # Use Get-Content which works even when file is locked by cloudflared
                $content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
                $m = [regex]::Matches($content, 'https://[a-z0-9-]+\.trycloudflare\.com')
                if ($m.Count -gt 0) { return $m[$m.Count-1].Value }
            } catch {}
        }
    }
    return ""
}

function Push-Url($url) {
    try {
        Set-Content -Path $jsonFile -Value "{`"url`": `"$url`"}" -Encoding UTF8
        Set-Location $baseDir
        git add "current_url.json" 2>$null
        git commit -m "Auto-update tunnel URL" 2>$null
        git push origin main 2>$null
        Write-Log "GitHub updated: $url"
    } catch {
        Write-Log "GitHub push failed: $_"
    }
}

# ── Initial startup ──
Write-Log "=== DSAT Watchdog starting ==="
$flaskProc  = Start-Flask
Start-Sleep -Seconds 4
$tunnelProc = Start-Tunnel
$url = Get-TunnelUrl
if ($url) { Push-Url $url } else { Write-Log "WARNING: Could not get tunnel URL on startup" }

# ── Monitor loop (check every 20 seconds) ──
while ($true) {
    Start-Sleep -Seconds 20

    # Check Flask
    $fAlive = Get-Process python -ErrorAction SilentlyContinue
    if (-not $fAlive) {
        Write-Log "Flask died — restarting..."
        $flaskProc = Start-Flask
        Start-Sleep -Seconds 3
    }

    # Check Cloudflared
    $cAlive = Get-Process cloudflared -ErrorAction SilentlyContinue
    if (-not $cAlive) {
        Write-Log "Tunnel died — restarting..."
        $tunnelProc = Start-Tunnel
        $url = Get-TunnelUrl
        if ($url) { Push-Url $url }
    }
}
