@echo off
REM Стратегия Другие провайдеры 1
REM VERSION: 1.2
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

start "zapret: winws Other_Providers_v1" /b "winws.exe" ^
 --wf-l3=ipv4,ipv6 --wf-tcp=443 --wf-udp=443,50000-65535 ^
 --filter-udp=443 --hostlist="youtubeQ.txt" --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic="quic_initial_www_google_com.bin" --new ^
 --filter-tcp=443 --hostlist="youtube.txt" --dpi-desync=split --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls="tls_clienthello_www_google_com.bin" --dpi-desync-ttl=1 --new ^
 --filter-tcp=443 --hostlist="discord.txt" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls="tls_clienthello_4.bin" --dpi-desync-ttl=4 --new ^
 --filter-udp=443 --hostlist="discord.txt" --dpi-desync=fake,split2 --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic="quic_initial_www_google_com.bin" --new ^
 --filter-udp=50000-59000 --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic="quic_initial_www_google_com.bin" --new ^
 --filter-tcp=443 --hostlist="other.txt" --hostlist="faceinsta.txt" --ipset="ipset-cloudflare.txt" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls="tls_clienthello_3.bin" --dpi-desync-ttl=2