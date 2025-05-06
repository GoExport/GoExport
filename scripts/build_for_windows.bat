@echo off

REM Change directory to the script's location to ensure relative paths work
cd /d "%~dp0"

REM Build the application using pyinstaller

pyinstaller --onefile ../src/main.py --name "GoExport" --distpath ../dist --workpath ../build --specpath ../ --noconfirm

echo Build process completed.
pause