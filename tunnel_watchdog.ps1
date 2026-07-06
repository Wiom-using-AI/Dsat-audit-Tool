# Tunnel Watchdog - keeps cloudflared alive and auto-updates GitHub
$baseDir = "C:\Users\Preeti Naval\OneDrive\Desktop\Dsat Tool"
$cloudflared = "$baseDir\cloudflared.exe"
$logFile = "$baseDir\tunnel.log"
$jsonFile = "$baseDir\current_url.json"

function Start-Tunnel {
    if (Test-Path $logFile) { Remove-Item $logFile -Force -ErrorAction SilentlyContinue }
    Start-Process -FilePath $cloudflared -ArgumentList "tunnel --url http://localhost:5001" -RedirectStandardError $logFile -NoNewWindow -PassThru
}

function Get-TunnelUrl {
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-Path $logFile) {
            $content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
            $m = [regex]::Matches($content, 'https://[a-z0-9-]+\.trycloudflare\.com')
            if ($m.Count -gt 0) { return $m[$m.Count-1].Value }
        }
    }
    return ""
}

function Push-Url($url) {
    Set-Content -Path $jsonFile -Value "{`"url`": `"$url`"}"
    Set-Location $baseDir
    git add "current_url.json" 2>$null
    git commit -m "Auto-update tunnel URL" 2>$null
    git push origin main 2>$null
    Write-Host "$(Get-Date -Format 'HH:mm:ss') Pushed new URL: $url"
}

Write-Host "Watchdog started. Monitoring tunnel..."
$proc = Start-Tunnel
$url = Get-TunnelUrl
if ($url) { Push-Url $url }

while ($true) {
    Start-Sleep -Seconds 30
    $running = Get-Process cloudflared -ErrorAction SilentlyContinue
    if (-not $running) {
        Write-Host "$(Get-Date -Format 'HH:mm:ss') Tunnel died! Restarting..."
        $proc = Start-Tunnel
        $url = Get-TunnelUrl
        if ($url) { Push-Url $url }
    }
}
