@echo off
    REM stop.bat - останавливает все экземпляры winws.exe
    REM VERSION: 1.0

    echo Остановка всех процессов winws.exe...

    REM Метод 1: taskkill
    taskkill /F /IM winws.exe /T

    REM Метод 2: через PowerShell
    powershell -Command "Get-Process winws -ErrorAction SilentlyContinue | Stop-Process -Force"

    REM Метод 3: через wmic
    wmic process where name='winws.exe' call terminate

    REM Добавляем паузу для стабильности
    timeout /t 1 /nobreak >nul

    echo Остановка процессов завершена.
    exit /b 0
    