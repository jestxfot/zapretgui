@echo off
REM Стратегия Fake TLS Mod ttl 4
REM VERSION: 1.3
REM Дата обновления: 2025

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
set "vbsSilent=%BIN%runsilent.vbs"
> "%vbsSilent%" (
    echo Dim sh : Set sh = CreateObject("WScript.Shell"^)
    echo sh.CurrentDirectory = "%BIN%"
    echo cmd = """" ^& "%BIN%winws.exe" ^&""""
    echo cmd = cmd ^& " --wf-tcp=80,443 --wf-udp=443,50000-50100"
    echo cmd = cmd ^& " --filter-udp=443 --hostlist=""discord.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake --dpi-desync-repeats=8 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
    echo cmd = cmd ^& " --filter-udp=50000-50100 --ipset=""ipset-discord.txt"" --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-repeats=8 --new"
    echo cmd = cmd ^& " --filter-tcp=80 --hostlist=""discord.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake,split2 --dpi-desync-autottl=3 --dpi-desync-fooling=md5sig --new"
    echo cmd = cmd ^& " --filter-tcp=443 --hostlist=""discord.txt"" --hostlist=""youtube.txt"" --hostlist=""faceinsta.txt"" --hostlist=""other.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake --dpi-desync-ttl=4 --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"
    echo sh.Run cmd, 0, False ' 0 = hidden, False = не ждать завершения
)
:: ---------------------------------------------
:: запускаем скрипт без консоли
:: ---------------------------------------------
"%SystemRoot%\System32\wscript.exe" "%vbsSilent%"
:: если нужно – удаляем VBS
::del "%vbsSilent%" 2>nul
endlocal