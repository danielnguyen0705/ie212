param(
    [switch]$RemoveVenv
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot "compose\compose.yaml"
$ComposeEnv = Join-Path $RepoRoot "compose\.env"
$ComposeEnvExample = Join-Path $RepoRoot "compose\.env.example"

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Reset-Directory {
    param([string]$Path)
    Ensure-Directory -Path $Path
    Get-ChildItem -LiteralPath $Path -Force |
        Where-Object { $_.Name -ne ".gitkeep" } |
        Remove-Item -Recurse -Force
}

Write-Host "Resetting IE212 workspace at $RepoRoot"

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    $envFileToUse = if (Test-Path -LiteralPath $ComposeEnv) { $ComposeEnv } else { $ComposeEnvExample }
    if (Test-Path -LiteralPath $envFileToUse) {
        Write-Host "Stopping Docker services and removing named volumes..."
        & docker compose --env-file $envFileToUse -f $ComposeFile down -v --remove-orphans
    } else {
        Write-Host "Skipping docker compose reset because no env file was found."
    }
} else {
    Write-Host "Docker not found. Skipping container reset."
}

$pathsToReset = @(
    (Join-Path $RepoRoot "airflow\logs"),
    (Join-Path $RepoRoot "data\raw"),
    (Join-Path $RepoRoot "data\processed"),
    (Join-Path $RepoRoot "models"),
    (Join-Path $RepoRoot "services\spark\out")
)

foreach ($path in $pathsToReset) {
    Write-Host "Cleaning $path"
    Reset-Directory -Path $path
}

$filesToRemove = @(
    (Join-Path $RepoRoot "data\inference\latest_window.npz"),
    (Join-Path $RepoRoot "outputs\inference\latest_prediction.json"),
    (Join-Path $RepoRoot "outputs\exp_results_full.csv"),
    (Join-Path $RepoRoot "outputs\compare_step_full.csv"),
    (Join-Path $RepoRoot "outputs\stock_mse_full.csv"),
    (Join-Path $RepoRoot "outputs\graph_step_full.csv"),
    (Join-Path $RepoRoot "outputs\gate_step_full.csv"),
    (Join-Path $RepoRoot "outputs\metrics_full.json")
)

foreach ($file in $filesToRemove) {
    if (Test-Path -LiteralPath $file) {
        Write-Host "Removing $file"
        Remove-Item -LiteralPath $file -Force
    }
}

Write-Host "Removing Python cache directories..."
Get-ChildItem -LiteralPath $RepoRoot -Directory -Recurse -Force |
    Where-Object { $_.Name -eq "__pycache__" } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }

if ($RemoveVenv) {
    $venvPath = Join-Path $RepoRoot ".venv"
    if (Test-Path -LiteralPath $venvPath) {
        Write-Host "Removing virtual environment $venvPath"
        Remove-Item -LiteralPath $venvPath -Recurse -Force
    }
}

Ensure-Directory -Path (Join-Path $RepoRoot "data\inference")
Ensure-Directory -Path (Join-Path $RepoRoot "outputs\inference")

Write-Host ""
Write-Host "Reset complete."
Write-Host "You can now rerun the setup and training commands from README.md."
