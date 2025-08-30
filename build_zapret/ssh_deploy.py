"""
build_tools/ssh_deploy.py - SSH деплой на VPS сервер
"""

from pathlib import Path
from typing import Optional, Tuple
import stat
import json
from datetime import date
from build_zapret import UPDATER_SERVER, SSH_PASSWORD

# ════════════════════════════════════════════════════════════════
# НАСТРОЙКИ SSH - ИЗМЕНИТЕ НА СВОИ
# ════════════════════════════════════════════════════════════════
SSH_PORT = 22  # Порт SSH, обычно 22
SSH_USERNAME = "root"
SSH_KEY_PATH = ""  # Например: "C:/Users/You/.ssh/id_rsa"
REMOTE_PATH = "/root/zapretgpt"
SSH_ENABLED = True  # Включить деплой

# URL для скачивания файлов (измените на свой домен)
#DOWNLOAD_BASE_URL = "https://nozapret.ru"

# ════════════════════════════════════════════════════════════════

def is_ssh_configured() -> bool:
    """Проверяет, настроен ли SSH"""
    return SSH_ENABLED and UPDATER_SERVER and SSH_USERNAME

def get_ssh_config_info() -> str:
    """Возвращает информацию о текущей конфигурации SSH"""
    if not SSH_ENABLED:
        return "SSH деплой выключен"
    if not UPDATER_SERVER:
        return "SSH не настроен"
    return f"SSH: {SSH_USERNAME}@{UPDATER_SERVER}:{SSH_PORT}"

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
    
    # Создаем Transport с оптимизированными параметрами
    transport = None
    
    try:
        # Создаем transport напрямую для большего контроля
        transport = paramiko.Transport((UPDATER_SERVER, SSH_PORT))
        
        # ОПТИМИЗАЦИЯ 1: Увеличиваем размер окна и пакетов
        transport.window_size = 2147483647  # Максимальный размер окна (2GB)
        transport.packetizer.REKEY_BYTES = pow(2, 40)  # Реже пересогласование ключей
        transport.packetizer.REKEY_PACKETS = pow(2, 40)
        
        # ОПТИМИЗАЦИЯ 2: Включаем сжатие (ускоряет на медленных каналах)
        transport.use_compression(True)
        
        # Подключаемся
        if SSH_KEY_PATH and Path(SSH_KEY_PATH).exists():
            pkey = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
            transport.connect(username=SSH_USERNAME, pkey=pkey)
        else:
            transport.connect(username=SSH_USERNAME, password=SSH_PASSWORD)
        
        if log_queue:
            log_queue.put("✅ SSH соединение установлено (оптимизированное)")
        
        # Создаем SSH и SFTP клиентов
        ssh = paramiko.SSHClient()
        ssh._transport = transport
        
        # ОПТИМИЗАЦИЯ 3: Увеличиваем буфер SFTP
        sftp = transport.open_sftp_client()
        
        # Увеличиваем размер буфера чтения/записи
        sftp.MAX_REQUEST_SIZE = 32768  # 32KB вместо стандартных 32KB

        # Создаем директорию если нужно
        if log_queue:
            log_queue.put(f"📁 Создание директории {REMOTE_PATH}")
        
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {REMOTE_PATH}')
        stdout.read()
        
        # Открываем SFTP сессию
        sftp = ssh.open_sftp()
        
        # 1. Копируем основной файл
        remote_file = f"{REMOTE_PATH}/{file_path.name}"
        file_size = file_path.stat().st_size
        
        if log_queue:
            log_queue.put(f"📤 Отправка {file_path.name} → {remote_file}")
            log_queue.put(f"📊 Размер: {file_size / (1024*1024):.1f} MB")

        # Открываем файлы с буферизацией
        import time
        start_time = time.time()
        
        # ОПТИМИЗАЦИЯ 5: Используем prefetch для параллельной передачи
        with open(file_path, 'rb') as local_file:
            # Открываем удаленный файл для записи
            remote_file_handle = sftp.open(remote_file, 'wb')
            
            # Устанавливаем размер буфера
            remote_file_handle.MAX_REQUEST_SIZE = 65536  # 64KB chunks
            
            # Передаем файл большими блоками
            chunk_size = 262144  # 256KB блоки
            transferred = 0
            last_percent = 0
            
            while True:
                data = local_file.read(chunk_size)
                if not data:
                    break
                
                remote_file_handle.write(data)
                transferred += len(data)
                
                # Прогресс
                percent = int((transferred / file_size) * 100)
                if log_queue and percent >= last_percent + 5:
                    last_percent = percent
                    speed = transferred / (time.time() - start_time) / (1024*1024)
                    log_queue.put(f"    Прогресс: {percent}% | Скорость: {speed:.1f} MB/s")
            
            remote_file_handle.close()
        
        # Логируем результат
        elapsed = time.time() - start_time
        speed = file_size / elapsed / (1024*1024)
        if log_queue:
            log_queue.put(f"✅ Передано за {elapsed:.1f} сек. Средняя скорость: {speed:.1f} MB/s")
        
        # Устанавливаем права
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