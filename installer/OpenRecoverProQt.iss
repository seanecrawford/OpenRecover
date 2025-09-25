#define AppName      "Sprig OpenRecover"
#ifndef AppVersion
  #define AppVersion "0.7-ci"
#endif

#ifndef ReleaseDist
  #error "Pass /DReleaseDist=""<dist path>"" (points to folder containing SprigOpenRecover.exe)."
#endif

[Setup]
AppId={{F1DE5A8A-1BC3-4D5A-B1B4-8F0E3A8E1B7C}
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
; This is the EXE we copied there in the workflow
Source: "{#ReleaseDist}\SprigOpenRecover.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\SprigOpenRecover.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\SprigOpenRecover.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create &desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\SprigOpenRecover.exe"; Flags: nowait postinstall skipifsilent
