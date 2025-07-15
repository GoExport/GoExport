@echo off
setlocal

:: Ask for tag name
set /p TAGNAME=Enter the tag name (e.g. v1.0.0): 

:: Create the tag locally
git tag %TAGNAME%
if errorlevel 1 (
    echo Failed to create tag. Make sure you are in a git repository.
    exit /b 1
)
echo Tag "%TAGNAME%" created locally.

:: Ask if user wants to push the tag
set /p PUSHNOW=Do you want to push the tag to origin now? (y/n): 

if /i "%PUSHNOW%"=="y" (
    git push origin %TAGNAME%
    if errorlevel 1 (
        echo Failed to push tag to origin.
        exit /b 1
    )
    echo Tag "%TAGNAME%" pushed to origin.
) else (
    echo Tag "%TAGNAME%" is only local.
    set /p PUSHLATER=Do you want to push the tag to origin later? (y/n): 
    if /i "%PUSHLATER%"=="y" (
        git push origin %TAGNAME%
        if errorlevel 1 (
            echo Failed to push tag to origin.
            exit /b 1
        )
        echo Tag "%TAGNAME%" pushed to origin.
    )
    if /i not "%PUSHLATER%"=="y" (
        echo You can push the tag later with: git push origin %TAGNAME%
    )
)

endlocal