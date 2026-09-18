Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
exePath = currentDir & "\dist\不加了\不加了.exe"
WshShell.CurrentDirectory = currentDir & "\dist\不加了"
WshShell.Run """" & exePath & """", 1, False
