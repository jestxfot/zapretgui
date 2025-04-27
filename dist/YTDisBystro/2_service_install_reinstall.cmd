@echo off
chcp 866
pushd "%~dp0"

if not "%1"=="am_admin" (powershell start -verb runas '%0' am_admin & exit /b)

del /F /Q "%~dp0logfile.log"

:: !НЕ ТРОГАЙТЕ ТУТ НИЧЕГО! ::
set YTDB_YTPot=--dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-split-seqovl-pattern="%~dp0fake\tls_clienthello_7.bin"
set YTDB_WinSZ=43 --hostlist-domains=googlevideo.com --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=2,midsld-2 --dpi-desync-split-seqovl-pattern="%~dp0fake\tls_clienthello_7.bin"
set YTDB_YTQC=--dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic="%~dp0fake\quic_4.bin" --dpi-desync-cutoff=n3 --dpi-desync-repeats=2
set YTDB_DIS1=--hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fake --dpi-desync-fooling=badseq --dpi-desync-fake-tls="%~dp0fake\tls_clienthello_7.bin" --dpi-desync-fake-tls-mod=rnd
set YTDB_DIS2=--hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fake,udplen --dpi-desync-udplen-increment=5 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic="%~dp0fake\quic_2.bin" --dpi-desync-repeats=7 --dpi-desync-cutoff=n2
set YTDB_DIS3=--filter-l7=discord,stun --dpi-desync=fake
:: ^^ !НЕ ТРОГАЙТЕ ТУТ НИЧЕГО! ^^ ::

set YTDB_RTMPS=43 --ipset="%~dp0lists\russia-youtube-rtmps.txt" --dpi-desync=syndata --dpi-desync-fake-syndata="%~dp0fake\tls_clienthello_4.bin" --dpi-desync-autottl

:: Здесь можно включить другую стратегию для Ютуба по протоколу QUIC [интерфейс и googlevideo.com], убрав rem и выключить, добавив rem ::
rem set YTDB_YTQC=--dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic="%~dp0fake\quic_3.bin" --dpi-desync-cutoff=n3 --dpi-desync-repeats=2
rem set YTDB_YTQC=--dpi-desync=fake --dpi-desync-fake-quic="%~dp0fake\quic_2.bin" --dpi-desync-cutoff=n3 --dpi-desync-repeats=6
rem set YTDB_YTQC=--dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0xFEA82025 --dpi-desync-fake-quic="%~dp0fake\quic_3.bin" --dpi-desync-cutoff=n4 --dpi-desync-repeats=2
rem set YTDB_YTQC=--dpi-desync=fake,udplen --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic="%~dp0fake\quic_3.bin" --dpi-desync-repeats=2 --dpi-desync-cutoff=n3
rem set YTDB_YTQC=[Вы можете добавить сюда свою стратегию]

:: Здесь можно включить другую стратегию для интерфейса Ютуба без QUIC убрав rem и выключить, добавив rem ::
rem set YTDB_YTPot=--dpi-desync=fake,multisplit --dpi-desync-fooling=badseq --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=2 --dpi-desync-fake-tls="%~dp0fake\tls_clienthello_2n.bin" --dpi-desync-fake-tls-mod=rnd --dpi-desync-autottl
rem set YTDB_YTPot=--dpi-desync=fake,multisplit --dpi-desync-fooling=badseq --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=2 --dpi-desync-fake-tls-mod=dupsid,sni=drive.google.com --dpi-desync-autottl
rem set YTDB_YTPot=--dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern="%~dp0fake\tls_clienthello_2.bin"
rem set YTDB_YTPot=[Вы можете добавить сюда свою стратегию]

:: Здесь можно включить другую стратегию или wssize для видео Ютуба без QUIC [googlevideo.com] убрав rem и выключить, добавив rem ::
rem set YTDB_WinSZ=43 --hostlist-domains=googlevideo.com --dpi-desync=fakeddisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=2,midsld-2 --dpi-desync-fakedsplit-pattern="%~dp0fake\tls_clienthello_7.bin" --dpi-desync-fooling=badseq --dpi-desync-autottl
rem set YTDB_WinSZ=43 --hostlist-domains=googlevideo.com --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10  --dpi-desync-autottl
rem set YTDB_WinSZ=43 --hostlist-domains=googlevideo.com --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern="%~dp0fake\tls_clienthello_2.bin"
rem set YTDB_WinSZ=43 [Вы можете добавить сюда свою стратегию]
rem set YTDB_WinSZ=43 --wssize 1:6 --dpi-desync=fakedsplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --dpi-desync-fooling=badseq --dpi-desync-autottl
rem set YTDB_ZMESS=43 --ipset-ip=XXX.XXX.XXX.XXX/XX,XXX.XXX.XXX.XXX/XX --wssize=1:6 --hostlist-domains=googlevideo.com --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2

