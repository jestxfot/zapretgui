@echo off
REM Стратегия Fake TLS Mod 2 md5sig
REM VERSION: 1.3
REM Дата обновления: 2025

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoLogo -NoProfile -Command ^
        "Start-Process -FilePath '%~f0' -ArgumentList 'ELEV' -Verb RunAs"
    exit /b
)
if /i "%1"=="ELEV" shift /1

taskkill /f /im winws.exe >nul 2>&1
sc stop windivert >nul 2>&1
sc delete windivert >nul 2>&1
sc delete windivert >nul 2>&1
cd /d "%~dp0"

start "zapret: winws Fake_Tls_Mod_v2" /b "winws.exe" ^
 --wf-tcp=80,443 --wf-udp=443,50000-50100 ^
 --filter-udp=443 --hostlist="discord.txt" --ipset="ipset-cloudflare.txt" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic="quic_initial_www_google_com.bin" --new ^
 --filter-udp=50000-50100 --ipset="ipset-discord.txt" --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new ^
 --filter-tcp=80 --hostlist="discord.txt" --ipset="ipset-cloudflare.txt" --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new ^
 --filter-tcp=443 --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new