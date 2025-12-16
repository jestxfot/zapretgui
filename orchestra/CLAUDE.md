# Orchestra Module - Circular Auto-Learning DPI Bypass

Автоматическое обучение стратегий DPI bypass с использованием `circular` оркестратора из zapret2.

## Архитектура

### Компоненты

1. **orchestra_runner.py** - Главный Python runner
   - Запускает winws2.exe с H:\Privacy\zapret\lua\circular-config.txt
   - Генерирует strategies-all.txt, strategies-http-all.txt, strategies-udp-all.txt с автонумерацией
   - Сохраняет залоченные стратегии в Windows Registry
   - Генерирует learned-strategies.lua для предзагрузки
   - Парсит логи winws2 и обновляет UI через callbacks

2. **Lua файлы** (в `lua/` папке, исходники в H:\Privacy\zapret\lua\):
   - `zapret-lib.lua` - Базовые хелперы
   - `zapret-antidpi.lua` - DPI атаки (fake, multisplit, fakedsplit и т.д.)
   - `zapret-auto.lua` - Circular оркестратор
   - `combined-detector.lua` - Детекция успеха/провала
   - `strategy-stats.lua` - Механизм LOCK/UNLOCK + HISTORY + preload wrapper
   - `silent-drop-detector.lua` - Детекция silent drop

3. **Конфиги** (генерируются автоматически):
   - `circular-config.txt` - Главный конфиг winws2
   - `strategies-all.txt` - Список TLS стратегий (генерируется)
   - `strategies-http-all.txt` - Список HTTP стратегий (генерируется)
   - `strategies-udp-all.txt` - Список UDP стратегий для QUIC, Discord Voice, Games (генерируется)
   - `learned-strategies.lua` - Предзагрузка стратегий из реестра (генерируется)
   - `whitelist.txt` - Список доменов для обхода

## Хранение данных

### Windows Registry
Все данные хранятся в реестре под `HKEY_CURRENT_USER\Software\Zapret2Reg\Orchestra`:
- `TLS` - Залоченные TLS стратегии (hostname=strategy_num)
- `HTTP` - Залоченные HTTP стратегии
- `UDP` - Залоченные UDP стратегии (IP=strategy_num)
- `History` - История успехов/провалов для каждой стратегии

### NLD-cut (N-Level Domain)
Все hostname'ы нормализуются до 2-го уровня домена:
- `static.xx.fbcdn.net` → `fbcdn.net`
- `www.bbc.co.uk` → `bbc.co.uk` (учитываются multi-part TLD)

Это позволяет группировать поддомены и применять одну стратегию ко всем.

## Процесс запуска

### 1. Подготовка (prepare())
```
1. Загрузка стратегий из реестра в память
2. Генерация strategies-all.txt с автонумерацией strategy=1,2,3...
3. Генерация whitelist.txt
4. Ротация старых логов (MAX_ORCHESTRA_LOGS = 10)
```

### 2. Запуск (start())
```
1. Генерация learned-strategies.lua с предзагрузкой:
   - strategy_preload(hostname, strategy, "tls"/"http")
   - strategy_preload_history(hostname, strategy, successes, failures)
   - install_circular_wrapper() - устанавливает wrapper для применения preload

2. Запуск winws2.exe:
   winws2.exe @circular-config.txt --lua-init=@learned-strategies.lua

3. Запуск потока парсинга логов (_log_reader_thread)
```

### 3. Парсинг логов
Runner читает stdout winws2 и парсит события:
- `LOCKED hostname strategy [TLS/HTTP/UDP]` → сохраняет в реестр, UI callback
- `UNLOCKING hostname [TLS/HTTP/UDP]` → удаляет из реестра, UI callback
- `SUCCESS hostname strategy [TLS/HTTP/UDP]` → обновляет историю
- `FAIL hostname strategy [TLS/HTTP/UDP]` → обновляет историю
- `HISTORY hostname strategy=N successes=X failures=Y` → обновляет историю
- `circular: rotate strategy to N` → UI callback с текущим hostname

## Механизм LOCK/UNLOCK (strategy-stats.lua)

### Параметры
```lua
LOCK_THRESHOLD = 5   -- Залочить после 5 успехов (было 3)
UNLOCK_THRESHOLD = 2 -- Разлочить после 2 провалов
```

### STICKY механизм
При ПЕРВОМ успехе стратегия становится "sticky":
- Устанавливается `hrec.final` чтобы circular не переключался
- Если sticky стратегия фейлится - final очищается, circular продолжает

