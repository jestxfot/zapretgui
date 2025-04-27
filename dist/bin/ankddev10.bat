@echo off
REM Стратегия Ankddev v10
REM VERSION: 1.5
REM Дата обновления: 2024

whoami /groups | find "S-1-5-32-544" >nul 2>&1 && goto :ADMIN
powershell -nop -c "Start-Process '%~f0' -arg @('ELEV','%*') -Verb RunAs"
exit /b
:ADMIN
if /i "%1"=="ELEV" shift

taskkill /f /im winws.exe >nul 2>&1
sc stop windivert >nul 2>&1
sc delete windivert >nul 2>&1
sc delete windivert >nul 2>&1
cd /d "%~dp0"

start "zapret: winws Ankdev v10" /b "winws.exe" ^
 --wf-l3=ipv4,ipv6 --wf-tcp=443 --wf-udp=443,50000-65535 ^
 --filter-tcp=443 --hostlist="discord.txt" --dpi-desync=syndata,disorder2 --dpi-desync-split-pos=3 --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls="tls_clienthello_www_google_com.bin" --new ^
 --filter-udp=443 --hostlist="discord.txt" --dpi-desync=fake,split2 --dpi-desync-repeats=11 --dpi-desync-udplen-increment=15 --dpi-desync-fake-quic="quic_initial_www_google_com.bin" --new ^
 --filter-udp=50000-50099 --ipset="ipset-discord.txt" --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d5 --dpi-desync-repeats=11 --new ^
 --filter-tcp=443 --dpi-desync=syndata,multidisorder --dpi-desync-split-pos=4 --dpi-desync-repeats=10 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls="tls_clienthello_vk_com_kyber.bin" --new ^
 --filter-udp=443 --hostlist="youtubeQ.txt" --dpi-desync=fake,split2 --dpi-desync-repeats=10 --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic="quic_initial_www_google_com.bin"