## ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА (читай первым!)

### 1. В НАЧАЛЕ КАЖДОЙ СЕССИИ:
1. Прочитай TODO.md - там текущие задачи
2. Записывай свои задачи в TODO.md
3. Используй агентов для любой работы с кодом, ты лишь менеджер по проекту который всё проверяет за агентами и связывает их друг с другом. При этом ты активно читаешь проект чтобы понять его структуру, но сам ничего не правишь.

### 2. ВСЕГДА ИСПОЛЬЗУЙ АГЕНТОВ:

| Задача | Агент | Обязательность |
|--------|-------|----------------|
| Любой поиск по коду | `Explore` | **ОБЯЗАТЕЛЬНО** |
| Редактирование Python | `general-purpose` | **ОБЯЗАТЕЛЬНО** |
| Редактирование Lua | `orchestra-lua-reviewer` | **ОБЯЗАТЕЛЬНО** |
| Большие задачи (>3 шагов) | `python-engineer` | **ОБЯЗАТЕЛЬНО** |
| После любых изменений | `qa-reviewer` | **РЕКОМЕНДУЕТСЯ** |
| UI/UX стили, кнопки | `ui-designer` | **РЕКОМЕНДУЕТСЯ** |

### 3. НИКОГДА НЕ ДЕЛАЙ САМ:
- ❌ Не редактируй большие файлы (>50 строк) напрямую
- ❌ Не ищи по коду через Grep/Glob напрямую
- ❌ Не делай несколько изменений без TODO списка
- ❌ Не пиши JSON стратегии сам (зависнешь)

### 4. ДЕЛЕГИРУЙ:
- ✅ Используй Task tool с нужным subagent_type
- ✅ Запускай несколько агентов параллельно
- ✅ Записывай прогресс в TODO.md

### Архитектура агентов (Manager Pattern)

```
┌─────────────────────────────────────────────────┐
│              Claude (Менеджер)                  │
│  - Принимает задачи от пользователя             │
│  - Делегирует python-engineer                   │
│  - Докладывает результаты пользователю          │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│           python-engineer (Координатор)          │
│  - Планирует выполнение                         │
│  - Делегирует специалистам                      │
│  - Собирает результаты                          │
└─────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
   [Специалисты]   [doc-writer]   [qa-reviewer]
                   (по запросу)    (проверяет всё)
```

### Кастомные агенты проекта:

