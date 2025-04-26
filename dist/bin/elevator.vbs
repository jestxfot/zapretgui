Set UAC = CreateObject("Shell.Application") 
args = "ELEV " 
For Each strArg in WScript.Arguments 
args = args & strArg & " "  
Next 
args = "/c """ + "C:\root\bin\zapretgui\dist\bin\original_bolvan_v2.bat" + """ " + args 
UAC.ShellExecute "C:\Windows\System32\cmd.exe", args, "", "runas", 1 
