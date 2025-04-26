@echo off
REM Стратегия МГТС 1
REM VERSION: 1.1
REM Дата обновления: 2024

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

start "zapret: winws MGTS_v1" /b "winws.exe" ^
 --wf-tcp=80,443 --wf-udp=443,50000-50010 ^
 --filter-tcp=443 --hostlist="youtubeGV.txt" --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=4 --new ^
 --filter-tcp=443 --hostlist="youtube.txt" --dpi-desync=split --dpi-desync-split-pos=3 --dpi-desync-repeats=4 --dpi-desync-autottl=1 --new ^
 --filter-udp=50000-50010 --ipset="ipset-discord.txt" --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new ^
 --filter-tcp=443 --hostlist="discord.txt" --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new ^
 --filter-tcp=443 --hostlist="other.txt" --hostlist="faceinsta.txt" --ipset="ipset-cloudflare.txt" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls="tls_clienthello_3.bin" --dpi-desync-ttl=2