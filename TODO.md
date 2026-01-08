# TODO - Единая система задач для всех агентов

> **Формат:** Агенты читают этот файл в начале работы и записывают свой прогресс.

## Текущие задачи

| Статус | Задача | Агент | Дата |
|--------|--------|-------|------|
| [~] | Рефакторинг locked/blocked в отдельный Lua модуль | orchestra-lua-reviewer | 2025-12-21 |
| [x] | Исправить логику полей фильтров (base_filter_ipset) | Claude | 2026-01-02 |
| [x] | Обновить кнопки Сбросить/Выключить в strategies_page.py | Claude | 2026-01-08 |
| [x] | Добавить разделение режимов (preset vs registry) в strategies_page.py | Claude | 2026-01-08 |
| [x] | Переименовать strategies_page.py → direct_zapret2_page.py и упростить код | Claude | 2026-01-08 |
| [x] | Переделать default.txt в константу Python кода | Claude | 2026-01-08 |

## В процессе

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
| Переделан механизм default.txt - хранится как константа в коде (preset_defaults.py) | Claude | 2026-01-08 |
| Добавлена функция restore_default_preset() для восстановления Default.txt | Claude | 2026-01-08 |
| Пересоздан default.txt с 3 категориями: youtube tcp, discord tcp, discord_voice udp | Claude | 2026-01-08 |
| Исправлены баги с DIRECT_STRATEGY_KEY в zapret1_direct_strategies_page.py и zapret2_orchestra_strategies_page.py | Claude | 2026-01-08 |
| Обновлены тестовые файлы test_syndata_parser.py и test_syndata_simple.py под новый формат --out-range=-n8 | Claude | 2026-01-08 |
| Исправлен формат --out-range=-n8 в _get_out_range_args() (preset_model.py) | Claude | 2026-01-08 |
| Исправлен порядок аргументов в get_full_tcp_args() и get_full_udp_args() (preset_model.py) | Claude | 2026-01-08 |
| Исправлен парсинг --out-range=-n8 формата в extract_out_range_from_args() | Claude | 2026-01-08 |
| Добавлена фильтрация syndata/send/out-range в extract_strategy_args() (txt_preset_parser.py) | Claude | 2026-01-08 |
| Созданы кнопки "Сбросить" (копирует default.txt) и "Выключить" (очищает категории) в strategies_page.py | Claude | 2026-01-08 |
| Создан файл default.txt в preset_zapret2/ с базовыми настройками (youtube+discord) | Claude | 2026-01-08 |
| Добавлено восстановление syndata из syndata_dict в load_preset() (preset_zapret2/preset_storage.py) | Claude | 2026-01-08 |
| Обновлены preset_manager.py и preset_storage.py для использования get_full_tcp_args()/get_full_udp_args() | python-engineer | 2026-01-08 |
| Добавлен парсинг syndata/send/out-range в txt_preset_parser.py | Claude | 2026-01-08 |
| Добавлены методы генерации syndata/send/out-range в CategoryConfig (preset_zapret2/preset_model.py) | Claude | 2026-01-08 |
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
