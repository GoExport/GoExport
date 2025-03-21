@echo off
for %%f in (data\*) do if not "%%~nxf"==".gitignore" del /Q "%%f"
rmdir /S /Q dist
pyinstaller --onefile --name "GoExport" --icon ./assets/icon.png ^
 --add-data "data;data" --add-data "dependencies;dependencies" ^
 --hidden-import=modules.capture --hidden-import=modules.compatibility ^
 --hidden-import=modules.controller --hidden-import=modules.editor ^
 --hidden-import=modules.logger --hidden-import=modules.navigator ^
 .\main.py
copy readme.md dist\
copy LICENSE dist\
xcopy assets dist\assets /E /I /Q /Y