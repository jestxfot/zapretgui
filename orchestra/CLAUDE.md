# Orchestra Module - Circular Auto-Learning DPI Bypass

This module implements automatic DPI bypass strategy learning using the `circular` orchestrator from zapret2.

## Architecture Overview

### Core Components

1. **orchestra_runner.py** - Main Python runner
   - Starts winws2.exe with circular-config.txt
   - Monitors logs/winws2_orchestra.log for LOCKED/UNLOCKING events
   - Saves learned strategies to best-strategies.txt
   - Provides callbacks for UI updates

2. **Lua Files** (in `lua/` folder):
   - `zapret-lib.lua` - Core helpers
   - `zapret-antidpi.lua` - DPI attack strategies (fake, multisplit, fakedsplit, etc.)
   - `zapret-auto.lua` - Circular orchestrator
   - `combined-detector.lua` - Failure/success detection
   - `strategy-stats.lua` - LOCK/UNLOCK mechanism
   - `domain-grouping.lua` - Subdomain grouping
   - `silent-drop-detector.lua` - Silent drop detection

3. **Config Files**:
   - `circular-config.txt` - Main winws2 configuration
   - `strategies-all.txt` - List of all DPI bypass strategies
   - `blobs.txt` - Binary blob definitions
   - `best-strategies.txt` - Learned strategies (auto-generated)

## How It Works

### Detection Mechanism (combined-detector.lua)
Его исходный код хранится здесь H:\Privacy\zapret\lua\combined-detector.lua (как и все луа файлы, при сборке попадают в корень приложения в папку lua)

Документация по Zapret 2 находится здесь F:\doc\zapret2

The system detects three types of events:

1. **SUCCESS** - Connection received >= 2KB of data
   - Records success in strategy-stats
   - After 3 successes on same strategy → LOCK

2. **Silent Drop** - DPI drops packets without RST
   - Detected when: out_packets >= 4 AND in_packets <= 1
   - Triggers strategy rotation

3. **RST Injection** - DPI sends fake RST
   - Detected when: RST packet at sequence <= 1
   - Triggers strategy rotation

### LOCK/UNLOCK Mechanism (strategy-stats.lua)

```
LOCK_THRESHOLD = 3   -- Lock after 3 successes
UNLOCK_THRESHOLD = 2 -- Unlock after 2 failures
```

**LOCK Flow:**
1. Strategy works → SUCCESS recorded
2. Same strategy works again → count++
3. count >= 3 → LOCK (sets circular `final`)
4. Circular stops rotating for this domain

**UNLOCK Flow:**
1. LOCKED strategy fails → fail_count++
2. fail_count >= 2 → UNLOCK
3. Clears circular `final`
4. Circular resumes rotation

### Domain Grouping (domain-grouping.lua)

Subdomains are grouped under base domain:
- `rr5---sn-xxx.googlevideo.com` → `googlevideo.com`
- `www.youtube.com` → `youtube.com`
- `i.ytimg.com` → `ytimg.com`

This allows finding one strategy for entire service.

### strategies-all.txt
```
--lua-desync=pass:strategy=1
--lua-desync=fake:strategy=2:blob=tls5:ip_ttl=3
--lua-desync=multisplit:strategy=3:seqovl=500:seqovl_pattern=tls7
...
```

## API Usage

```python
from orchestra.orchestra_runner import OrchestraRunner

# Create runner
runner = OrchestraRunner()

# Set callbacks
runner.set_output_callback(lambda msg: print(msg))
runner.set_lock_callback(lambda host, strat: print(f"LOCKED: {host}={strat}"))
runner.set_unlock_callback(lambda host: print(f"UNLOCKED: {host}"))

# Сохранять debug файл после остановки (для отладки, по умолчанию удаляется)
runner.set_keep_debug_file(True)

# Start
if runner.prepare():
    runner.start()

# Get learned data
data = runner.get_learned_data()
# Returns: {'tls': {'googlevideo.com': [61], ...}, 'http': {}}

# Stop
runner.stop()

# Clear learning
runner.clear_learned_data()
```

## Troubleshooting

### Strategy stops working after LOCK
The system will automatically UNLOCK after 2 failures and start re-learning.

### Manual reset
Delete `lua/best-strategies.txt` and restart winws2.

### Check logs
Включите чекбокс "Сохранять сырой debug файл" и после остановки смотрите `logs/winws2_orchestra.log`:
- `LOCKED hostname to strategy=N` - Strategy found
- `UNLOCKING hostname` - Re-learning started
- `SUCCESS hostname strategy=N` - Strategy working
- `FAIL hostname strategy=N` - Strategy failed

Обработанные логи Python (LOCKED/UNLOCKED) всегда отображаются в UI независимо от чекбокса.

## Key Parameters

### TLS Profile (port 443)
| Parameter | Value | Description |
|-----------|-------|-------------|
| success_bytes | 0x800 (2KB) | Bytes to confirm success |
| tcp_out | 6 | Out packets for silent drop |
| tcp_in | 1 | In packets for silent drop |
| rst | 1 | RST sequence threshold |

### HTTP Profile (port 80)
| Parameter | Value | Description |
|-----------|-------|-------------|
| success_bytes | 0x100 (256B) | Lower threshold for 301/302 redirects |
| tcp_out | 4 | Faster silent drop detection |
| tcp_in | 1 | In packets for silent drop |
| rst | 1 | RST sequence threshold |

### Common
| Parameter | Value | Description |
|-----------|-------|-------------|
| LOCK_THRESHOLD | 3 | Successes to lock |
| UNLOCK_THRESHOLD | 2 | Failures to unlock |
