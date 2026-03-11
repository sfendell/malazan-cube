@echo off
if "%~1"=="" (
  echo Usage: qc "commit message"
  exit /b 1
)
git add -A .
git commit -m "%*"
git push origin HEAD --force
