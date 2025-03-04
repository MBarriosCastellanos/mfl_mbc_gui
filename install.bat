@echo off
REM -------------------------------
REM Verificar si PyInstaller está instalado
REM -------------------------------
echo Verificando si PyInstaller está instalado...
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller no est&aacute; instalado. Instalando...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo Error al instalar PyInstaller.
        pause
        exit /b 1
    )
) else (
    echo PyInstaller ya est&aacute; instalado.
)

REM -------------------------------
REM Generar el ejecutable con PyInstaller
REM -------------------------------
echo Ejecutando PyInstaller...
python -m PyInstaller --onedir --noconsole main.py
if errorlevel 1 (
    echo Error al ejecutar PyInstaller.
    pause
    exit /b 1
)

REM -------------------------------
REM Verificar que se haya creado la carpeta dist
REM -------------------------------
if not exist "dist" (
    echo La carpeta "dist" no se encontr&oacute;.
    pause
    exit /b 1
)

REM -------------------------------
REM Copiar la carpeta figures (por ejemplo, el archivo mfl_sup.jpg) a dist\figures
REM -------------------------------
if exist "figures" (
    xcopy /E /I /Y figures "dist\main\figures\"
    echo Carpeta "figures" copiada en dist.
) else (
    echo La carpeta "figures" no existe.
)

REM -------------------------------
REM Asumir que el ejecutable generado es main.exe en la carpeta dist
REM -------------------------------
set "EXE_PATH=%CD%\dist\main.exe"

REM -------------------------------
REM Obtener la ruta del Escritorio usando PowerShell
REM -------------------------------
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do (
    set "DESKTOP_PATH=%%i"
)
set "SHORTCUT_PATH=%DESKTOP_PATH%\MainApp.lnk"

echo Creando acceso directo en el Escritorio...

REM -------------------------------
REM Crear un script VBS temporal para generar el acceso directo
REM -------------------------------
set "TEMP_VBS=%TEMP%\CreateShortcut.vbs"
(
    echo Set oWS = WScript.CreateObject("WScript.Shell")
    echo sLinkFile = "%SHORTCUT_PATH%"
    echo Set oLink = oWS.CreateShortcut(sLinkFile)
    echo oLink.TargetPath = "%EXE_PATH%"
    echo oLink.WorkingDirectory = "%CD%\dist"
    echo oLink.WindowStyle = 7
    echo oLink.Description = "Acceso directo a MainApp"
    echo oLink.Save
) > "%TEMP_VBS%"

cscript //nologo "%TEMP_VBS%"
del "%TEMP_VBS%"

echo Acceso directo creado en: %SHORTCUT_PATH%
pause
exit /b 0