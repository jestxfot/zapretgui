"""
build_tools/github_release.py - Модуль для работы с GitHub releases
Поддерживает как GitHub API, так и GitHub CLI для надежной загрузки больших файлов
"""

import json
import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tempfile
import mimetypes
import ssl
import urllib3
import subprocess
import shutil
import time

# ────────────────────────────────────────────────────────────────
#  НАСТРОЙКИ GITHUB (отредактируйте под свой репозиторий)
# ────────────────────────────────────────────────────────────────
GITHUB_CONFIG = {
    "enabled": True,  # True - включить GitHub releases, False - отключить
    "token": "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",  # Fine-grained токен
    "repo_owner": "youtubediscord",   # Владелец репозитория
    "repo_name": "zapret",           # Имя репозитория
    "release_settings": {
        "draft": False,              # True - создавать draft releases
        "prerelease_for_test": True, # True - test releases как prerelease
        "auto_generate_notes": True  # Автогенерация release notes
    },
    "ssl_settings": {
        "verify_ssl": True,         # False - отключить проверку SSL
        "disable_warnings": True     # True - отключить предупреждения SSL
    },
    "upload_settings": {
        "use_cli_for_large_files": True,  # Использовать GitHub CLI для больших файлов
        "large_file_threshold_mb": 50,    # Порог в МБ для переключения на CLI
        "retry_attempts": 3,               # Количество попыток при ошибках
        "chunk_size_mb": 5                # Размер чанка для загрузки
    }
}

def detect_token_type(token: str) -> str:
    """Определить тип токена GitHub"""
    if token.startswith('github_pat_'):
        return 'fine-grained'
    elif token.startswith('ghp_'):
        return 'classic'
    elif token.startswith('gho_'):
        return 'oauth'
    else:
        return 'unknown'

