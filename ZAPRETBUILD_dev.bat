@echo off
rem ──────────────────────────────────────────────────────────────
rem  build.bat  –  build + clean
rem ──────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

rem -------- пути ------------------------------------------------
set ROOT=%cd%
set OUT=%ROOT%\..\zapret
set WORK=%TEMP%\pyi_%RANDOM%

rem -------- очистка прошлых __pycache__ -------------------------
echo Cleaning old __pycache__ ...
for /d /r "%ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d"
)

rem -------- version_info.txt ------------------------------------
echo Gen file version...
python zapretbuild.py
if errorlevel 1 goto :failed

rem -------- PyInstaller ----------------------------------------
echo Building...
python -m PyInstaller ^
        --onefile ^
        --console ^
        --windowed ^
        --icon "%ROOT%\zapret.ico" ^
        --name zapret ^
        --version-file "%ROOT%\version_info.txt" ^
        --hidden-import=win32com ^
        --hidden-import=win32com.client ^
        --hidden-import=pythoncom ^
        --workpath "%WORK%" ^
        --distpath "%OUT%" ^
        "%ROOT%\main.py"
if errorlevel 1 goto :failed

rem -------- удаляем временный work-каталог ----------------------
rd /s /q "%WORK%"

rem -------- удаляем новые __pycache__ (если появились) ----------
echo Cleaning fresh __pycache__ ...
for /d /r "%ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d"
)

echo Done!  Exe is in "%OUT%"
pause
goto :eof

:failed
echo Build FAILED & pause
exit /b 1