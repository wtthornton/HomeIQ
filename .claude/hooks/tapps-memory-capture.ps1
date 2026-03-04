# TappsMCP Stop hook - Memory Capture (Epic 34.5)
# Writes session quality data to .tapps-mcp/session-capture.json for
# persistence into shared memory on next session start.
# IMPORTANT: Must check stop_hook_active to prevent infinite loops.
$rawInput = @($input) -join "`n"
try {
    $data = $rawInput | ConvertFrom-Json
    $active = $data.stop_hook_active
} catch {
    $active = $false
}
if ($active -eq $true -or $active -eq "true" -or $active -eq "True") {
    exit 0
}
$projDir = $env:CLAUDE_PROJECT_DIR
if (-not $projDir) { $projDir = "." }
$captureDir = "$projDir/.tapps-mcp"
$marker = "$captureDir/.validation-marker"
$validated = if (Test-Path $marker) { $true } else { $false }
$dateStr = (Get-Date -Format "yyyy-MM-dd")
try {
    $gitOutput = git diff --name-only HEAD 2>$null
    $filesEdited = @($gitOutput | Where-Object { $_ -match '\.py$' }).Count
} catch {
    $filesEdited = 0
}
if (-not (Test-Path $captureDir)) {
    New-Item -ItemType Directory -Path $captureDir -Force | Out-Null
}
$capture = @{ date = $dateStr; validated = $validated; files_edited = $filesEdited }
$capture | ConvertTo-Json | Set-Content -Path "$captureDir/session-capture.json" -Encoding UTF8
exit 0
