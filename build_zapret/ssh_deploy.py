# build_zapret/ssh_deploy.py
"""
SSH деплой на несколько VPS серверов с автоматическим обновлением JSON
Поддержка балансировки нагрузки между серверами
ОБНОВЛЕНО: Добавлена поддержка входа по паролю
"""

import paramiko
import os
import subprocess
import re
from pathlib import Path
from typing import Optional, Any, List, Dict, Tuple
import json
from datetime import datetime
import tempfile
import shlex
# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ СЕРВЕРОВ
# ═══════════════════════════════════════════════════════════════

def _load_dotenv_if_present() -> None:
    """
    Minimal .env loader (no external dependency).
    - Only sets keys that are not already present in process env.
    - Supports plain KEY=VALUE and quoted KEY="VALUE"/KEY='VALUE'.
    """
    if os.environ.get("ZAPRET_DISABLE_DOTENV") == "1":
        return

    try:
        start_dir = Path(__file__).resolve().parent
    except Exception:
        start_dir = Path.cwd()

    for parent in (start_dir, *start_dir.parents):
        dotenv_path = parent / ".env"
        if dotenv_path.exists() and dotenv_path.is_file():
            try:
                for raw_line in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    if not key or key in os.environ:
                        continue
                    value = value.strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                        value = value[1:-1]
                    os.environ[key] = value
            except Exception:
                pass
            return

_load_dotenv_if_present()


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_falsy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _version_to_filename_suffix(ver: str) -> str:
    v = (ver or "").strip().lstrip("v")
    out: list[str] = []
    prev_us = False
    for ch in v:
        if ch.isdigit():
            out.append(ch)
            prev_us = False
            continue
        if ch in {".", "_", "-"}:
            if not prev_us:
                out.append("_")
                prev_us = True
            continue
    s = "".join(out).strip("_")
    return s


def _is_installer_for_channel(filename: str, channel: str) -> bool:
    n = (filename or "").strip().lower()
    ch = (channel or "").strip().lower()
    if not n.endswith(".exe"):
        return False
    if ch in {"test", "dev"}:
        return n == "zapret2setup_test.exe" or n.startswith("zapret2setup_test_")
    # stable
    if n == "zapret2setup.exe":
        return True
    if n.startswith("zapret2setup_test_"):
        return False
    return n.startswith("zapret2setup_")


def _cleanup_remote_installers(
    *,
    sftp: Any,
    upload_dir: str,
    channel: str,
    keep_names: set[str],
    keep_n: int,
    log_func,
) -> None:
    """Remove older installers in upload_dir, keeping only newest N for channel."""

    keep_n = max(1, int(keep_n or 1))
    keep_lc = {k.strip().lower() for k in (keep_names or set()) if (k or "").strip()}

    try:
        names = list(sftp.listdir(upload_dir))
    except Exception as e:
        log_func(f"   ⚠️ Не удалось получить список файлов для очистки: {e}")
        return

    candidates: list[tuple[int, str]] = []
    for name in names:
        if not _is_installer_for_channel(name, channel):
            continue
        if name.strip().lower() in keep_lc:
            continue
        try:
            st = sftp.stat(f"{upload_dir}/{name}")
            mtime = int(getattr(st, "st_mtime", 0) or 0)
        except Exception:
            mtime = 0
        candidates.append((mtime, name))

    if not candidates:
        return

    # Keep newest keep_n installers among candidates+kept.
    candidates.sort(key=lambda x: x[0], reverse=True)

    # If keep_lc has only the newest one (normal case), we delete all candidates.
    # If keep_n > 1, keep the first (keep_n - already_kept_count) from candidates.
    already_kept = 0
    for n in names:
        if _is_installer_for_channel(n, channel) and n.strip().lower() in keep_lc:
            already_kept += 1
    to_keep_from_candidates = max(0, keep_n - already_kept)
    delete_list = [name for _mtime, name in candidates[to_keep_from_candidates:]]

    removed = 0
    for name in delete_list:
        try:
            sftp.remove(f"{upload_dir}/{name}")
            removed += 1
        except Exception as e:
            log_func(f"   ⚠️ Не удалось удалить {name}: {e}")
    if removed:
        log_func(f"   🧹 Удалено старых установщиков: {removed}")


