@echo off
setlocal
set "SCRIPT=%~dp0Set-AntigravityLocalization.ps1"
if not exist "%SCRIPT%" (
  echo Antigravity localization helper is missing.
  exit /b 2
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -Mode zh
exit /b %errorlevel%
