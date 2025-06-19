"""
Конфигурация основных и резервных URL для загрузки стратегий
"""

# Основные URLs (GitFlic)
PRIMARY_JSON_URL = "https://raw.githubusercontent.com/youtubediscord/src/refs/heads/main/strag.json"

# Резервные URLs (GitHub)
BACKUP_JSON_URL = "https://raw.githubusercontent.com/youtubediscord/src/refs/heads/main/strag.json"

# Список всех доступных источников в порядке приоритета
URL_SOURCES = [
    {
        "name": "GitHub",
        "json_url": PRIMARY_JSON_URL,
        "raw_template": "https://raw.githubusercontent.com/youtubediscord/src/refs/heads/main/{0}"
    },
    {
        "name": "GitHub 2",
        "json_url": BACKUP_JSON_URL,
        "raw_template": "https://raw.githubusercontent.com/youtubediscord/src/refs/heads/main/{0}"
    }
]