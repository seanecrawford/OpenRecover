
# Build OpenRecover Pro Qt v0.7
param([string]$ReleaseRoot = "C:\Dev\Programs\OpenRecoverProQt_release")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $here "..\src"
$py = Join-Path $ReleaseRoot "venv\Scripts\python.exe"
if (!(Test-Path $py)) { python -m venv (Join-Path $ReleaseRoot "venv"); $py = Join-Path $ReleaseRoot "venv\Scripts\python.exe"; & $py -m pip install --upgrade pip pyinstaller PySide6 }
Remove-Item "$ReleaseRoot\build","$ReleaseRoot\dist","$ReleaseRoot\*.spec" -Recurse -Force -ErrorAction SilentlyContinue
& $py -m PyInstaller --clean -F -w -n OpenRecoverProQt        --distpath "$ReleaseRoot\dist" --workpath "$ReleaseRoot\build" --specpath "$ReleaseRoot" (Join-Path $src "main.py")
& $py -m PyInstaller --clean -F -w --uac-admin -n OpenRecoverProQt_Admin --distpath "$ReleaseRoot\dist" --workpath "$ReleaseRoot\build" --specpath "$ReleaseRoot" (Join-Path $src "main.py")
Get-ChildItem "$ReleaseRoot\dist\OpenRecoverProQt*.exe" | Select Name, LastWriteTime, Length
