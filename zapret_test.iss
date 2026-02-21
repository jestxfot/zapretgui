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

; Пути можно переопределять из CI: ISCC.exe /DSOURCEPATH=... /DPROJECTPATH=...
; SOURCEPATH должен указывать на папку, где лежит Zapret.exe и ресурсы Zapret:
;   Zapret.exe
;   _internal\
;   bin\ exe\ json\ lists\ lua\ presets\ ...
#ifndef SOURCEPATH
  #define SOURCEPATH "\\wsl.localhost\Debian\opt\zapret"
#endif
#ifndef PROJECTPATH
  #define PROJECTPATH "\\wsl.localhost\Debian\opt\zapretgui"
#endif

; ✅ Настройки в зависимости от канала
#if CHANNEL == "test"
  #define AppName "Zapret 2 Dev"
  #define AppId "{{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F1-TEST}}"
  #define OutputName "Zapret2Setup_TEST"
  #define GroupName "Zapret 2 Dev"
  #define DataFolder "ZapretTwoDev"
  #define IconFile "ZapretDevLogo4.ico"
#else
  #define AppName "Zapret 2"
  #define AppId "{{5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F1}}"
  #define OutputName "Zapret2Setup"
  #define GroupName "Zapret 2"
  #define DataFolder "ZapretTwo"
  #define IconFile "Zapret2.ico"
#endif

; Имя ярлыков (Start Menu / Desktop) с версией
#define ShortcutName AppName + " v" + VERSION

