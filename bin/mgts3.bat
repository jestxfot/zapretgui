@echo off
REM Стратегия МГТС 3
REM VERSION: 1.0
REM Дата обновления: 2024

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
ECHO args = args ^& strArg ^& " " >> "%vbsGetPrivileges%"
ECHO Next >> "%vbsGetPrivileges%"
ECHO args = "/c """ + "!batchPath!" + """ " + args >> "%vbsGetPrivileges%"
ECHO UAC.ShellExecute "%SystemRoot%\System32\cmd.exe", args, "", "runas", 1 >> "%vbsGetPrivileges%"
"%SystemRoot%\System32\WScript.exe" "%vbsGetPrivileges%" %*
exit /B
:fileRemove
del "%vbsGetPrivileges%" 1>nul 2>nul & shift /1
cd /d "%~dp0"
taskkill /f /im winws.exe 1>nul 2>nul
sc stop windivert 1>nul 2>nul
sc delete windivert 1>nul 2>nul
sc delete windivert 1>nul 2>nul
:: ---------------------------------------------
:: создаём VBS-файл
:: ---------------------------------------------
setlocal
set "BIN=%~dp0"
set "vbsSilent=%BIN%runsilent_MGTS_v3.vbs"
> "%vbsSilent%" (
    echo Dim sh : Set sh = CreateObject("WScript.Shell"^)
    echo sh.CurrentDirectory = "%BIN%"
    echo cmd = """" ^& "%BIN%winws.exe" ^& """"
    echo cmd = cmd ^& " --wf-tcp=80,443 --wf-udp=443,50000-50900"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""youtube.txt"" --dpi-desync=split --dpi-desync-split-pos=3 --dpi-desync-repeats=4 --dpi-desync-autottl=1 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""discord.txt"" --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=3 --new"
    echo cmd = cmd ^& " --filter-udp=443 --hostlist=""youtubeQ.txt"" --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
    echo cmd = cmd ^& " --filter-udp=443 --hostlist=""discord.txt"" --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=""quic_test_00.bin"" --dpi-desync-cutoff=n2 --new"
    echo cmd = cmd ^& " --filter-udp=50000-59000 --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=""quic_test_00.bin"" --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""other.txt"" --hostlist=""faceinsta.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=""tls_clienthello_3.bin"" --dpi-desync-ttl=2"
    echo sh.Run cmd, 0, False ' 0 = hidden, False = не ждать завершения
)
:: ---------------------------------------------
:: запускаем скрипт без консоли
:: ---------------------------------------------
"%SystemRoot%\System32\wscript.exe" "%vbsSilent%"
:: если нужно – удаляем VBS
::del "%vbsSilent%" 2>nul
endlocal