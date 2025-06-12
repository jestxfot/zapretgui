"""
Конфигурация основных и резервных URL для загрузки стратегий
"""

# Основные URLs (GitFlic)
PRIMARY_BASE_URL = "https://gitflic.ru/project/main1234/main1234/blob/raw?file="
PRIMARY_JSON_URL = "https://gitflic.ru/project/main1234/main1234/blob/raw?file=index.json"

# Резервные URLs (GitHub)
BACKUP_BASE_URL = "https://raw.githubusercontent.com/youtubediscord/zapret/refs/heads/main/"
BACKUP_JSON_URL = "https://raw.githubusercontent.com/youtubediscord/zapret/refs/heads/main/index.json"

# Список всех доступных источников в порядке приоритета
URL_SOURCES = [
    {
        "name": "GitFlic",
        "base_url": PRIMARY_BASE_URL,
        "json_url": PRIMARY_JSON_URL,
        "raw_template": "https://gitflic.ru/project/main1234/main1234/blob/raw?file={}"
    },
    {
        "name": "GitHub Backup",
        "base_url": BACKUP_BASE_URL,
        "json_url": BACKUP_JSON_URL,
        "raw_template": "https://raw.githubusercontent.com/youtubediscord/zapret/refs/heads/main/{}"
    }
]