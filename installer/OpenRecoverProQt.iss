#define AppName      "Sprig OpenRecover"
#ifndef AppVersion
  #define AppVersion "0.7-ci"
#endif

#ifndef ReleaseDist
  #error "Pass /DReleaseDist=""<dist path>"" (folder that contains SprigOpenRecover.exe)."
#endif

[Setup]
AppId={{A9625A0C-3E62-4C2C-B3A9-9FAD5E5193B4}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher="OpenRecover Project"
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=SprigOpenRecover_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Files]
Source: "{#ReleaseDist}\SprigOpenRecover.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\SprigOpenRecover.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\SprigOpenRecover.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create &desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\SprigOpenRecover.exe"; Flags: nowait postinstall skipifsilent
