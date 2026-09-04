#define MyAppName "Antigravity 智能启动器"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "zwmopen"
#define MyAppURL "https://github.com/zwmopen/Antigravity-Windows-Recovery-Launcher"
#define MyAppExeName "Antigravity-Recovery-Launcher.exe"

[Setup]
AppId={{28BDF688-75ED-4FA8-BB41-AC4B2E35C328}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Antigravity\launcher
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UsePreviousAppDir=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\releases\public
OutputBaseFilename=Antigravity-Windows-Recovery-Setup-{#MyAppVersion}-windows-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\src\Antigravity-Launcher.ico
SetupLogging=yes
CloseApplications=no
RestartApplications=no
LicenseFile=..\LICENSE
InfoBeforeFile=..\docs\INSTALLER-README.txt
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion=1.0.0.0

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "..\releases\current\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\install.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\uninstall.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 Antigravity 智能启动器"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
Filename: "{app}"; Description: "打开安装目录"; Flags: shellexec postinstall skipifsilent unchecked

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall.ps1"" -InstallRoot ""{app}"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveLauncherIntegration"

[UninstallDelete]
Type: files; Name: "{app}\tools\agy\agy.exe"
Type: files; Name: "{app}\tools\agy\agy.download"
Type: dirifempty; Name: "{app}\tools\agy"
Type: dirifempty; Name: "{app}\tools"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := '正在下载并校验 Google 官方组件，首次安装可能需要几分钟...';
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\install.ps1') +
      '" -InstallRoot "' + ExpandConstant('{app}') + '" -SourceApp "' + ExpandConstant('{app}') + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('无法启动安装配置程序。');
    if ResultCode <> 0 then
      RaiseException(Format('安装配置失败，退出代码：%d。', [ResultCode]));
  end;
end;
