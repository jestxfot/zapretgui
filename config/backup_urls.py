"""
Конфигурация основных и резервных URL для загрузки стратегий
"""

PRIMARY_JSON_URL = "https://zapretdpi.ru/index.json"
BACKUP_JSON_URL = "https://zapretdpi.ru/index.json"

# Список всех доступных источников в порядке приоритета
URL_SOURCES = [
    {
        "name": "ZapretDPI.ru",
        "json_url": PRIMARY_JSON_URL,
        "raw_template": "https://zapretdpi.ru/{0}"
    },
    {
        "name": "GitHub 2",
        "json_url": BACKUP_JSON_URL,
        "raw_template": "https://zapretdpi.ru/{0}"
    }
]