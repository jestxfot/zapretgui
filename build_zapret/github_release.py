# build_zapret/github_release.py

"""
build_tools/github_release.py - Модуль для работы с GitHub releases
Поддерживает как GitHub API, так и GitHub CLI для надежной загрузки больших файлов
"""

import base64
import json, os, sys, re, requests, tempfile, mimetypes, ssl, urllib3, subprocess, shutil, time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Load /opt/zapretgui/.env if present so GITHUB_TOKEN/GH_TOKEN can be configured
# without hardcoding it in repo.
try:
    _ROOT = Path(__file__).resolve().parents[1]
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from utils.dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", _ROOT / "build_zapret" / ".env")
except Exception:
    pass


PARTS = [
    ("PTIqBWgSLAAwFw==", 0x5A, 0),
    ("C18MW3toC2UMTg==", 0x3D, 10),
    ("eG1uR11aQH56dQ==", 0x2C, 20),
    ("RgwEFk4WDzAGTQ==", 0x7E, 30),
]

CHECKSUM = 927

CACHE = ""


def _rebuild() -> str:
    global CACHE
    
    if CACHE:
        return CACHE
    
    try:
        result = [''] * 40
        
        for encoded, xor_key, offset in PARTS:
            decoded = base64.b64decode(encoded)
            for i, byte in enumerate(decoded):
                if offset + i < len(result):
                    result[offset + i] = chr(byte ^ xor_key)
        
        value = ''.join(result).rstrip('\x00')
        
        # Проверка контрольной суммы
        checksum = sum(ord(c) for c in value[:10])
        if checksum != CHECKSUM:
            return ""
        
        CACHE = value
        return CACHE
    except:
        return ""


def get() -> str:
    token = _rebuild()
    if token and len(token) > 20:
        return token
    
    # Приоритет 2: Переменная окружения
    env_token = os.getenv('GITHUB_TOKEN')
    if env_token:
        return env_token
    
    return ""


# ────────────────────────────────────────────────────────────────
#  НАСТРОЙКИ GITHUB (отредактируйте под свой репозиторий)
# ────────────────────────────────────────────────────────────────
GITHUB_CONFIG = {
    "enabled": True,  # True - включить GitHub releases, False - отключить
    "token": get(),  # Обфусцированный токен
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
        "large_file_threshold_mb": 40,    # Порог в МБ для переключения на CLI
        "retry_attempts": 3,               # Количество попыток при ошибках
        "chunk_size_mb": 5                # Размер чанка для загрузки
    }
}

def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip() in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}

def _pick_gh_runner() -> tuple[list[str], str, str]:
    """
    Возвращает (base_cmd, mode, distro) для запуска gh.

    base_cmd - это список аргументов перед "gh ...".
      - Windows+WSL: ["wsl.exe","-d","Debian","--"]
      - иначе: []
    """
    distro = os.environ.get("ZAPRET_WSL_DISTRO", "Debian")

    # Форсировать WSL gh можно env-переменной или автоматически,
    # если сам проект запущен с \\wsl.localhost\...
    prefer_wsl = (
        _env_truthy("ZAPRET_GITHUB_PREFER_WSL_GH")
        or _env_truthy("ZAPRET_GITHUB_USE_WSL_GH")
        or str(__file__).startswith("\\\\wsl.localhost\\")
    )

    if sys.platform == "win32" and prefer_wsl and shutil.which("wsl.exe"):
        return (["wsl.exe", "-d", distro, "--"], f"WSL:{distro}", distro)

    if sys.platform == "win32":
        return ([], "Windows", distro)

    return ([], "Linux", distro)

def _to_wsl_path(path: Path, distro: str) -> str:
    """
    Конвертирует путь Windows/UNC в Linux-путь для запуска внутри WSL.

    Поддержка:
      - \\\\wsl.localhost\\<Distro>\\opt\\...  -> /opt/...
      - //wsl.localhost/<Distro>/opt/...       -> /opt/...
      - C:\\Users\\...                        -> /mnt/c/Users/...
    """
    s = str(path)

    # UNC: \\wsl.localhost\Distro\...
    if s.startswith("\\\\wsl.localhost\\"):
        parts = s.split("\\")
        # ["", "", "wsl.localhost", "Debian", "opt", ...]
        if len(parts) >= 5 and parts[3].lower() == distro.lower():
            rest = [p for p in parts[4:] if p]
            return "/" + "/".join(rest)

    # POSIX UNC: //wsl.localhost/Distro/...
    s_posix = path.as_posix()
    prefix = f"//wsl.localhost/{distro}/"
    if s_posix.lower().startswith(prefix.lower()):
        return "/" + s_posix[len(prefix):].lstrip("/")

    # Drive path: C:\...
    m = re.match(r"^([A-Za-z]):[\\\\/](.*)$", s)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"

    # Если уже linux-путь
    if s.startswith("/"):
        return s

    return s

