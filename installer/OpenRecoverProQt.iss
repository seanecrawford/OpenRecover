; CI-ready Inno script

#ifndef ReleaseDist
  #define ReleaseDist GetEnv("ReleaseDist")
#endif
#if ReleaseDist == ""
  #error "Pass /DReleaseDist=<dist path>."
#endif

#ifndef AppVersion
  #define AppVersion "0.0.0-ci"
#endif

#define AppName      "OpenRecover Pro Qt"
#define AppPublisher "OpenRecover Project"

[Setup]
AppId={{FD1E5A8A-18C3-4D5A-B1B4-8F0E3A5E1B7C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=OpenRecoverProQt_Setup
OutputDir={#ReleaseDist}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
Source: "{#ReleaseDist}\OpenRecoverProQt.exe";       DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDist}\OpenRecoverProQt_Admin.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\OpenRecover Pro Qt";         Filename: "{app}\OpenRecoverProQt.exe"
Name: "{group}\OpenRecover Pro Qt (Admin)"; Filename: "{app}\OpenRecoverProQt_Admin.exe"
Name: "{commondesktop}\OpenRecover Pro Qt"; Filename: "{app}\OpenRecoverProQt.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\OpenRecoverProQt.exe"; Flags: nowait postinstall skipifsilent
