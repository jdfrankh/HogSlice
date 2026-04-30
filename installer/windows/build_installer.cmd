@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS1_PATH=%SCRIPT_DIR%build_installer.ps1"

if not exist "%PS1_PATH%" (
  echo Could not find build_installer.ps1 at:
  echo %PS1_PATH%
  pause
  exit /b 1
)

echo Running HogSlice installer build...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo Build failed with exit code %EXITCODE%.
  pause
  exit /b %EXITCODE%
)

echo.
echo Build completed successfully.
pause
exit /b 0
