title ---] �஢�ઠ ���ᨨ Windows... [---
@echo off
PUSHD "%~dp0"
setlocal
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%version%" == "6.1" (
color FD
echo.
echo !!!��������!!!
echo.
echo �����㦥�� Windows 7. �� Win 7 ��ଠ�쭠� ࠡ�� ��� 䠩��� ����� ����
echo ����襭�, �᫨ � ��� � ����� YTDisBystro ���� ���᪨� �㪢�. �᫨ � ���
echo ��� ���짮��⥫� �� ���᪮� �몥, ����� ࠧ����� ����� YTDisBystro �
echo ����㧪�� ��� �� ����祬 �⮫�.
echo ��७��� ����� ���ਬ�� � ᮧ������ ����� �� ��᪥ �: ��� � �����-�����
echo ����� ��� ���᪨� �㪢 � ��� �� ��᪥ D: ��᫥ �⮣� ������� 䠩�
echo !!!get_zapret_first!!!.cmd �� ࠧ � �⢥��� Y �� ����� "�� ࠢ��
echo �த������?".
echo.
echo ����� ���� � �����: "%~dp0"
echo �᫨ �� �� ����� ��������� ᨬ����� ��� ���᪨� �㪢 � ���窥 � ��⥬ �
echo ����� ���, ����� ����窠�� - �⢥��� Y ��אַ ᥩ��.
echo.
goto :PROMPT
)

goto :END

:PROMPT
set /P AREYOUSURE=��� ࠢ�� �த������ (Y/[N])?
if /I "%AREYOUSURE%" NEQ "N" goto :END

:MEAT
endlocal
exit

:END
endlocal > nul
"!!!get_zapret_first!!!.cmd :startall" > nul
