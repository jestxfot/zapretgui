"""
Конфигурация основных и резервных URL для загрузки стратегий
"""

PRIMARY_JSON_URL = "https://nozapret.ru/index.json"
BACKUP_JSON_URL = "https://nozapret.ru/index.json"

# Список всех доступных источников в порядке приоритета
URL_SOURCES = [
    {
        "name": "nozapret.ru",
        "json_url": PRIMARY_JSON_URL,
        "raw_template": "https://nozapret.ru/{0}"
    },
    {
        "name": "GitHub 2",
        "json_url": BACKUP_JSON_URL,
        "raw_template": "https://nozapret.ru/{0}"
    }
]