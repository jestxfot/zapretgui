@echo off
REM Стратегия Оригинальная bol-van v1 (07.04.2025)
REM VERSION: 1.2
REM Дата обновления: 2025-04-10

chcp 1251

:init
 set "batchPath=%~dpnx0"
 set BIN=%~dp0\
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


taskkill /f /im winws.exe 
sc delete windivert
sc stop windivert

start "presetOrig" /min "winws.exe" ^
--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=443,50000-50099 ^
--filter-tcp=80 --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new ^
--filter-tcp=443 --hostlist="youtube.txt" --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls="tls_clienthello_www_google_com.bin" --new ^
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new ^
--filter-udp=443 --hostlist="youtube.txt" --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic="quic_initial_www_google_com.bin" --new ^
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=11 --new ^
--filter-udp=50000-50099 --ipset="ipset-discord.txt" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --new ^
--filter-tcp=443 --hostlist="faceinsta.txt" --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern="tls_clienthello_chat_deepseek_com.bin"