#define ExePath GetDefine("ExePath")

#ifndef ExePath
  #error "Pass /DEXEPath=<full path to SprigOpenRecover.exe> to ISCC."
#endif

#define AppName      "Sprig OpenRecover"
#define AppVersion   "0.7.0"
#define AppPublisher "OpenRecover Project"

[Setup]
AppId={{A9F6E20E-74C0-4BE3-AC28-9D0D8B0AAE10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=SprigOpenRecover_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
; Use the exact EXE path provided by the workflow
Source: "{#ExePath}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";       Filename: "{app}\SprigOpenRecover.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\SprigOpenRecover.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\SprigOpenRecover.exe"; Flags: nowait postinstall skipifsilent
