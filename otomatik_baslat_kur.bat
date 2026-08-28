@echo off
title MTF Auto-Startup Kurulumu
echo ============================================================
echo MTF Trend Sinyal Motorunu Windows Baslangicina Ekliyor...
echo ============================================================

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set TARGET_VBS=C:\Users\depco\OneDrive\Desktop\mtf_signal_engine\arkada_baslat.vbs

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = "%STARTUP_DIR%\MTF_Signal_Engine.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "wscript.exe" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Arguments = """%TARGET_VBS%""" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "C:\Users\depco\OneDrive\Desktop\mtf_signal_engine" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WindowStyle = 0 >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"
cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"

echo.
echo [BASARILI] Sistem artik bilgisayar her acildiginda arkada otomatik calisacak!
echo Web UI: http://127.0.0.1:8080
echo.
pause
