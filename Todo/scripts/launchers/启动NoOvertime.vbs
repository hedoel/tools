Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
exePath = currentDir & "\dist\NoOvertime\NoOvertime.exe"
WshShell.CurrentDirectory = currentDir & "\dist\NoOvertime"
WshShell.Run """" & exePath & """", 1, False
