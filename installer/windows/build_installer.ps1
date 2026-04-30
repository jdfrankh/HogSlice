param(
    [string]$PythonExe = "python",
    [string]$InnoCompilerPath = "",
    [switch]$NoLaunchInstaller
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$VenvDir = Join-Path $RepoRoot ".venv-installer"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
$DistDir = Join-Path $RepoRoot "dist\HogSlice"
$BuildDir = Join-Path $RepoRoot "build"
$InstallerScript = Join-Path $ScriptDir "HogSlice.iss"
$SetupPyPath = Join-Path $RepoRoot "setup.py"

function Get-PythonVersionInfo {
    param([string]$Exe)

    $verText = (& $Exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($verText)) {
        return $null
    }

    $parts = $verText.Trim().Split('.')
    if ($parts.Count -lt 2) {
        return $null
    }

    return [pscustomobject]@{
        Major = [int]$parts[0]
        Minor = [int]$parts[1]
    }
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$FailureMessage
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Resolve-CompatiblePythonExe {
    param([string]$Requested)

    $requestedInfo = Get-PythonVersionInfo -Exe $Requested
    if ($requestedInfo -and $requestedInfo.Major -eq 3 -and $requestedInfo.Minor -le 12) {
        return $Requested
    }

    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        foreach ($minor in @(12, 11, 10)) {
            try {
                $candidate = (& $pyLauncher.Source -3.$minor -c "import sys; print(sys.executable)" 2>$null)
                if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($candidate)) {
                    return $candidate.Trim()
                }
            } catch {
                # Continue trying other versions; do not fail resolver on probe errors.
                continue
            }
        }
    }

    return $Requested
}

function Get-AppVersionFromSetupPy {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "setup.py not found at $Path"
    }

    $content = Get-Content -Path $Path -Raw
    $match = [regex]::Match($content, 'version\s*=\s*[''\"]([^''\"]+)[''\"]')
    if (-not $match.Success) {
        throw "Could not find version='x.y.z' style entry in setup.py"
    }

    return $match.Groups[1].Value
}

function Resolve-InnoCompilerPath {
    param([string]$PreferredPath)

    if (-not [string]::IsNullOrWhiteSpace($PreferredPath) -and (Test-Path $PreferredPath)) {
        return $PreferredPath
    }

    $possible = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 5\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 5\ISCC.exe"
    )
    foreach ($path in $possible) {
        if (-not [string]::IsNullOrWhiteSpace($path) -and (Test-Path $path)) {
            return $path
        }
    }

    $isccCmd = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($isccCmd -and (Test-Path $isccCmd.Source)) {
        return $isccCmd.Source
    }

    $regKeys = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKCU:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1",
        "HKCU:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1"
    )
    foreach ($key in $regKeys) {
        try {
            if (Test-Path $key) {
                $props = Get-ItemProperty -Path $key
                if ($props.InstallLocation) {
                    $candidate = Join-Path $props.InstallLocation "ISCC.exe"
                    if (Test-Path $candidate) {
                        return $candidate
                    }
                }
            }
        } catch {
            # Keep searching other detection paths.
        }
    }

    $globRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)
    foreach ($root in $globRoots) {
        if ([string]::IsNullOrWhiteSpace($root) -or -not (Test-Path $root)) {
            continue
        }

        $patterns = @(
            (Join-Path $root "Inno Setup*\ISCC.exe"),
            (Join-Path $root "JRSoftware\Inno Setup*\ISCC.exe"),
            (Join-Path $root "Programs\Inno Setup*\ISCC.exe")
        )

        foreach ($pattern in $patterns) {
            $hits = @(Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue)
            if ($hits.Count -gt 0 -and (Test-Path $hits[0].FullName)) {
                return $hits[0].FullName
            }
        }
    }

    return ""
}

function Try-InstallInnoSetup {
    $winget = Get-Command "winget" -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Inno Setup not found. Attempting install with winget..."
        try {
            & $winget.Source install --id JRSoftware.InnoSetup --exact --accept-source-agreements --accept-package-agreements --silent
            if ($LASTEXITCODE -eq 0) {
                return $true
            }
        } catch {
            # Fall through to direct installer fallback.
        }
    }

    Write-Host "winget install failed or unavailable. Attempting direct installer download..."

    $tempExe = Join-Path $env:TEMP "innosetup-installer.exe"
    try {
        Invoke-WebRequest -Uri "https://jrsoftware.org/download.php/is.exe" -OutFile $tempExe -UseBasicParsing
        if (-not (Test-Path $tempExe)) {
            return $false
        }

        $args = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"
        $proc = Start-Process -FilePath $tempExe -ArgumentList $args -Verb RunAs -PassThru -Wait
        return $proc.ExitCode -eq 0
    } catch {
        return $false
    } finally {
        if (Test-Path $tempExe) {
            Remove-Item $tempExe -Force -ErrorAction SilentlyContinue
        }
    }
}

