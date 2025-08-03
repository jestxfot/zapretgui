"""
build_tools/ssh_deploy.py - SSH деплой на VPS сервер
"""

from pathlib import Path
from typing import Optional, Tuple
import stat
import json
from datetime import date

# ════════════════════════════════════════════════════════════════
# НАСТРОЙКИ SSH - ИЗМЕНИТЕ НА СВОИ
# ════════════════════════════════════════════════════════════════
SSH_PORT = 22  # Порт SSH, обычно 22
SSH_HOST = "88.210.21.236"  # Ваш сервер
SSH_USERNAME = "root"
SSH_PASSWORD = "3btNATB94p"  # Или используйте SSH ключ
SSH_KEY_PATH = ""  # Например: "C:/Users/You/.ssh/id_rsa"
REMOTE_PATH = "/root/zapretgpt"
SSH_ENABLED = True  # Включить деплой

# URL для скачивания файлов (измените на свой домен)
#DOWNLOAD_BASE_URL = "https://nozapret.ru"

# ════════════════════════════════════════════════════════════════

def is_ssh_configured() -> bool:
    """Проверяет, настроен ли SSH"""
    return SSH_ENABLED and SSH_HOST and SSH_USERNAME

def get_ssh_config_info() -> str:
    """Возвращает информацию о текущей конфигурации SSH"""
    if not SSH_ENABLED:
        return "SSH деплой выключен"
    if not SSH_HOST:
        return "SSH не настроен"
    return f"SSH: {SSH_USERNAME}@{SSH_HOST}:{SSH_PORT}"

def create_version_json(channel: str, version: str, notes: str, existing_data: dict = None) -> str:
    """Создает содержимое version.json"""
    if existing_data is None:
        existing_data = {
            "stable": {},
            "test": {}
        }
    
    # Обновляем данные для нужного канала
    existing_data[channel] = {
        "version": version,
        #"update_url": f"{DOWNLOAD_BASE_URL}/ZapretSetup{'_TEST' if channel == 'test' else ''}.exe",
        "release_notes": notes,
        "date": date.today().strftime("%Y-%m-%d")
    }
    
    return json.dumps(existing_data, indent=2, ensure_ascii=False)

def deploy_to_vps(file_path: Path, channel: str = None, version: str = None, 
                  notes: str = None, log_queue=None) -> Tuple[bool, str]:
    """
    Отправляет файл на VPS сервер и обновляет version.json
    Возвращает (успех, сообщение)
    """
    if not SSH_ENABLED:
        return False, "SSH деплой выключен"
        
    if not file_path.exists():
        return False, f"Файл не найден: {file_path}"
    
    try:
        import paramiko
    except ImportError:
        return False, "Модуль paramiko не установлен. Выполните: pip install paramiko"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Логируем
        if log_queue:
            log_queue.put(f"📡 Подключение к {SSH_USERNAME}@{SSH_HOST}:{SSH_PORT}")
        
        # Подключаемся
        if SSH_KEY_PATH and Path(SSH_KEY_PATH).exists():
            ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USERNAME, 
                       key_filename=SSH_KEY_PATH, timeout=30)
        else:
            ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USERNAME, 
                       password=SSH_PASSWORD, timeout=30)
        
        if log_queue:
            log_queue.put("✅ SSH соединение установлено")
        
        # Создаем директорию если нужно
        if log_queue:
            log_queue.put(f"📁 Создание директории {REMOTE_PATH}")
        
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {REMOTE_PATH}')
        stdout.read()
        
        # Открываем SFTP сессию
        sftp = ssh.open_sftp()
        
        # 1. Копируем основной файл
        remote_file = f"{REMOTE_PATH}/{file_path.name}"
        
        if log_queue:
            log_queue.put(f"📤 Отправка {file_path.name} → {remote_file}")
        
        # Callback для прогресса
        file_size = file_path.stat().st_size
        transferred = 0
        last_percent = 0
        
        def progress_callback(current, total):
            nonlocal transferred, last_percent
            transferred = current
            percent = int((current / total) * 100)
            if log_queue and percent >= last_percent + 10:  # Логируем каждые 10%
                last_percent = percent
                log_queue.put(f"    Прогресс: {percent}%")
        
        # Отправляем файл
        sftp.put(str(file_path), remote_file, callback=progress_callback)
        
        # Устанавливаем права на выполнение
        sftp.chmod(remote_file, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        
        if log_queue:
            log_queue.put(f"✅ Файл успешно отправлен: {remote_file}")
        
        # 2. Обновляем version.json если переданы параметры
        if channel and version:
            version_path = f"{REMOTE_PATH}/version.json"
            
            if log_queue:
                log_queue.put(f"📄 Обновление {version_path}")
            
            # Пытаемся загрузить существующий version.json
            existing_data = None
            try:
                # Загружаем существующий файл
                with sftp.open(version_path, 'r') as f:
                    existing_data = json.load(f)
                    if log_queue:
                        log_queue.put("    Загружен существующий version.json")
            except Exception as e:
                if log_queue:
                    log_queue.put("    Создаётся новый version.json")
                existing_data = {"stable": {}, "test": {}}
            
            # Создаем обновленный JSON
            json_content = create_version_json(channel, version, notes or f"Zapret {version}", existing_data)
            
            # Сохраняем во временный локальный файл
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.json') as tmp:
                tmp.write(json_content)
                tmp_path = tmp.name
            
            try:
                # Отправляем на сервер
                sftp.put(tmp_path, version_path)
                
                # Устанавливаем права на чтение
                sftp.chmod(version_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                
                if log_queue:
                    log_queue.put(f"✅ version.json обновлен для {channel}: {version}")
                    
            finally:
                # Удаляем временный файл
                Path(tmp_path).unlink(missing_ok=True)
        
        sftp.close()
        ssh.close()
        
        return True, f"Файлы успешно развернуты в {REMOTE_PATH}"
        
    except paramiko.AuthenticationException:
        return False, "Ошибка аутентификации SSH"
    except paramiko.SSHException as e:
        return False, f"SSH ошибка: {str(e)}"
    except Exception as e:
        return False, f"Ошибка деплоя: {str(e)}"
    finally:
        try:
            ssh.close()
        except:
            pass