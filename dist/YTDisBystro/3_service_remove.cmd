@echo off
chcp 866 > nul
title ---] zapret - services cleaning... [---
color f1
pushd "%~dp0"

if not "%1"=="am_admin" (powershell start -verb runas '%0' am_admin & exit /b)

del /F /Q /S "%~dp0logfile.log" > nul
echo.
call :srvdel zapret
rem call :srvdel zapret2
goto :eof

:srvdel
net stop %1
sc delete %1
net stop Windivert
sc delete Windivert

tasklist /fi "IMAGENAME eq RBTray.exe" | find /i "RBTray.exe"
if errorlevel 0 (
TASKKILL /F /IM RBTray.exe /T
regsvr32 /u /s "%~dp0tray\RBHook.dll"
)

color fA
echo.
echo Очистка завершена...
pause
