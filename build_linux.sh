#!/bin/bash

# Remove all files in the data directory
rm -rf data/*

# Remove all files in the dist directory
rm -rf dist/*

# Run pyinstaller with the specified options
pyinstaller --onefile --name "GoExport" --icon ./assets/icon.png --add-data "data:data" --add-data "dependencies:dependencies" --add-data "assets:assets" ./main.py

# Copy readme.md and LICENSE to the dist directory
cp readme.md dist/
cp LICENSE dist/
