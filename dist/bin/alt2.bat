@echo off
REM Стратегия Alt 2
REM VERSION: 2.4
REM Дата обновления: 2025

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

start "zapret: winws custom 4" /b "winws.exe" ^
 --wf-tcp=80,443 --wf-udp=443,50000-50100 ^
 --filter-udp=443 --hostlist="discord.txt" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic="quic_initial_www_google_com.bin" --new ^
 --filter-udp=50000-50100 --ipset="ipset-discord.txt" --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new ^
 --filter-tcp=80 --hostlist="discord.txt" --ipset="ipset-cloudflare.txt" --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new ^
 --filter-tcp=443 --hostlist-exclude-domains=lmarena.ai,gitflic.ru,searchengines.guru,habr.com,cdn.ampproject.org,st.top100.ru,rootsplants.co.uk,podviliepitomnik.ru,cvetovod.by,veresk.by,use.fontawesome.com,xn--p1ai --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern="tls_clienthello_www_google_com.bin" --new ^
 --filter-udp=443 --ipset="ipset-cloudflare.txt" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic="quic_initial_www_google_com.bin"