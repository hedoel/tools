; Inno Setup 6 脚本 - NoOvertime 64位 Windows 安装程序
#define MyAppName "NoOvertime"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "NoOvertime"
#define MyAppExeName "NoOvertime.exe"

[Setup]
; 应用程序基础标识
AppId={{D37E88A1-477C-4C2E-BF59-6C8E649F98AA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
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

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

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