def detect_token_type(token: str) -> str:
    if token.startswith('github_pat_'):
        return 'fine-grained'
    elif token.startswith('ghp_'):
        return 'classic'
    elif token.startswith('gho_'):
        return 'oauth'
    else:
        return 'unknown'

def check_gh_cli() -> Tuple[bool, str]:
    """Проверяет наличие и настройку GitHub CLI (нативно или через WSL)."""

    # Создаем окружение с токеном
    env = os.environ.copy()
    env['GITHUB_TOKEN'] = GITHUB_CONFIG['token']
    env['GH_TOKEN'] = GITHUB_CONFIG['token']
    env['GH_PROMPT_DISABLED'] = '1'

    base_cmd, mode, distro = _pick_gh_runner()
    if base_cmd:
        flags = "GH_TOKEN/u:GITHUB_TOKEN/u:GH_PROMPT_DISABLED/u"
        current = env.get("WSLENV", "").strip(":")
        env["WSLENV"] = f"{current}:{flags}".strip(":") if current else flags

    # Проверяем, что gh доступен
    try:
        if base_cmd:
            # WSL mode
            version_check = subprocess.run(
                [*base_cmd, "gh", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                shell=False,
            )
            if version_check.returncode != 0:
                error = (version_check.stderr or version_check.stdout or "").strip()
                hint = ""
                if mode.startswith("WSL:"):
                    hint = " (установите в WSL: sudo apt update && sudo apt install gh -y)"
                return False, f"GitHub CLI ({mode}) не найден: {error}{hint}"
        else:
            gh_path = shutil.which("gh")
            if not gh_path:
                return False, "GitHub CLI не установлен"
    except subprocess.TimeoutExpired:
        return False, "GitHub CLI не отвечает"
    except Exception as e:
        return False, f"Ошибка проверки gh: {e}"

    # Проверяем доступ к репозиторию напрямую (без auth status)
    try:
        repo = f"{GITHUB_CONFIG['repo_owner']}/{GITHUB_CONFIG['repo_name']}"
        result = subprocess.run(
            [*base_cmd, "gh", "repo", "view", repo, "--json", "name"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            shell=False,
        )

        if result.returncode != 0:
            error = (result.stderr or result.stdout or "").strip()
            return False, f"Нет доступа к {repo} ({mode}): {error}"

        return True, f"GitHub CLI работает ({mode}) с {repo} (токен из конфига)"

    except subprocess.TimeoutExpired:
        return False, "GitHub CLI не отвечает"
    except Exception as e:
        return False, f"Ошибка проверки: {e}"

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
        self.gh_base_cmd, self.gh_mode, self.wsl_distro = _pick_gh_runner()

    def _get_gh_env(self) -> dict:
        """Создает окружение с токеном для GitHub CLI"""
        env = os.environ.copy()
        env['GITHUB_TOKEN'] = self.token
        env['GH_TOKEN'] = self.token
        env['GH_PROMPT_DISABLED'] = '1'

        # Для запуска gh внутри WSL с Windows важно пробросить env в Linux-процесс.
        # WSLENV как раз для этого (значения не являются путями, поэтому используем /u).
        if self.gh_base_cmd:
            flags = "GH_TOKEN/u:GITHUB_TOKEN/u:GH_PROMPT_DISABLED/u"
            current = env.get("WSLENV", "").strip(":")
            env["WSLENV"] = f"{current}:{flags}".strip(":") if current else flags
        return env
            
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
        force_cli = _env_truthy("ZAPRET_GITHUB_FORCE_CLI") or (use_cli and self.gh_base_cmd)
        
        # Решаем какой метод использовать
        if use_cli and self.cli_available and (force_cli or file_size_mb > threshold):
            if hasattr(self, 'log_queue') and self.log_queue:
                self.log_queue.put(f"📤 Используем GitHub CLI ({self.gh_mode}) ({file_size_mb:.1f} MB)")
            return self._upload_asset_via_cli(release_id, file_path)
        else:
            return self._upload_asset_via_api(release_id, file_path, content_type)

    def _upload_asset_via_cli(self, release_id: int, file_path: Path) -> Dict[str, Any]:
        """Загрузить файл через GitHub CLI с выводом прогресса"""
        response = self._make_request("GET", f"/releases/{release_id}")
        release_data = response.json()
        tag = release_data['tag_name']
        
        repo = f"{self.repo_owner}/{self.repo_name}"
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"🚀 Загружаем через GitHub CLI ({self.gh_mode}): {file_path.name}")

        cli_file_path = str(file_path)
        if self.gh_base_cmd:
            cli_file_path = _to_wsl_path(file_path, self.wsl_distro)
        
        cmd = [
            *self.gh_base_cmd,
            "gh", "release", "upload", tag,
            cli_file_path,
            "--repo", repo,
            "--clobber"
        ]
        
        try:
            # ✅ ИСПРАВЛЕНИЕ: Запускаем с Popen для реального вывода
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Объединяем stderr в stdout
                text=True,
                encoding='utf-8',
                errors='replace',
                env=self._get_gh_env(),
                shell=False,
                bufsize=1,  # Построчная буферизация
                universal_newlines=True
            )
            
            # Читаем вывод в реальном времени
            output_lines = []
            start_time = time.time()
            last_update = start_time
            
            while True:
                line = process.stdout.readline()
                
                if not line:
                    # Проверяем завершился ли процесс
                    if process.poll() is not None:
                        break
                        
                    # Показываем индикатор что процесс жив
                    current_time = time.time()
                    if current_time - last_update > 5:  # Каждые 5 секунд
                        elapsed = int(current_time - start_time)
                        if hasattr(self, 'log_queue') and self.log_queue:
                            self.log_queue.put(f"  ⏳ Загрузка... {elapsed}s")
                        last_update = current_time
                        
                    time.sleep(0.1)
                    continue
                
                line = line.rstrip()
                if line:
                    output_lines.append(line)
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put(f"  gh> {line}")
                    last_update = time.time()
            
            # Ждем завершения с таймаутом
            try:
                returncode = process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                raise Exception("GitHub CLI не завершился после загрузки")
            
            if returncode != 0:
                error_msg = "\n".join(output_lines) if output_lines else "Unknown error"
                if hasattr(self, 'log_queue') and self.log_queue:
                    self.log_queue.put(f"❌ GitHub CLI ошибка: {error_msg}")
                # Fallback на API метод
                return self._upload_asset_via_api(release_id, file_path)
                
            if hasattr(self, 'log_queue') and self.log_queue:
                elapsed = int(time.time() - start_time)
                self.log_queue.put(f"✔ Файл загружен через CLI ({elapsed}s)")
                
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
        """Загрузить файл через GitHub API с прогрессом"""
        if content_type is None:
            content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            
        file_size = file_path.stat().st_size
        filename = file_path.name
        
        if hasattr(self, 'log_queue') and self.log_queue:
            self.log_queue.put(f"📤 Загружаем через API: {filename} ({file_size / 1024 / 1024:.1f} MB)")
        
        upload_url = f"https://uploads.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/{release_id}/assets"
        
        max_attempts = GITHUB_CONFIG.get("upload_settings", {}).get("retry_attempts", 3)
        
        for attempt in range(max_attempts):
            try:
                upload_session = requests.Session()
                upload_session.headers.update(self.headers)
                upload_session.headers["Content-Type"] = content_type
                upload_session.headers["Content-Length"] = str(file_size)
                
                # ✅ ИСПРАВЛЕНИЕ: Используем генератор для отслеживания прогресса
                def file_reader_with_progress(file_obj, chunk_size=8192):
                    total_read = 0
                    last_percent = -1
                    start_time = time.time()
                    
                    while True:
                        chunk = file_obj.read(chunk_size)
                        if not chunk:
                            break
                            
                        total_read += len(chunk)
                        percent = int((total_read / file_size) * 100)
                        
                        # Обновляем каждые 10%
                        if percent >= last_percent + 10:
                            elapsed = int(time.time() - start_time)
                            speed_mb = (total_read / 1024 / 1024) / max(elapsed, 1)
                            if hasattr(self, 'log_queue') and self.log_queue:
                                self.log_queue.put(f"  📊 {percent}% ({total_read / 1024 / 1024:.1f} MB) — {speed_mb:.1f} MB/s")
                            last_percent = percent
                        
                        yield chunk
                
                with open(file_path, 'rb') as f:
                    try:
                        response = upload_session.post(
                            upload_url,
                            params={"name": filename},
                            data=file_reader_with_progress(f),
                            verify=self.verify_ssl,
                            timeout=(30, 1200)  # ✅ Увеличили таймаут до 20 минут
                        )
                    except requests.exceptions.SSLError:
                        if hasattr(self, 'log_queue') and self.log_queue:
                            self.log_queue.put("⚠️ SSL ошибка, повторяем без проверки...")
                        
                        f.seek(0)
                        response = upload_session.post(
                            upload_url,
                            params={"name": filename},
                            data=file_reader_with_progress(f),
                            verify=False,
                            timeout=(30, 1200)
                        )
                
                if response.ok:
                    asset_data = response.json()
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put(f"✔ Файл загружен: {asset_data['browser_download_url']}")
                    return asset_data
                elif response.status_code == 422:
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put("⚠️ Файл уже существует в релизе")
                    return {"name": filename, "browser_download_url": f"https://github.com/{self.repo_owner}/{self.repo_name}/releases/"}
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    ConnectionAbortedError) as e:
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 5
                    if hasattr(self, 'log_queue') and self.log_queue:
                        self.log_queue.put(
                            f"⚠️ Ошибка загрузки (попытка {attempt + 1}/{max_attempts}): {type(e).__name__}. "
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
