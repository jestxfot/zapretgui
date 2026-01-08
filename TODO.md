# TODO - Единая система задач для всех агентов

> **Формат:** Агенты читают этот файл в начале работы и записывают свой прогресс.

## Текущие задачи

| Статус | Задача | Агент | Дата |
|--------|--------|-------|------|
| [~] | Рефакторинг locked/blocked в отдельный Lua модуль | orchestra-lua-reviewer | 2025-12-21 |
| [x] | Исправить логику полей фильтров (base_filter_ipset) | Claude | 2026-01-02 |

## В процессе

### Claude - Рефакторинг zapret2_settings_reset.py + preset форматирование
- [x] Задача 1: Убрать реестр из zapret2_settings_reset.py, использовать PresetManager
- [x] Задача 2: Исправить форматирование preset файлов (всё в одну строку)
  - [x] Найдена причина: strategy_menu/__init__.py:803-823
  - [x] Проблема: combine_strategies() возвращает командную строку с пробелами
  - [ ] Исправление: использовать shlex.split() для разбивки
- [~] Делегирование python-engineer для выполнения обеих задач
- [ ] Запустить qa-reviewer для проверки

### python-engineer - Рефакторинг blocked_strategies_manager.py
- [~] Прочитать locked_strategies_manager.py как эталон
- [ ] Добавить разделение по протоколам (blocked_by_askey)
- [ ] Добавить user_blocked_by_askey отдельно от default blocks
- [ ] Исправить нормализацию hostname (единая точка)
- [ ] Исправить подсчёт user_count
- [ ] Исправить save() (безопасное сохранение без удаления всего)
- [ ] Синхронизировать API с locked_strategies_manager

### Рефакторинг Locked/Blocked стратегий

**Проблема:** Заблокированные стратегии продолжают ротироваться из-за:
1. **КРИТИЧНО**: Несовпадение регистра hostname (Python: `.lower()`, Lua: без нормализации)
2. Логика разбросана по нескольким файлам
3. Нет единой точки нормализации hostkey

**План:**
- [ ] Создать `H:\Privacy\zapret\lua\strategy-lock-manager.lua`
- [ ] Вынести логику из `combined-detector.lua` (строки 913-1108)
- [ ] Вынести логику из `strategy-stats.lua` (is_strategy_blocked, should_skip_pass)
- [ ] Добавить `slm_normalize_hostkey()` - единственное место для `.lower()`
- [ ] Обновить `combined-detector.lua` использовать `slm_*` функции
- [ ] Обновить `strategy-stats.lua` использовать `slm_*` функции
- [ ] Обновить порядок `--lua-init` в конфиге

**API нового модуля:**
```lua
slm_normalize_hostkey(hostname) -> string
slm_get_locked(hostkey) -> number|nil
slm_set_locked(hostkey, strategy, reason)
slm_is_blocked(hostkey, strategy) -> bool
slm_should_skip_pass(hostkey) -> bool
slm_record_result(hostkey, strategy, success)
slm_get_best(hostkey, skip_strategy) -> number|nil
```

## Выполненные

| Задача | Агент | Дата |
|--------|-------|------|
| Добавлено отображение протоколов (askey) в orchestra_blocked_page.py | ui-designer | 2025-12-25 |
| Создан NotificationBanner виджет (Windows 11 Fluent Design) | ui-designer | 2025-12-25 |
| Добавлена проверка is_blocked в orchestra_locked_page.py | ui-designer | 2025-12-25 |
| Созданы JSON стратегии для Zapret 1 | general-purpose | 2025-12-21 |
| Исправлен strategy_loader.py для Zapret 1 | general-purpose | 2025-12-21 |
| Создана система агентов (python-engineer, qa-reviewer, doc-writer) | Claude | 2025-12-21 |
| Создана единая функция get_current_winws_exe() для определения winws.exe | python-engineer | 2025-12-21 |
| QA Review: рефакторинг get_current_winws_exe() - OK | qa-reviewer | 2025-12-21 |

---

## Правила работы с TODO

### Для всех агентов:

1. **В начале работы** - прочитай этот файл
2. **Перед началом задачи** - добавь её в "В процессе"
3. **После завершения** - перенеси в "Выполненные"
4. **При проблемах** - добавь заметку в секцию "Проблемы"

### Формат записи:

```markdown
## В процессе

### [название-агента] - Краткое описание задачи
- [ ] Подзадача 1
- [ ] Подзадача 2
- [x] Выполненная подзадача
```

### Статусы:

- `[ ]` - не начато
- `[~]` - в процессе
- `[x]` - выполнено
- `[!]` - заблокировано/проблема

---

## Проблемы и заметки

*Агенты записывают сюда важные находки и проблемы*

---

## История сессий

### 2025-12-21
- Создана единая система TODO
- Настроены агенты для чтения/записи TODO.md
