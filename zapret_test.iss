;---------------------------------------------------
;  Zapret installer / updater (ProgramData by default)
;---------------------------------------------------

; Определяем дефолтные значения
#ifndef CHANNEL
  #define CHANNEL "stable"
#endif

#ifndef VERSION
  #define VERSION "16.1.0.0"
#endif

; ✅ АБСОЛЮТНЫЕ ПУТИ
#define SourcePath "H:\Privacy\zapret"
#define ProjectPath "H:\Privacy\zapretgui"

; Настройки в зависимости от канала
#if CHANNEL == "test"
  #define AppName "Zapret Dev"
  #define AppId "{{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0-TEST}}"
  #define OutputName "ZapretSetup_TEST"
  #define GroupName "Zapret Dev"
  #define DataFolder "ZapretDev"
  #define IconFile "ZapretDevLogo4.ico"
#else
  #define AppName "Zapret"
  #define AppId "{{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0}}"
  #define OutputName "ZapretSetup"
  #define GroupName "Zapret"
  #define DataFolder "Zapret"
  #define IconFile "Zapret2.ico"
#endif

[Setup]
AppName={#AppName}
AppVersion={#VERSION}
AppId={#AppId}
DefaultDirName={code:GetInstallDir}
DisableDirPage=no
UsePreviousAppDir=yes
PrivilegesRequired=admin
DefaultGroupName={#GroupName}
AllowNoIcons=yes
; ✅ Выходной файл в папке проекта
OutputDir={#ProjectPath}
OutputBaseFilename=ZapretSetup_test_1763738963_tmp
Compression=lzma2
SolidCompression=yes
; ✅ ИСПРАВЛЕНО: Проверяем разные пути к иконке
#ifexist SourcePath + "\ico\" + IconFile
  ; Иконка в папке сборки
  SetupIconFile={#SourcePath}\ico\{#IconFile}
#elif FileExists(ProjectPath + "\ico\" + IconFile)
  ; Иконка в папке проекта
  SetupIconFile={#ProjectPath}\ico\{#IconFile}
#elif FileExists(ProjectPath + "\" + IconFile)
  ; Иконка в корне проекта
  SetupIconFile={#ProjectPath}\{#IconFile}
#else
  ; Используем стандартную иконку Inno Setup если наша не найдена
  ; Закомментируйте эту строку, чтобы увидеть ошибку если иконка не найдена
  ; SetupIconFile=
#endif
UninstallDisplayIcon={app}\Zapret.exe
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
; ✅ ИСПОЛЬЗУЕМ АБСОЛЮТНЫЕ ПУТИ
Source: "{#SourcePath}\Zapret.exe"; DestDir: "{app}"; Flags: ignoreversion;

; Копируем папки
Source: "{#SourcePath}\bat\*"; DestDir: "{app}\bat"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\bin\*"; DestDir: "{app}\bin"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\exe\*"; DestDir: "{app}\exe"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\json\*"; DestDir: "{app}\json"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\ico\*"; DestDir: "{app}\ico"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\lists\*"; DestDir: "{app}\lists"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\sos\*"; DestDir: "{app}\sos"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\help\*"; DestDir: "{app}\help"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SourcePath}\windivert.filter\*"; DestDir: "{app}\windivert.filter"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Zapret.exe"; WorkingDir: "{app}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\Zapret.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\Zapret.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Создать ярлык на рабочем столе";

[InstallDelete]
Type: filesandordirs; Name: "{commonappdata}\{#DataFolder}"
; ✅ ИСПРАВЛЕНИЕ: Удаляем старые ярлыки перед созданием новых
Type: files; Name: "{commondesktop}\Zapret.lnk"
Type: files; Name: "{commondesktop}\Zapret Dev.lnk"

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\{#DataFolder}"

[Run]
Filename: "{app}\Zapret.exe"; Description: "Запустить {#AppName}"; \
    Flags: nowait postinstall skipifsilent shellexec; \
    Check: not IsAutoUpdate

[Code]
var
  IsUpdateMode: Boolean;
  AppToLaunch: string;

{ ✅ Функция проверки режима обновления }
function IsAutoUpdate: Boolean;
var
  I: Integer;
begin
  Result := False;
  
  // ✅ БЕЗ использования {app} или других констант!
  for I := 1 to ParamCount do
  begin
    if (CompareText(ParamStr(I), '/SILENT') = 0) or 
       (CompareText(ParamStr(I), '/VERYSILENT') = 0) or
       (CompareText(ParamStr(I), '/NORESTART') = 0) then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

{ ✅ Функция для завершения процессов }
function KillProcessWithRetry(const ExeName: string): Boolean;
var 
  R: Integer;
  Attempts: Integer;
begin
  Result := True;
  
  // Корректное закрытие
  Exec('powershell.exe', 
       '-Command "Get-Process | Where-Object {$_.ProcessName -eq ''' + 
       Copy(ExeName, 1, Length(ExeName) - 4) + 
       '''} | ForEach-Object { $_.CloseMainWindow() | Out-Null }"',
       '', SW_HIDE, ewWaitUntilTerminated, R);
  
  Sleep(100);
  
  // Форсированное завершение
  for Attempts := 1 to 3 do
  begin
    Exec('taskkill.exe', '/IM ' + ExeName + ' /F /T', '',
         SW_HIDE, ewWaitUntilTerminated, R);
    
    if R = 0 then
    begin
      Sleep(100);
      Break;
    end;
    
    if Attempts < 3 then
      Sleep(100);
  end;
end;

procedure StopAndDeleteService(const ServiceName: string);
var R: Integer;
begin
  Exec('sc.exe', 'stop "' + ServiceName + '"', '',
       SW_HIDE, ewWaitUntilTerminated, R);
  Sleep(100);
  Exec('sc.exe', 'delete "' + ServiceName + '"', '',
       SW_HIDE, ewWaitUntilTerminated, R);
end;

{ ✅ ИСПРАВЛЕНО: InitializeSetup БЕЗ прогресс-бара }
function InitializeSetup: Boolean;
begin
  Result := True;
  
  // ✅ СРАЗУ ЗАКРЫВАЕМ ZAPRET.EXE БЕЗ GUI (WizardForm еще не создана)
  KillProcessWithRetry('Zapret.exe');
  KillProcessWithRetry('winws.exe');
  
  // Определяем режим обновления
  IsUpdateMode := IsAutoUpdate;
  AppToLaunch := '';
end;

{ ✅ PrepareToInstall с прогресс-баром (WizardForm уже существует) }
function PrepareToInstall(var NeedsRestart: Boolean): string;
var
  ProgressPage: TOutputProgressWizardPage;
  StepCount: Integer;
  CurrentStep: Integer;
  IsSilent: Boolean;
begin
  Result := '';
  
  // ✅ ВАЖНО: Проверяем Silent режим
  IsSilent := IsAutoUpdate() or WizardSilent();
  
  // В Silent режиме просто выполняем действия без GUI
  if IsSilent then
  begin
    KillProcessWithRetry('Zapret.exe');
    KillProcessWithRetry('winws.exe');
    StopAndDeleteService('WinDivert');
    StopAndDeleteService('WinDivert14');
    StopAndDeleteService('WinDivert1.4');
    StopAndDeleteService('WinDivert64');
    StopAndDeleteService('Monkey');
    Sleep(500);
    Exit;
  end;
  
  // Только для GUI режима показываем прогресс
  ProgressPage := CreateOutputProgressPage('Подготовка к установке',
    'Остановка служб и финальная подготовка...');
  
  try
    ProgressPage.Show;
    
    StepCount := 8;
    CurrentStep := 0;
    
    CurrentStep := CurrentStep + 1;
    ProgressPage.SetText('Проверка процесса Zapret.exe...', '');
    ProgressPage.SetProgress(CurrentStep, StepCount);
    KillProcessWithRetry('Zapret.exe');
    
    CurrentStep := CurrentStep + 1;
    ProgressPage.SetText('Проверка процесса winws.exe...', '');
    ProgressPage.SetProgress(CurrentStep, StepCount);
    KillProcessWithRetry('winws.exe');
    
    CurrentStep := CurrentStep + 1;
    ProgressPage.SetText('Остановка службы Monkey...', '');
    ProgressPage.SetProgress(CurrentStep, StepCount);
    StopAndDeleteService('Monkey');
    
    CurrentStep := CurrentStep + 1;
    ProgressPage.SetText('Очистка временных файлов...', '');
    ProgressPage.SetProgress(CurrentStep, StepCount);
    Sleep(500);
    
    CurrentStep := CurrentStep + 1;
    ProgressPage.SetText('Подготовка завершена', '');
    ProgressPage.SetProgress(CurrentStep, StepCount);
    Sleep(500);
    
  finally
    ProgressPage.Hide;
  end;
end;

function GetInstallDir(Param: string): string;
begin
  Result := ExpandConstant('{commonappdata}\{#DataFolder}');
end;

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

procedure CurUninstallStepChanged(CurStep: TUninstallStep);
begin
  if CurStep = usUninstall then
  begin
    // ✅ Проверяем Silent режим при удалении
    if UninstallSilent() then
    begin
      // В Silent режиме без GUI
      StopAndDeleteService('WinDivert');
      StopAndDeleteService('WinDivert64');
      StopAndDeleteService('Monkey');
      KillProcessWithRetry('winws.exe');
      KillProcessWithRetry('Zapret.exe');
      Sleep(500);
      Exit;
    end;
    
    // ✅ GUI режим - используем стандартную форму деинсталлятора
    UninstallProgressForm.StatusLabel.Caption := 'Остановка служб...';
    UninstallProgressForm.ProgressBar.Position := 20;
    
    StopAndDeleteService('WinDivert');
    StopAndDeleteService('WinDivert64');
    StopAndDeleteService('Monkey');
    
    UninstallProgressForm.StatusLabel.Caption := 'Завершение процессов...';
    UninstallProgressForm.ProgressBar.Position := 60;
    
    KillProcessWithRetry('winws.exe');
    
    UninstallProgressForm.ProgressBar.Position := 80;
    
    KillProcessWithRetry('Zapret.exe');
    
    UninstallProgressForm.StatusLabel.Caption := 'Завершение удаления...';
    UninstallProgressForm.ProgressBar.Position := 100;
    
    Sleep(500);
  end;
end;

procedure DeinitializeSetup;
var
  ResultCode: Integer;
  LaunchPath: string;
begin
  // ✅ Используем {app} только здесь - она уже инициализирована
  if IsAutoUpdate() or WizardSilent() then
  begin
    LaunchPath := ExpandConstant('{app}\Zapret.exe');
    
    if FileExists(LaunchPath) then
    begin
      Exec('cmd.exe', 
           '/c "timeout /t 2 >nul && start """" ""' + LaunchPath + '"""',
           '', SW_HIDE, ewNoWait, ResultCode);
    end;
  end;
end;

// ✅ Убедитесь, что AppToLaunch устанавливается правильно
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) then
  begin
    // Убираем проверку IsUpdateMode - устанавливаем всегда
    AppToLaunch := ExpandConstant('{app}\Zapret.exe');
  end;
end;