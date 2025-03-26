@echo off

REM Ask if user is sure
echo This will remove the program from your computer.
echo Note: MAKE SURE TO RUN AS ADMIN OR IT WON'T WORK! (It MAY say it worked, but it didn't.)
pause

REM Remove the program and unregister the dlls located in lib/
regsvr32 /u /s lib\screen-capture-recorder-x64.dll
regsvr32 /u /s lib\screen-capture-recorder.dll
regsvr32 /u /s lib\audio_sniffer-x64.dll
regsvr32 /u /s lib\audio_sniffer.dll
del first_run

REM Tell the user we're done and they can delete the folder
echo Done! You can now delete the application folder. Press any key to exit.
pause