# updater/release_manager.py
"""
release_manager.py
────────────────────────────────────────────────────────────────
Менеджер получения релизов с поддержкой fallback на собственный сервер.
При любых ошибках GitHub (403, rate limit и др.) автоматически 
переключается на запасной HTTP/HTTPS сервер.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import requests
import os
import urllib3
from urllib.parse import urljoin

from .github_release import get_latest_release as github_get_latest_release
from .github_release import normalize_version
from log import log
from config import CHANNEL

# Отключаем предупреждения о самоподписанных сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Конфигурация fallback серверов через переменные окружения или дефолтные значения
def get_fallback_servers():
    """Получает список fallback серверов из переменных окружения или использует дефолтные"""
    servers = []
    
    # Читаем из переменных окружения ZAPRET_FALLBACK_SERVER_1, ZAPRET_FALLBACK_SERVER_2, etc.
    # Формат: https://example.com или http://example.com
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
                "name": "Local HTTPS"
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
                "name": "Local HTTP"
            })
    
    return servers

# Таймаут для запросов
TIMEOUT = 10

class ReleaseManager:
    """Менеджер для получения информации о релизах с поддержкой fallback"""
    
    def __init__(self):
        self.last_error: Optional[str] = None
        self.last_source: Optional[str] = None
        self.fallback_servers = get_fallback_servers()
        
    def get_latest_release(self, channel: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о последнем релизе.
        Сначала пытается GitHub, при ошибке переключается на fallback серверы.
        
        Args:
            channel: "stable" или "dev"
            
        Returns:
            Dict с информацией о релизе или None
        """
        # 1. Сначала пробуем GitHub
        log("🔍 Проверка обновлений через GitHub...", "🔄 RELEASE")
        github_result = self._try_github(channel)
        
        if github_result:
            self.last_source = "GitHub"
            self.last_error = None
            return github_result
            
        # 2. GitHub не сработал, пробуем fallback серверы
        log(f"⚠️ GitHub недоступен: {self.last_error}. Пробуем резервные серверы...", "🔄 RELEASE")
        
        # Сортируем серверы по приоритету
        servers = sorted(self.fallback_servers, key=lambda x: x["priority"])
        
        for server in servers:
            log(f"🔗 Попытка подключения к супер секретному серверу если РКН забанит GitHub...", "🔄 RELEASE")
            
            fallback_result = self._try_fallback_server(server, channel)
            if fallback_result:
                self.last_source = server['name']
                self.last_error = None
                return fallback_result
                
        # 3. Ничего не сработало
        log(f"❌ Не удалось получить информацию о релизах ни из одного источника", "🔄 RELEASE")
        return None
        
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
            
            # Создаем список альтернативных URL
            alt_urls = []
            
            # Если основной URL это HTTPS, добавляем HTTP как альтернативу
            if download_url.startswith("https://") and "88.210.21.236" in download_url:
                # Находим соответствующий HTTP сервер
                for alt_server in self.fallback_servers:
                    if alt_server["url"].startswith("http://") and "88.210.21.236" in alt_server["url"]:
                        alt_download_url = urljoin(alt_server["url"], f"/download/{download_channel}")
                        if api_key:
                            alt_download_url += f"?api_key={api_key}"
                        alt_urls.append(alt_download_url)
                        break
            
            # Преобразуем в формат, совместимый с github_release
            result = {
                "version": normalize_version(data.get("version", "0.0.0")),
                "tag_name": data.get("tag", f"v{data.get('version', '0.0.0')}"),
                "update_url": download_url,
                "release_notes": data.get("release_notes", ""),
                "prerelease": channel == "dev",
                "name": data.get("name", f"Zapret {channel}"),
                "published_at": data.get("date", ""),
                "source": server['name'],  # Добавляем источник
                "verify_ssl": verify  # Добавляем флаг проверки SSL
            }
            
            # Добавляем альтернативные URL если есть
            if alt_urls:
                result["alt_urls"] = alt_urls
                
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