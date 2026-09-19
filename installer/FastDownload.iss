; FastDownload - installer Inno Setup
; Compila con:  iscc FastDownload.iss
; (o dal menu di FastDownload.bat)

#define AppName "FastDownload"
#define AppVersion "1.0.0"
#define AppPublisher "FastDownload"
#define AppURL "https://github.com/"

[Setup]
AppId={{D2E5B7A4-7E4C-4F0B-9C6A-1F3D5A8B2C74}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
LicenseFile=
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
OutputDir=output
OutputBaseFilename=FastDownload-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
DisableDirPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "browsertab"; Description: "Add the FastDownload tab to the FL Studio browser (FL must be closed)"; GroupDescription: "FL Studio integration:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
; motore Python (server + UI)
Source: "..\engine\api.py";           DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\main.py";          DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\server.py";        DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\flproject.py";     DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\audio_meta.py";    DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\browser_tab.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\monochrome.py";    DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\plugin_icon.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine\assets\plugin-icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\engine\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
; la UI non usa ui\assets (logo/sorgenti): esclusi dal pacchetto
Source: "..\engine\ui\*";             DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs; \
    Excludes: "assets\*,assets"
; plugin VST3
Source: "..\plugin\dist\FastDownload.vst3\*"; DestDir: "{commoncf}\VST3\FastDownload.vst3"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
; solo HKLM: l'install e' admin e HKCU finirebbe nell'hive dell'amministratore,
; non in quello di chi avvia il setup. In HKCU resta possibile un override manuale.
Root: HKLM; Subkey: "Software\FastDownload"; ValueType: string; ValueName: "EnginePath"; \
    ValueData: "{app}"; Flags: uninsdeletekey

[Icons]
Name: "{group}\FastDownload";          Filename: "pythonw.exe"; Parameters: """{app}\main.py"""
Name: "{group}\FastDownload server";   Filename: "pythonw.exe"; Parameters: """{app}\server.py"" --port 8731"
Name: "{group}\Uninstall FastDownload"; Filename: "{uninstallexe}"
Name: "{autodesktop}\FastDownload";    Filename: "pythonw.exe"; Parameters: """{app}\main.py"""; Tasks: desktopicon

[Run]
; dipendenze Python (best effort: se manca rete/Python l'app lo segnala al primo avvio)
Filename: "python.exe"; Parameters: "-m pip install --quiet --disable-pip-version-check -r ""{app}\requirements.txt"""; \
    StatusMsg: "Installing Python dependencies..."; Flags: runhidden waituntilterminated; Check: PythonAvailable
; tab del browser FL (richiede FL chiuso) — come utente originale, non come admin:
; cosi' tab e junction finiscono nel profilo di chi ha avviato il setup
Filename: "python.exe"; Parameters: """{app}\browser_tab.py"""; \
    StatusMsg: "Configuring the FL Studio browser tab..."; \
    Flags: runhidden waituntilterminated runasoriginaluser; \
    Tasks: browsertab; Check: PythonAvailable
; icona del plugin nel Plugin database di FL — come utente originale
Filename: "python.exe"; Parameters: """{app}\plugin_icon.py"""; \
    StatusMsg: "Installing the plugin icon..."; \
    Flags: runhidden waituntilterminated runasoriginaluser; Check: PythonAvailable
; avvio app
Filename: "pythonw.exe"; Parameters: """{app}\main.py"""; Description: "Launch FastDownload"; \
    Flags: nowait postinstall skipifsilent; Check: PythonAvailable

[UninstallRun]
Filename: "python.exe"; Parameters: """{app}\browser_tab.py"" --uninstall"; \
    Flags: runhidden; RunOnceId: "RemoveBrowserTab"; Check: PythonAvailable

[Code]
function PythonAvailable(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c python --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
            and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not PythonAvailable() then
    if MsgBox('Python 3 was not found on this system.' + #13#10 +
              'FastDownload needs Python 3.10+ (with pip) to run.' + #13#10#13#10 +
              'Install it from python.org (check "Add python.exe to PATH"), then run this setup again.' + #13#10#13#10 +
              'Continue anyway?',
              mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
end;
