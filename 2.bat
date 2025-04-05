pyarmor-7 init --src=. --entry=updater.py dist
pyarmor-7 obfuscate -O dist updater.py
pyinstaller --onefile --distpath dist dist/updater.py
pause