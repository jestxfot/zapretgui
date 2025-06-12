@echo off
rem ───────────────────────────────────────────────────────────────
rem  ZAPRETBUILD_stable.bat  —  PyInstaller build + Inno Setup
rem ───────────────────────────────────────────────────────────────

rem 0. Всегда работаем из папки, где лежит .bat
cd /d "%~dp0"

rem 1. Если не admin → перезапускаем скрипт с Run-as-Admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command ^
      "Start-Process -FilePath '%comspec%' -ArgumentList '/c','\"%~f0\" --elevated' -Verb RunAs -WorkingDirectory '%~dp0'"
    exit /b
)

rem 2. (опционально) при повторном входе можно удалить флаг аргумента
if "%1"=="--elevated" shift

rem ───── переменные путей ────────────────────────────────────────
setlocal EnableDelayedExpansion
set ROOT=%cd%
set OUT=%ROOT%\..\zapret
set WORK=%TEMP%\pyi_%RANDOM%

rem ───── чистим старые кеши ──────────────────────────────────────
for /d /r "%ROOT%" %%d in (__pycache__) do rd /s /q "%%d" 2>nul

echo Gen file version...
rem ───── генерируем version_info.txt ─────────────────────────────
python "%ROOT%\zapretbuild.py" || goto :failed

rem ───── гасим старый zapret.exe (если запущен) ─────────────────
tasklist /fi "imagename eq zapret.exe" | find /i "zapret.exe" >nul
if not errorlevel 1 (
    echo Stopping running zapret.exe...
    taskkill /f /t /im zapret.exe 2>nul
)

echo Building...
rem ───── PyInstaller ────────────────────────────────────────────
python -m PyInstaller ^
        --onefile ^
        --noconsole ^
        --windowed ^
        --icon "%ROOT%\zapret.ico" ^
        --name zapret ^
        --version-file "%ROOT%\version_info.txt" ^
        --hidden-import=win32com ^
        --hidden-import=win32com.client ^
        --hidden-import=pythoncom ^
        --workpath "%WORK%" ^
        --distpath "%OUT%" ^
        "%ROOT%\main.py" || goto :failed

rem ───── Inno Setup (создание инсталлятора) ──────────────────────
echo Creating installer...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "%ROOT%\zapret.iss" || goto :failed_inno

rem ───── удаляем временный workpath и свежие __pycache__ ─────────
rd /s /q "%WORK%" 2>nul
for /d /r "%ROOT%" %%d in (__pycache__) do rd /s /q "%%d" 2>nul

echo Done!
pause
goto :eof

:failed_inno
echo ERROR: Inno Setup failed! Check if zapret.iss exists and Inno Setup is installed.
pause
exit /b 1

:failed
echo ERROR: Build failed!
pause
exit /b 1