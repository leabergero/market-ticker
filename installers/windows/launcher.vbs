' Lanzador de Market Ticker (destino del acceso directo del menú inicio).
' Si el venv ya existe arranca la app sin ninguna consola; si no, lanza
' setup.bat en una consola visible para la instalación de dependencias
' del primer arranque.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = appDir & "\venv\Scripts\pythonw.exe"
sh.CurrentDirectory = appDir
If fso.FileExists(pyw) Then
    sh.Run """" & pyw & """ """ & appDir & "\launcher.pyw""", 0, False
Else
    sh.Run "cmd /c """"" & appDir & "\setup.bat""""", 1, False
End If
