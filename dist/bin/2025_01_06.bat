@echo off
REM Стратегия Все сайты (06.01.2025)
REM VERSION: 1.0
REM Дата обновления: 2025-01-06

chcp 1251

:init
set "batchPath=%~dpnx0"
set BIN=%~dp0\
set BINS=%~dp0
set "vbsGetPrivileges=%BIN%\elevator.vbs"
setlocal EnableDelayedExpansion

if '%1'=='ELEV' (echo ELEV & shift /1 & goto fileRemove)
ECHO Set UAC = CreateObject^("Shell.Application"^) > "%vbsGetPrivileges%"
ECHO args = "ELEV " >> "%vbsGetPrivileges%"
ECHO For Each strArg in WScript.Arguments >> "%vbsGetPrivileges%"
ECHO args = args ^& strArg ^& " "  >> "%vbsGetPrivileges%"
ECHO Next >> "%vbsGetPrivileges%"
ECHO args = "/c """ + "!batchPath!" + """ " + args >> "%vbsGetPrivileges%"
ECHO UAC.ShellExecute "%SystemRoot%\System32\cmd.exe", args, "", "runas", 1 >> "%vbsGetPrivileges%"
"%SystemRoot%\System32\WScript.exe" "%vbsGetPrivileges%" %*
exit /B

:fileRemove
del "%vbsGetPrivileges%" 1>nul 2>nul  &  shift /1
cd /d "%~dp0"

taskkill /f /im winws.exe
sc stop windivert
sc delete windivert
sc delete windivert

:: ---------------------------------------------
:: создаём VBS-файл
:: ---------------------------------------------
setlocal
set "BIN=%~dp0"
set "vbsSilent=%BIN%runsilent.vbs"

> "%vbsSilent%" (
    echo Dim sh : Set sh = CreateObject("WScript.Shell"^)
    echo sh.CurrentDirectory = "%BIN%"
    echo cmd = """" ^& "%BIN%winws.exe" ^& """"
    echo cmd = cmd ^& " --wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=443,50000-50099"
    echo cmd = cmd ^& " --filter-tcp=443 --ipset=""russia-youtube-rtmps.txt"" --dpi-desync=syndata --dpi-desync-fake-syndata=""tls_clienthello_4.bin"" --dpi-desync-autottl --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""youtube_v2.txt"" --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""youtubeGV.txt"" --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --new"
    echo cmd = cmd ^& " --filter-udp=443 --hostlist=""youtubeQ.txt"" --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=""quic_3.bin"" --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""other.txt"" --hostlist=""faceinsta.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=""tls_clienthello_www_google_com.bin"" --dpi-desync-ttl=2 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --ipset=""ipset-discord.txt"" --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_3.bin --dpi-desync-autottl --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""discord.txt"" --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"
    echo cmd = cmd ^& " --filter-udp=443 --hostlist=""discord.txt"" --dpi-desync=fake,udplen --dpi-desync-udplen-increment=5 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=""quic_2.bin"" --dpi-desync-repeats=7 --dpi-desync-cutoff=n2 --new"
    echo cmd = cmd ^& " --filter-udp=50000-50090 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n3 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --ipset-ip=XXX.XXX.XXX.XXX/XX,XXX.XXX.XXX.XXX/XX --wssize=1:6 --hostlist-domains=googlevideo.com --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2 --new"

    echo sh.Run cmd, 0, False          ' 0 = hidden, False = не ждать завершения
)

:: ---------------------------------------------
:: запускаем скрипт без консоли
:: ---------------------------------------------
"%SystemRoot%\System32\wscript.exe" "%vbsSilent%"

:: если нужно – удаляем VBS
::del "%vbsSilent%" 2>nul
endlocal