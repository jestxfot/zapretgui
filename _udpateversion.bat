@echo off
:: ----------- настройки -------------
set "HOST=root@37.233.85.174"
set "REMOTE_DIR=/var/www/zapret_site/public"
set "LOCAL_FILE=D:\Privacy\zapretgui\version.json"
set "SSH_KEY=%USERPROFILE%\.ssh\id_ed25519"   :: если работаете по ключу
:: ----------- логика -----------------
if not exist "%LOCAL_FILE%" (
    echo [ERROR] %LOCAL_FILE% not found!
    exit /b 1
)

echo === Копируем файл на сервер ===
scp -i "%SSH_KEY%" -C "%LOCAL_FILE%" %HOST%:%REMOTE_DIR%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] scp failed
    exit /b %ERRORLEVEL%
)

echo === Готово! ===
pause