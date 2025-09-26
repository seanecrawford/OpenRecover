; -------- Inno Setup script for SprigOpenRecover --------
; Pass from CI:
;   iscc installer\OpenRecoverProQt.iss /DReleaseDist="<abs-path-to-dist>" /DAppVer="1234"

#ifndef ReleaseDist
  #error "ReleaseDist not set. Pass /DReleaseDist=""<abs path to dist>"""
#endif

#ifndef AppVer
  #define AppVer "0.7"
#endif

#define AppName      "SprigOpenRecover"
#define AppPublisher "Sprig Labs"

[Setup]
AppId={{E6B7A97E-3F08-4C33-9E3E-4C8C1D0B9F8D}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher={#AppPublisher}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=installer\Output
OutputBaseFilename={#AppName}_Setup_{#AppVer}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern

[Files]
Source: "{#ReleaseDist}\SprigOpenRecover.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";               Filename: "{app}\SprigOpenRecover.exe"
Name: "{commondesktop}\{#AppName}";       Filename: "{app}\SprigOpenRecover.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\SprigOpenRecover.exe"; Flags: nowait postinstall skipifsilent
