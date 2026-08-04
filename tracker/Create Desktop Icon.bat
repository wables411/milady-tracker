@echo off
rem Creates a "Milady Tracker" icon on the Desktop that starts the server
rem (if needed) and opens the tracker in its own app window.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Milady Tracker.lnk'); $s.TargetPath='powershell.exe'; $s.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%~dp0launch.ps1\"'; $s.IconLocation='%~dp0milady.ico'; $s.WorkingDirectory='%~dp0'; $s.Save()"
if %errorlevel%==0 (echo Done — "Milady Tracker" is on your Desktop.) else (echo Something went wrong.)
pause