### LOCK Flow
```
1. SUCCESS → count++, sticky на первом успехе
2. count >= 5 → LOCK
3. hrec.final = strategy (circular останавливается)
4. Python сохраняет в реестр
```

### UNLOCK Flow
```
1. LOCKED стратегия фейлится → fail_count++
2. fail_count >= 2 → UNLOCK
3. hrec.final = nil (circular возобновляется)
4. Выбирается лучшая стратегия из HISTORY (если есть с rate >= 50%)
5. Python удаляет из реестра
```

### HISTORY
Для каждого hostname хранится статистика по всем испробованным стратегиям:
```lua
strategy_history[hostname][strategy] = {successes=N, failures=N}
```
При UNLOCK система выбирает стратегию с лучшим success rate.

### Preload Wrapper (circular_with_preload)
При запуске устанавливается wrapper вокруг функции `circular`:
- Перехватывает первый пакет для каждого hostname
- Если есть preloaded стратегия - применяет её до начала ротации
- Использует `standard_hostkey()` для NLD-cut совместимости

## UI состояния (OrchestraPage)

| Состояние | Триггер | Цвет |
|-----------|---------|------|
| IDLE | Нет активности | Серый |
| LEARNING | RST detected, rotated, первый SUCCESS/FAIL | Оранжевый |
| RUNNING | PRELOADED, LOCKED | Зелёный |
| UNLOCKED | UNLOCKING | Красный |

## API

```python
from orchestra.orchestra_runner import OrchestraRunner

runner = OrchestraRunner()

# Callbacks
runner.set_output_callback(lambda msg: print(msg))
runner.set_lock_callback(lambda host, strat: print(f"LOCKED: {host}={strat}"))
runner.set_unlock_callback(lambda host: print(f"UNLOCKED: {host}"))

# Debug файл (по умолчанию удаляется после остановки)
runner.set_keep_debug_file(True)

# Запуск
if runner.prepare():
    runner.start()

# Получить данные
data = runner.get_learned_data()
# {'tls': {'youtube.com': [1], ...}, 'http': {...}, 'udp': {'142.250.x.x': [3], ...}, 'history': {...}}

# Остановка
runner.stop()

# Сброс обучения (очищает реестр)
runner.clear_learned_data()
```

## Форматы сообщений в UI

```
[18:21:27] PRELOADED: google.com = strategy 7 [http]
[18:21:59] ✓ SUCCESS: google.com strategy=1
[18:22:01] 🔄 Strategy rotated to 2 (ntc.party)
[18:28:03] 🔒 LOCKED: ntc.party :443 = strategy 6
[18:30:00] ⚡ RST detected - DPI block
[18:35:00] 🔓 UNLOCKED: ntc.party :443 - re-learning...
[18:35:05] ✗ FAIL: ntc.party :443 strategy=6
```

## Параметры детекции

### TLS Profile (port 443)
| Параметр | Значение | Описание |
|----------|----------|----------|
| success_bytes | 0x800 (2KB) | Байт для подтверждения успеха |
| tcp_out | 6 | Исходящих пакетов для silent drop |
| tcp_in | 1 | Входящих пакетов для silent drop |
| rst | 1 | Порог RST sequence |

### HTTP Profile (port 80)
| Параметр | Значение | Описание |
|----------|----------|----------|
| success_bytes | 0x100 (256B) | Ниже для 301/302 редиректов |
| tcp_out | 4 | Быстрее детектит silent drop |
| tcp_in | 1 | Входящих пакетов для silent drop |
| rst | 1 | Порог RST sequence |

### UDP Profile (ports 443-65535)
| Параметр | Значение | Описание |
|----------|----------|----------|
| udp_out | 4 | Исходящих UDP пакетов |
| udp_in | 1 | Входящих UDP пакетов для silent drop |
| nld | 2 | NLD-cut не применяется (используется IP) |

Используется для:
- QUIC (YouTube, Google, Cloudflare)
- Discord Voice
- Online Games (Steam, etc.)

## Troubleshooting

### Стратегия перестала работать после LOCK
Система автоматически UNLOCK после 2 провалов и начнёт переобучение.

### Ручной сброс
Кнопка "Сбросить обучение" в UI или `runner.clear_learned_data()`.

### Домен не группируется с поддоменами
Проверьте что NLD-cut работает корректно. Multi-part TLD (.co.uk, .com.ru) обрабатываются отдельно.

## Документация Zapret 2
F:\doc\zapret2
