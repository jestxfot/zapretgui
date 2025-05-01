;---------------------------------------------------
;  Zapret installer / updater (ProgramData by default)
;---------------------------------------------------
[Setup]
AppName=Zapret
AppVersion=15.5.0
AppId={{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0}}
; ───────────────────────────────────────────────────────────────
DefaultDirName={code:GetInstallDir}
DisableDirPage=no
UsePreviousAppDir=yes
; ───────────────────────────────────────────────────────────────
PrivilegesRequired=admin
DefaultGroupName=Zapret
OutputDir=installer
OutputBaseFilename=ZapretSetup
Compression=lzma2
SolidCompression=yes
SetupIconFile=zapret.ico
UninstallDisplayIcon={app}\Zapret.exe
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
;---------------------------------------------------

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "dist\Zapret.exe";           DestDir: "{app}";      Flags: ignoreversion
Source: "dist\bin\*";                DestDir: "{app}\bin";  Flags: recursesubdirs ignoreversion;   Excludes: "aaaaaaaaa"
Source: "dist\bin\aaaaaaaaa";        DestDir: "{app}\bin";  Flags: onlyifdoesntexist ignoreversion
Source: "dist\bin\winws.exe";        DestDir: "{app}\bin";  Flags: onlyifdoesntexist ignoreversion


[Files]
	   
[Icons]
Name: "{group}\Zapret";              Filename: "{app}\Zapret.exe"; WorkingDir: "{app}"
Name: "{group}\Удалить Zapret";      Filename: "{uninstallexe}";   IconFilename: "{app}\Zapret.exe"
Name: "{commondesktop}\Zapret";      Filename: "{app}\Zapret.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

;──────────────────────────────────────────────
[Code]
{ 1.  КИЛЛИМ два процесса ───────────────────── }
procedure KillProcess(const ExeName: string);
var R: Integer;
begin
  Exec('taskkill.exe', '/IM ' + ExeName + ' /F', '',
       SW_HIDE, ewWaitUntilTerminated, R);
end;

function PrepareToInstall(var NeedsRestart: Boolean): string;
begin
  KillProcess('winws.exe');
  KillProcess('Zapret.exe');
  Result := '';
end;

{ 2.  ДЕФОЛТНЫЙ ПУТЬ ────────────────────────── }
function GetInstallDir(Param: string): string;
begin
  { если есть предыдущая установка – Inno сам подставит её,
    иначе отдаём ProgramData }
  Result := ExpandConstant('{commonappdata}\Zapret');
end;

{ 3.  ПРОВЕРКА ПУТИ ──────────────────────────── }
function IsAsciiLetter(C: Char): Boolean;
begin
  Result := (C >= 'A') and (C <= 'Z') or (C >= 'a') and (C <= 'z');
end;

function IsAllowedChar(C: Char): Boolean;
begin
  { допустимы только лат. буквы, обратный слэш и двоеточие }
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
  Result := True;                                { по умолчанию идём дальше }

  if CurPageID = wpSelectDir then                { страница выбора папки }
  begin
    if not CheckDirName(WizardDirValue) then
    begin
      MsgBox('Путь к папке установки может содержать только латинские буквы ' +
             'и символы "\" и ":". ' + #13#10 +
             'Без пробелов, цифр и специальных символов.',
             mbError, MB_OK);
      Result := False;                           { остаёмся на странице }
    end;
  end;
end;