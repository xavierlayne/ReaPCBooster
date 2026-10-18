@echo off
title ReaPCBooster - Sürücü Yöneticisi
chcp 65001 >nul
cd /d "%~dp0"
echo ReaPCBooster baslatiliyor...
"C:\Users\KARACA\AppData\Local\Python\bin\python.exe" main.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bir hata olustu. Cikis icin bir tusa basin...
    pause >nul
)
