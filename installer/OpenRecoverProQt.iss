; OpenRecoverProQt.iss — minimal installer for CI

#define ReleaseDist GetEnv("ReleaseDist")
#ifndef ReleaseDist
  #error "Pass /DReleaseDist=... when compiling."
#endif

#define MyAppName     "OpenRecover Pro Qt"
#define MyAppVersion  GetEnv("AppVersion")
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-ci"
#endif
#define MyAppPublisher "OpenRecover Project"

[Setup]
AppId={{FD1E5A8A-18C3-4D5A-B1B4-8F0E3A5E1B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=OpenRecoverProQt_Setup
OutputDir={#ReleaseDist}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
; The workflow puts the EXEs in %DIST%
Source: "{#ReleaseDist}\OpenRecoverProQt.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDist}\OpenRecoverProQt_Admin.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\OpenRecover Pro Qt";              Filename: "{app}\OpenRecoverProQt.exe"
Name: "{group}\OpenRecover Pro Qt (Admin)";      Filename: "{app}\OpenRecoverProQt_Admin.exe"
Name: "{commondesktop}\OpenRecover Pro Qt";      Filename: "{app}\OpenRecoverProQt.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\OpenRecoverProQt.exe"; Flags: nowait postinstall skipifsilent
