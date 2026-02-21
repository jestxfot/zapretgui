Prefer delegating codebase exploration to subagents; ask questions only when truly blocked; consider several options before making interactive/destructive changes.

План работы и коммуникации с пользователем:
1. Смотришь код и как что завязано. Смотришь ВСЕ файлы очень подробно.
2. Потом показываешь в ответе полный flow чтобы ты запомнил как файлы связаны друг с другом и что как работает
3. ВСЕГДА ЗАДАВАЙ МНЕ ВОПРОСЫ ПЕРЕД ЛЮБЫМИ ПРАВКАМИ!

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

hosts.ini (каталог доменов)

- Канонический путь каталога: `<repo>/json/hosts.ini` (рядом с репозиторием).
- Для exe-сборки это тоже внешний файл рядом с папкой приложения: `<exe_dir>/json/hosts.ini`.
- Единственный валидный путь: внешний `./json/hosts.ini` (рядом с репой или рядом с exe).
- Любые пути вида `.../_internal/json/hosts.ini`, `sys._MEIPASS/...` и вычисление от `__file__` внутри frozen-бандла считаются багом и должны быть устранены (не использовать как fallback).

Каталоги стратегий (канонические пути)

- direct_zapret1: только `%APPDATA%/zapret/direct_zapret1/*.txt`.
- direct_zapret2 basic: только `%APPDATA%/zapret/direct_zapret2/basic_strategies/*`.
- direct_zapret2 advanced: только `%APPDATA%/zapret/direct_zapret2/advanced_strategies/*`.
- Пути внутри `_internal` (например `.../_internal/preset_zapret1/...`, `.../_internal/preset_zapret2/...`), `sys._MEIPASS/...` и вычисление от `__file__` внутри frozen-бандла для загрузки стратегий считаются багом и не допускаются даже как fallback.
