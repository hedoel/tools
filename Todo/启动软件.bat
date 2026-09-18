@echo off
cd /d "%~dp0"
title EVE Overtime Tracker
echo Starting EVE Overtime Tracker...
python main.py
if errorlevel 1 (
    echo.
    echo Application exited with error.
    pause
)
