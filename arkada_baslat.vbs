Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d ""C:\Users\depco\OneDrive\Desktop\mtf_signal_engine"" && .venv\Scripts\python.exe run.py", 0, False
