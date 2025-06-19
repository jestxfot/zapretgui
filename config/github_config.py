# GitHub API конфигурация
# Токен для увеличения лимитов запросов к GitHub API (с 60 до 5000 в час)

# GitHub Classic Personal Access Token (жестко зафиксирован для стабильной работы)
# Scope: public_repo (доступ к публичным репозиториям)
GITHUB_API_TOKEN = "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"

def get_github_headers():
    """Возвращает стандартные заголовки для GitHub API с авторизацией"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {GITHUB_API_TOKEN}',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'close'
    }

def get_github_raw_headers():
    """Возвращает заголовки для скачивания raw файлов с GitHub"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/vnd.github.v3.raw',
        'Authorization': f'token {GITHUB_API_TOKEN}',
        'Cache-Control': 'no-cache',
        'Connection': 'close'
    }

def is_github_url(url):
    """Проверяет, является ли URL адресом GitHub"""
    return "github.com" in url.lower()

def test_github_token():
    """Тестирует работоспособность GitHub токена"""
    import requests
    try:
        headers = get_github_headers()
        response = requests.get('https://api.github.com/rate_limit', headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            limit = data['rate']['limit']
            remaining = data['rate']['remaining']
            return True, f"Токен работает! Лимит: {limit}, осталось: {remaining}"
        else:
            return False, f"Ошибка токена: {response.status_code}"
            
    except Exception as e:
        return False, f"Ошибка проверки: {str(e)}"
