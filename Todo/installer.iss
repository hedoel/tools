; Inno Setup 6 脚本 - 不加了 64位 Windows 安装程序
#define MyAppName "不加了"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "不加了"
#define MyAppExeName "NoOvertime.exe"

[Setup]
; 应用程序基础标识
AppId={{D37E88A1-477C-4C2E-BF59-6C8E649F98AA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\NoOvertime
DefaultGroupName={#MyAppName}

; 输出目录与输出文件名
OutputDir=dist\x64
OutputBaseFilename=NoOvertime_Setup_x64

; 图标与视觉
SetupIconFile=img\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern

; 64 位架构支持
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; 权限设置：支持免管理员安装到当前用户空间，也支持管理员全系统安装
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; 压缩算法 (LZMA2 Ultra)
Compression=lzma2/ultra64
SolidCompression=yes

; 卸载与静默设置
CloseApplications=yes
RestartApplications=no
DisableWelcomePage=no
DisableProgramGroupPage=yes
DisableDirPage=no
AlwaysShowDirOnReadyPage=yes

; 进程互斥体原生检测
AppMutex=NoOvertime_Application_Mutex

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "cleanconfig"; Description: "全新安装"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; 用户配置统一存放于 %APPDATA%\NoOvertime\config.json，不再随安装包分发，
; 因此升级安装不会覆盖用户设置，卸载也不会残留在安装目录
Source: "dist\NoOvertime\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\卸载{#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时彻底删除安装目录中的所有动态生成文件与子文件夹
Type: filesandordirs; Name: "{app}"
; 卸载时彻底清除本地个人配置（工号、密码等隐私数据），确保不留痕迹
Type: filesandordirs; Name: "{userappdata}\NoOvertime"
Type: filesandordirs; Name: "{userappdata}\不加了"

[Registry]
; 卸载时自动清理开机自启注册表项，防止残留
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "NoOvertime"; Flags: dontcreatekey uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "不加了"; Flags: dontcreatekey uninsdeletevalue

[Code]
// 检测程序是否正在运行：优先检测 Win32 Mutex，兜底检测 powershell 进程列表
function IsAppProcessRunning(): Boolean;
var
  ResultCode: Integer;
begin
  if CheckForMutexes('NoOvertime_Application_Mutex') then
  begin
    Result := True;
    Exit;
  end;
  // 兜底检查：通过 powershell 查询进程是否存在
  if Exec('powershell.exe', '-NoProfile -Command "if (Get-Process NoOvertime -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := (ResultCode = 1);
  end
  else
  begin
    Result := False;
  end;
end;

// 卸载初始化：先检查程序是否在运行，必须关闭运行中的程序方可卸载
function InitializeUninstall(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;

  while IsAppProcessRunning() do
  begin
    if MsgBox('检测到「{#MyAppName}」正在运行！' + #13#10 + #13#10 +
              '必须先关闭运行中的程序方可继续卸载。' + #13#10 + #13#10 +
              '是否由卸载程序自动关闭程序并继续？' + #13#10 +
              '（点击【是】自动退出程序并继续卸载；点击【否】退出卸载向导）',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 强制终止程序进程
      Exec('taskkill.exe', '/F /T /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
      Sleep(800);
      if not IsAppProcessRunning() then
      begin
        Result := True;
        Exit;
      end;
    end
    else
    begin
      // 用户选择取消卸载
      Result := False;
      Exit;
    end;
  end;
end;

// 安装初始化：若有老版本正在运行，提示并关闭后再安装
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;

  while IsAppProcessRunning() do
  begin
    if MsgBox('检测到「{#MyAppName}」正在运行！' + #13#10 + #13#10 +
              '必须先关闭运行中的程序方可进行安装或更新。' + #13#10 + #13#10 +
              '是否由安装程序自动关闭程序并继续？' + #13#10 +
              '（点击【是】自动退出程序并继续安装；点击【否】退出安装向导）',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('taskkill.exe', '/F /T /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
      Sleep(800);
      if not IsAppProcessRunning() then
      begin
        Result := True;
        Exit;
      end;
    end
    else
    begin
      Result := False;
      Exit;
    end;
  end;
end;

// 安装完成时，若用户勾选了全新安装，则清空历史残留的账号密码配置
procedure CurStepChanged(CurStep: TSetupStep);
var
  UserDataDir: String;
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('cleanconfig') then
  begin
    UserDataDir := ExpandConstant('{userappdata}\NoOvertime');
    if (UserDataDir <> '') and DirExists(UserDataDir) then
    begin
      DelTree(UserDataDir, True, True, True);
    end;
    UserDataDir := ExpandConstant('{userappdata}\不加了');
    if (UserDataDir <> '') and DirExists(UserDataDir) then
    begin
      DelTree(UserDataDir, True, True, True);
    end;
  end;
end;

// 卸载完成后安全清空并删除整个安装目录以及用户个人数据目录（包括运行期动态生成的日志、缓存、本地存储的账号密码）
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: String;
  UserDataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    // 确保目录有效且不是盘符根目录（如 C:\），安全递归删除整个安装目录
    if (AppDir <> '') and (Length(AppDir) > 3) and DirExists(AppDir) then
    begin
      DelTree(AppDir, True, True, True);
    end;

    // 彻底清除用户 AppData 目录下的隐私配置文件（工号、密码密文、个性化设置）
    UserDataDir := ExpandConstant('{userappdata}\NoOvertime');
    if (UserDataDir <> '') and DirExists(UserDataDir) then
    begin
      DelTree(UserDataDir, True, True, True);
    end;
    UserDataDir := ExpandConstant('{userappdata}\不加了');
    if (UserDataDir <> '') and DirExists(UserDataDir) then
    begin
      DelTree(UserDataDir, True, True, True);
    end;
  end;
end;