| Агент | Назначение | Роль |
|-------|------------|------|
| `python-engineer` | **Главный инженер** - планирует, координирует, делегирует | Координатор |
| `qa-reviewer` | **QA** - проверяет качество ВСЕХ изменений после агентов | Контроль |
| `doc-writer` | **Документация** - пишет доки только по запросу | По запросу |
| `zapret-source-expert` | Эксперт по оригинальному zapret2 (F:\doc\zapret2) | Только читает |
| `orchestra-lua-reviewer` | Lua код (exe/lua/, H:\Privacy\zapret\lua\) | Редактирует |
| `orchestra-python-reviewer` | Python оркестратора (orchestra/*.py) | Редактирует |
| `nfq2-lua-orchestrator` | Создание новых Lua/Python файлов | Создаёт |
| `ui-designer` | **UI/UX** - следит за согласованностью дизайна Windows 11 | Стили |
| `dpi-bypass-researcher` | **Исследователь DPI** - генерирует инновационные идеи обхода DPI | Идеи |
| `lua-strategy-creator` | **Создатель Lua стратегий** - пишет НОВЫЙ Lua код для winws2 | Создаёт |
| `strategy-search-expert` | **Эксперт по поиску** - SearchBar, FilterEngine, адаптеры | Поиск |

### Workflow для больших задач:

1. **Claude** получает задачу → делегирует `python-engineer`
2. **python-engineer** планирует → делегирует специалистам (параллельно!)
3. **Специалисты** выполняют → докладывают python-engineer
4. **qa-reviewer** проверяет каждое изменение
5. **python-engineer** собирает результаты → докладывает Claude
6. **Claude** докладывает пользователю

### Каких агентов когда использовать:

- **Нужно понять как работает оригинальный circular_quality?** → `zapret-source-expert`
- **Нужно исправить парсер логов Python?** → `orchestra-python-reviewer`
- **Нужно изменить Lua wrapper в strategy-stats.lua?** → `orchestra-lua-reviewer`
- **Нужно создать новый Lua скрипт?** → `nfq2-lua-orchestrator`
- **Некрасивые кнопки или несогласованный UI?** → `ui-designer`
- **Нужны новые идеи для обхода жёсткого DPI?** → `dpi-bypass-researcher`
- **Нужно написать новые Lua функции для winws2?** → `lua-strategy-creator`
- **Проблемы с поиском/фильтрацией/сортировкой стратегий?** → `strategy-search-expert`

### Workflow для создания новых DPI bypass стратегий:

```
1. dpi-bypass-researcher → генерирует идеи и псевдокод
2. lua-strategy-creator  → реализует рабочий Lua код
3. qa-reviewer           → проверяет качество кода
```

### ВАЖНО: Разделение кода

- **Оригинальный код zapret2:** `F:\doc\zapret2\` - читает только `zapret-source-expert`
- **Наши Lua модификации:** `H:\Privacy\zapret\lua\` - редактирует `orchestra-lua-reviewer`
- **Python оркестратор:** `H:\Privacy\zapretgui\orchestra\` - редактирует `orchestra-python-reviewer`

### ОБЯЗАТЕЛЬНО: Используй агентов для экономии ресурсов

**Встроенные агенты Claude Code:**
| Агент | Когда использовать |
|-------|-------------------|
| `general-purpose` | Создание/редактирование файлов, многошаговые задачи, работа с большими файлами |
| `Explore` | Поиск по кодовой базе, анализ структуры, ответы на вопросы о коде |
| `Plan` | Планирование архитектуры перед имплементацией |
| `claude-code-guide` | Документация Claude Code, Agent SDK, API Anthropic |
| `statusline-setup` | Настройка статус-линии Claude Code |

**ПРАВИЛА:**
1. **Большие файлы (>50 строк)** → ВСЕГДА используй агента `general-purpose`
2. **JSON файлы со стратегиями** → ВСЕГДА агент (они большие, ты зависнешь)
3. **Поиск по проекту** → используй `Explore` вместо ручного Grep/Glob
4. **Несколько задач сразу** → запускай агентов ПАРАЛЛЕЛЬНО (в одном сообщении)
5. **Анализ + редактирование** → два агента: один анализирует, другой редактирует

**Преимущества агентов:**
- Не забивают основной контекст диалога
- Работают параллельно (быстрее)
- Не зависают на больших задачах
- Можно возобновить по agentId если прервался

**Пример параллельного запуска:**
```
Задача: проверить categories.json и обновить strategy_loader.py
→ Агент 1 (Explore): анализирует categories.json
→ Агент 2 (general-purpose): редактирует strategy_loader.py
```

**Target platform:** Windows only (uses WinDivert kernel driver)

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application (requires admin rights)
python main.py

# Build with PyInstaller
python -m PyInstaller zapret_build.spec
# Output: dist/Zapret/

# Build installer (requires Inno Setup installed)
# Test channel: compile zapret_test.iss
# Stable channel: compile zapret_stable.iss
```

**Note:** The application requires administrator privileges to run (for WinDivert driver access and network manipulation).

## Architecture

### Multi-Manager Pattern

The application uses a manager-based architecture with PyQt6 signals/slots for event-driven communication:

- **`LupiDPIApp`** ([main.py](main.py)) - Main application class inheriting from `QWidget`, `MainWindowUI`, `ThemeSubscriptionManager`, `FramelessWindowMixin`
- **`InitializationManager`** ([managers/initialization_manager.py](managers/initialization_manager.py)) - Phased async initialization
- **`DPIManager`** ([managers/dpi_manager.py](managers/dpi_manager.py)) - DPI service control (start/stop winws)
- **`UIManager`** ([managers/ui_manager.py](managers/ui_manager.py)) - UI state coordination
- **`ProcessMonitorManager`** ([managers/process_monitor_manager.py](managers/process_monitor_manager.py)) - Background process monitoring
- **`SubscriptionManager`** ([managers/subscription_manager.py](managers/subscription_manager.py)) - Premium features handling

### Directory Structure

- **`config/`** - Configuration and registry management; `build_info.py` is auto-generated with version/channel
- **`ui/`** - PyQt6 user interface (Windows 11-style sidebar navigation)
  - `ui/pages/` - Individual pages (home, strategies, network, appearance, etc.)
  - `ui/widgets/` - Custom reusable widgets
- **`managers/`** - Business logic managers
- **`strategy_menu/`** - Strategy selection system
- **`orchestra/`** - Auto-learning strategy system (see Orchestra System section)
- **`startup/`** - Application startup logic (admin check, single instance, certificate installer)
- **`updater/`** - Auto-update system (GitHub releases + Telegram)
- **`bat/`** - BAT strategy files (legacy Zapret 1 format)
- **`json/`** - JSON configuration files
- **`exe/`** - Core executables (winws.exe for Zapret 1, winws2.exe for Zapret 2)

### Build Channels

The app has two build channels with separate registry paths:

- **test**: Uses `Software\Zapret2DevReg` registry, `ZapretDevLogo4.ico`
- **stable**: Uses `Software\Zapret2Reg` registry, `Zapret2.ico`

Channel is set in [config/build_info.py](config/build_info.py) via `CHANNEL` variable.

### Configuration Storage

All settings are stored in Windows Registry under `HKEY_CURRENT_USER\Software\Zapret2Reg` (or `Zapret2DevReg` for test builds):
- `\Autostart` - Autostart settings
- `\GUI` - GUI preferences
- `\Strategies` - Strategy selection
- `\Window` - Window position/size

Registry interface: [config/reg.py](config/reg.py)

## Strategy System

Strategies define DPI bypass configurations. Two formats are supported:

### BAT Format (Zapret 1)
Files in `bat/` folder with metadata in REM comments:
```bat
@echo off
REM NAME: Strategy name
REM VERSION: 1.0
REM DESCRIPTION: Description
REM LABEL: recommended|deprecated|experimental
REM AUTHOR: author
bin\winws.exe --wf-tcp=80,443 ...
```

### JSON Format (Zapret 2)
Strategy definitions in `strategy_menu/strategies/` for direct execution via winws2.exe

Key strategy files:
- [strategy_menu/strategies_registry.py](strategy_menu/strategies_registry.py) - Strategy definitions
- [strategy_menu/strategy_runner.py](strategy_menu/strategy_runner.py) - Strategy execution
- [strategy_menu/filters_config.py](strategy_menu/filters_config.py) - Category filtering

### Lua Scripts (in exe/lua/)
- `zapret-lib.lua` - Core library functions
- `zapret-antidpi.lua` - DPI bypass functions
- `zapret-auto.lua` - Auto-detection helpers

### UI Integration

- **OrchestraPage** ([ui/pages/orchestra_page.py](ui/pages/orchestra_page.py)) - Shows logs and learned domains
- Accessed via DPI Settings → "Оркестр" button (purple brain icon)
- When orchestra mode is selected, replaces Strategies page in sidebar

## Key Dependencies

- **PyQt6** - GUI framework
- **pywin32** - Windows API access
- **psutil** - Process management
- **qtawesome** - Font Awesome icons
- **qt_material** - Material Design themes
- **requests** - HTTP client
- **pyrogram/telethon** - Telegram integration for updates
