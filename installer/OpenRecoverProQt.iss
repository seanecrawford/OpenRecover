#define MyAppName "Sprig OpenRecover"
#define MyAppVersion "0.7.0"

[Setup]
AppId={{F1DE5ABA-1BC3-4D3A-B1B4-8F0E3A5E1B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer\Output
OutputBaseFilename={#MyAppName}_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\SprigOpenRecover.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\SprigOpenRecover.exe"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\SprigOpenRecover.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\SprigOpenRecover.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
