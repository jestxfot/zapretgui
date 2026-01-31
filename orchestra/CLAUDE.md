# Orchestra Module - Circular Quality Auto-Learning DPI Bypass

Автоматическое обучение стратегий DPI bypass с использованием `circular_quality` оркестратора из zapret2.
Оркестратор отслеживает success rate каждой стратегии и автоматически лочит лучшую.

## Архитектура

### Компоненты

1. **orchestra_runner.py** - Главный Python runner
   - Запускает winws2.exe с circular-config.txt
   - Генерирует strategies-all.txt по пути C:\ProgramData\ZapretTwoDev\lua\strategies-all.txt с автонумерацией `:strategy=N`
   - Парсит подробные логи из `circular_quality` оркестратора
   - Сохраняет залоченные стратегии в Windows Registry
   - Генерирует learned-strategies.lua для предзагрузки
   - **SKIP_PASS фильтр**: блокирует сохранение strategy=1 для заблокированных доменов (YouTube, Discord, Google и др.)
   - Три точки фильтрации: загрузка из реестра, генерация lua, парсинг LOCK событий

2. **Lua файлы** (исходники в /home/privacy/zapret/lua/):
   - `zapret-lib.lua` - Базовые хелперы (deepcopy, blob, rawsend и т.д.)
   - `zapret-antidpi.lua` - DPI атаки (fake, multisplit, fakedsplit, syndata и т.д.)
   - `zapret-auto.lua` - Оркестраторы: circular, circular_quality, repeater
   - `combined-detector.lua` - Расширенная детекция: TLS Alert, HTTP status, block pages, strategy quality tracking
   - `strategy-stats.lua` - Preload wrapper, SKIP_PASS домены, is_strategy_blocked()
   - `domain-grouping.lua` - NLD-cut группировка поддоменов

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
Runner читает stdout winws2 и парсит события из `circular_quality` оркестратора:

**Основные паттерны (combined-detector.lua):**
- `strategy_quality: LOCK hostname -> strat=N` → сохраняет в реестр, UI callback
- `circular_quality: AUTO-UNLOCK hostname after N consecutive fails` → удаляет из реестра, UI callback
- `strategy_quality: hostname strat=N SUCCESS X/Y` → обновляет историю (X успехов из Y тестов)
- `strategy_quality: hostname strat=N FAIL X/Y` → обновляет историю
- `strategy_quality: RESET hostname` → сброс статистики хоста

**Legacy паттерны (для обратной совместимости):**
- `LOCKED hostname to strategy=N [TLS/HTTP/UDP]`
- `UNLOCKING hostname [TLS/HTTP/UDP]`

## Механизм LOCK/UNLOCK (combined-detector.lua)

### Параметры circular_quality
```lua
MIN_TESTS_FOR_LOCK = 3      -- Минимум тестов для LOCK
MIN_SUCCESS_RATE = 50       -- Минимальный success rate для LOCK (%)
UNLOCK_FAIL_COUNT = 3       -- Провалов подряд для AUTO-UNLOCK
```

### Strategy Quality Tracking
Для каждого hostname ведётся статистика:
```lua
strategy_quality_scores[hostkey] = {
    strategy_successes = {[strat_id] = count, ...},  -- Успехи по стратегиям
    strategy_tests = {[strat_id] = count, ...},      -- Всего тестов
    total_tests = N,                                  -- Общее число тестов
    locked_strategy = N or nil,                       -- Залоченная стратегия
    lock_reason = "quality" or nil                    -- Причина LOCK
}
```

### LOCK Flow
```
1. SUCCESS → strategy_successes[strat]++, strategy_tests[strat]++
2. После MIN_TESTS_FOR_LOCK тестов: вычисляется success rate
3. Если rate >= MIN_SUCCESS_RATE → LOCK лучшей стратегии
4. hrec.locked_strategy = best_id
5. Python сохраняет в реестр
```

