@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FastDownload

if /i "%~1"=="app"        goto app
if /i "%~1"=="server"     goto server
if /i "%~1"=="standalone" goto standalone
if /i "%~1"=="build"      goto build
if /i "%~1"=="install"    goto install
if /i "%~1"=="tab"        goto tab
if /i "%~1"=="installer"  goto installer

:menu
cls
echo.
echo   FastDownload
echo   ============================================
echo   1  Desktop app
echo   2  Server for FL / browser  -  127.0.0.1:8731
echo   3  Plugin standalone - test without FL Studio
echo   4  Build plugin VST3
echo   5  Install plugin into FL Studio - admin
echo   6  Install browser tab into FL - close FL first
echo   7  Build setup installer (Inno Setup)
echo   0  Exit
echo.
set /p "choice=Choice: "
if "%choice%"=="" exit /b 0
if "%choice%"=="1" goto app
if "%choice%"=="2" goto server
if "%choice%"=="3" goto standalone
if "%choice%"=="4" goto build
if "%choice%"=="5" goto install
if "%choice%"=="6" goto tab
if "%choice%"=="7" goto installer
if "%choice%"=="0" exit /b 0
goto menu


:app
python engine\main.py
goto menu


:server
echo Server at http://127.0.0.1:8731/   -   Ctrl+C to stop
python engine\server.py --port 8731
pause
goto menu


:standalone
if exist "plugin\dist\Standalone\FastDownload.exe" goto run_standalone
echo Not built yet: use option 4.
pause
goto menu

:run_standalone
start "" "plugin\dist\Standalone\FastDownload.exe"
goto menu


:tab
echo Make sure FL Studio is CLOSED before continuing.
pause
python engine\browser_tab.py
echo.
echo Open FL Studio: the "FastDownload" tab will show the active project's folder.
pause
goto menu


:installer
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files (x86)\Inno Setup 7\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" goto installer_missing
echo Compiling installer...
"%ISCC%" "installer\FastDownload.iss"
echo.
echo Setup: installer\output\FastDownload-Setup.exe
pause
goto menu

:installer_missing
echo Inno Setup not found. Install it from https://jrsoftware.org/isdl.php
pause
goto menu


:build
set JUCE_TAG=8.0.15
set WV2_VER=1.0.3485.44

if exist "plugin\external\JUCE\CMakeLists.txt" goto have_juce
echo Downloading JUCE %JUCE_TAG% ...
git clone --depth 1 --branch %JUCE_TAG% https://github.com/juce-framework/JUCE.git "plugin\external\JUCE"
if errorlevel 1 goto build_err

:have_juce
if exist "plugin\external\webview2" goto have_wv2
echo Downloading WebView2 SDK %WV2_VER% ...
powershell -NoProfile -Command "$d='plugin\external\webview2'; New-Item -ItemType Directory -Force -Path $d | Out-Null; $z=Join-Path $d 'wv2.zip'; Invoke-WebRequest -UseBasicParsing 'https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2/%WV2_VER%' -OutFile $z; Expand-Archive $z (Join-Path $d 'Microsoft.Web.WebView2.%WV2_VER%') -Force; Remove-Item $z"
if errorlevel 1 goto build_err

:have_wv2
echo Configuring...
cmake -S plugin -B plugin/build -G "Visual Studio 17 2022" -A x64
if errorlevel 1 goto build_err

echo Building...
cmake --build plugin/build --config Release --parallel
if errorlevel 1 goto build_err

echo Copying artifacts to plugin\dist ...
powershell -NoProfile -Command "$d='plugin\dist'; New-Item -ItemType Directory -Force -Path (Join-Path $d 'Standalone') | Out-Null; Copy-Item -Recurse -Force 'plugin\build\FastDownload_artefacts\Release\VST3\FastDownload.vst3' $d; Copy-Item -Force 'plugin\build\FastDownload_artefacts\Release\Standalone\FastDownload.exe' (Join-Path $d 'Standalone')"
echo.
echo Build completed: plugin\dist
pause
goto menu

:build_err
echo.
echo Build failed.
pause
goto menu


:install
net session >nul 2>&1
if not errorlevel 1 goto install_admin
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList 'install' -Verb RunAs"
exit /b 0

:install_admin
if exist "plugin\dist\FastDownload.vst3" goto install_copy
echo Not built yet: use option 4.
pause
goto menu

:install_copy
echo Installing to C:\Program Files\Common Files\VST3 ...
robocopy "plugin\dist\FastDownload.vst3" "C:\Program Files\Common Files\VST3\FastDownload.vst3" /E /NFL /NDL /NJH /NJS /NP >nul
echo.
echo Done. In FL Studio: Options ^> Manage plugins ^> Find more plugins.
pause
goto menu
