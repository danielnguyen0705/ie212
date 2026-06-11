@echo off
setlocal
cd /d "%~dp0..\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\performance\run_performance_suite.py" --pipeline-runs 1 --api-iterations 5 --docker-stats-samples 2 --output-dir "outputs\performance"
) else (
  python "scripts\performance\run_performance_suite.py" --pipeline-runs 1 --api-iterations 5 --docker-stats-samples 2 --output-dir "outputs\performance"
)
endlocal
