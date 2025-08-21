;---------------------------------------------------
;  Zapret installer / updater (ProgramData by default)
;  Используйте: ISCC.exe /DCHANNEL=test /DVERSION=1.0.0.0 zapret_universal.iss
;  или:         ISCC.exe /DCHANNEL=stable /DVERSION=1.0.0.0 zapret_universal.iss
;---------------------------------------------------

; Определяем дефолтные значения
#ifndef CHANNEL
  #define CHANNEL "stable"
#endif

#ifndef VERSION
  #define VERSION "16.1.0.0"
#endif

; Настройки в зависимости от канала
#if CHANNEL == "test"
  #define AppName "Zapret Dev"
  #define AppId "{{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0-TEST}}"
  #define OutputName "ZapretSetup_TEST"
  #define GroupName "Zapret Dev"
  #define DataFolder "ZapretDev"
  #define IconFile "ZapretDevLogo3.ico"
#else
  #define AppName "Zapret"
  #define AppId "{{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0}}"
  #define OutputName "ZapretSetup"
  #define GroupName "Zapret"
  #define DataFolder "Zapret"
  #define IconFile "Zapret1.ico"
#endif

[Setup]
AppName={#AppName}
AppVersion={#VERSION}
AppId={#AppId}
; ───────────────────────────────────────────────────────────────
DefaultDirName={code:GetInstallDir}
DisableDirPage=no
UsePreviousAppDir=yes
; ───────────────────────────────────────────────────────────────
PrivilegesRequired=admin
DefaultGroupName={#GroupName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename={#OutputName}
Compression=lzma2
SolidCompression=yes
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\Zapret.exe
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "..\zapret\Zapret.exe";         DestDir: "{app}"; Flags: ignoreversion
Source: "..\zapret\bat\*";              DestDir: "{app}\bat"; Flags: recursesubdirs ignoreversion
Source: "..\zapret\bin\*";              DestDir: "{app}\bin"; Flags: recursesubdirs ignoreversion
Source: "..\zapret\exe\*";              DestDir: "{app}\exe"; Flags: recursesubdirs ignoreversion
Source: "..\zapret\json\*";             DestDir: "{app}\json"; Flags: recursesubdirs ignoreversion
Source: "..\zapret\ico\*";              DestDir: "{app}\ico"; Flags: recursesubdirs ignoreversion
Source: "..\zapret\lists\*";            DestDir: "{app}\lists"; Flags: recursesubdirs ignoreversion
Source: "..\zapret\sos\*";              DestDir: "{app}\sos"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\Zapret.exe"; WorkingDir: "{app}"
Name: "{group}\Удалить {#AppName}";      Filename: "{uninstallexe}"; IconFilename: "{app}\Zapret.exe"
Name: "{commondesktop}\{#AppName}";      Filename: "{app}\Zapret.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\{#DataFolder}"

[Run]
; Запуск для обычной установки
Filename: "{app}\Zapret.exe"; Description: "Запустить {#AppName}"; \
    Flags: nowait postinstall skipifsilent shellexec; \
    Check: not WizardNoIcons

; Автозапуск при тихой установке (для автообновления)
Filename: "{app}\Zapret.exe"; \
    Flags: nowait runhidden shellexec runasoriginaluser; \
    Check: WizardNoIcons; \
    Parameters: ""

;──────────────────────────────────────────────
[Code]
{ КИЛЛИМ процессы }
procedure KillProcess(const ExeName: string);
var R: Integer;
begin
  Exec('taskkill.exe', '/IM ' + ExeName + ' /F', '',
       SW_HIDE, ewWaitUntilTerminated, R);
end;

{ ОСТАНОВКА/УДАЛЕНИЕ СЛУЖБЫ WinDivert }
procedure StopAndDeleteService(const ServiceName: string);
var R: Integer;
begin
  Exec('sc.exe', 'stop "' + ServiceName + '"', '',
       SW_HIDE, ewWaitUntilTerminated, R);
  Exec('sc.exe', 'delete "' + ServiceName + '"', '',
       SW_HIDE, ewWaitUntilTerminated, R);
end;

{ ПОДГОТОВКА К УСТАНОВКЕ }
function PrepareToInstall(var NeedsRestart: Boolean): string;
begin
  StopAndDeleteService('WinDivert');
  StopAndDeleteService('WinDivert14'); 
  StopAndDeleteService('WinDivert1.4');
  StopAndDeleteService('WinDivert64');
  
  KillProcess('winws.exe');
  KillProcess('Zapret.exe');

  Result := '';
end;

{ ДЕФОЛТНЫЙ ПУТЬ }
function GetInstallDir(Param: string): string;
begin
  Result := ExpandConstant('{commonappdata}\{#DataFolder}');
end;

{ ПРОВЕРКА ПУТИ }
function IsAsciiLetter(C: Char): Boolean;
begin
  Result := (C >= 'A') and (C <= 'Z') or (C >= 'a') and (C <= 'z');
end;

function IsAllowedChar(C: Char): Boolean;
begin
  Result := IsAsciiLetter(C) or (C = '\') or (C = ':');
end;

function CheckDirName(const Dir: string): Boolean;
var I: Integer;
begin
  for I := 1 to Length(Dir) do
    if not IsAllowedChar(Dir[I]) then
    begin
      Result := False;
      Exit;
    end;
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = wpSelectDir then
  begin
    if not CheckDirName(WizardDirValue) then
    begin
      MsgBox('Путь к папке установки может содержать только латинские буквы ' +
             'и символы "\" и ":". ' + #13#10 +
             'Без пробелов, цифр и специальных символов.',
             mbError, MB_OK);
      Result := False;
    end;
  end;
end;

{ УДАЛЕНИЕ }
procedure CurUninstallStepChanged(CurStep: TUninstallStep);
begin
  if CurStep = usUninstall then
  begin
    StopAndDeleteService('WinDivert');
    StopAndDeleteService('WinDivert14');
    StopAndDeleteService('WinDivert1.4');
    StopAndDeleteService('WinDivert64');

    KillProcess('winws.exe');
    KillProcess('Zapret.exe');
  end;
end;

{ ПРОВЕРКА ПАРАМЕТРА /NORESTART }
function WizardNoIcons: Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/NORESTART') = 0 then
    begin
      Result := True;
      Exit;
    end;
end;