### AUTO-UNLOCK Flow
```
1. LOCKED стратегия фейлится → hrec.locked_fail_count++
2. locked_fail_count >= UNLOCK_FAIL_COUNT → AUTO-UNLOCK
3. hrec.locked_strategy = nil, locked_fail_count = 0
4. Circular продолжает ротацию с учётом накопленной статистики
5. Python удаляет из реестра
```

### Выбор лучшей стратегии
При LOCK выбирается стратегия с максимальным success rate:
```lua
rate = (strategy_successes[strat] / strategy_tests[strat]) * 100
```
Стратегия должна иметь минимум MIN_TESTS_FOR_LOCK тестов и rate >= MIN_SUCCESS_RATE.

### Preload Wrapper (strategy-stats.lua)
При запуске устанавливается wrapper вокруг `circular` и `circular_quality`:
- Перехватывает первый пакет для каждого hostname
- Если есть preloaded стратегия - устанавливает `hrec.nstrategy` для старта с неё
- Использует `standard_hostkey()` для NLD-cut совместимости
- Проверяет `SKIP_PASS_DOMAINS` - домены которым нужен активный DPI bypass
- При UDP: поддерживает /16 subnet lookup для группировки IP

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
[18:21:59] ✓ SUCCESS: googlevideo.com strat=5 (3/5)
[18:22:01] 🔄 Strategy rotated to 2 (ntc.party)
[18:28:03] 🔒 LOCKED: ntc.party -> strat=6 (rate=75%)
[18:30:00] ⚡ RST detected - DPI block
[18:35:00] 🔓 AUTO-UNLOCK: ntc.party (3 fails)
[18:35:05] ✗ FAIL: ntc.party strat=6 (2/5)
[18:40:00] 🔄 RESET: youtube.com - статистика сброшена
```

**Формат SUCCESS/FAIL:** `hostname strat=N (X/Y)` где X - успехи, Y - всего тестов

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

## SKIP_PASS домены

### Проблема
Strategy=1 (pass/passthrough) - это "нулевая" стратегия без DPI bypass. Для некоторых заблокированных доменов (YouTube, Discord, Google) стратегия 1 может показывать SUCCESS из-за:
- Кешированных DNS ответов
- CDN edge серверов
- Временных "пробоев" блокировки

Если такой домен залочится на strategy=1, он перестанет работать.

### Решение: SKIP_PASS_DOMAINS
В `orchestra_runner.py` определён список доменов, для которых strategy=1 игнорируется:

```python
SKIP_PASS_DOMAINS = {
    # Discord
    "discord.com", "discordapp.com", "discord.gg", "discord.media", "discordapp.net",
    # YouTube / Google Video
    "youtube.com", "googlevideo.com", "ytimg.com", "youtu.be",
    # Google
    "google.com", "google.ru", "googleapis.com", "gstatic.com",
    # ... и другие заблокированные сервисы
}
```

### Где применяется SKIP_PASS фильтр

**1. При загрузке из реестра (`load_strategies`):**
```python
# Автоматически удаляет skip_pass домены со strategy=1 из памяти и реестра
for domain, strategy in list(self.locked_strategies.items()):
    if strategy == 1 and is_skip_pass_domain(domain):
        del self.locked_strategies[domain]
        reg_delete_value(REGISTRY_ORCHESTRA_TLS, domain)
```

**2. При генерации learned-strategies.lua (`_generate_learned_lua`):**

**A) Для залоченных skip_pass доменов со strategy=1 - подмена на лучшую из истории:**
```python
if strategy == 1 and is_skip_pass_domain(hostname):
    best_alt = self._get_best_strategy_from_history(hostname, exclude_strategy=1)
    if best_alt:
        strategy = best_alt  # Подменяем на лучшую из истории
    else:
        strategy = 2  # Или на strategy=2 если нет истории
```

**B) Для skip_pass доменов из истории, которые НЕ залочены - preload с лучшей стратегией:**
```python
for hostname in self.strategy_history.keys():
    if hostname in self.locked_strategies:
        continue  # Уже обработан
    if not is_skip_pass_domain(hostname):
        continue
    best_strat = self._get_best_strategy_from_history(hostname, exclude_strategy=1)
    if best_strat:
        f.write(f'strategy_preload("{hostname}", {best_strat}, "tls")\n')
