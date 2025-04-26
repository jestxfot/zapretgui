@echo off
REM Стратегия Ульта конфиг ZL
REM VERSION: 1.1
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
set "vbsSilent=%BIN%runsilent_Ultimate_Config_ZL.vbs"
> "%vbsSilent%" (
    echo Dim sh : Set sh = CreateObject("WScript.Shell"^)
    echo sh.CurrentDirectory = "%BIN%"
    echo cmd = """" ^& "%BIN%winws.exe" ^& """"
    echo cmd = cmd ^& " --wf-tcp=80,443 --wf-udp=443,50000-50099"
    echo cmd = cmd ^& " --filter-udp=443 --hostlist=""youtubeQ.txt"" --dpi-desync=fake --dpi-desync-fake-quic=""quic_1.bin"" --dpi-desync-repeats=4 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""youtubeGV.txt"" --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""youtube.txt"" --hostlist=""other.txt"" --hostlist=""faceinsta.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=""tls_clienthello_2.bin"" --dpi-desync-ttl=3 --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""discord.txt"" --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"
    echo cmd = cmd ^& " --filter-udp=443 --hostlist=""discord.txt"" --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=""quic_2.bin"" --dpi-desync-repeats=8 --dpi-desync-cutoff=n2 --new"
    echo cmd = cmd ^& " --filter-udp=50000-50099 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=""quic_1.bin"""
    echo sh.Run cmd, 0, False ' 0 = hidden, False = не ждать завершения
)
:: ---------------------------------------------
:: запускаем скрипт без консоли
:: ---------------------------------------------
"%SystemRoot%\System32\wscript.exe" "%vbsSilent%"
:: если нужно – удаляем VBS
::del "%vbsSilent%" 2>nul
endlocal