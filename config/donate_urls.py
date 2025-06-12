"""
Конфигурация URL для проверки подписки
"""

# Основной URL (GitFlic)
PRIMARY_DONATE_URL = "https://gitflic.ru/project/megacompacy/test/blob/raw?file=donate.json"

# Резервные URLs
BACKUP_DONATE_URL = "https://raw.githubusercontent.com/youtubediscord/zapret/refs/heads/main/donate.json"

# Список всех доступных источников в порядке приоритета
DONATE_URL_SOURCES = [
    {
        "name": "GitFlic",
        "url": PRIMARY_DONATE_URL
    },
    {
        "name": "GitHub Mirror", 
        "url": BACKUP_DONATE_URL
    }
]