```

**C) Фильтрация strategy=1 из history:**
```python
if strat_num == 1 and is_skip_pass_domain(hostname):
    continue  # Не preload'им "успешную" историю strategy=1
```

**3. При получении LOCK от Lua (парсинг логов) - ДВА МЕСТА:**

Есть два независимых пути, по которым домен может залочиться:

**A) Явное сообщение LOCK от circular_quality (~line 1260):**
Lua отправляет `strategy_quality: LOCK hostname -> strat=N` когда достигнут порог success rate.
```python
# Парсинг паттерна lock_pattern или legacy_lock_pattern
match = lock_pattern.search(line)  # strategy_quality: LOCK hostname -> strat=N
if match:
    host = match.group(1)
    strat = int(match.group(2))
    # ... определение протокола, nld_cut ...

    # SKIP_PASS фильтр
    if strat == 1 and is_skip_pass_domain(host):
        # Игнорируем, не сохраняем в реестр
        continue

    # Сохранение в реестр
    target_dict[host] = strat
```

**B) При накоплении SUCCESS'ов в Python (~line 1486):**
Python сам считает SUCCESS'ы и лочит после порога (3 для TCP, 1 для UDP).
Это ВТОРОЙ путь, который работает параллельно с Lua circular_quality.
```python
# Парсинг std_success_pattern или automate_success_pattern
if std_success_pattern.search(line):  # standard_success_detector:.*successful
    # Инкремент счётчика успехов
    self._success_counts[host_key] = self._success_counts.get(host_key, 0) + 1

    # Проверка порога (3 для TCP, 1 для UDP)
    lock_threshold = 1 if is_udp else 3
    if self._success_counts[host_key] >= lock_threshold:
        # SKIP_PASS фильтр - БЕЗ НЕГО googlevideo.com лочился на strategy=1!
        if current_strat == 1 and is_skip_pass_domain(lock_host):
            # Не лочим, продолжаем обучение
            pass
        else:
            # Сохранение в реестр
            target_dict[lock_host] = current_strat
```

**ВАЖНО:** Оба пути должны иметь SKIP_PASS фильтр! Раньше фильтр был только в (A),
и googlevideo.com лочился через путь (B) при накоплении 3 SUCCESS'ов для strategy=1.

### Функция проверки
```python
def is_skip_pass_domain(hostname: str) -> bool:
    hostname = hostname.lower().strip()
    # Точное совпадение
    if hostname in SKIP_PASS_DOMAINS:
        return True
    # Проверка субдоменов (cdn.discord.com -> discord.com)
    for domain in SKIP_PASS_DOMAINS:
        if hostname.endswith("." + domain):
            return True
    return False
```

### Логи
При срабатывании skip_pass фильтра выводятся сообщения:
```
[INFO] SKIP_PASS: очищено N доменов со strategy=1: googlevideo.com...
[INFO] SKIP_PASS: пропущено N записей истории для strategy=1
[INFO] ⚠️ SKIP_PASS: googlevideo.com заблокирован strategy=1, игнорируем
```

### Добавление новых доменов
Если домен заблокирован, но лочится на strategy=1, добавьте его в `SKIP_PASS_DOMAINS` в `orchestra_runner.py`.

## Troubleshooting

### Стратегия перестала работать после LOCK
Система автоматически UNLOCK после 2 провалов и начнёт переобучение.

### Ручной сброс
Кнопка "Сбросить обучение" в UI или `runner.clear_learned_data()`.

### Домен не группируется с поддоменами
Проверьте что NLD-cut работает корректно. Multi-part TLD (.co.uk, .com.ru) обрабатываются отдельно.

### Skip_pass домен всё равно лочится на strategy=1
1. Убедитесь что домен (после NLD-cut) есть в `SKIP_PASS_DOMAINS`
2. Проверьте что код запущен из Python (не из скомпилированного exe)
3. Посмотрите логи - должны быть `[SKIP_PASS]` сообщения
4. Удалите вручную из реестра: `reg delete "HKCU\Software\Zapret2DevReg\Orchestra\TLS" /v "domain.com" /f`

### Домен не появляется в логах (игнорируется)

**ВАЖНО:** Оркестратор видит только **НОВЫЕ TLS/TCP соединения**!

**НОВОЕ:** Теперь оркестратор кэширует связки IP → hostname и может обрабатывать Keep-Alive соединения!

#### Механизм кэширования IP → hostname:

Оркестратор теперь **автоматически кэширует** связки IP → hostname из `desync profile search`:
```
1. Первый пакет: desync profile search ... ip=142.250.74.206 hostname='youtube.com'
   → Сохраняем: 142.250.74.206 → youtube.com

