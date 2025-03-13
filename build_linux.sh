pyinstaller --onefile --name "GoExport" --icon ./assets/icon.png ./main.py
if [ -d "dist/assets" ]; then
    rm -rf dist/assets
fi
cp -r assets dist/assets
if [ -d "dist/dependencies" ]; then
    rm -rf dist/dependencies
fi
cp -r dependencies dist/dependencies
if [ ! -d "dist/logs" ]; then
    mkdir -p dist/logs
fi
if [ ! -d "dist/data" ]; then
    mkdir -p dist/data
fi
cp readme.md dist/
cp LICENSE dist/