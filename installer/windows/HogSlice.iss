; HogSlice Windows Installer Script (Inno Setup)
; Build prerequisites:
; 1) Run installer/windows/build_installer.ps1 to produce dist/HogSlice
; 2) Compile this script with ISCC (Inno Setup Compiler)

#define MyAppName "HogSlice"
#ifndef MyAppVersion
	#define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "Hogforge"
#define MyAppExeName "HogSlice.exe"

[Setup]
AppId={{E2D8E63A-C651-4D6A-920C-B8A2B42BB714}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputBaseFilename=HogSlice-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\..\dist\HogSlice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent runasoriginaluser
