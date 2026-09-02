@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
set "INSTALL_EXIT=%ERRORLEVEL%"
if not "%INSTALL_EXIT%"=="0" (
  echo.
  echo Installation failed with exit code %INSTALL_EXIT%.
  echo Keep this window open and copy the error message for troubleshooting.
  pause
)
exit /b %INSTALL_EXIT%
