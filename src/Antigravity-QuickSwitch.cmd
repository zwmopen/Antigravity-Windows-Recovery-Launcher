@echo off
chcp 65001 >nul
title Antigravity 智能切号与平滑重启
echo ========================================================
echo   Antigravity 智能切号与平滑重启助手
echo   优雅保存退出 -^> 自动轮换高额度账号 -^> 专线启动器恢复
echo ========================================================
echo.

set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%antigravity_smart_switch.py" (
    set TARGET_PY="%SCRIPT_DIR%antigravity_smart_switch.py"
) else (
    set TARGET_PY="%LOCALAPPDATA%\Antigravity\launcher\antigravity_smart_switch.py"
)

python %TARGET_PY% --force %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 智能切号流程遇到异常，退出码: %ERRORLEVEL%
    pause
)
