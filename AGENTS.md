Ask questions before changing anything interactively, considering several possible options!

Всe действия в этом репозитории выполняй через WSL (редактирование, сборка/тесты, git): так быстрее, чем работать через Windows.
- Не открывай/редактируй файлы из Windows и не используй Windows tooling по путям вида `\\wsl$\...`.
- Не размещай репозиторий на `/mnt/c` и других Windows-mounted дисках.
- Если команда запускается из Windows, запускай ее через `wsl.exe`.

“Make sure to commit every change, as the code sometimes gets reset.

hosts.ini (каталог доменов)

- Канонический путь каталога: `<repo>/json/hosts.ini` (рядом с репозиторием).
- Для exe-сборки это тоже внешний файл рядом с репой/папкой приложения; не полагаться на пути вида `.../_internal/json/hosts.ini` / `sys._MEIPASS`.
- Если в логах/отладке путь выглядит как `.../_internal/json/hosts.ini`, это признак того, что путь вычислили от `__file__` внутри PyInstaller-бандла (и это не то поведение, которое здесь считаем правильным).

Обязательно перед каждым `git commit`:
- проверь, что staged-изменения содержат актуальный код: `git diff --staged`

Обязательно сразу после каждого коммита:
- проверь, что в коммите именно последние изменения (а не старый код): `git show --stat` и при необходимости `git show`
