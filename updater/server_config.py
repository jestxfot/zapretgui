"""
server_config.py
────────────────────────────────────────────────────────────────
Конфигурация серверов для балансировки нагрузки
ОБНОВЛЕНО: добавлен новый основной сервер 45.144.30.84
"""

# ═══════════════════════════════════════════════════════════════
# СПИСОК VPS СЕРВЕРОВ
# ═══════════════════════════════════════════════════════════════

VPS_SERVERS = [
    # ═══ НОВЫЙ ОСНОВНОЙ СЕРВЕР ═══
    {
        'id': 'vps0',
        'name': 'VPS Primary (Новый основной)',
        'host': '45.144.30.84',
        'https_port': 888,
        'http_port': 887,
        'priority': 1,  # ← Самый высокий приоритет
        'weight': 50,   # 50% трафика
    },
    {
        'id': 'vps1',
        'name': 'VPS Server 1',
        'host': '84.54.30.233',
        'https_port': 1094,
        'http_port': 1093,
        'priority': 2,  # ← Понижен
        'weight': 30,   # 30% трафика
    },
    {
        'id': 'vps2',
        'name': 'VPS Server 2 (Резервный)',
        'host': '185.68.247.42',
        'https_port': 888,
        'http_port': 887,
        'priority': 3,  # ← Понижен
        'weight': 20,   # 20% трафика
    },
]

# ═══════════════════════════════════════════════════════════════
# НАСТРОЙКИ БАЛАНСИРОВКИ
# ═══════════════════════════════════════════════════════════════

MAX_CONSECUTIVE_FAILURES = 3
SERVER_BLOCK_DURATION = 3600  # 1 час
FAST_RESPONSE_THRESHOLD = 2000  # 2 секунды
AUTO_SWITCH_TO_FASTER = True
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 15

# ═══════════════════════════════════════════════════════════════
# ОБРАТНАЯ СОВМЕСТИМОСТЬ
# ═══════════════════════════════════════════════════════════════

_primary_server = VPS_SERVERS[0] if VPS_SERVERS else None

if _primary_server:
    VPS_SERVER = _primary_server['host']
    HTTPS_PORT = _primary_server['https_port']
    HTTP_PORT = _primary_server['http_port']
    
    VPS_BASE_URLS = {
        'https': f"https://{VPS_SERVER}:{HTTPS_PORT}",
        'http': f"http://{VPS_SERVER}:{HTTP_PORT}"
    }
else:
    VPS_SERVER = None
    HTTPS_PORT = None
    HTTP_PORT = None
    VPS_BASE_URLS = {}

# ═══════════════════════════════════════════════════════════════
# НАСТРОЙКИ SSL
# ═══════════════════════════════════════════════════════════════

VERIFY_SSL = False

def should_verify_ssl() -> bool:
    return VERIFY_SSL

# ═══════════════════════════════════════════════════════════════
# GITHUB (резервный источник)
# ═══════════════════════════════════════════════════════════════

GITHUB_REPO = "youtubediscord/zapret"