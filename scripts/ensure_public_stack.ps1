param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$streamlitPidFile = Join-Path $repoRoot ".streamlit.public.pid"
$tunnelPidFile = Join-Path $repoRoot ".cf-tunnel.pid"
$streamlitOut = Join-Path $repoRoot "streamlit.public.out.log"
$streamlitErr = Join-Path $repoRoot "streamlit.public.err.log"
$tunnelOut = Join-Path $repoRoot "cf-tunnel.out.log"
$tunnelErr = Join-Path $repoRoot "cf-tunnel.err.log"
$localUrl = "http://127.0.0.1:$Port"

function Get-LiveProcessFromPidFile {
    param([string]$PidPath)

    if (-not (Test-Path -LiteralPath $PidPath)) {
        return $null
    }

    $rawPid = Get-Content -LiteralPath $PidPath -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $rawPid) {
        return $null
    }

    try {
        return Get-Process -Id ([int]$rawPid) -ErrorAction Stop
    } catch {
        return $null
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$Attempts = 40,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    return $false
}

function Get-TunnelUrl {
    param([string]$LogPath)

    if (-not (Test-Path -LiteralPath $LogPath)) {
        return $null
    }

    $contenido = Get-Content -LiteralPath $LogPath -ErrorAction SilentlyContinue
    $coincidencia = $contenido | Select-String -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -Last 1
    if (-not $coincidencia) {
        return $null
    }

    $url = [regex]::Match($coincidencia.Line, 'https://[a-z0-9-]+\.trycloudflare\.com').Value
    return $url
}

Set-Location $repoRoot

$streamlitProcess = Get-LiveProcessFromPidFile -PidPath $streamlitPidFile
$localReady = $false
if ($streamlitProcess) {
    $localReady = Wait-HttpReady -Url $localUrl -Attempts 2 -DelaySeconds 1
}

if (-not $localReady) {
    if ($streamlitProcess) {
        Stop-Process -Id $streamlitProcess.Id -Force -ErrorAction SilentlyContinue
    }

    $pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
    $streamlitProcess = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList "-m", "streamlit", "run", "app.py", "--server.port", "$Port", "--server.address", "127.0.0.1" `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput $streamlitOut `
        -RedirectStandardError $streamlitErr `
        -PassThru

    Set-Content -LiteralPath $streamlitPidFile -Value $streamlitProcess.Id
    $localReady = Wait-HttpReady -Url $localUrl
}

if (-not $localReady) {
    throw "Streamlit no responde en $localUrl"
}

$tunnelProcess = Get-LiveProcessFromPidFile -PidPath $tunnelPidFile
$publicUrl = Get-TunnelUrl -LogPath $tunnelErr
$publicReady = $false

if ($tunnelProcess -and $publicUrl) {
    $publicReady = Wait-HttpReady -Url $publicUrl -Attempts 2 -DelaySeconds 1
}

if (-not $publicReady) {
    if ($tunnelProcess) {
        Stop-Process -Id $tunnelProcess.Id -Force -ErrorAction SilentlyContinue
    }

    $tunnelProcess = Start-Process `
        -FilePath "npx.cmd" `
        -ArgumentList "wrangler", "tunnel", "quick-start", $localUrl `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput $tunnelOut `
        -RedirectStandardError $tunnelErr `
        -PassThru

    Set-Content -LiteralPath $tunnelPidFile -Value $tunnelProcess.Id

    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 2
        $publicUrl = Get-TunnelUrl -LogPath $tunnelErr
        if ($publicUrl) {
            $publicReady = Wait-HttpReady -Url $publicUrl -Attempts 10 -DelaySeconds 2
            if ($publicReady) {
                break
            }
        }
    }
}

if (-not $publicUrl) {
    throw "No se pudo detectar la URL publica de Cloudflare Tunnel."
}

if (-not $publicReady) {
    throw "El tunel de Cloudflare se abrio pero la URL publica no respondio correctamente."
}

Write-Output ("LOCAL_URL=" + $localUrl)
Write-Output ("PUBLIC_URL=" + $publicUrl)
Write-Output ("STREAMLIT_PID=" + $streamlitProcess.Id)
Write-Output ("TUNNEL_PID=" + $tunnelProcess.Id)