:: Здесь можно включить другую стратегию для Дискорда убрав rem и выключить, добавив rem ::
rem set YTDB_DIS1=--hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fakedsplit --dpi-desync-split-pos=midsld-1,1 --dpi-desync-fooling=badseq --dpi-desync-fakedsplit-pattern="%~dp0fake\tls_clienthello_4.bin" --dpi-desync-autottl
rem set YTDB_DIS1=--hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=dupsid,sni=river.rutube.ru,padencap --dpi-desync-autottl
rem set YTDB_DIS1=--ipset="%~dp0lists\russia-discord-ipset.txt" --dpi-desync=syndata,fake,multidisorder --dpi-desync-fake-syndata="%~dp0fake\tls_clienthello_1.bin" --hostlist="%~dp0lists\russia-discord.txt" --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,midsld-2 --dpi-desync-fake-tls="%~dp0fake\tls_clienthello_4.bin" --dpi-desync-fooling=badseq --dpi-desync-autottl
rem set YTDB_DIS1=--ipset="%~dp0lists\russia-discord-ipset.txt" --dpi-desync=syndata --dpi-desync-fake-syndata="%~dp0fake\tls_clienthello_4.bin" --dpi-desync-autottl
rem set YTDB_DIS1=--hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fake --dpi-desync-fooling=badseq --dpi-desync-fake-tls="%~dp0fake\tls_clienthello_2n.bin" --dpi-desync-fake-tls-mod=rnd --dpi-desync-repeats=4 --dpi-desync-autottl
rem set YTDB_DIS1=--hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fake --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=dupsid,sni=drive.google.com,padencap --dpi-desync-repeats=4 --dpi-desync-autottl
rem set YTDB_DIS1=[Вы можете добавить сюда свою стратегию (запуск Дискорда)]
rem set YTDB_DIS2=--hostlist="%~dp0lists\russia-discord.txt" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic="%~dp0fake\quic_1.bin"
rem set YTDB_DIS3=--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6
rem set YTDB_DIS3=--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-fake-unknown-udp=0xC30000000108 --dpi-desync-cutoff=n2
rem set YTDB_DIS3=[Вы можете добавить сюда свою стратегию (голос)]
:: Конец блока настройки стратегий ::

set ARGS=--wf-tcp=80,443 --wf-udp=443,50000-50090 --filter-tcp=80,443 --hostlist="%~dp0lists\netrogat.txt" --new --filter-tcp=4%YTDB_RTMPS% --new --filter-udp=443 --hostlist="%~dp0lists\russia-youtubeQ.txt" %YTDB_YTQC% --new --filter-tcp=443 --hostlist="%~dp0lists\russia-youtube.txt" %YTDB_YTPot% --new --filter-tcp=80,443 --hostlist="%~dp0lists\mycdnlist.txt" --dpi-desync=fakeddisorder --dpi-desync-split-pos=2,midsld --dpi-desync-fakedsplit-pattern="%~dp0fake\tls_clienthello_1.bin" --dpi-desync-fooling=badseq --new --filter-tcp=80 --hostlist="%~dp0lists\russia-blacklist.txt" --hostlist="%~dp0lists\myhostlist.txt" --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=badseq --new --filter-tcp=443 --hostlist="%~dp0lists\russia-blacklist.txt" --hostlist="%~dp0lists\myhostlist.txt" --dpi-desync=fakedsplit --dpi-desync-fooling=badseq --dpi-desync-split-pos=2,midsld-1 --dpi-desync-fakedsplit-pattern="%~dp0fake\tls_clienthello_4.bin" --new --filter-tcp=443 %YTDB_DIS1% --new --filter-udp=443 %YTDB_DIS2% --new --filter-udp=50000-50090 %YTDB_DIS3% --new --filter-tcp=4%YTDB_ZMESS% --new --filter-tcp=4%YTDB_WinSZ% --new --filter-tcp=443 --hostlist-auto="%~dp0lists\autohostlist.txt" --hostlist-exclude="%~dp0lists\netrogat.txt" --dpi-desync=fakeddisorder --dpi-desync-split-pos=2,midsld+1 --dpi-desync-fakedsplit-pattern="%~dp0fake\tls_clienthello_4.bin" --dpi-desync-fooling=badseq

set ARGS=%ARGS:"=\"%

call :srvinst zapret
rem set ARGS=--wf-l3=ipv4,ipv6 --wf-udp=443 --dpi-desync=fake 
rem call :srvinst zapret2
goto :eof

:srvinst
echo Add zapret service and start it
net stop %1 >>"%~dp0logfile.log"
sc delete %1 >>"%~dp0logfile.log"
sc create %1 binPath= "\"%~dp0winws.exe\" %ARGS%" DisplayName= "Zapret DPI bypass : %1" start= auto >>"%~dp0logfile.log"
sc description %1 "Zapret DPI bypass software" >>"%~dp0logfile.log"
sc start %1
echo. >>"%~dp0logfile.log"
echo List of all services >>"%~dp0logfile.log"
sc query >>"%~dp0logfile.log"
