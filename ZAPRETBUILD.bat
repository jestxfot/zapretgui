echo Gen file version...
python build_version_info.py
echo Building....
pyinstaller --onefile --noconsole --hidden-import=win32com --hidden-import=win32com.client --hidden-import=pythoncom --hidden-import=sip --windowed --icon "%cd%\zapret.ico" --name zapret --version-file=version_info.txt "%cd%\main.py"
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" zapret.iss
echo Done!
pause