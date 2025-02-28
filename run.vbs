Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c run.bat", 0, True
Set WshShell = Nothing