function Try-InstallPython311 {
    $winget = Get-Command "winget" -ErrorAction SilentlyContinue
    if (-not $winget) {
        return $false
    }

    Write-Host "Attempting to install Python 3.11 with winget..."
    try {
        & $winget.Source install --id Python.Python.3.11 --exact --accept-source-agreements --accept-package-agreements --silent
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Resolve-Python311Exe {
    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $candidate = (& $pyLauncher.Source -3.11 -c "import sys; print(sys.executable)" 2>$null)
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($candidate)) {
                return $candidate.Trim()
            }
        } catch {}
    }

    $possible = @(
        "${env:LocalAppData}\Programs\Python\Python311\python.exe",
        "${env:ProgramFiles}\Python311\python.exe",
        "${env:ProgramFiles(x86)}\Python311\python.exe"
    )
    foreach ($p in $possible) {
        if (-not [string]::IsNullOrWhiteSpace($p) -and (Test-Path $p)) {
            return $p
        }
    }

    return ""
}

function Setup-BuildVenv {
    param([string]$BasePythonExe)

    if (-not (Test-Path $VenvPy)) {
        Invoke-Checked -FilePath $BasePythonExe -Arguments @("-m", "venv", $VenvDir) -FailureMessage "Failed to create build venv using $BasePythonExe"
    }

    $requirementsPath = Join-Path $RepoRoot "requirements.txt"
    $filteredRequirementsPath = Join-Path $VenvDir "requirements-installer.txt"

    if (-not (Test-Path $requirementsPath)) {
        throw "requirements.txt not found at $requirementsPath"
    }

    # Skip extruder-turtle-Rhino for Windows installer builds.
    Get-Content $requirementsPath |
        Where-Object { $_ -notmatch "extruder-turtle-Rhino" } |
        Set-Content -Path $filteredRequirementsPath

    Invoke-Checked -FilePath $VenvPy -Arguments @("-m", "pip", "install", "--upgrade", "pip") -FailureMessage "Failed to upgrade pip in build environment."
    Invoke-Checked -FilePath $VenvPy -Arguments @("-m", "pip", "install", "-r", $filteredRequirementsPath) -FailureMessage "Failed to install filtered requirements into build environment."
    Invoke-Checked -FilePath $VenvPy -Arguments @("-m", "pip", "install", "pyinstaller") -FailureMessage "Failed to install PyInstaller into build environment."
}

$AppVersion = Get-AppVersionFromSetupPy -Path $SetupPyPath
$PythonExe = Resolve-CompatiblePythonExe -Requested $PythonExe

Write-Host "[1/6] Preparing isolated build environment..."
Write-Host "[2/6] Installing build dependencies..."
Setup-BuildVenv -BasePythonExe $PythonExe

Write-Host "[2/6] Verifying runtime dependencies in build environment..."
& $VenvPy -c "import PyQt5, vtk; print('Dependency check passed: PyQt5 + vtk')"
if ($LASTEXITCODE -ne 0) {
    throw "PyQt5/vtk failed to import in build environment. Ensure your Python version is compatible with the latest PyQt5 wheels and rerun."
}

Write-Host "[3/6] Cleaning previous build outputs..."
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

Write-Host "[4/6] Building HogSlice executable bundle with PyInstaller..."
Push-Location $RepoRoot
Invoke-Checked -FilePath $VenvPy -Arguments @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "HogSlice",
    "--onedir",
    "--add-data", "assets;assets",
    "--collect-submodules", "vtkmodules",
    "--collect-submodules", "PyQt5",
    "--hidden-import", "PyQt5.sip",
    "main.py"
) -FailureMessage "PyInstaller build failed."
Pop-Location

if (-not (Test-Path (Join-Path $DistDir "HogSlice.exe"))) {
    throw "PyInstaller build did not produce dist\HogSlice\HogSlice.exe"
}

Write-Host "[5/6] Locating Inno Setup compiler (ISCC.exe)..."
$InnoCompilerPath = Resolve-InnoCompilerPath -PreferredPath $InnoCompilerPath
if ([string]::IsNullOrWhiteSpace($InnoCompilerPath)) {
    $installed = Try-InstallInnoSetup
    if ($installed) {
        Start-Sleep -Seconds 2
        $InnoCompilerPath = Resolve-InnoCompilerPath -PreferredPath ""
    }
}

if ([string]::IsNullOrWhiteSpace($InnoCompilerPath) -or -not (Test-Path $InnoCompilerPath)) {
    throw "Inno Setup compiler not found. Install Inno Setup 6 (https://jrsoftware.org/isdl.php) or pass -InnoCompilerPath <path-to-ISCC.exe>."
}

Write-Host "[6/6] Compiling setup wizard executable..."
Push-Location $ScriptDir
& $InnoCompilerPath "/DMyAppVersion=$AppVersion" $InstallerScript
Pop-Location

$installerExe = Join-Path $ScriptDir "Output\HogSlice-Setup-$AppVersion.exe"
if (-not (Test-Path $installerExe)) {
    throw "Installer was not generated at expected path: $installerExe"
}

Write-Host "Done. Installer created at $installerExe"
if (-not $NoLaunchInstaller) {
    Write-Host "Launching installer wizard..."
    Start-Process -FilePath $installerExe
}