def _tg_ssh_config_from_env() -> Optional[Dict[str, Any]]:
    """Config for publishing to Telegram from a remote server via SSH.

    If ZAPRET_TG_SSH_HOST is set (or ZAPRET_TG_SSH_ENABLED=1), we will publish via SSH
    instead of local Telegram publishing.
    """
    enabled = _env_truthy("ZAPRET_TG_SSH_ENABLED")
    host = (os.environ.get("ZAPRET_TG_SSH_HOST") or "").strip()
    if not host and not enabled:
        return None

    if not host:
        # enabled but host missing
        return {
            "error": "ZAPRET_TG_SSH_HOST is not set",
        }

    port_s = (os.environ.get("ZAPRET_TG_SSH_PORT") or "22").strip()
    try:
        port = int(port_s)
    except Exception:
        port = 22

    user = (os.environ.get("ZAPRET_TG_SSH_USER") or "root").strip()
    key_path = (os.environ.get("ZAPRET_TG_SSH_KEY_PATH") or "").strip() or None
    key_password = (os.environ.get("ZAPRET_TG_SSH_KEY_PASSWORD") or "").strip() or None

    scripts_dir = (os.environ.get("ZAPRET_TG_SSH_SCRIPTS_DIR") or "/root/publisher").strip()
    upload_dir = (os.environ.get("ZAPRET_TG_SSH_UPLOAD_DIR") or f"{scripts_dir}/inbox").strip()
    env_file = (os.environ.get("ZAPRET_TG_SSH_ENV_FILE") or f"{scripts_dir}/.env").strip()
    # Default: bootstrap is enabled so you only change host in .env.
    bootstrap = not _env_falsy("ZAPRET_TG_SSH_BOOTSTRAP")
    # Disable remote dependency installation (apt/pip/venv) when set to 0/false.
    install_deps = not _env_falsy("ZAPRET_TG_SSH_INSTALL_DEPS")

    return {
        "name": f"Telegram Publisher ({host})",
        "host": host,
        "port": port,
        "user": user,
        "password": None,
        "password_env": os.environ.get("ZAPRET_TG_SSH_PASSWORD_ENV") or "ZAPRET_TG_SSH_PASSWORD",
        "key_path": key_path,
        "key_password": key_password,
        "scripts_dir": scripts_dir,
        "upload_dir": upload_dir,
        "env_file": env_file,
        "bootstrap": bootstrap,
        "install_deps": install_deps,
    }

VPS_SERVERS = [
    {
        'id': 'vps_super',
        'name': 'VPS Super (Новый основной)',
        'host': '206.251.51.235',
        'port': 10222,
        'user': 'root',
        'password': None,
        'key_path': None,
        'key_password': None,
        'upload_dir': '/var/www/zapret/download',
        'scripts_dir': '/root/zapretgpt/tests',
        'json_path': '/var/www/zapret/api/all_versions.json',
        'priority': 1,
        'use_for_telegram': False,
    },
    {
        'id': 'vps0',
        'name': 'VPS Primary (Новый основной)',
        'host': '46.21.80.246',
        'port': 10222,
        'user': 'root',
        'password': None,
        'key_path': None,
        'key_password': None,
        'upload_dir': '/var/www/zapret/download',
        'scripts_dir': '/root/zapretgpt/tests',
        'json_path': '/var/www/zapret/api/all_versions.json',
        'priority': 2,
        'use_for_telegram': False,
    },
    {
        'id': 'vps2',
        'name': 'VPS Server 2 (Резервный)',
        'host': '185.68.247.42',
        'port': 2089,
        'user': 'root',
        'password': None,
        'key_path': None,
        'key_password': None,
        'upload_dir': '/var/www/zapret/download',
        'scripts_dir': '/root/zapretgpt/tests',
        'json_path': '/var/www/zapret/api/all_versions.json',
        'priority': 3,
        'use_for_telegram': False,  # ← Резервный сервер нестабилен
    },
]

# ═══════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def _normalize_env_key(value: str) -> str:
    return re.sub(r'[^A-Za-z0-9]+', '_', value).upper().strip('_')

def _password_env_name(server_config: Dict[str, Any]) -> str:
    explicit = server_config.get('password_env')
    if explicit:
        return explicit
    server_id = server_config.get('id') or ""
    if server_id:
        return f"ZAPRET_{_normalize_env_key(server_id)}_PASSWORD"
    return "ZAPRET_SSH_PASSWORD"

def _resolve_password(server_config: Dict[str, Any]) -> Optional[str]:
    password = server_config.get('password')
    if password:
        return password
    return os.environ.get(_password_env_name(server_config)) or None


def _key_path_env_name(server_config: Dict[str, Any]) -> str:
    explicit = server_config.get("key_path_env")
    if explicit:
        return explicit
    server_id = server_config.get("id") or ""
    if server_id:
        return f"ZAPRET_{_normalize_env_key(server_id)}_KEY_PATH"
    return "ZAPRET_SSH_KEY_PATH"


def _key_password_env_name(server_config: Dict[str, Any]) -> str:
    explicit = server_config.get("key_password_env")
    if explicit:
        return explicit
    server_id = server_config.get("id") or ""
    if server_id:
        return f"ZAPRET_{_normalize_env_key(server_id)}_KEY_PASSWORD"
    return "ZAPRET_SSH_KEY_PASSWORD"


def _resolve_key_path(server_config: Dict[str, Any]) -> Optional[str]:
    key_path = server_config.get("key_path")
    if key_path:
        return str(key_path)
    return os.environ.get(_key_path_env_name(server_config)) or os.environ.get("ZAPRET_SSH_KEY_PATH") or None


def _resolve_key_password(server_config: Dict[str, Any]) -> Optional[str]:
    key_password = server_config.get("key_password")
    if key_password:
        return str(key_password)
    return os.environ.get(_key_password_env_name(server_config)) or os.environ.get("ZAPRET_SSH_KEY_PASSWORD") or None

