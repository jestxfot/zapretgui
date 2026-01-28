# build_zapret/ssh_deploy.py
"""
SSH деплой на несколько VPS серверов с автоматическим обновлением JSON
Поддержка балансировки нагрузки между серверами
ОБНОВЛЕНО: Добавлена поддержка входа по паролю
"""

import paramiko
import os
import subprocess
from pathlib import Path
from typing import Optional, Any, List, Dict
import json
from datetime import datetime
import tempfile

# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ СЕРВЕРОВ
# ═══════════════════════════════════════════════════════════════

VPS_SERVERS = [
    # ═══ НОВЫЙ ОСНОВНОЙ СЕРВЕР (вход по паролю) ═══
    {
        'id': 'vps_super',
        'name': 'VPS Super (Новый основной)',
        'host': '185.114.116.232',
        'port': 22,
        'user': 'root',
        'password': 'MuN24tvDGL',  # ← Вход по паролю
        'key_path': None,
        'key_password': None,
        'upload_dir': '/var/www/zapret/download',
        'scripts_dir': '/root/zapretgpt/tests',
        'json_path': '/var/www/zapret/api/all_versions.json',
        'priority': 1,
        'use_for_telegram': True,
    },
    {
        'id': 'vps0',
        'name': 'VPS Primary (Новый основной)',
        'host': '45.144.30.84',
        'port': 22,
        'user': 'root',
        'password': '105SuT4QnL59',  # ← Вход по паролю
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
        'key_path': 'H:/Privacy/main',
        'key_password': 'zxcvbita2014',
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

def convert_key_to_pem(key_path: str, password: str = None) -> Optional[str]:
    """Конвертирует OpenSSH ключ в PEM формат для Paramiko"""
    try:
        temp_pem = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        temp_pem_path = temp_pem.name
        temp_pem.close()
        
        import shutil
        shutil.copy2(key_path, temp_pem_path)
        
        result = subprocess.run(
            ["ssh-keygen", "-p", "-f", temp_pem_path, "-m", "PEM", "-N", "", "-P", password if password else ""],
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

def is_ssh_configured() -> bool:
    """Проверка конфигурации SSH"""
    if not VPS_SERVERS:
        return False
    
    for server in VPS_SERVERS:
        # Сервер с паролем или с существующим ключом
        if server.get('password'):
            return True
        key_path = server.get('key_path')
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
    
    count = len(VPS_SERVERS)
    first = VPS_SERVERS[0]
    
    auth_type = "пароль" if first.get('password') else "ключ"
    
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
    password = server_config.get('password')
    key_path = server_config.get('key_path')
    key_password = server_config.get('key_password')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pem_key_path = None
    
    try:
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
            key = None
            
            for key_type, key_class in [
                ("RSA", paramiko.RSAKey),
                ("Ed25519", paramiko.Ed25519Key),
                ("ECDSA", paramiko.ECDSAKey),
            ]:
                try:
                    key = key_class.from_private_key_file(
                        str(key_path_obj),
                        password=key_password if key_password else None
                    )
                    log_func(f"✅ SSH ключ загружен ({key_type})")
                    break
                except:
                    continue
            
            if not key:
                log_func(f"⚠️ Прямая загрузка не удалась, пробуем конвертацию в PEM...")
                pem_key_path = convert_key_to_pem(str(key_path_obj), key_password)
                
                if pem_key_path:
                    try:
                        key = paramiko.RSAKey.from_private_key_file(pem_key_path)
                        log_func(f"✅ SSH ключ загружен после конвертации")
                    except Exception as e:
                        log_func(f"❌ Конвертация не помогла: {e}")
            
            if not key:
                return None, pem_key_path, "Не удалось загрузить SSH ключ"
            
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
            return ssh, pem_key_path, ""
            
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
        telegram_server = None
        for result in results:
            if result['success'] and result['config'].get('use_for_telegram', False):
                telegram_server = result['config']
                break
        
        if telegram_server:
            log(f"\n{'='*60}")
            log(f"📢 ПУБЛИКАЦИЯ В TELEGRAM")
            log(f"{'='*60}")
            log(f"📍 Выбран сервер: {telegram_server['name']}")
            
            telegram_success, telegram_message = _publish_to_telegram_via_ssh(
                channel=channel,
                version=version,
                notes=notes,
                server_config=telegram_server,
                log_queue=log_queue
            )
            
            if telegram_success:
                log(f"✅ Telegram публикация успешна")
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
        
        remote_filename = f"Zapret2Setup{'_TEST' if channel == 'test' else ''}.exe"
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
        remote_filename = f"Zapret2Setup{'_TEST' if channel == 'test' else ''}.exe"
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
            percent = int((transferred / total) * 100)
            if percent >= last_percent + 10:
                last_percent = percent - (percent % 10)
                log(f"   📊 {last_percent}% ({transferred/1024/1024:.1f}/{total/1024/1024:.1f} МБ)")
        
        sftp.put(str(file_path), remote_path, callback=progress_callback)
        
        log(f"✅ Файл загружен ({file_size_mb:.1f} МБ)")
        
        # ═══ ОБНОВЛЕНИЕ JSON ═══
        log(f"\n📝 Обновление JSON API...")
        
        file_stat = sftp.stat(remote_path)
        file_mtime = int(file_stat.st_mtime)
        
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
        
        json_data[channel] = {
            "version": version,
            "channel": channel,
            "file_path": remote_path,
            "file_size": int(file_stat.st_size),
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