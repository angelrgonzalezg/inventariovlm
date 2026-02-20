; Inno Setup script for InventarioVLM
; Requires Inno Setup (https://jrsoftware.org/isinfo.php) to compile into an installer .exe
[Setup]
AppName=Inventario VLM
AppVersion=1.0
DefaultDirName={pf}\InventarioVLM
DefaultGroupName=Inventario VLM
DisableDirPage=no
DisableProgramGroupPage=no
OutputBaseFilename=InventarioVLM_Installer
Compression=lzma
SolidCompression=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#Src}\InventarioVLM.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Src}\inventariovlm.db"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Src}\icons\*"; DestDir: "{app}\icons"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Inventario VLM"; Filename: "{app}\InventarioVLM.exe"; IconFilename: "{app}\icons\\cj_electrical_supplies.ico"
Name: "{commondesktop}\Inventario VLM"; Filename: "{app}\InventarioVLM.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\InventarioVLM.exe"; Description: "Lanzar Inventario VLM"; Flags: nowait postinstall skipifsilent

; Note: to compile this script replace {#Src} with the absolute path to the installer folder or
; use Inno Setup preprocessor -DMySourceDir="C:\Path\To\releases\InventarioVLM_installer"
; Example: ISCC.exe /DMySourceDir="C:\...\releases\InventarioVLM_installer" InventarioVLM_installer.iss
