"""
release_manager.py
────────────────────────────────────────────────────────────────
Менеджер получения релизов с поддержкой fallback на собственный сервер.
При любых ошибках GitHub (403, rate limit и др.) автоматически 
переключается на запасной HTTP/HTTPS сервер.

С умной приоритизацией источников на основе истории успешных запросов.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import requests
import os
import json
import time
import urllib3
from urllib.parse import urljoin
from datetime import datetime

from .github_release import get_latest_release as github_get_latest_release
from .github_release import normalize_version, is_rate_limited
from log import log
from config import CHANNEL

# Отключаем предупреждения о самоподписанных сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Файл для сохранения статистики серверов
STATS_FILE = os.path.join(os.path.dirname(__file__), '.server_stats.json')

def get_fallback_servers():
    """Получает список fallback серверов из переменных окружения или использует дефолтные"""
    servers = []
    
    # Читаем из переменных окружения ZAPRET_FALLBACK_SERVER_1, ZAPRET_FALLBACK_SERVER_2, etc.
    for i in range(1, 10):  # До 9 серверов
        server_url = os.getenv(f"ZAPRET_FALLBACK_SERVER_{i}")
        if server_url:
            servers.append({
                "url": server_url.rstrip('/'),
                "verify_ssl": not server_url.startswith("https://127.0.0.1") and not server_url.startswith("https://localhost"),
                "priority": i,
                "name": f"Fallback Server {i}"
            })
    
    # Если переменных окружения нет, используем дефолтные локальные серверы
    if not servers:
        # Основной HTTPS сервер
        if os.getenv("ZAPRET_HTTPS_SERVER"):
            servers.append({
                "url": os.getenv("ZAPRET_HTTPS_SERVER").rstrip('/'),
                "verify_ssl": False,
                "priority": 1,
                "name": "Custom HTTPS Server"
            })
        else:
            servers.append({
                "url": "https://88.210.21.236:888",
                "verify_ssl": False,
                "priority": 1,
                "name": "Private Server"  
            })
        
        # Резервный HTTP сервер
        if os.getenv("ZAPRET_HTTP_SERVER"):
            servers.append({
                "url": os.getenv("ZAPRET_HTTP_SERVER").rstrip('/'),
                "verify_ssl": True,
                "priority": 2,
                "name": "Custom HTTP Server"
            })
        else:
            servers.append({
                "url": "http://88.210.21.236:887",
                "verify_ssl": True,
                "priority": 2,
                "name": "Private HTTP Server"
            })
    
    return servers

# Таймаут для запросов
TIMEOUT = 10

class ServerStats:
    """Класс для хранения статистики серверов"""
    
    def __init__(self):
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict[str, Dict[str, Any]]:
        """Загружает статистику из файла"""
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_stats(self):
        """Сохраняет статистику в файл"""
        try:
            with open(STATS_FILE, 'w') as f:
                json.dump(self.stats, f)
        except:
            pass
    
    def record_success(self, server_name: str, response_time: float):
        """Записывает успешный запрос"""
        if server_name not in self.stats:
            self.stats[server_name] = {
                'successes': 0,
                'failures': 0,
                'avg_response_time': 0,
                'last_success': None,
                'last_failure': None
            }
        
        stats = self.stats[server_name]
        stats['successes'] += 1
        stats['last_success'] = time.time()
        
        # Обновляем среднее время ответа
        if stats['avg_response_time'] == 0:
            stats['avg_response_time'] = response_time
        else:
            stats['avg_response_time'] = (stats['avg_response_time'] + response_time) / 2
        
        self._save_stats()
    
    def record_failure(self, server_name: str):
        """Записывает неудачный запрос"""
        if server_name not in self.stats:
            self.stats[server_name] = {
                'successes': 0,
                'failures': 0,
                'avg_response_time': 0,
                'last_success': None,
                'last_failure': None
            }
        
        self.stats[server_name]['failures'] += 1
        self.stats[server_name]['last_failure'] = time.time()
        self._save_stats()
    
    def get_success_rate(self, server_name: str) -> float:
        """Возвращает процент успешных запросов"""
        if server_name not in self.stats:
            return 0.5  # По умолчанию 50%
        
        stats = self.stats[server_name]
        total = stats['successes'] + stats['failures']
        if total == 0:
            return 0.5
        
        return stats['successes'] / total

class ReleaseManager:
    """Менеджер для получения информации о релизах с поддержкой fallback"""
    
    def __init__(self):
        self.last_error: Optional[str] = None
        self.last_source: Optional[str] = None
        self.fallback_servers = get_fallback_servers()
        self.server_stats = ServerStats()
        
    def get_latest_release(self, channel: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о последнем релизе.
        Умная приоритизация источников на основе истории и текущего состояния.
        
        Args:
            channel: "stable" или "dev"
            
        Returns:
            Dict с информацией о релизе или None
        """
        # Определяем порядок источников на основе текущего состояния
        sources = self._get_prioritized_sources()
        
        for source in sources:
            log(f"🔍 Проверка обновлений через {source['name']}...", "🔄 RELEASE")
            
            start_time = time.time()
            
            if source['type'] == 'github':
                result = self._try_github(channel)
            else:
                result = self._try_fallback_server(source, channel)
            
            response_time = time.time() - start_time
            
            if result:
                self.last_source = source['name']
                self.last_error = None
                self.server_stats.record_success(source['name'], response_time)
                log(f"✅ {source['name']}: найден релиз {result['version']} (время: {response_time:.2f}с)", "🔄 RELEASE")
                return result
            else:
                self.server_stats.record_failure(source['name'])
                log(f"⚠️ {source['name']} недоступен: {self.last_error}", "🔄 RELEASE")
        
        # Ничего не сработало
        log(f"❌ Не удалось получить информацию о релизах ни из одного источника", "🔄 RELEASE")
        return None
    
    def _get_prioritized_sources(self) -> List[Dict[str, Any]]:
        """Возвращает список источников в порядке приоритета"""
        sources = []
        
        # Проверяем состояние GitHub rate limit
        is_limited, reset_dt = is_rate_limited()
        
        if not is_limited:
            # GitHub доступен
            sources.append({
                'name': 'GitHub',
                'type': 'github',
                'priority': 0
            })
        else:
            log(f"⏳ GitHub rate limit до {reset_dt}, пропускаем", "🔄 RELEASE")
        
        # Добавляем fallback серверы
        for server in self.fallback_servers:
            sources.append({
                'name': server['name'],
                'type': 'fallback',
                'priority': server['priority'],
                'url': server['url'],
                'verify_ssl': server['verify_ssl']
            })
        
        # Сортируем по приоритету и успешности
        def sort_key(source):
            # Базовый приоритет
            base_priority = source['priority']
            
            # Модификатор на основе статистики
            success_rate = self.server_stats.get_success_rate(source['name'])
            stats = self.server_stats.stats.get(source['name'], {})
            
            # Если сервер недавно был успешен, повышаем приоритет
            if stats.get('last_success'):
                time_since_success = time.time() - stats['last_success']
                if time_since_success < 300:  # Менее 5 минут назад
                    base_priority -= 1
            
            # Учитываем процент успешности
            base_priority -= success_rate * 2
            
            return base_priority
        
        sources.sort(key=sort_key)
        
        return sources
        
    def _try_github(self, channel: str) -> Optional[Dict[str, Any]]:
        """Пытается получить релиз с GitHub"""
        try:
            result = github_get_latest_release(channel)
            if result:
                log(f"✅ GitHub: найден релиз {result['version']}", "🔄 RELEASE")
            return result
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 403:
                self.last_error = "GitHub API rate limit (403)"
            else:
                self.last_error = f"HTTP error: {e}"
        except requests.exceptions.Timeout:
            self.last_error = "GitHub timeout"
        except requests.exceptions.ConnectionError:
            self.last_error = "GitHub connection error"
        except Exception as e:
            self.last_error = f"GitHub error: {str(e)}"
            
        return None

    def _try_fallback_server(self, server: Dict[str, Any], channel: str) -> Optional[Dict[str, Any]]:
        """Пытается получить релиз с fallback сервера"""
        try:
            # Определяем endpoint в зависимости от канала
            api_channel = "test" if channel == "dev" else channel
            endpoint = f"/api/version/{api_channel}"
            url = urljoin(server["url"], endpoint)
            
            # Настройки SSL
            verify = server["verify_ssl"]
            
            # Делаем запрос
            response = requests.get(
                url,
                timeout=TIMEOUT,
                verify=verify,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Проверяем наличие файла
            if not data.get("file") or not data["file"].get("exists"):
                log(f"⚠️ {server['name']}: файл не найден на сервере", "🔄 RELEASE")
                return None
                
            # Формируем URL для скачивания
            download_channel = "test" if channel == "dev" else channel
            download_url = urljoin(server["url"], f"/download/{download_channel}")
            
            # Добавляем API ключ если есть
            api_key = os.getenv("ZAPRET_SERVER_API_KEY")
            if api_key:
                download_url += f"?api_key={api_key}"
            
            # Преобразуем в формат, совместимый с github_release
            result = {
                "version": normalize_version(data.get("version", "0.0.0")),
                "tag_name": data.get("tag", f"v{data.get('version', '0.0.0')}"),
                "update_url": download_url,
                "release_notes": data.get("release_notes", ""),
                "prerelease": channel == "dev",
                "name": data.get("name", f"Zapret {channel}"),
                "published_at": data.get("date", ""),
                "source": server['name'],
                "verify_ssl": verify
            }
                
            return result
            
        except requests.exceptions.HTTPError as e:
            self.last_error = f"{server['name']}: HTTP {e.response.status_code if e.response else 'error'}"
        except requests.exceptions.Timeout:
            self.last_error = f"{server['name']}: timeout"
        except requests.exceptions.ConnectionError:
            self.last_error = f"{server['name']}: connection error"
        except requests.exceptions.SSLError:
            self.last_error = f"{server['name']}: SSL error"
        except Exception as e:
            self.last_error = f"{server['name']}: {str(e)}"
            
        return None
        
    def check_server_health(self, server_url: str, verify_ssl: bool = True) -> Dict[str, Any]:
        """
        Проверяет состояние сервера
        
        Returns:
            Dict с информацией о состоянии сервера
        """
        try:
            url = urljoin(server_url, "/api/health")
            response = requests.get(
                url,
                timeout=5,
                verify=verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_server_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику всех серверов"""
        return self.server_stats.stats

# Глобальный экземпляр менеджера
_release_manager = ReleaseManager()

# Экспортируемые функции для обратной совместимости
def get_latest_release(channel: str) -> Optional[Dict[str, Any]]:
    """
    Получает информацию о последнем релизе (совместимость с github_release.py)
    """
    return _release_manager.get_latest_release(channel)

def get_release_manager() -> ReleaseManager:
    """Возвращает экземпляр менеджера релизов"""
    return _release_manager