def convert_key_to_pem(key_path: str, password: str = "") -> Optional[str]:
    """Конвертирует OpenSSH ключ в PEM формат для Paramiko"""
    try:
        temp_pem = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        temp_pem_path = temp_pem.name
        temp_pem.close()
        
        import shutil
        shutil.copy2(key_path, temp_pem_path)
        
        result = subprocess.run(
            ["ssh-keygen", "-p", "-f", temp_pem_path, "-m", "PEM", "-N", "", "-P", password or ""],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return temp_pem_path
        else:
            os.unlink(temp_pem_path)
            return None
    except:
        return None


def _peek_key_header(key_path_obj: Path) -> str:
    try:
        with key_path_obj.open("r", encoding="utf-8", errors="ignore") as f:
            return (f.readline() or "").strip()
    except Exception:
        return ""


def _load_paramiko_pkey(
    key_path_obj: Path,
    key_password: Optional[str],
    log_func,
) -> Tuple[Optional[paramiko.PKey], Optional[str]]:
    """Try to load a private key for Paramiko.

    Returns: (pkey, error_message)
    """

    # Fast detection for PuTTY PPK.
    header = _peek_key_header(key_path_obj)
    if header.startswith("PuTTY-User-Key-File"):
        return None, (
            "Ключ в формате PuTTY (.ppk). Paramiko ожидает OpenSSH private key. "
            "Сконвертируйте: puttygen key.ppk -O private-openssh -o id_ed25519"
        )

    # Try common key types.
    errors: list[str] = []
    for key_type, key_class in [
        ("Ed25519", paramiko.Ed25519Key),
        ("ECDSA", paramiko.ECDSAKey),
        ("RSA", paramiko.RSAKey),
    ]:
        try:
            pkey = key_class.from_private_key_file(
                str(key_path_obj),
                password=key_password if key_password else None,
            )
            log_func(f"✅ SSH ключ загружен ({key_type})")
            return pkey, None
        except paramiko.PasswordRequiredException:
            return None, (
                "SSH ключ защищен паролем. Укажите ZAPRET_TG_SSH_KEY_PASSWORD "
                "(или ZAPRET_TG_SSH_KEY_PASSWORD) в .env"
            )
        except Exception as e:
            errors.append(f"{key_type}: {type(e).__name__}")

    # Legacy conversion: works for RSA/ECDSA, but not for Ed25519.
    try:
        log_func("⚠️ Прямая загрузка не удалась, пробуем конвертацию в PEM...")
        pem_key_path = convert_key_to_pem(str(key_path_obj), (key_password or ""))
        if pem_key_path:
            try:
                pkey = paramiko.RSAKey.from_private_key_file(pem_key_path)
                log_func("✅ SSH ключ загружен после конвертации")
                return pkey, None
            except Exception as e:
                return None, f"Не удалось загрузить ключ даже после конвертации: {type(e).__name__}"
    except Exception:
        pass

    hint = ""
    if header.startswith("-----BEGIN OPENSSH PRIVATE KEY-----"):
        hint = " (OpenSSH key detected; возможно, нужен пароль или старая версия paramiko/cryptography)"
    return None, f"Не удалось загрузить SSH ключ{hint}. Пробовали: {', '.join(errors) if errors else 'n/a'}"

def is_ssh_configured() -> bool:
    """Проверка конфигурации SSH"""
    if not VPS_SERVERS:
        return False
    
    for server in VPS_SERVERS:
        # Сервер с паролем или с существующим ключом
        if _resolve_password(server):
            return True

        key_path = _resolve_key_path(server)
        if key_path and Path(key_path).exists():
            return True
    
    return False

def get_ssh_config_info() -> str:
    """Информация о конфигурации SSH"""
    if not VPS_SERVERS:
        return "SSH не настроен"
    
    try:
        import paramiko
    except ImportError:
        return "Paramiko не установлен (pip install paramiko)"

    # If nothing can authenticate, provide a concrete hint.
    if not is_ssh_configured():
        hints: list[str] = []
        seen: set[str] = set()
        for server in VPS_SERVERS:
            for name in (_password_env_name(server), _key_path_env_name(server), _key_password_env_name(server)):
                if name and name not in seen:
                    seen.add(name)
                    hints.append(name)
        for name in ("ZAPRET_SSH_KEY_PATH", "ZAPRET_SSH_KEY_PASSWORD"):
            if name not in seen:
                seen.add(name)
                hints.append(name)
        hint_s = ", ".join(hints[:8])
        if len(hints) > 8:
            hint_s += ", ..."
        return "SSH не настроен: задайте пароль/ключ через env (например: " + hint_s + ")"
    
    count = len(VPS_SERVERS)
    first = VPS_SERVERS[0]
    
    auth_type = "пароль" if not _resolve_key_path(first) else "ключ"
    
    if count == 1:
        return f"SSH настроен (1 сервер, {auth_type}): {first['user']}@{first['host']}"
    else:
        return f"SSH настроен ({count} серверов): {first['user']}@{first['host']} +{count-1}"

# ═══════════════════════════════════════════════════════════════
# ФУНКЦИЯ SSH ПОДКЛЮЧЕНИЯ (НОВАЯ)
# ═══════════════════════════════════════════════════════════════

def _ssh_connect(server_config: Dict[str, Any], log_func) -> tuple[Optional[paramiko.SSHClient], Optional[str], str]:
    """
    Универсальная функция подключения по SSH
    
    Returns:
        (ssh_client, pem_key_path, error_message)
        Если успешно: (client, pem_path_or_none, "")
        Если ошибка: (None, None, "error message")
    """
    host = server_config['host']
    port = server_config['port']
    user = server_config['user']
    password = _resolve_password(server_config)
    key_path = _resolve_key_path(server_config)
    key_password = _resolve_key_password(server_config)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pem_key_path = None
    
    try:
        if not key_path and not password:
            return None, None, f"Пароль не задан для {user}@{host}:{port}. Установите переменную окружения {_password_env_name(server_config)}"

        if password and not key_path:
            # ═══ ВХОД ПО ПАРОЛЮ ═══
            log_func(f"🔑 Подключение по паролю к {user}@{host}:{port}...")
            ssh.connect(
                hostname=host,
                port=port,
                username=user,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=30,
                banner_timeout=30,
                auth_timeout=30
            )
            log_func("✅ Подключено по паролю")
            return ssh, None, ""
        
        else:
            # ═══ ВХОД ПО SSH КЛЮЧУ ═══
            key_path_obj = Path(key_path) if key_path else None
            
            if not key_path_obj or not key_path_obj.exists():
                return None, None, f"SSH ключ не найден: {key_path}"
            
            log_func(f"🔑 Загрузка SSH ключа: {key_path_obj.name}")

            key, load_err = _load_paramiko_pkey(key_path_obj, key_password, log_func)
            if not key:
                return None, None, (load_err or "Не удалось загрузить SSH ключ")
            
            log_func(f"🔌 Подключение к {user}@{host}:{port}...")
            ssh.connect(
                hostname=host,
                port=port,
                username=user,
                pkey=key,
                look_for_keys=False,
                allow_agent=False,
                timeout=30,
                banner_timeout=30,
                auth_timeout=30
            )
            log_func("✅ Подключено по SSH ключу")
            return ssh, None, ""
            
    except paramiko.AuthenticationException as e:
        return None, pem_key_path, f"Ошибка аутентификации: {e}"
    except Exception as e:
        return None, pem_key_path, f"Ошибка подключения: {e}"

# ═══════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ ДЕПЛОЯ
# ═══════════════════════════════════════════════════════════════

def deploy_to_all_servers(
    file_path: Path,
    channel: str,
    version: str,
    notes: str,
    publish_telegram: bool = False,
    log_queue: Optional[Any] = None
) -> tuple[bool, str]:
    """
    Деплой на все сервера из списка с публикацией в Telegram
    """
    def log(msg: str):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)
    
    if not file_path.exists():
        return False, f"Файл не найден: {file_path}"
    
    if not VPS_SERVERS:
        return False, "Нет серверов в конфигурации"
    
    servers = sorted(VPS_SERVERS, key=lambda s: s['priority'])
    
    log(f"\n{'='*60}")
    log(f"📤 ДЕПЛОЙ НА {len(servers)} {'СЕРВЕР' if len(servers) == 1 else 'СЕРВЕРОВ'}")
    log(f"{'='*60}")
    
    results = []
    
    for i, server in enumerate(servers, 1):
        log(f"\n{'─'*60}")
        log(f"📍 Сервер {i}/{len(servers)}: {server['name']}")
        log(f"{'─'*60}")
        
        success, message = _deploy_to_single_server(
            file_path=file_path,
            channel=channel,
            version=version,
            notes=notes,
            server_config=server,
            log_queue=log_queue
        )
        
        results.append({
            'server': server['name'],
            'server_id': server['id'],
            'success': success,
            'message': message,
            'config': server
        })
        
        if success:
            log(f"✅ {server['name']}: деплой успешен")
        else:
            log(f"❌ {server['name']}: {message}")
    
    log(f"\n{'='*60}")
    log(f"📊 ИТОГИ ДЕПЛОЯ")
    log(f"{'='*60}")
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    log(f"✅ Успешно: {successful}/{len(results)}")
    
    if failed > 0:
        log(f"❌ Ошибки: {failed}/{len(results)}")
        for r in results:
            if not r['success']:
                log(f"  • {r['server']}: {r['message']}")
    
    if successful == 0:
        return False, "Деплой не удался ни на одном сервере"
    
    # Публикация в Telegram
    if publish_telegram:
        tg_cfg = _tg_ssh_config_from_env()
        if tg_cfg and not tg_cfg.get("error"):
            log(f"\n{'='*60}")
            log(f"📢 ПУБЛИКАЦИЯ В TELEGRAM (SSH, Pyrogram)")
            log(f"{'='*60}")

            telegram_success, telegram_message = _publish_to_telegram_via_ssh_pyrogram(
                file_path=file_path,
                channel=channel,
                version=version,
                notes=notes,
                server_config=tg_cfg,
                log_queue=log_queue,
            )
        else:
            if tg_cfg and tg_cfg.get("error"):
                log(f"⚠️ Telegram SSH: {tg_cfg['error']}")

            log(f"\n{'='*60}")
            log(f"📢 ПУБЛИКАЦИЯ В TELEGRAM (ЛОКАЛЬНО, SOCKS5)")
            log(f"{'='*60}")

            telegram_success, telegram_message = _publish_to_telegram_local(
                file_path=file_path,
                channel=channel,
                version=version,
                notes=notes,
                log_queue=log_queue,
            )

        if telegram_success:
            log("✅ Telegram публикация успешна")
        else:
            log(f"⚠️ Telegram: {telegram_message}")
    
    if successful < len(results):
        return True, f"Деплой завершён частично ({successful}/{len(results)})"
    else:
        return True, f"Деплой успешно завершён на всех {len(results)} серверах"

