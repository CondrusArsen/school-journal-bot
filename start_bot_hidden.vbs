Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d d:\school_journal_bot && venv\Scripts\pythonw.exe bot.py", 0, False
