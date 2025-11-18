# build_zapret/ssh_deploy.py
"""
SSH деплой на несколько VPS серверов с автоматическим обновлением JSON
Поддержка балансировки нагрузки между серверами
"""

import paramiko
import os
import subprocess
from pathlib import Path
from typing import Optional, Any, List, Dict
import json
from datetime import datetime
import tempfile

# ═══════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ СЕРВЕРОВ
# ═══════════════════════════════════════════════════════════

VPS_SERVERS = [
    {
        'id': 'vps1',
        'name': 'VPS Server 1 (Основной)',
        'host': '84.54.30.233',
        'port': 2089,
        'user': 'root',
        'key_path': 'H:/Privacy/main',
        'key_password': 'zxcvbita2014',
        'upload_dir': '/var/www/zapret/download',
        'scripts_dir': '/root/zapretgpt/tests',
        'json_path': '/var/www/zapret/api/all_versions.json',
        'priority': 1,
        'use_for_telegram': False,  # ❌ Основной сервер - только деплой
    },
    {
        'id': 'vps2',
        'name': 'VPS Server 2 (Резервный)',
        'host': '185.68.247.42',
        'port': 2089,
        'user': 'root',
        'key_path': 'H:/Privacy/main',
        'key_password': 'zxcvbita2014',
        'upload_dir': '/var/www/zapret/download',
        'scripts_dir': '/root/zapretgpt/tests',
        'json_path': '/var/www/zapret/api/all_versions.json',
        'priority': 2,
        'use_for_telegram': True,  # ✅ Этот сервер будет публиковать в Telegram
    },
]

# ═══════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════

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
    
    # Проверяем хотя бы один сервер
    for server in VPS_SERVERS:
        key_path = Path(server['key_path'])
        if key_path.exists():
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
    
    if count == 1:
        return f"SSH настроен (1 сервер): {first['user']}@{first['host']}"
    else:
        return f"SSH настроен ({count} серверов): {first['user']}@{first['host']} +{count-1}"

# ═══════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ ДЕПЛОЯ
# ═══════════════════════════════════════════════════════════

