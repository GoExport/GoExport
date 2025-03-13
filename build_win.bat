pyinstaller --onefile --name "GoExport" --icon ./assets/icon.png .\main.py
if exist dist\assets\ rmdir /s /q dist\assets\
xcopy assets dist\assets\ /s /i /e
if exist dist\dependencies\ rmdir /s /q dist\dependencies\
xcopy dependencies dist\dependencies\ /s /i /e
if not exist dist\logs\ mkdir dist\logs\
if not exist dist\data\ mkdir dist\data\
copy readme.md dist\
copy LICENSE dist\