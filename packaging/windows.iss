#ifndef AppVersion
  #define AppVersion "0.1.0-alpha.4"
#endif
[Setup]
AppId={{A437464D-5B56-48A7-BCB4-4946830FD019}
AppName=SignalPier
AppVersion={#AppVersion}
AppPublisher=SignalPier contributors
AppPublisherURL=https://brandenskaggs-rgb.github.io/signalpier/
DefaultDirName={localappdata}\Programs\SignalPier
DefaultGroupName=SignalPier
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=SignalPier-{#AppVersion}-windows-x64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=signalpier.ico
UninstallDisplayIcon={app}\SignalPier.exe
LicenseFile=..\LICENSE
AppMutex=Local\SignalPierDesktop
CloseApplications=yes
RestartApplications=no
[Files]
Source: "..\dist\windows\SignalPier\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\SignalPier"; Filename: "{app}\SignalPier.exe"
Name: "{autodesktop}\SignalPier"; Filename: "{app}\SignalPier.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Run]
Filename: "{app}\SignalPier.exe"; Description: "Open SignalPier"; Flags: nowait postinstall skipifsilent; Check: not IsSignalPierUpdate
Filename: "{app}\SignalPier.exe"; Flags: nowait; Check: IsSignalPierUpdate
[Code]
function IsSignalPierUpdate: Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/SIGNALPIERUPDATE') = 0 then Result := True;
end;