2. Второй пакет (Keep-Alive): dpi desync src=142.250.74.206 ...
   → НЕТ hostname, но есть IP → восстанавливаем youtube.com из кэша
   → SUCCESS/RST события теперь правильно привязываются к домену!
```

**Преимущества:**
- ✅ Keep-Alive соединения теперь учитываются
- ✅ HTTP/2 мультиплексирование обрабатывается корректно
- ✅ Автоматическая очистка (макс 1000 записей)

**Ограничения:**
- ⚠️ На одном IP может быть несколько хостов (CDN) → используется последний известный
- ⚠️ Кэш сбрасывается при перезапуске оркестратора

#### Причины невидимости (устарело для новых версий):

1. **HTTP Keep-Alive** ✅ ИСПРАВЛЕНО кэшированием
   - Браузер переиспользует существующее TCP соединение
   - Нет нового TLS handshake → winws2 не видит SNI
   - **Теперь:** оркестратор восстанавливает hostname из кэша по IP
   - Пример: открыли youtube.com → смотрите 10 видео → только 1 TLS handshake, но все SUCCESS привязываются к youtube.com
   
2. **Кэш браузера**
   - Страница загружается из локального кэша
   - Вообще нет сетевых запросов
   
3. **HTTP/2 или HTTP/3 мультиплексирование**
   - 1 TCP соединение = сотни запросов
   - Оркестратор видит только первый handshake
   
4. **Соединение установлено ДО запуска оркестратора**
   - Браузер уже подключён к сайту
   - winws2 не может перехватить существующие соединения
   
5. **Discord/Voice - прямые IP**
   - Голосовые серверы используют UDP без SNI
   - Оркестратор видит только IP адрес (не домен)
   - IP может меняться → каждый раз новый /16 subnet в логах

#### Решения:

✅ **Для тестирования:**
```
1. Закройте ВСЕ окна браузера (или перезапустите браузер)
2. Очистите кэш (Ctrl+Shift+Del)
3. Откройте приватное окно (Ctrl+Shift+N)
4. Принудительная перезагрузка (Ctrl+F5)
5. Проверьте логи сразу после открытия сайта
```

✅ **Для Discord:**
```
1. Перезапустите Discord приложение
2. Переподключитесь к голосовому каналу
3. В логах ищите IP адреса (не домены):
   LUA: strategy-stats: APPLIED 66.22.x.x = strategy 15
```

✅ **Диагностика:**
- Если в логах вообще нет активности → проблема с WinDivert драйвером
- Если есть `PRELOADED: youtube.com` но нет новых событий → домен использует старое соединение (это нормально)
- Если видите `www.youtube.com` вместо `youtube.com` → NLD-cut сработал, проверьте историю для `youtube.com`

#### Проверка что оркестратор работает:

```powershell
# 1. Откройте НОВЫЙ сайт (который точно не в кэше)
https://httpbin.org/delay/5

# 2. В логах должно появиться:
LUA: strategy-stats: APPLIED httpbin.org = strategy X
```

## Документация Zapret 2
F:\doc\zapret2