def _publish_to_telegram_via_ssh(
    channel: str,
    version: str,
    notes: str,
    server_config: Dict[str, Any],
    log_queue: Optional[Any] = None
) -> tuple[bool, str]:
    """Публикация в Telegram через SSH"""
    def log(msg: str):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)
    
    pem_key_path = None
    
    try:
        scripts_dir = server_config.get('scripts_dir')
        upload_dir = server_config['upload_dir']
        
        if not scripts_dir:
            return False, "scripts_dir не указан"
        
        suffix = "_TEST" if (channel or "").strip().lower() in {"test", "dev"} else ""
        v = _version_to_filename_suffix(version)
        remote_filename = f"Zapret2Setup{suffix}_{v}.exe" if v else f"Zapret2Setup{suffix}.exe"
        remote_path = f"{upload_dir}/{remote_filename}"
        
        # Подключение
        ssh, pem_key_path, error = _ssh_connect(server_config, log)
        if not ssh:
            return False, error
        
        # Запуск скрипта
        notes_escaped = notes.replace('"', '\\"').replace('$', '\\$')
        telegram_cmd = (
            f"cd {scripts_dir} && "
            f"python3 ssh_telegram_publisher.py "
            f'"{remote_path}" "{channel}" "{version}" "{notes_escaped}"'
        )
        
        log(f"📤 Запуск: ssh_telegram_publisher.py")
        
        stdin, stdout, stderr = ssh.exec_command(telegram_cmd, timeout=600)
        
        for line in stdout:
            log(f"   {line.rstrip()}")
        
        exit_code = stdout.channel.recv_exit_status()
        
        stderr_output = stderr.read().decode('utf-8')
        if stderr_output:
            for line in stderr_output.split('\n'):
                if line.strip():
                    log(f"   ⚠️ {line}")
        
        ssh.close()
        
        if exit_code == 0:
            return True, "OK"
        else:
            return False, f"Код выхода: {exit_code}"
        
    except Exception as e:
        return False, str(e)[:100]
    finally:
        if pem_key_path and os.path.exists(pem_key_path):
            try:
                os.unlink(pem_key_path)
            except:
                pass


