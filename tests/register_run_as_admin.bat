REM register the dlls
regsvr32 "%~dp0\..\libs\screen-capture-recorder.dll"
regsvr32 "%~dp0\..\libs\screen-capture-recorder-x64.dll"
regsvr32 "%~dp0\..\libs\audio_sniffer.dll"
regsvr32 "%~dp0\..\libs\audio_sniffer-x64.dll"
pause