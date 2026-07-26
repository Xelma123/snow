' Launch run_agent.ps1 without a console window (Scheduled Task entrypoint)
Set sh = CreateObject("WScript.Shell")
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & dir & "\run_agent.ps1"""
sh.Run cmd, 0, False
