@echo off
chcp 866
pushd "%~dp0"

if not "%1"=="am_admin" (powershell start -verb runas '%0' am_admin & exit /b)
del /F /Q "%~dp0logfile.log" > nul

set ARGS=--wf-tcp=80,443 --wf-udp=443,50000-50099 --filter-udp=443 --hostlist="%~dp0lists\russia-youtubeQ.txt" --dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic="%~dp0fake\quic_1.bin" --new --filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new --filter-tcp=443 --hostlist="%~dp0lists\russia-youtube.txt" --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls="%~dp0fake\tls_clienthello_2.bin" --dpi-desync-ttl=3 --new --filter-tcp=80 --hostlist="%~dp0lists\russia-blacklist.txt" --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --new --filter-tcp=443 --hostlist="%~dp0lists\russia-blacklist.txt" --hostlist="%~dp0lists\myhostlist.txt" --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls="%~dp0fake\tls_clienthello_2.bin" --dpi-desync-ttl=5 --new --filter-tcp=443 --hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new --filter-udp=443 --hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic="%~dp0fake\quic_2.bin" --dpi-desync-repeats=8 --dpi-desync-cutoff=n2 --new --filter-udp=50000-50099 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-fake-quic="%~dp0fake\quic_1.bin" --dpi-desync-cutoff=d2 --new --filter-tcp=443 --hostlist-auto="%~dp0lists\autohostlist.txt" --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld,1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls="%~dp0fake\tls_clienthello_4.bin" --dpi-desync-autottl

set ARGS=%ARGS:"=\"%

call :srvinst zapret
rem set ARGS=--wf-l3=ipv4,ipv6 --wf-udp=443 --dpi-desync=fake 
rem call :srvinst zapret2
goto :EOF

:srvinst
net stop %1 >>"%~dp0logfile.log"
sc delete %1 >>"%~dp0logfile.log"
sc create %1 binPath= "\"%~dp0winws.exe\" %ARGS%" DisplayName= "Zapret DPI bypass : %1" start= auto >>"%~dp0logfile.log"
sc description %1 "Zapret DPI bypass software" >>"%~dp0logfile.log"
sc start %1
echo. >>"%~dp0logfile.log"
echo List of all services >>"%~dp0logfile.log"
sc query >>"%~dp0logfile.log"
