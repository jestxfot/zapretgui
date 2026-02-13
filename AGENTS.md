Prefer delegating codebase exploration to subagents; ask questions only when truly blocked; consider several options before making interactive/destructive changes.

Ask questions before changing anything interactively, considering several possible options!

Note: In this repo, multiple agents may work in parallel (e.g. GPT/Codex/Claude). If you see unexpected local changes, assume another agent might be working; don't panic or revert automatically.

## Subagents (keep context clean)

Goal: keep the main agent's context "clean" and quickly converge on what to change, instead of wandering through the repo. Delegate most searching/reading/tracing to subagents.

- Code analysis (project-wide search, reading many files, tracing flows, finding the source of a bug): start with `Task` using the `explore` subagent.
- Production debugging / incident triage (root-cause hypotheses, verification commands, remediation plan): start with `Task` using the `general` subagent.
- The main agent should read files directly only when:
  - applying a concrete patch (targeted change);
  - validating the final context around the edit.
- Ask subagents to return a "ready-to-use" response:
  - exact file paths (`path/to/file.py`) and the relevant functions/classes;
  - 1-3 key causes/hypotheses;
  - a concrete fix proposal (minimal patch / pseudopatch);
  - how to verify (tests/run/diagnostics).

Recommended prompt template:

```text
Analyze <symptom/log/question>. Find where it happens in the code and propose the minimal fix.
Return: (1) files+symbols, (2) root cause, (3) targeted fix, (4) how to verify.
```

“Make sure to commit every change, as the code sometimes gets reset.

Git workflow (auto-commit + push)

- После любых изменений в коде/конфигах: делай коммит (обычно 1 коммит на задачу/запрос), не оставляй изменения незакоммиченными.
- По умолчанию после каждого успешного коммита: делай `git push upstream` на текущую ветку.
- Не полагайся на `origin` (форк может отсутствовать/быть удален).
- Если push невозможен (нет remote/прав/инета): сообщи об ошибке и оставь локальный коммит.
- Никогда не используй `--force`/`--force-with-lease`.
- Никогда не меняй git config.

hosts.ini (каталог доменов)

- Канонический путь каталога: `<repo>/json/hosts.ini` (рядом с репозиторием).
- Для exe-сборки это тоже внешний файл рядом с папкой приложения: `<exe_dir>/json/hosts.ini`.
- Единственный валидный путь: внешний `./json/hosts.ini` (рядом с репой или рядом с exe).
- Любые пути вида `.../_internal/json/hosts.ini`, `sys._MEIPASS/...` и вычисление от `__file__` внутри frozen-бандла считаются багом и должны быть устранены (не использовать как fallback).

Обязательно перед каждым `git commit`:
- проверь, что staged-изменения содержат актуальный код: `git diff --staged`

Обязательно сразу после каждого коммита:
- проверь, что в коммите именно последние изменения (а не старый код): `git show --stat` и при необходимости `git show`