def check_gh_cli() -> Tuple[bool, str]:
    """Проверяет наличие и настройку GitHub CLI"""
    # Проверяем наличие gh.exe
    gh_path = shutil.which("gh")
    if not gh_path:
        return False, "GitHub CLI не установлен"
    
    # Проверяем авторизацию
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode != 0:
            return False, "GitHub CLI не авторизован"
            
        # Проверяем доступ к репозиторию
        repo = f"{GITHUB_CONFIG['repo_owner']}/{GITHUB_CONFIG['repo_name']}"
        result = subprocess.run(
            ["gh", "repo", "view", repo, "--json", "name"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode != 0:
            return False, f"Нет доступа к репозиторию {repo}"
            
        return True, f"GitHub CLI настроен для {repo}"
        
    except subprocess.TimeoutExpired:
        return False, "GitHub CLI не отвечает"
    except Exception as e:
        return False, f"Ошибка проверки GitHub CLI: {e}"

class GitHubReleaseManager:
    """Менеджер для работы с GitHub releases"""
    
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_base = "https://api.github.com"
        
        # Определяем тип токена и настраиваем заголовки
        self.token_type = detect_token_type(token)
        self.setup_headers()
        
        # Настройка SSL
        self.setup_ssl()
        
        # Проверяем доступность GitHub CLI
        self.cli_available, self.cli_status = check_gh_cli()
        
    def setup_headers(self):
        """Настройка заголовков в зависимости от типа токена"""
        if self.token_type == 'fine-grained':
            # Fine-grained токены используют Bearer
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",  # Важно для fine-grained токенов
                "User-Agent": "Zapret-Release-Builder"
            }
        else:
            # Classic токены используют token
            self.headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Zapret-Release-Builder"
            }
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"🔑 Тип токена: {self.token_type}")
        
    def setup_ssl(self):
        """Настройка SSL и сессии requests"""
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Настройки SSL из конфига
        ssl_config = GITHUB_CONFIG.get("ssl_settings", {})
        
        # Отключаем предупреждения SSL если настроено
        if ssl_config.get("disable_warnings", True):
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Настраиваем проверку SSL
        self.verify_ssl = ssl_config.get("verify_ssl", True)
        
        if hasattr(self, 'log_queue') and self.log_queue:
            if not self.verify_ssl:
                self.log_queue.put("⚠️ ВНИМАНИЕ: Проверка SSL отключена!")
            else:
                self.log_queue.put("🔒 SSL проверка включена")
    
    def check_token_validity(self) -> bool:
        """Проверить действительность токена"""
        try:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"🔍 Проверяем токен ({self.token_type})...")
            
            # Classic/OAuth – /user, fine-grained – репозиторий
            test_endpoint = (f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}"
                             if self.token_type == 'fine-grained'
                             else f"{self.api_base}/user")

            response = self.session.get(test_endpoint, verify=self.verify_ssl)
            
            if response.ok:
                # Для fine-grained токена user-данных не будет,
                # поэтому условно выводим имя репозитория.
                info = response.json().get('login') or response.json().get('full_name')
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put(f"✅ Токен действителен: {info}")
                return True
            else:
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put(f"❌ Токен недействителен: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"❌ Ошибка проверки токена: {e}")
            return False
    
    def check_repository_access(self) -> bool:
        """Проверить доступ к репозиторию"""
        try:
            # Сначала проверяем сам токен
            if not self.check_token_validity():
                return False
            
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"🔍 Проверяем доступ к репозиторию {self.repo_owner}/{self.repo_name}...")
            
            # Для fine-grained токенов нужно проверить конкретные права
            response = self._make_request("GET", "", handle_404=True)
            if response:
                repo_data = response.json()
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put("✅ Репозиторий найден и доступен!")
                    
                    # Проверяем права доступа
                    permissions = repo_data.get('permissions', {})
                    if permissions:
                        self.log_queue.put(f"📝 Права: admin={permissions.get('admin')}, push={permissions.get('push')}, pull={permissions.get('pull')}")
                    
                    # Для fine-grained токенов проверяем, можем ли создавать releases
                    if self.token_type == 'fine-grained':
                        releases_response = self._make_request("GET", "/releases", handle_404=True)
                        if releases_response:
                            self.log_queue.put("✅ Доступ к releases есть")
                        else:
                            self.log_queue.put("❌ Нет доступа к releases! Проверьте права токена.")
                            return False
                
                return True
            else:
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put("❌ Репозиторий не найден или нет доступа")
                    
                    # Дополнительные советы для fine-grained токенов
                    if self.token_type == 'fine-grained':
                        self.log_queue.put("💡 Для fine-grained токенов проверьте:")
                        self.log_queue.put("   • Resource owner: youtubediscord")
                        self.log_queue.put("   • Repository access: zapret")
                        self.log_queue.put("   • Permissions: Contents(Write), Metadata(Read), Releases(Write)")
                
                return False
                
        except Exception as e:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"❌ Ошибка проверки репозитория: {e}")
            return False
    
    def _make_request(self, method: str, endpoint: str, handle_404: bool = False, **kwargs) -> Optional[requests.Response]:
        """Выполнить HTTP запрос к GitHub API"""
        url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}{endpoint}"
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"GitHub API: {method} {url}")
        
        # Добавляем настройки SSL
        kwargs['verify'] = self.verify_ssl
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            if response.status_code == 404:
                if handle_404:
                    return None
                
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put(f"❌ 404 - Репозиторий не найден!")
                    self.log_queue.put(f"🔍 Проверьте:")
                    self.log_queue.put(f"   • Правильность имени: {self.repo_owner}/{self.repo_name}")
                    self.log_queue.put(f"   • Существует ли репозиторий: https://github.com/{self.repo_owner}/{self.repo_name}")
                    
                    if self.token_type == 'fine-grained':
                        self.log_queue.put(f"   • Resource owner в токене: {self.repo_owner}")
                        self.log_queue.put(f"   • Repository access включает: {self.repo_name}")
                
                raise Exception(f"Repository {self.repo_owner}/{self.repo_name} not found (404)")
            
            if not response.ok:
                error_msg = f"GitHub API error: {response.status_code} {response.text}"
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put(f"❌ {error_msg}")
                raise Exception(error_msg)
                
            return response
            
        except requests.exceptions.SSLError as e:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"❌ SSL ошибка: {e}")
            
            # Пробуем повторить запрос без SSL проверки
            if self.verify_ssl:
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put("🔄 Повторяем запрос без SSL проверки...")
                
                kwargs['verify'] = False
                try:
                    response = self.session.request(method, url, **kwargs)
                    
                    if response.status_code == 404:
                        if handle_404:
                            return None
                        raise Exception(f"Repository {self.repo_owner}/{self.repo_name} not found (404)")
                    
                    if not response.ok:
                        error_msg = f"GitHub API error: {response.status_code} {response.text}"
                        if hasattr(self, 'log_queue') and self.log_queue:
                            self.log_queue.put(f"❌ {error_msg}")
                        raise Exception(error_msg)
                        
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put("✔ Запрос успешен (без SSL проверки)")
                    
                    return response
                    
                except Exception as retry_error:
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put(f"❌ Повторная попытка не удалась: {retry_error}")
                    raise
            
            raise
            
        except Exception as e:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"❌ Ошибка запроса: {e}")
            raise
    
    def create_release(self, tag_name: str, name: str, body: str, 
                      draft: bool = False, prerelease: bool = False) -> Dict[str, Any]:
        """Создать новый release"""
        # Сначала проверяем доступ к репозиторию
        if not self.check_repository_access():
            raise Exception("Нет доступа к репозиторию")
        
        data = {
            "tag_name": tag_name,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease
        }
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"📦 Создаем GitHub release: {name}")
        
        response = self._make_request("POST", "/releases", json=data)
        release_data = response.json()
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"✔ Release создан: {release_data['html_url']}")
        
        return release_data
        
    def get_release_by_tag(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Получить release по тегу"""
        try:
            response = self._make_request("GET", f"/releases/tags/{tag_name}", handle_404=True)
            return response.json() if response else None
        except Exception:
            return None
            
    def update_release(self, release_id: int, **kwargs) -> Dict[str, Any]:
        """Обновить существующий release"""
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"🔄 Обновляем release {release_id}")
            
        response = self._make_request("PATCH", f"/releases/{release_id}", json=kwargs)
        return response.json()
        
    def upload_asset(self, release_id: int, file_path: Path, 
                    content_type: Optional[str] = None) -> Dict[str, Any]:
        """Загрузить файл к release с автоматическим выбором метода"""
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
            
        file_size_mb = file_path.stat().st_size / 1024 / 1024
        upload_settings = GITHUB_CONFIG.get("upload_settings", {})
        use_cli = upload_settings.get("use_cli_for_large_files", True)
        threshold = upload_settings.get("large_file_threshold_mb", 50)
        
        # Решаем какой метод использовать
        if use_cli and self.cli_available and file_size_mb > threshold:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"📤 Используем GitHub CLI для большого файла ({file_size_mb:.1f} MB)")
            return self._upload_asset_via_cli(release_id, file_path)
        else:
            return self._upload_asset_via_api(release_id, file_path, content_type)
    
    def _upload_asset_via_cli(self, release_id: int, file_path: Path) -> Dict[str, Any]:
        """Загрузить файл через GitHub CLI"""
        # Получаем информацию о релизе для tag
        response = self._make_request("GET", f"/releases/{release_id}")
        release_data = response.json()
        tag = release_data['tag_name']
        
        repo = f"{self.repo_owner}/{self.repo_name}"
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"🚀 Загружаем через GitHub CLI: {file_path.name}")
        
        cmd = [
            "gh", "release", "upload", tag,
            str(file_path),
            "--repo", repo,
            "--clobber"  # Перезаписать если существует
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 минут
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put(f"❌ GitHub CLI ошибка: {error_msg}")
                # Fallback на API метод
                return self._upload_asset_via_api(release_id, file_path)
                
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"✔ Файл загружен через CLI")
                
            # Возвращаем информацию об asset
            return {
                "name": file_path.name,
                "browser_download_url": f"https://github.com/{repo}/releases/download/{tag}/{file_path.name}"
            }
            
        except subprocess.TimeoutExpired:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put("⚠️ Таймаут GitHub CLI, переключаемся на API")
            return self._upload_asset_via_api(release_id, file_path)
        except Exception as e:
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"⚠️ Ошибка CLI: {e}, переключаемся на API")
            return self._upload_asset_via_api(release_id, file_path)
    
    def _upload_asset_via_api(self, release_id: int, file_path: Path, 
                             content_type: Optional[str] = None) -> Dict[str, Any]:
        """Загрузить файл через GitHub API с retry логикой"""
        if content_type is None:
            content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            
        file_size = file_path.stat().st_size
        filename = file_path.name
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"📤 Загружаем через API: {filename} ({file_size / 1024 / 1024:.1f} MB)")
        
        # URL для загрузки assets отличается от обычного API
        upload_url = f"https://uploads.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/{release_id}/assets"
        
        # Настройки для retry
        max_attempts = GITHUB_CONFIG.get("upload_settings", {}).get("retry_attempts", 3)
        
        for attempt in range(max_attempts):
            try:
                # Создаем отдельную сессию для загрузки
                upload_session = requests.Session()
                upload_session.headers.update(self.headers)
                upload_session.headers["Content-Type"] = content_type
                
                with open(file_path, 'rb') as f:
                    try:
                        response = upload_session.post(
                            upload_url,
                            params={"name": filename},
                            data=f,
                            verify=self.verify_ssl,
                            timeout=(30, 600)  # 30 сек на соединение, 600 на загрузку
                        )
                    except requests.exceptions.SSLError:
                        if hasattr(self, 'log_queue') and self.log_queue:
                            self.log_queue.put("⚠️ SSL ошибка при загрузке, повторяем без проверки...")
                        
                        f.seek(0)  # Перематываем файл
                        response = upload_session.post(
                            upload_url,
                            params={"name": filename},
                            data=f,
                            verify=False,
                            timeout=(30, 600)
                        )
                
                if response.ok:
                    asset_data = response.json()
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put(f"✔ Файл загружен: {asset_data['browser_download_url']}")
                    return asset_data
                elif response.status_code == 422:
                    # Файл уже существует
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put("⚠️ Файл уже существует в релизе")
                    return {"name": filename, "browser_download_url": f"https://github.com/{self.repo_owner}/{self.repo_name}/releases/"}
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    ConnectionAbortedError) as e:
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 5  # 5, 10, 15 секунд
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put(
                            f"⚠️ Ошибка загрузки (попытка {attempt + 1}/{max_attempts}): {type(e).__name__}. "
                            f"Повтор через {wait_time} сек..."
                        )
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                if attempt < max_attempts - 1 and "Connection aborted" in str(e):
                    wait_time = (attempt + 1) * 5
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put(
                            f"⚠️ Соединение прервано (попытка {attempt + 1}/{max_attempts}). "
                            f"Повтор через {wait_time} сек..."
                        )
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"Не удалось загрузить файл после {max_attempts} попыток")
        
    def delete_asset(self, asset_id: int):
        """Удалить asset из release"""
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"🗑 Удаляем asset {asset_id}")
            
        self._make_request("DELETE", f"/releases/assets/{asset_id}")
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put("✔ Asset удален")
            
    def get_release_assets(self, release_id: int) -> list:
        """Получить список assets для release"""
        response = self._make_request("GET", f"/releases/{release_id}/assets")
        return response.json()


def is_github_enabled() -> bool:
    """Проверить, включена ли интеграция с GitHub"""
    return (GITHUB_CONFIG.get("enabled", False) and 
            bool(GITHUB_CONFIG.get("token")) and
            not GITHUB_CONFIG.get("token").endswith("_here"))


def create_github_release(channel: str, version: str, file_path: Path, 
                         release_notes: str, log_queue=None) -> Optional[str]:
    """
    Создать GitHub release и загрузить файл
    
    Returns:
        URL на созданный release или None если отключено
    """
    if not is_github_enabled():
        if log_queue:
            token = GITHUB_CONFIG.get("token", "")
            if token.endswith("_here"):
                log_queue.put("ℹ GitHub releases: настройте токен в github_release.py")
            else:
                log_queue.put("ℹ GitHub releases отключены")
        return None
        
    try:
        manager = GitHubReleaseManager(
            token=GITHUB_CONFIG["token"],
            repo_owner=GITHUB_CONFIG["repo_owner"],
            repo_name=GITHUB_CONFIG["repo_name"]
        )
        
        # Передаем log_queue в менеджер
        if log_queue:
            manager.log_queue = log_queue
            
            # Информируем о статусе CLI
            if manager.cli_available:
                log_queue.put(f"✅ GitHub CLI доступен: {manager.cli_status}")
            else:
                log_queue.put(f"ℹ️ GitHub CLI недоступен: {manager.cli_status}")
        
        # Настройки release
        tag_name = version
        release_name = f"Zapret {version}"
        if channel == "test":
            release_name += " (Test)"
        
        is_prerelease = (channel == "test" and 
                        GITHUB_CONFIG["release_settings"].get("prerelease_for_test", True))
        is_draft = GITHUB_CONFIG["release_settings"].get("draft", False)
        
        # Проверяем, существует ли уже release с таким тегом
        existing_release = manager.get_release_by_tag(tag_name)
        
        if existing_release:
            if log_queue:
                log_queue.put(f"🔄 Release {tag_name} уже существует, обновляем")
            
            # Удаляем старые assets с таким же именем
            assets = manager.get_release_assets(existing_release["id"])
            for asset in assets:
                if asset["name"] == file_path.name:
                    manager.delete_asset(asset["id"])
                    
            release_data = existing_release
        else:
            # Создаем новый release
            release_data = manager.create_release(
                tag_name=tag_name,
                name=release_name,
                body=release_notes,
                draft=is_draft,
                prerelease=is_prerelease
            )
        
        # Загружаем файл (автоматически выберется CLI или API)
        asset_data = manager.upload_asset(release_data["id"], file_path)
        
        if log_queue:
            log_queue.put(f"✔ GitHub release готов: {release_data['html_url']}")
            
        return release_data["html_url"]
        
    except Exception as e:
        if log_queue:
            log_queue.put(f"❌ Ошибка создания GitHub release: {e}")
        # Не прерываем процесс сборки из-за ошибки GitHub
        return None


def get_github_config_info() -> str:
    """Получить информацию о текущей конфигурации GitHub"""
    if not GITHUB_CONFIG.get("enabled", False):
        return "Отключено"
    
    token = GITHUB_CONFIG.get("token", "")
    if token.endswith("_here") or not token:
        return "Не настроено (укажите токен)"
        
    repo = f"{GITHUB_CONFIG.get('repo_owner', '')}/{GITHUB_CONFIG.get('repo_name', '')}"
    if repo == "/":
        return "Не настроено (укажите репозиторий)"
    
    token_type = detect_token_type(token)
    ssl_status = "SSL✓" if GITHUB_CONFIG.get("ssl_settings", {}).get("verify_ssl", True) else "SSL✗"
    
    # Проверяем CLI
    cli_available, _ = check_gh_cli()
    cli_status = "CLI✓" if cli_available else "CLI✗"
    
    return f"Настроено: {repo} ({token_type}, {ssl_status}, {cli_status})"


def test_github_connection(log_queue=None) -> bool:
    """Тест соединения с GitHub API"""
    if not is_github_enabled():
        if log_queue:
            log_queue.put("❌ GitHub не настроен")
        return False
    
    try:
        manager = GitHubReleaseManager(
            token=GITHUB_CONFIG["token"],
            repo_owner=GITHUB_CONFIG["repo_owner"],
            repo_name=GITHUB_CONFIG["repo_name"]
        )
        
        if log_queue:
            manager.log_queue = log_queue
            log_queue.put("🔍 Тестируем соединение с GitHub...")
        
        # Проверяем доступ к репозиторию
        success = manager.check_repository_access()
        
        if success and log_queue:
            log_queue.put("✅ Тест GitHub соединения успешен!")
            
        return success
        
    except Exception as e:
        if log_queue:
            log_queue.put(f"❌ Ошибка тестирования GitHub: {e}")
        return False