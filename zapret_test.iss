;---------------------------------------------------
;  Zapret installer / updater (ProgramData by default)
;---------------------------------------------------

; Определяем дефолтные значения
#ifndef IS_TEST
  #define IS_TEST 0
#endif

#ifndef VERSION
  #define VERSION "16.1.0.0"
#endif

; ✅ АБСОЛЮТНЫЕ ПУТИ
#define SourcePath "H:\Privacy\zapret"
#define ProjectPath "H:\Privacy\zapretgui"

; ✅ Настройки в зависимости от канала (числовой флаг надёжнее строк!)
#if IS_TEST
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
OutputDir={#ProjectPath}
OutputBaseFilename=Zapret2Setup_test_1765300851_tmp
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
; ✅ Копируем lists, но исключаем пользовательские файлы (other2.txt, my-ipset.txt, netrogat.txt)
Source: "{#SourcePath}\lists\*"; DestDir: "{app}\lists"; Excludes: "other2.txt;my-ipset.txt;netrogat.txt"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
; ✅ other2.txt копируется ТОЛЬКО если его нет (сохраняем пользовательские домены при обновлении)
Source: "{#SourcePath}\lists\other2.txt"; DestDir: "{app}\lists"; Flags: onlyifdoesntexist skipifsourcedoesntexist
; ✅ my-ipset.txt копируется ТОЛЬКО если его нет (сохраняем пользовательские IP при обновлении)
Source: "{#SourcePath}\lists\my-ipset.txt"; DestDir: "{app}\lists"; Flags: onlyifdoesntexist skipifsourcedoesntexist
; ✅ netrogat.txt копируется ТОЛЬКО если его нет (сохраняем пользовательские исключения)
Source: "{#SourcePath}\lists\netrogat.txt"; DestDir: "{app}\lists"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SourcePath}\lua\*"; DestDir: "{app}\lua"; Flags: recursesubdirs ignoreversion createallsubdirs skipifsourcedoesntexist
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
; Удаляем СТАРЫЕ папки (миграция на новые имена)
Type: filesandordirs; Name: "{commonappdata}\Zapret2Dev"
Type: filesandordirs; Name: "{commonappdata}\Zapret2"
Type: filesandordirs; Name: "{commonappdata}\ZapretDev"
Type: filesandordirs; Name: "{commonappdata}\Zapret"
; Удаляем только ярлык ТЕКУЩЕЙ версии перед созданием нового
Type: files; Name: "{commondesktop}\{#AppName}.lnk"

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
begin
  // Всегда используем новый путь
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

// ✅ Убедитесь, что AppToLaunch устанавливается правильно
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) then
  begin
    // Убираем проверку IsUpdateMode - устанавливаем всегда
    AppToLaunch := ExpandConstant('{app}\Zapret.exe');
  end;
end;