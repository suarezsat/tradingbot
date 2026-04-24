$ErrorActionPreference = "SilentlyContinue"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidFiles = @(
    (Join-Path $repoRoot ".streamlit.public.pid"),
    (Join-Path $repoRoot ".cf-tunnel.pid")
)

foreach ($pidFile in $pidFiles) {
    if (-not (Test-Path -LiteralPath $pidFile)) {
        continue
    }

    $rawPid = Get-Content -LiteralPath $pidFile | Select-Object -First 1
    if ($rawPid) {
        Stop-Process -Id ([int]$rawPid) -Force -ErrorAction SilentlyContinue
    }

    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Output "PUBLIC_STACK_STOPPED"
