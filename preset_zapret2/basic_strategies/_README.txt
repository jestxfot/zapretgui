Direct Zapret2 - Basic strategies catalog

This folder is the source for the Basic direct launch mode catalogs.

At install time, these files are copied to:
  %APPDATA%\zapret\direct_zapret2\basic_strategies\

Expected filenames (TXT INI-like format, same as tcp.txt/udp.txt):
  - tcp.txt
  - udp.txt
  - http80.txt
  - discord_voice.txt

The app reads Basic catalogs only from the Roaming AppData location above.
In dev mode, missing files are seeded from this repo folder (only if absent).
