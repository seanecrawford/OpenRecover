; ===== OpenRecover / SprigOpenRecover Installer =====

#define AppName    GetString(DocString("AppName"),    "SprigOpenRecover")
#define AppVersion GetString(DocString("AppVersion"), "0.0.0")
#define ReleaseDist GetString(DocString("ReleaseDist"), "..\\dist")

[Setup]
AppId={{EFA72C94-76D9-4B3A-8E3C-64AA44C0F889}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=OpenRecover Project
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer\output
OutputBaseFilename={#AppName}_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern

[Files]
Source: "{#ReleaseDist}\{#AppName}.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppName}.exe"
Name: "{commondesktop}\{#AppName}";  Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\{#AppName}.exe"; Flags: nowait postinstall skipifsilent
