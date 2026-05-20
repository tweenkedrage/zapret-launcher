[Setup]
AppId={{8A5F5B5E-8B5E-4B5E-8B5E-8B5E8B5E8B5E}}
AppName=Zapret Launcher
AppVersion=3.2.1.8
AppVerName=Zapret Launcher 3.2.1.8
AppPublisher=trimansberg
AppPublisherURL=https://github.com/tweenkedrage/zapret-launcher
AppSupportURL=https://github.com/tweenkedrage/zapret-launcher
AppUpdatesURL=https://github.com/tweenkedrage/zapret-launcher/releases

DefaultDirName={userappdata}\Zapret Launcher
DisableDirPage=yes
DisableProgramGroupPage=yes
AllowRootDirectory=no
AllowNetworkDrive=no

SetupIconFile=resources\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

OutputDir=dist
OutputBaseFilename=zapret-launcher-installer

ShowLanguageDialog=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "dist\updater\*"; DestDir: "{userappdata}\Zapret Launcher"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "resources\icon.ico"; DestDir: "{userappdata}\Zapret Launcher\resources"; Flags: ignoreversion
Source: "resources\icon.png"; DestDir: "{userappdata}\Zapret Launcher\resources"; Flags: ignoreversion
Source: "zapret_core\*"; DestDir: "{userappdata}\Zapret Launcher\zapret_core"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userstartmenu}\Zapret Launcher"; Filename: "{userappdata}\Zapret Launcher\updater.exe"; IconFilename: "{userappdata}\Zapret Launcher\resources\icon.ico"
Name: "{userdesktop}\Zapret Launcher"; Filename: "{userappdata}\Zapret Launcher\updater.exe"; IconFilename: "{userappdata}\Zapret Launcher\resources\icon.ico"

[Code]
procedure CurPageChanged(CurPageID: Integer);
var
  AppDataPath: string;
begin
  if CurPageID = wpSelectDir then
  begin
    AppDataPath := ExpandConstant('{userappdata}') + '\Zapret Launcher';
    WizardForm.DirEdit.Text := AppDataPath;
    WizardForm.DirEdit.Enabled := False;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\Zapret Launcher"
Type: filesandordirs; Name: "{userstartmenu}\Zapret Launcher.lnk"
Type: filesandordirs; Name: "{userdesktop}\Zapret Launcher.lnk"