def _publish_to_telegram_via_ssh_pyrogram(
    *,
    file_path: Path,
    channel: str,
    version: str,
    notes: str,
    server_config: Dict[str, Any],
    log_queue: Optional[Any] = None,
) -> tuple[bool, str]:
    """Publish to Telegram by uploading the installer to a remote server and running Pyrogram uploader there."""

    def log(msg: str):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)

    pem_key_path = None
    ssh = None

    try:
        scripts_dir = (server_config.get("scripts_dir") or "").strip()
        upload_dir = (server_config.get("upload_dir") or "").strip()
        env_file = (server_config.get("env_file") or "").strip() or f"{scripts_dir}/.env"
        bootstrap = bool(server_config.get("bootstrap"))
        install_deps = bool(server_config.get("install_deps", True))

        if not scripts_dir:
            return False, "scripts_dir is not set (ZAPRET_TG_SSH_SCRIPTS_DIR)"
        if not upload_dir:
            return False, "upload_dir is not set (ZAPRET_TG_SSH_UPLOAD_DIR)"

        if not file_path.exists():
            return False, f"File not found: {file_path}"

        # Connect
        ssh, pem_key_path, error = _ssh_connect(server_config, log)
        if not ssh:
            return False, error

        # Prepare dirs
        for d in (scripts_dir, upload_dir):
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {d}")
            stdout.channel.recv_exit_status()

        # Upload the installer
        suffix = "_TEST" if (channel or "").strip().lower() in {"test", "dev"} else ""
        v = _version_to_filename_suffix(version)
        remote_filename = f"Zapret2Setup{suffix}_{v}.exe" if v else f"Zapret2Setup{suffix}.exe"
        remote_installer = f"{upload_dir}/{remote_filename}"

        log(f"📤 Upload to Telegram host: {file_path.name} → {remote_installer}")
        sftp = ssh.open_sftp()
        sftp.put(str(file_path), remote_installer)

        # Upload publisher scripts (keep them in scripts_dir)
        local_dir = Path(__file__).resolve().parent
        local_uploader = local_dir / "telegram_uploader_pyrogram.py"
        local_auth = local_dir / "telegram_auth_pyrogram.py"

        if not local_uploader.exists():
            return False, f"Local uploader missing: {local_uploader}"

        remote_uploader = f"{scripts_dir}/telegram_uploader_pyrogram.py"
        remote_auth = f"{scripts_dir}/telegram_auth_pyrogram.py"

        sftp.put(str(local_uploader), remote_uploader)
        if local_auth.exists():
            sftp.put(str(local_auth), remote_auth)

        sftp.close()

        # Ensure remote env exists (do not overwrite).
        stdin, stdout, stderr = ssh.exec_command(f"test -f {env_file} && echo OK || echo NO")
        has_env = (stdout.read().decode("utf-8", errors="ignore").strip() == "OK")
        if not has_env:
            log(f"⚠️ Remote env is missing: {env_file}")
            template = (
                "TELEGRAM_API_ID=\n"
                "TELEGRAM_API_HASH=\n"
                "# Optional proxy for Telegram:\n"
                "# ZAPRET_PROXY_SCHEME=socks5\n"
                "# ZAPRET_PROXY_HOST=\n"
                "# ZAPRET_PROXY_PORT=\n"
                "# ZAPRET_PROXY_USER=\n"
                "# ZAPRET_PROXY_PASS=\n"
            )
            # Use a single-quoted heredoc to avoid shell expansion.
            create_env_cmd = f"cat > {env_file} <<'EOF'\n{template}\nEOF\nchmod 600 {env_file}"
            _stdin, _stdout, _stderr = ssh.exec_command(create_env_cmd)
            _stdout.channel.recv_exit_status()
            return False, f"Remote Telegram env created at {env_file}. Fill TELEGRAM_API_ID/TELEGRAM_API_HASH and re-run."

        # Optional bootstrap for Python deps (default enabled).
        # Runs only if remote python can't import deps.
        python_cmd = f"{scripts_dir}/.venv/bin/python3"
        import_probe = "import pyrogram, tgcrypto, socks"

        def _remote_ok(cmd: str) -> bool:
            _stdin, _stdout, _stderr = ssh.exec_command(cmd)
            return (_stdout.read().decode("utf-8", errors="ignore").strip() == "OK")

        venv_deps_ok = _remote_ok(
            f"test -x {python_cmd} && {python_cmd} -c \"{import_probe}\" >/dev/null 2>&1 && echo OK || echo NO"
        )
        sys_deps_ok = _remote_ok(
            f"python3 -c \"{import_probe}\" >/dev/null 2>&1 && echo OK || echo NO"
        )

        if bootstrap and install_deps and not (venv_deps_ok or sys_deps_ok):
            log("🧰 Bootstrap: install python deps on remote")
            bootstrap_cmd = (
                f"set -e; "
                f"export DEBIAN_FRONTEND=noninteractive; "
                f"(command -v apt-get >/dev/null 2>&1 && apt-get update && apt-get -y install python3 python3-venv python3-pip) || true; "
                f"cd {scripts_dir}; "
                f"python3 -m venv .venv; "
                f". .venv/bin/activate; "
                f"python -m pip install -U pip; "
                f"python -m pip install pyrogram tgcrypto pysocks"
            )
            stdin, stdout, stderr = ssh.exec_command(bootstrap_cmd, timeout=1800)
            for line in stdout:
                s = (line or "").rstrip()
                if s:
                    log(f"   {s}")
            rc = stdout.channel.recv_exit_status()
            if rc != 0:
                err = stderr.read().decode("utf-8", errors="ignore")
                return False, f"Bootstrap failed (rc={rc}): {err[:200]}"

            venv_deps_ok = _remote_ok(
                f"test -x {python_cmd} && {python_cmd} -c \"{import_probe}\" >/dev/null 2>&1 && echo OK || echo NO"
            )

        if venv_deps_ok:
            python_exec = python_cmd
        elif sys_deps_ok:
            python_exec = "python3"
        else:
            return False, (
                "Remote python deps are missing for Telegram publisher. "
                "Install once on the server (pyrogram/tgcrypto/pysocks) or enable auto-install with "
                "ZAPRET_TG_SSH_INSTALL_DEPS=1 (or ZAPRET_TG_SSH_BOOTSTRAP=1)."
            )

        # Ensure remote session exists.
        session_file = f"{scripts_dir}/zapret_uploader_pyrogram.session"
        stdin, stdout, stderr = ssh.exec_command(f"test -f {session_file} && echo OK || echo NO")
        has_session = (stdout.read().decode("utf-8", errors="ignore").strip() == "OK")
        if not has_session:
            return False, (
                "Remote Pyrogram session is missing. Run once on the server to authorize:\n"
                f"ssh {server_config.get('user','root')}@{server_config.get('host')} \"cd {scripts_dir} && set -a && . {env_file} && set +a && {python_exec} telegram_auth_pyrogram.py\""
            )

        # Run uploader. Credentials come from env_file on remote.
        notes_escaped = (notes or "").replace('"', '\\"').replace('$', '\\$')
        telegram_cmd = (
            f"set -e; cd {scripts_dir}; "
            f"if [ -f {env_file} ]; then set -a; . {env_file}; set +a; fi; "
            f"{python_exec} telegram_uploader_pyrogram.py "
            f"\"{remote_installer}\" \"{channel}\" \"{version}\" \"{notes_escaped}\""
        )

        log("📤 Telegram publish: running on remote host")
        stdin, stdout, stderr = ssh.exec_command(telegram_cmd, timeout=1800)

        for line in stdout:
            s = (line or "").rstrip()
            if s:
                log(f"   {s}")

        rc = stdout.channel.recv_exit_status()
        err = stderr.read().decode("utf-8", errors="ignore")
        if err.strip():
            for line in err.splitlines():
                s = (line or "").rstrip()
                if s:
                    log(f"   ⚠️ {s}")

        if rc == 0:
            return True, "OK"
        return False, f"Uploader exit code: {rc}"

    except Exception as e:
        return False, str(e)[:200]
    finally:
        try:
            if ssh:
                ssh.close()
        except Exception:
            pass
        if pem_key_path and os.path.exists(pem_key_path):
            try:
                os.unlink(pem_key_path)
            except Exception:
                pass


