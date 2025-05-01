;---------------------------------------------------
;  Zapret installer / updater (ProgramData / D:\)
;---------------------------------------------------
[Setup]
AppName=Zapret
AppVersion=15.0.18
AppId={{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0}}
DefaultDirName={code:GetInstallDir}
DisableDirPage=yes             
; прячем стандартный выбор папки
UsePreviousAppDir=yes               
; при апдейте берём старый путь
PrivilegesRequired=admin            
; нужен для ProgramData
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

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "dist\Zapret.exe";           DestDir: "{app}";      Flags: ignoreversion
Source: "dist\bin\*";                DestDir: "{app}\bin";  Flags: recursesubdirs ignoreversion;     Excludes: "aaaaaaaaa"
Source: "dist\bin\aaaaaaaaa";        DestDir: "{app}\bin";  Flags: onlyifdoesntexist ignoreversion

[Icons]
Name: "{group}\Zapret";              Filename: "{app}\Zapret.exe"
Name: "{commondesktop}\Zapret";      Filename: "{app}\Zapret.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

;──────────────────────────────────────────────
[Code]

var
  LocationPage: TInputOptionWizardPage;
  IdxDiskD: Integer;
  IsUpdate: Boolean;

function DriveExists(const Letter: string): Boolean;
begin
  Result := DirExists(Letter + ':\');
end;

function GetInstallDir(Param: string): string;
begin
  { Если страницу не создали (апдейт) или выбран ProgramData → ProgramData }
  if (LocationPage = nil) or (LocationPage.SelectedValueIndex = 1) then
    Result := ExpandConstant('{commonappdata}\Zapret')
  else
    Result := 'D:\Zapret';
end;

procedure InitializeWizard();
var
  PrevDir: string;
begin
  { ── определяем, обновление ли это ── }
  PrevDir  := GetPreviousData('instdir', '');
  IsUpdate := DirExists(PrevDir);

  { ── если НЕ обновление → показываем страницу ── }
  if not IsUpdate then
  begin
    LocationPage :=
      CreateInputOptionPage(wpWelcome,
        'Куда установить Zapret?',
        'Выберите место установки:',
        'Папка будет создана, если её ещё нет.', True, False);

    { пункт D:\Zapret }
    if DriveExists('D') then
      IdxDiskD := LocationPage.Add('В корень диска D:  (D:\Zapret)')
    else
    begin
      IdxDiskD := LocationPage.Add('В корень диска D:  (диск D: не найден)');
      LocationPage.CheckListBox.ItemEnabled[IdxDiskD] := False;
    end;

    { пункт ProgramData }
    LocationPage.Add('В общую папку ProgramData  (C:\ProgramData\Zapret)');
    LocationPage.SelectedValueIndex := 1;    { ProgramData по умолчанию }
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  { проверяем только если страница существует }
  if (LocationPage <> nil)
     and (CurPageID = LocationPage.ID)
     and (LocationPage.SelectedValueIndex = IdxDiskD)
     and (not DriveExists('D')) then
  begin
    MsgBox('Диск D: не найден. Выберите другой вариант установки.',
           mbError, MB_OK);
    Result := False;
  end;
end;