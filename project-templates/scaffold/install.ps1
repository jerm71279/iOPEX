# Master Prompt — Claude CLI installer for Windows (PowerShell)

Write-Host ""
Write-Host "  ┌─────────────────────────────────────────┐" -ForegroundColor Blue
Write-Host "  │   Master Prompt — Claude CLI Installer  │" -ForegroundColor Blue
Write-Host "  │   JIT Technologies LLC │" -ForegroundColor Blue
Write-Host "  └─────────────────────────────────────────┘" -ForegroundColor Blue
Write-Host ""

# ── 1. Node.js ──────────────────────────────────────────────────────────────
Write-Host "[1/4] Checking Node.js..." -ForegroundColor White
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = node -v
    Write-Host "  ✓ Node.js $nodeVer found" -ForegroundColor Green
} else {
    Write-Host "  Node.js not found. Installing via winget..." -ForegroundColor Yellow
    winget install OpenJS.NodeJS.LTS
    Write-Host "  ✓ Node.js installed. Please restart PowerShell and re-run this script." -ForegroundColor Green
    exit 0
}

# ── 2. Claude CLI ───────────────────────────────────────────────────────────
Write-Host "[2/4] Installing Claude CLI..." -ForegroundColor White
npm install -g @anthropic-ai/claude-code
Write-Host "  ✓ Claude CLI installed" -ForegroundColor Green

# ── 3. Scaffold command ─────────────────────────────────────────────────────
Write-Host "[3/4] Installing /scaffold command..." -ForegroundColor White
$claudeDir = "$env:USERPROFILE\.claude\commands"
New-Item -ItemType Directory -Force -Path $claudeDir | Out-Null
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item "$scriptDir\SCAFFOLD-ONBOARDING-PROMPT.md" "$claudeDir\scaffold.md" -Force
Write-Host "  ✓ /scaffold command ready" -ForegroundColor Green

# ── 4. API Key ──────────────────────────────────────────────────────────────
Write-Host "[4/4] Anthropic API Key" -ForegroundColor White
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Host "  ⚠  ANTHROPIC_API_KEY is not set." -ForegroundColor Red
    Write-Host "  Get your key at: https://console.anthropic.com"
    Write-Host "  Then run:"
    Write-Host '  [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY","sk-ant-...","User")'
} else {
    Write-Host "  ✓ ANTHROPIC_API_KEY found" -ForegroundColor Green
}

# ── Done ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:"
Write-Host "  1. cd into any project folder"
Write-Host "  2. Run: claude"
Write-Host "  3. Type: /scaffold"
Write-Host ""
