@echo off
setlocal enabledelayedexpansion

REM Set the working directory to the script's location
cd /d "%~dp0"

REM Ask for video files for each aspect ratio
set /p "video_4_3=Enter path to video file for aspect ratio 4:3: "
set /p "video_14_9=Enter path to video file for aspect ratio 14:9: "
set /p "video_9_16=Enter path to video file for aspect ratio 9:16: "
set /p "video_16_9=Enter path to video file for aspect ratio 16:9: "

REM Process 4:3
mkdir standard
cd standard
for %%S in (320x240 480x360 560x420 640x480) do (
    for /f "tokens=1,2 delims=x" %%w in ("%%S") do (
        set "width=%%w"
        set "height=%%x"
        set "input=!video_4_3!"
        set "output=%%S.mp4"
        echo Resizing !input! to %%S for aspect ratio 4:3...
        call ffmpeg -i "!input!" -vf "scale=w='if(gte(a,!width!/!height!),!width!,-2)':h='if(gte(a,!width!/!height!),-2,!height!)',pad=!width!:!height!:(!width!-iw)/2:(!height!-ih)/2" -c:a copy "!output!"
    )
)

REM Repeat for each ratio

REM 14:9
cd ..
mkdir classic
cd classic
for %%S in (640x432 720x480 768x576 848x576) do (
    for /f "tokens=1,2 delims=x" %%w in ("%%S") do (
        set "width=%%w"
        set "height=%%x"
        set "input=!video_14_9!"
        set "output=%%S.mp4"
        echo Resizing !input! to %%S for aspect ratio 14:9...
        call ffmpeg -i "!input!" -vf "scale=w='if(gte(a,!width!/!height!),!width!,-2)':h='if(gte(a,!width!/!height!),-2,!height!)',pad=!width!:!height!:(!width!-iw)/2:(!height!-ih)/2" -c:a copy "!output!"
    )
)

REM 9:16
cd ..
mkdir tall
cd tall
for %%S in (360x640 480x854 720x1280 1080x1920) do (
    for /f "tokens=1,2 delims=x" %%w in ("%%S") do (
        set "width=%%w"
        set "height=%%x"
        set "input=!video_9_16!"
        set "output=%%S.mp4"
        echo Resizing !input! to %%S for aspect ratio 9:16...
        call ffmpeg -i "!input!" -vf "scale=w='if(gte(a,!width!/!height!),!width!,-2)':h='if(gte(a,!width!/!height!),-2,!height!)',pad=!width!:!height!:(!width!-iw)/2:(!height!-ih)/2" -c:a copy "!output!"
    )
)

REM 16:9
cd ..
mkdir wide
cd wide
for %%S in (640x360 854x480 1280x720 1920x1080) do (
    for /f "tokens=1,2 delims=x" %%w in ("%%S") do (
        set "width=%%w"
        set "height=%%x"
        set "input=!video_16_9!"
        set "output=%%S.mp4"
        echo Resizing !input! to %%S for aspect ratio 16:9...
        call ffmpeg -i "!input!" -vf "scale=w='if(gte(a,!width!/!height!),!width!,-2)':h='if(gte(a,!width!/!height!),-2,!height!)',pad=!width!:!height!:(!width!-iw)/2:(!height!-ih)/2" -c:a copy "!output!"
    )
)

REM Return to the original directory
cd /d "%~dp0"

echo All videos processed.
pause

REM End of script
endlocal