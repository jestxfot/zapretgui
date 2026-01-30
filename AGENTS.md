Ask questions before changing anything interactively, considering several possible options!

Всe действия в этом репозитории выполняй через WSL (редактирование, сборка/тесты, git): так быстрее, чем работать через Windows.
- Не открывай/редактируй файлы из Windows и не используй Windows tooling по путям вида `\\wsl$\...`.
- Не размещай репозиторий на `/mnt/c` и других Windows-mounted дисках.
- Если команда запускается из Windows, запускай ее через `wsl.exe`.

“Make sure to commit every change, as the code sometimes gets reset.

hosts.ini (каталог доменов)

- Канонический путь каталога: `<repo>/json/hosts.ini` (рядом с репозиторием).
- Для exe-сборки это тоже внешний файл рядом с папкой приложения: `<exe_dir>/json/hosts.ini`.
- Единственный валидный путь: внешний `./json/hosts.ini` (рядом с репой или рядом с exe).
- Любые пути вида `.../_internal/json/hosts.ini`, `sys._MEIPASS/...` и вычисление от `__file__` внутри frozen-бандла считаются багом и должны быть устранены (не использовать как fallback).

Обязательно перед каждым `git commit`:
- проверь, что staged-изменения содержат актуальный код: `git diff --staged`

Обязательно сразу после каждого коммита:
- проверь, что в коммите именно последние изменения (а не старый код): `git show --stat` и при необходимости `git show`