def _publish_to_telegram_local(
    *,
    file_path: Path,
    channel: str,
    version: str,
    notes: str,
    log_queue: Optional[Any] = None,
) -> tuple[bool, str]:
    """Публикация в Telegram напрямую с ПК через SOCKS5."""

    def log(msg: str):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)

    try:
        import sys
        import subprocess

        uploader = Path(__file__).resolve().parent / "telegram_uploader_telethon_fixed.py"
        if not uploader.exists():
            return False, f"Uploader не найден: {uploader}"

        api_id = (os.environ.get("TELEGRAM_API_ID") or os.environ.get("ZAPRET_TELEGRAM_API_ID") or "").strip()
        api_hash = (os.environ.get("TELEGRAM_API_HASH") or os.environ.get("ZAPRET_TELEGRAM_API_HASH") or "").strip()
        if not api_id or not api_hash:
            return False, "Telegram API ключи не найдены: TELEGRAM_API_ID/TELEGRAM_API_HASH"

        python_exe = sys.executable
        if python_exe.endswith("pythonw.exe"):
            python_exe = python_exe.replace("pythonw.exe", "python.exe")

        size_mb = file_path.stat().st_size / 1024 / 1024
        timeout = 1800 if size_mb > 100 else 1200

        cmd = [
            python_exe,
            str(uploader),
            str(file_path),
            channel,
            version,
            (notes or ""),
            str(api_id),
            str(api_hash),
        ]

        log(f"📤 Telegram uploader: {uploader.name}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).resolve().parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            s = (line or "").rstrip()
            if s:
                log(f"   {s}")

        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            rc = proc.wait(timeout=10)

        return (rc == 0), ("OK" if rc == 0 else f"Uploader exit code: {rc}")
    except Exception as e:
        return False, str(e)[:200]

# ═══════════════════════════════════════════════════════════════
# ДЕПЛОЙ НА ОДИН СЕРВЕР
# ═══════════════════════════════════════════════════════════════

def _deploy_to_single_server(
    file_path: Path,
    channel: str,
    version: str,
    notes: str,
    server_config: Dict[str, Any],
    log_queue: Optional[Any] = None
) -> tuple[bool, str]:
    """Деплой файла на конкретный VPS сервер"""
    def log(msg: str):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)
    
    pem_key_path = None
    ssh = None
    
    try:
        host = server_config['host']
        upload_dir = server_config['upload_dir']
        json_path = server_config['json_path']
        
        # ═══ SSH ПОДКЛЮЧЕНИЕ ═══
        ssh, pem_key_path, error = _ssh_connect(server_config, log)
        if not ssh:
            return False, error
        
        # Проверка
        stdin, stdout, stderr = ssh.exec_command("whoami", timeout=10)
        connected_user = stdout.read().decode().strip()
        log(f"✅ Вход: {connected_user}")
        
        # ═══ ЗАГРУЗКА ФАЙЛА ═══
        suffix = "_TEST" if (channel or "").strip().lower() in {"test", "dev"} else ""
        v = _version_to_filename_suffix(version)
        remote_filename = f"Zapret2Setup{suffix}_{v}.exe" if v else f"Zapret2Setup{suffix}.exe"
        remote_path = f"{upload_dir}/{remote_filename}"
        
        log(f"📤 Загрузка {file_path.name} → {remote_path}")
        
        sftp = ssh.open_sftp()
        
        try:
            sftp.stat(upload_dir)
        except:
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {upload_dir}")
            stdout.channel.recv_exit_status()
            log(f"✅ Создана директория: {upload_dir}")
        
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        last_percent = -1
        def progress_callback(transferred, total):
            nonlocal last_percent
            if not total:
                return
            percent = int((transferred / total) * 100)
            if percent >= last_percent + 10:
                last_percent = percent - (percent % 10)
                log(f"   📊 {last_percent}% ({transferred/1024/1024:.1f}/{total/1024/1024:.1f} МБ)")
        
        sftp.put(str(file_path), remote_path, callback=progress_callback)
        
        log(f"✅ Файл загружен ({file_size_mb:.1f} МБ)")

        # Create/refresh a stable link name for backward compatibility.
        # This does not duplicate the large file (symlink).
        try:
            latest_name = f"Zapret2Setup{'_TEST' if channel == 'test' else ''}.exe"
            link_cmd = f"cd {upload_dir} && ln -sf {remote_filename} {latest_name}"
            _stdin, _stdout, _stderr = ssh.exec_command(link_cmd)
            _stdout.channel.recv_exit_status()
        except Exception:
            pass

        # Cleanup older installers to avoid filling disk.
        try:
            keep_n = _env_int("ZAPRET_SSH_KEEP_INSTALLERS", 1)
            keep = {remote_filename, f"Zapret2Setup{'_TEST' if channel == 'test' else ''}.exe"}
            _cleanup_remote_installers(
                sftp=sftp,
                upload_dir=upload_dir,
                channel=channel,
                keep_names=keep,
                keep_n=keep_n,
                log_func=log,
            )
        except Exception:
            pass
        
        # ═══ ОБНОВЛЕНИЕ JSON ═══
        log(f"\n📝 Обновление JSON API...")

        # Paramiko SFTP can't create parent directories on put(); ensure API dir exists.
        api_dir = os.path.dirname(json_path)
        if api_dir:
            try:
                sftp.stat(api_dir)
            except Exception:
                _stdin, _stdout, _stderr = ssh.exec_command(f"mkdir -p {shlex.quote(api_dir)}")
                _stdout.channel.recv_exit_status()
         
        file_stat = sftp.stat(remote_path)
        file_mtime = int(file_stat.st_mtime or 0)
        
        json_data = {}
        try:
            with sftp.file(json_path, 'r') as json_file:
                json_content = json_file.read()
                try:
                    json_text = json_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        json_text = json_content.decode('utf-8-sig')
                    except:
                        json_text = json_content.decode('cp1251')
                
                json_data = json.loads(json_text)
                log(f"   ✓ Прочитан существующий JSON")
        except FileNotFoundError:
            log(f"   ⚠️ JSON не найден, создаём новый")
        except Exception as e:
            log(f"   ⚠️ Ошибка чтения JSON: {e}")
        
        import pytz
        moscow_tz = pytz.timezone('Europe/Moscow')
        modified_dt = datetime.fromtimestamp(file_mtime, tz=moscow_tz)
        
        st_size = file_stat.st_size
        file_size_int = int(st_size) if st_size is not None else 0

        json_data[channel] = {
            "version": version,
            "channel": channel,
            "file_name": remote_filename,
            "file_path": remote_path,
            "file_size": file_size_int,
            "mtime": file_mtime,
            "modified_at": modified_dt.isoformat(),
            "date": datetime.now(moscow_tz).strftime("%Y-%m-%d"),
            "release_notes": notes
        }
        
        json_data["last_updated"] = datetime.now(moscow_tz).isoformat()
        
        log(f"   ✓ Обновлён канал: {channel}")
        
        # Сохранение all_versions.json
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(json_data, tmp, indent=2, ensure_ascii=False)
            tmp_json_path = tmp.name
        
        sftp.put(tmp_json_path, json_path)
        os.unlink(tmp_json_path)
        log(f"   ✓ Сохранён all_versions.json")
        
        # Генерация отдельных JSON
        api_dir = os.path.dirname(json_path)
        
        if 'stable' in json_data:
            stable_path = f"{api_dir}/version_stable.json"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump(json_data['stable'], tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            sftp.put(tmp_path, stable_path)
            os.unlink(tmp_path)
            log(f"   ✓ Создан version_stable.json")
        
        if 'test' in json_data:
            test_path = f"{api_dir}/version_test.json"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump(json_data['test'], tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            sftp.put(tmp_path, test_path)
            os.unlink(tmp_path)
            log(f"   ✓ Создан version_test.json")
        
        sftp.close()
        ssh.close()
        
        return True, f"Деплой на {host} завершён"
        
    except Exception as e:
        import traceback
        log(f"❌ Ошибка:\n{traceback.format_exc()}")
        return False, str(e)[:100]
    finally:
        if ssh:
            try:
                ssh.close()
            except:
                pass
        if pem_key_path and os.path.exists(pem_key_path):
            try:
                os.unlink(pem_key_path)
            except:
                pass

# ═══════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("SSH Deploy Module")
    print("=" * 60)
    print(f"Configured: {is_ssh_configured()}")
    print(f"Info: {get_ssh_config_info()}")
    print(f"Servers: {len(VPS_SERVERS)}")
    print("=" * 60)
    
    if VPS_SERVERS:
        print("\nСписок серверов:")
        for i, server in enumerate(VPS_SERVERS, 1):
            auth = "пароль" if server.get('password') else "ключ"
            print(f"  {i}. {server['name']} ({server['host']}:{server['port']}) [{auth}]")
