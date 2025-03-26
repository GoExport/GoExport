REM unregister the dlls
regsvr32 /u "%~dp0\..\libs\screen-capture-recorder.dll"
regsvr32 /u "%~dp0\..\libs\screen-capture-recorder-x64.dll"
regsvr32 /u "%~dp0\..\libs\audio_sniffer.dll"
regsvr32 /u "%~dp0\..\libs\audio_sniffer-x64.dll"
pause