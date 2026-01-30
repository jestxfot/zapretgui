Ask questions before changing anything interactively, considering several possible options!

Всe действия в этом репозитории выполняй через WSL (редактирование, сборка/тесты, git): так быстрее, чем работать через Windows.
- Не открывай/редактируй файлы из Windows и не используй Windows tooling по путям вида `\\wsl$\...`.
- Не размещай репозиторий на `/mnt/c` и других Windows-mounted дисках.
- Если команда запускается из Windows, запускай ее через `wsl.exe`.

“Make sure to commit every change, as the code sometimes gets reset.

Обязательно перед каждым `git commit`:
- проверь, что staged-изменения содержат актуальный код: `git diff --staged`

Обязательно сразу после каждого коммита:
- проверь, что в коммите именно последние изменения (а не старый код): `git show --stat` и при необходимости `git show`
