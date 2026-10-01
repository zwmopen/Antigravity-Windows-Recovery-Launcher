@echo off
setlocal
chcp 65001 >nul
title Antigravity Smart Switch

set "SCRIPT_DIR=%~dp0"
set "TARGET_PY=%SCRIPT_DIR%antigravity_smart_switch.py"
if not exist "%TARGET_PY%" (
    set "TARGET_PY=%LOCALAPPDATA%\Antigravity\launcher\antigravity_smart_switch.py"
)

if not exist "%TARGET_PY%" (
    echo [ERROR] Cannot find antigravity_smart_switch.py
    exit /b 1
)

if "%~1"=="" (
    python "%TARGET_PY%" --force
) else (
    python "%TARGET_PY%" %*
)
endlocal