; Иконка установщика: ожидаем в {#SOURCEPATH}\ico\{#IconFile},
; но делаем fallback, чтобы сборка не падала на чистом окружении.
#define _ICON_FROM_SOURCE AddBackslash(SOURCEPATH) + "ico\\" + IconFile
#define _ICON_FROM_PROJECT AddBackslash(PROJECTPATH) + IconFile
#define _ICON_FALLBACK AddBackslash(PROJECTPATH) + "zapret.ico"
#if FileExists(_ICON_FROM_SOURCE)
  #define SetupIconResolved _ICON_FROM_SOURCE
#elif FileExists(_ICON_FROM_PROJECT)
  #define SetupIconResolved _ICON_FROM_PROJECT
#else
  #define SetupIconResolved _ICON_FALLBACK
#endif

[Setup]
AppName={#AppName}
AppVersion={#VERSION}
AppId={#AppId}
DefaultDirName={code:GetInstallDir}
DisableDirPage=no
UsePreviousAppDir=yes
DirExistsWarning=no
PrivilegesRequired=admin
DefaultGroupName={#GroupName}
AllowNoIcons=yes
; ✅ Выходной файл в папке проекта
OutputDir={#PROJECTPATH}
OutputBaseFilename=Zapret2Setup_test_1770207517_tmp
Compression=lzma2
SolidCompression=yes
; ✅ Иконка установщика (используем абсолютный путь)
SetupIconFile={#SetupIconResolved}
UninstallDisplayIcon={app}\Zapret.exe
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
; ✅ ИСПОЛЬЗУЕМ АБСОЛЮТНЫЕ ПУТИ
; ✅ Zapret.exe + _internal (onedir)
Source: "{#SOURCEPATH}\Zapret.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SOURCEPATH}\_internal\*"; DestDir: "{app}\_internal"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist

; ✅ V2 Preset templates -> %APPDATA%\zapret\presets_v2_template
; Always overwritten on update to keep templates current.
; At startup the app copies new templates to presets_v2/ (unless user deleted them).
Source: "{#PROJECTPATH}\preset_zapret2\builtin_presets\*.txt"; DestDir: "{userappdata}\zapret\presets_v2_template"; Excludes: "_*.txt"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist; BeforeInstall: RemovePresetTemplateIfExists

; V1 Preset templates -> %APPDATA%\zapret\presets_v1_template
Source: "{#PROJECTPATH}\preset_zapret1\builtin_presets\*.txt"; DestDir: "{userappdata}\zapret\presets_v1_template"; Excludes: "_*.txt"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist; BeforeInstall: RemovePresetTemplateIfExists

; ✅ direct_zapret1 strategies -> %APPDATA%\zapret\direct_zapret1
Source: "{#PROJECTPATH}\preset_zapret1\basic_strategies\*.txt"; DestDir: "{userappdata}\zapret\direct_zapret1"; Excludes: "_*.txt"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist

; ✅ direct_zapret2 Basic strategies -> %APPDATA%\zapret\direct_zapret2\basic_strategies
; Always overwritten on update to keep the Basic catalog current.
Source: "{#PROJECTPATH}\preset_zapret2\basic_strategies\*.txt"; DestDir: "{userappdata}\zapret\direct_zapret2\basic_strategies"; Excludes: "_*.txt"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist
Source: "{#PROJECTPATH}\preset_zapret2\basic_strategies\*.json"; DestDir: "{userappdata}\zapret\direct_zapret2\basic_strategies"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist

; ✅ direct_zapret2 Advanced strategies -> %APPDATA%\zapret\direct_zapret2\advanced_strategies
; Always overwritten on update to keep the Advanced catalog current.
Source: "{#PROJECTPATH}\preset_zapret2\advanced_strategies\*.txt"; DestDir: "{userappdata}\zapret\direct_zapret2\advanced_strategies"; Excludes: "_*.txt"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist
Source: "{#PROJECTPATH}\preset_zapret2\advanced_strategies\*.json"; DestDir: "{userappdata}\zapret\direct_zapret2\advanced_strategies"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist

; ✅ Hostlist template other.txt -> %APPDATA%\zapret\lists_template
; Source of truth comes from SOURCEPATH\lists\other.txt
Source: "{#SOURCEPATH}\lists\other.txt"; DestDir: "{userappdata}\zapret\lists_template"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist

; ✅ ZapretHub installer -> %APPDATA%\zaprettracker (always replaced on update)
Source: "{#PROJECTPATH}\tracker\ZapretHub-Setup-1.0.0.exe"; DestDir: "{userappdata}\zaprettracker"; DestName: "ZapretHub-Setup.exe"; Flags: ignoreversion overwritereadonly skipifsourcedoesntexist

; Копируем папки
Source: "{#SOURCEPATH}\bin\*"; DestDir: "{app}\bin"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SOURCEPATH}\exe\*"; DestDir: "{app}\exe"; Excludes: "cygwin1.dll"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
; ✅ cygwin1.dll копируется только при первичной установке (не заменяем, если уже существует)
Source: "{#SOURCEPATH}\exe\cygwin1.dll"; DestDir: "{app}\exe"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SOURCEPATH}\json\*"; DestDir: "{app}\json"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SOURCEPATH}\ico\*"; DestDir: "{app}\ico"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
; ✅ Копируем lists, но исключаем пользовательские файлы (other.txt, my-ipset.txt, netrogat.txt)
Source: "{#SOURCEPATH}\lists\*"; DestDir: "{app}\lists"; Excludes: "other.txt;my-ipset.txt;netrogat.txt"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
; ✅ other.txt создаётся и сбрасывается приложением из %APPDATA%\zapret\lists_template\other.txt
; ✅ my-ipset.txt копируется ТОЛЬКО если его нет (сохраняем пользовательские IP при обновлении)
Source: "{#SOURCEPATH}\lists\my-ipset.txt"; DestDir: "{app}\lists"; Flags: onlyifdoesntexist skipifsourcedoesntexist
; ✅ netrogat.txt копируется ТОЛЬКО если его нет (сохраняем пользовательские исключения)
Source: "{#SOURCEPATH}\lists\netrogat.txt"; DestDir: "{app}\lists"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SOURCEPATH}\lua\*"; DestDir: "{app}\lua"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SOURCEPATH}\sos\*"; DestDir: "{app}\sos"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SOURCEPATH}\help\*"; DestDir: "{app}\help"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
Source: "{#SOURCEPATH}\windivert.filter\*"; DestDir: "{app}\windivert.filter"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
; ✅ Копируем themes (фоновые изображения для тем), исключаем .exe файлы
Source: "{#SOURCEPATH}\themes\*"; DestDir: "{app}\themes"; Excludes: "*.exe"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#ShortcutName}"; Filename: "{app}\Zapret.exe"; WorkingDir: "{app}"
Name: "{group}\Удалить {#ShortcutName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\Zapret.exe"
Name: "{commondesktop}\{#ShortcutName}"; Filename: "{app}\Zapret.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Создать ярлык на рабочем столе";
Name: installzaphub; Description: "Установить ZapretHub (центр сообщества Zapret: стратегии, пресеты и форум)";

[InstallDelete]
; Удаляем СТАРЫЕ папки (миграция на новые имена)
Type: filesandordirs; Name: "{commonappdata}\Zapret2Dev"
Type: filesandordirs; Name: "{commonappdata}\Zapret2"
Type: filesandordirs; Name: "{commonappdata}\ZapretDev"
Type: filesandordirs; Name: "{commonappdata}\Zapret"
; Удаляем legacy-каталог стратегий из _internal (теперь direct_zapret1 только в %APPDATA%\zapret\direct_zapret1)
Type: filesandordirs; Name: "{app}\_internal\preset_zapret1"
; Удаляем старые ярлыки (без версии и с версией), чтобы не копились при обновлениях
Type: files; Name: "{commondesktop}\{#AppName}.lnk"
Type: files; Name: "{commondesktop}\{#AppName} v*.lnk"
Type: files; Name: "{group}\{#AppName}.lnk"
Type: files; Name: "{group}\{#AppName} v*.lnk"
Type: files; Name: "{group}\Удалить {#AppName}.lnk"
Type: files; Name: "{group}\Удалить {#AppName} v*.lnk"
; Удаляем старые версионные имена инсталлятора (если были)
Type: files; Name: "{userappdata}\zaprettracker\ZapretHub-Setup-*.exe"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\{#DataFolder}"
Type: filesandordirs; Name: "{commonappdata}\{#DataFolder}"

[Run]
Filename: "{userappdata}\zaprettracker\ZapretHub-Setup.exe"; \
    Parameters: "/S /SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART"; \
    Flags: runhidden nowait; \
    Tasks: installzaphub; \
    Check: TrackerInstallerExists and (not IsAutoUpdate)
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

function TrackerInstallerExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{userappdata}\zaprettracker\ZapretHub-Setup.exe'));
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
var 
  R: Integer;
  Attempt: Integer;
begin
  // Останавливаем службу
  Exec('sc.exe', 'stop "' + ServiceName + '"', '',
       SW_HIDE, ewWaitUntilTerminated, R);
  Sleep(200);
  
  // Пробуем удалить с повторными попытками (ошибка 1072 - служба помечена для удаления)
  for Attempt := 1 to 5 do
  begin
    Exec('sc.exe', 'delete "' + ServiceName + '"', '',
         SW_HIDE, ewWaitUntilTerminated, R);
    
    // Если успешно удалено или служба не существует - выходим
    if (R = 0) or (R = 1060) then
      Break;
    
    // Если служба помечена для удаления (1072) - ждём и пробуем снова
    if R = 1072 then
    begin
      // Убиваем процессы которые могут держать хэндлы
      Exec('taskkill.exe', '/F /IM winws.exe /T', '', SW_HIDE, ewWaitUntilTerminated, R);
      Exec('taskkill.exe', '/F /IM winws2.exe /T', '', SW_HIDE, ewWaitUntilTerminated, R);
      Sleep(500);
    end
    else
      Break;
  end;
end;

{ ✅ ИСПРАВЛЕНО: InitializeSetup БЕЗ прогресс-бара }
function InitializeSetup: Boolean;
begin
  Result := True;
  
  // ✅ СРАЗУ ЗАКРЫВАЕМ ZAPRET.EXE БЕЗ GUI (WizardForm еще не создана)
  KillProcessWithRetry('Zapret.exe');
  KillProcessWithRetry('winws.exe');
  KillProcessWithRetry('winws2.exe');
  
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
    KillProcessWithRetry('winws2.exe');
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
    KillProcessWithRetry('winws2.exe');
    
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
var
  Candidate: string;
begin
  // По умолчанию ставим в Roaming\AppData.
  // Пробелы в пути запрещаем (часть .bat/команд может ломаться без кавычек),
  // поэтому для профилей с пробелами откатываемся на ProgramData.
  Candidate := ExpandConstant('{userappdata}\{#DataFolder}');
  if Pos(' ', Candidate) = 0 then
    Result := Candidate
  else
    Result := ExpandConstant('{commonappdata}\{#DataFolder}');
end;

function IsAllowedChar(C: Char): Boolean;
begin
  // Разрешаем цифры и любые Unicode-буквы (включая русские),
  // но запрещаем пробелы в пути.
  Result := (C <> ' ');
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
      MsgBox('Путь к папке установки не должен содержать пробелов.' + #13#10 +
             'Цифры и русские буквы разрешены.',
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
      KillProcessWithRetry('winws2.exe');
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
    KillProcessWithRetry('winws2.exe');
    
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

procedure RemovePresetTemplateIfExists();
begin
  if FileExists(CurrentFileName) then
  begin
    if not DeleteFile(CurrentFileName) then
      Log('Presets: failed to delete template before overwrite: ' + CurrentFileName);
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