def deploy_to_all_servers(
    file_path: Path,
    channel: str,
    version: str,
    notes: str,
    publish_telegram: bool = False,  # ✅ Новый параметр
    log_queue: Optional[Any] = None
) -> tuple[bool, str]:
    """
    Деплой на все сервера из списка с публикацией в Telegram
    
    Args:
        file_path: Путь к .exe файлу
        channel: "stable" или "test"
        version: Версия (например, "16.5.26.4")
        notes: Release notes
        publish_telegram: Публиковать ли в Telegram после деплоя
        log_queue: Очередь для логов (опционально)
        
    Returns:
        (success, message): True если хотя бы один сервер успешен
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
    
    # Сортируем серверы по приоритету
    servers = sorted(VPS_SERVERS, key=lambda s: s['priority'])
    
    log(f"\n{'='*60}")
    log(f"📤 ДЕПЛОЙ НА {len(servers)} {'СЕРВЕР' if len(servers) == 1 else 'СЕРВЕРОВ'}")
    log(f"{'='*60}")
    
    results = []
    
    # ═══════════════════════════════════════════════════════
    # ШАГ 1: ДЕПЛОЙ НА ВСЕ СЕРВЕРА
    # ═══════════════════════════════════════════════════════
    
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
    
    # ═══════════════════════════════════════════════════════
    # ИТОГИ ДЕПЛОЯ
    # ═══════════════════════════════════════════════════════
    
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
    
    # Проверяем успешность деплоя
    if successful == 0:
        return False, "Деплой не удался ни на одном сервере"
    
    # ═══════════════════════════════════════════════════════
    # ШАГ 2: ПУБЛИКАЦИЯ В TELEGRAM (только с выделенного сервера)
    # ═══════════════════════════════════════════════════════
    
    if publish_telegram:
        # Ищем сервер для публикации в Telegram
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
            log(f"💡 Причина: менее нагруженный сервер (use_for_telegram=True)")
            
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
                log(f"⚠️ Telegram публикация не удалась: {telegram_message}")
                # Не прерываем - деплой уже успешен
        else:
            log(f"\n⚠️ Нет сервера с флагом 'use_for_telegram=True', пропускаем публикацию")
    
    # Финальный результат
    if successful < len(results):
        return True, f"Деплой завершён частично ({successful}/{len(results)} серверов)"
    else:
        return True, f"Деплой успешно завершён на всех {len(results)} серверах"

def _publish_to_telegram_via_ssh(
    channel: str,
    version: str,
    notes: str,
    server_config: Dict[str, Any],
    log_queue: Optional[Any] = None
) -> tuple[bool, str]:
    """
    Публикация в Telegram через SSH на конкретном сервере
    
    Args:
        channel: "stable" или "test"
        version: Версия релиза
        notes: Release notes
        server_config: Конфигурация сервера
        log_queue: Очередь для логов
        
    Returns:
        (success, message)
    """
    def log(msg: str):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)
    
    ssh = None
    pem_key_path = None
    
    try:
        # Извлекаем конфигурацию
        host = server_config['host']
        port = server_config['port']
        user = server_config['user']
        key_path = Path(server_config['key_path'])
        key_password = server_config.get('key_password')
        scripts_dir = server_config.get('scripts_dir')
        upload_dir = server_config['upload_dir']
        
        if not scripts_dir:
            return False, "scripts_dir не указан в конфигурации сервера"
        
        # Формируем путь к файлу на сервере
        remote_filename = f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
        remote_path = f"{upload_dir}/{remote_filename}"
        
        log(f"🔌 Подключение к {user}@{host}:{port}...")
        
        # ═══════════════════════════════════════════════════════
        # SSH ПОДКЛЮЧЕНИЕ
        # ═══════════════════════════════════════════════════════
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if not key_path.exists():
            return False, f"SSH ключ не найден: {key_path}"
        
        # Загрузка ключа (аналогично _deploy_to_single_server)
        key = None
        for key_type, key_class in [
            ("RSA", paramiko.RSAKey),
            ("Ed25519", paramiko.Ed25519Key),
            ("ECDSA", paramiko.ECDSAKey),
        ]:
            try:
                key = key_class.from_private_key_file(
                    str(key_path),
                    password=key_password if key_password else None
                )
                log(f"✅ SSH ключ загружен ({key_type})")
                break
            except:
                continue
        
        if not key:
            pem_key_path = convert_key_to_pem(str(key_path), key_password)
            if pem_key_path:
                try:
                    key = paramiko.RSAKey.from_private_key_file(pem_key_path)
                    log(f"✅ SSH ключ загружен после конвертации в PEM")
                except:
                    pass
        
        if not key:
            return False, "Не удалось загрузить SSH ключ"
        
        # Подключаемся
        ssh.connect(
            hostname=host,
            port=port,
            username=user,
            pkey=key,
            timeout=30
        )
        
        log(f"✅ Подключено к {host}")
        
        # ═══════════════════════════════════════════════════════
        # ЗАПУСК ПУБЛИКАЦИИ
        # ═══════════════════════════════════════════════════════
        
        # Экранируем кавычки в notes для bash
        notes_escaped = notes.replace('"', '\\"').replace('$', '\\$')
        
        telegram_cmd = (
            f"cd {scripts_dir} && "
            f"python3 ssh_telegram_publisher.py "
            f'"{remote_path}" "{channel}" "{version}" "{notes_escaped}"'
        )
        
        log(f"📤 Запуск: ssh_telegram_publisher.py")
        log(f"   Файл: {remote_path}")
        log(f"   Канал: {channel}")
        log(f"   Версия: {version}")
        
        stdin, stdout, stderr = ssh.exec_command(telegram_cmd, timeout=600)
        
        # Выводим stdout построчно
        for line in stdout:
            log(f"   {line.rstrip()}")
        
        exit_code = stdout.channel.recv_exit_status()
        
        # Выводим stderr если есть
        stderr_output = stderr.read().decode('utf-8')
        if stderr_output:
            for line in stderr_output.split('\n'):
                if line.strip():
                    log(f"   ⚠️ {line}")
        
        ssh.close()
        
        if exit_code == 0:
            return True, f"Telegram публикация выполнена с сервера {server_config['name']}"
        else:
            return False, f"Скрипт публикации завершился с кодом {exit_code}"
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log(f"❌ Ошибка публикации:\n{error_trace}")
        return False, f"Ошибка: {str(e)[:100]}"
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

# ═══════════════════════════════════════════════════════════
# ВНУТРЕННЯЯ ФУНКЦИЯ ДЕПЛОЯ НА ОДИН СЕРВЕР
# ═══════════════════════════════════════════════════════════

def _deploy_to_single_server(
    file_path: Path,
    channel: str,
    version: str,
    notes: str,
    server_config: Dict[str, Any],
    log_queue: Optional[Any] = None
) -> tuple[bool, str]:
    """
    Деплой файла на конкретный VPS сервер
    
    Args:
        file_path: Путь к .exe файлу
        channel: "stable" или "test"
        version: Версия релиза
        notes: Release notes
        server_config: Конфигурация сервера
        log_queue: Очередь для логов
        
    Returns:
        (success, message)
    """
    def log(msg: str):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)
    
    ssh = None
    pem_key_path = None
    
    try:
        # ═══════════════════════════════════════════════════════
        # ИЗВЛЕЧЕНИЕ КОНФИГУРАЦИИ
        # ═══════════════════════════════════════════════════════
        
        host = server_config['host']
        port = server_config['port']
        user = server_config['user']
        key_path = Path(server_config['key_path'])
        key_password = server_config.get('key_password')
        upload_dir = server_config['upload_dir']
        json_path = server_config['json_path']
        
        log(f"🔌 Подключение к {user}@{host}:{port}...")
        
        # ═══════════════════════════════════════════════════════
        # SSH ПОДКЛЮЧЕНИЕ
        # ═══════════════════════════════════════════════════════
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if not key_path.exists():
            return False, f"SSH ключ не найден: {key_path}"
        
        # Попытка загрузить ключ
        log(f"🔑 Загрузка SSH ключа: {key_path.name}")
        key = None
        key_error = None
        
        for key_type, key_class in [
            ("RSA", paramiko.RSAKey),
            ("Ed25519", paramiko.Ed25519Key),
            ("ECDSA", paramiko.ECDSAKey),
        ]:
            try:
                key = key_class.from_private_key_file(
                    str(key_path),
                    password=key_password if key_password else None
                )
                log(f"✅ SSH ключ загружен ({key_type})")
                break
            except Exception as e:
                key_error = e
                continue
        
        # Если прямая загрузка не удалась, пробуем конвертацию в PEM
        if not key:
            log(f"⚠️ Прямая загрузка не удалась, пробуем конвертацию в PEM...")
            pem_key_path = convert_key_to_pem(str(key_path), key_password)
            
            if pem_key_path:
                try:
                    key = paramiko.RSAKey.from_private_key_file(pem_key_path)
                    log(f"✅ SSH ключ загружен после конвертации в PEM")
                except Exception as e:
                    log(f"❌ Конвертация в PEM не помогла: {e}")
        
        if not key:
            return False, f"Не удалось загрузить SSH ключ: {key_error}"
        
        # Подключение
        log("🔌 Подключение с SSH ключом...")
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
        
        log("✅ Подключено к VPS")
        
        # Проверка
        stdin, stdout, stderr = ssh.exec_command("whoami", timeout=10)
        connected_user = stdout.read().decode().strip()
        log(f"✅ Вход под пользователем: {connected_user}")
        
        # ═══════════════════════════════════════════════════════
        # ЗАГРУЗКА ФАЙЛА
        # ═══════════════════════════════════════════════════════
        
        remote_filename = f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
        remote_path = f"{upload_dir}/{remote_filename}"
        
        log(f"📤 Загрузка {file_path.name} на VPS...")
        log(f"   → {remote_path}")
        
        sftp = ssh.open_sftp()
        
        # Создаём директорию если нужно
        try:
            sftp.stat(upload_dir)
        except:
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {upload_dir}")
            stdout.channel.recv_exit_status()
            log(f"✅ Создана директория: {upload_dir}")
        
        # Загружаем файл с прогрессом
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
        
        log(f"✅ Файл загружен на VPS ({file_size_mb:.1f} МБ)")
        
        # ═══════════════════════════════════════════════════════
        # ОБНОВЛЕНИЕ JSON API
        # ═══════════════════════════════════════════════════════
        
        log(f"\n📝 Обновление JSON API...")
        
        # Получаем информацию о файле
        file_stat = sftp.stat(remote_path)
        file_mtime = int(file_stat.st_mtime)
        
        # Читаем существующий JSON
        json_data = {}
        try:
            with sftp.file(json_path, 'r') as json_file:
                json_content = json_file.read()
                
                # Пробуем декодировать как UTF-8
                try:
                    json_text = json_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        json_text = json_content.decode('utf-8-sig')
                    except:
                        json_text = json_content.decode('cp1251')
                
                json_data = json.loads(json_text)
                
                log(f"   ✓ Прочитан существующий JSON")
                existing_channels = [k for k in json_data.keys() if k in ['stable', 'test']]
                log(f"   ✓ Найдено каналов: {len(existing_channels)} ({', '.join(existing_channels)})")
                
        except FileNotFoundError:
            log(f"   ⚠️ JSON файл не найден, создаём новый")
        except json.JSONDecodeError as e:
            log(f"   ⚠️ Ошибка парсинга JSON: {e}, создаём новый")
        except Exception as e:
            log(f"   ⚠️ Ошибка чтения JSON: {e}, создаём новый")
        
        # Обновляем данные для текущего канала
        import pytz
        
        moscow_tz = pytz.timezone('Europe/Moscow')
        modified_dt = datetime.fromtimestamp(file_mtime, tz=moscow_tz)
        
        # ✅ Обновляем только текущий канал, остальные сохраняем
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
        
        all_channels = [k for k in json_data.keys() if k in ['stable', 'test']]
        log(f"   ✓ Всего каналов в JSON: {len(all_channels)} ({', '.join(all_channels)})")
        
        # ═══════════════════════════════════════════════════════
        # СОХРАНЕНИЕ all_versions.json
        # ═══════════════════════════════════════════════════════
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(json_data, tmp, indent=2, ensure_ascii=False)
            tmp_json_path = tmp.name
        
        sftp.put(tmp_json_path, json_path)
        os.unlink(tmp_json_path)
        
        log(f"   ✓ Сохранён all_versions.json")
        
        # ═══════════════════════════════════════════════════════
        # ✅ ГЕНЕРАЦИЯ ОТДЕЛЬНЫХ JSON ДЛЯ КАЖДОГО КАНАЛА
        # ═══════════════════════════════════════════════════════
        
        api_dir = os.path.dirname(json_path)
        
        # Генерируем version_stable.json
        if 'stable' in json_data:
            stable_json_path = f"{api_dir}/version_stable.json"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump(json_data['stable'], tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            
            sftp.put(tmp_path, stable_json_path)
            os.unlink(tmp_path)
            
            log(f"   ✓ Создан version_stable.json")
        
        # Генерируем version_test.json
        if 'test' in json_data:
            test_json_path = f"{api_dir}/version_test.json"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump(json_data['test'], tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            
            sftp.put(tmp_path, test_json_path)
            os.unlink(tmp_path)
            
            log(f"   ✓ Создан version_test.json")
        
        # ═══════════════════════════════════════════════════════
        # ИТОГОВАЯ ИНФОРМАЦИЯ
        # ═══════════════════════════════════════════════════════
        
        log(f"\n✅ Все JSON файлы обновлены:")
        log(f"   • Канал: {channel}")
        log(f"   • Версия: {version}")
        log(f"   • Размер: {file_size_mb:.1f} МБ")
        log(f"   • Время: {modified_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"   • Доступные каналы: {', '.join(all_channels)}")
        log(f"   • Созданы файлы:")
        log(f"     - all_versions.json")
        if 'stable' in json_data:
            log(f"     - version_stable.json")
        if 'test' in json_data:
            log(f"     - version_test.json")
        
        sftp.close()
        
        ssh.close()
        
        return True, f"Деплой на {host} завершён успешно"
        
    except paramiko.AuthenticationException as e:
        return False, f"SSH аутентификация: {e}"
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log(f"❌ Полная ошибка:\n{error_trace}")
        return False, f"Ошибка: {str(e)[:100]}"
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

# ═══════════════════════════════════════════════════════════
# ТОЧКА ВХОДА ДЛЯ ТЕСТИРОВАНИЯ
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("SSH Deploy Module for Multiple Servers")
    print("=" * 60)
    print(f"Configured: {is_ssh_configured()}")
    print(f"Info: {get_ssh_config_info()}")
    print(f"Servers: {len(VPS_SERVERS)}")
    print("=" * 60)
    
    if VPS_SERVERS:
        print("\nСписок серверов:")
        for i, server in enumerate(VPS_SERVERS, 1):
            print(f"  {i}. {server['name']} ({server['host']}:{server['port']}) - приоритет {server['priority']}")