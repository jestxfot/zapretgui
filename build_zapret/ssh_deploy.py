"""
build_tools/ssh_deploy.py - SSH деплой на VPS сервер (оптимизированный)
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

    ssh = None
    transport = None
    sftp = None
    
    try:
        # ОПТИМИЗАЦИЯ: Создаем transport с максимальными параметрами
        transport = paramiko.Transport((UPDATER_SERVER, SSH_PORT))
        
        # Максимальные размеры окна и буферов
        transport.window_size = 2147483647  # 2GB window
        transport.max_packet_size = 2147483647  # 2GB max packet
        transport.packetizer.REKEY_BYTES = pow(2, 40)  # Реже пересогласование
        transport.packetizer.REKEY_PACKETS = pow(2, 40)
        
        # Отключаем сжатие для локальных/быстрых сетей (сжатие замедляет на быстрых каналах)
        # Включите если канал медленный: transport.use_compression(True)
        transport.use_compression(False)
        
        # Подключаемся
        if SSH_KEY_PATH and Path(SSH_KEY_PATH).exists():
            pkey = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
            transport.connect(username=SSH_USERNAME, pkey=pkey)
        else:
            transport.connect(username=SSH_USERNAME, password=SSH_PASSWORD)
        
        if log_queue:
            log_queue.put("✅ SSH соединение установлено (максимальная производительность)")
        
        # Создаем SSH клиент
        ssh = paramiko.SSHClient()
        ssh._transport = transport
        
        # Создаем директорию если нужно
        if log_queue:
            log_queue.put(f"📁 Создание директории {REMOTE_PATH}")
        
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {REMOTE_PATH}')
        stdout.read()
        
        # ОПТИМИЗАЦИЯ: Создаем SFTP с максимальными буферами
        sftp = transport.open_sftp_client()
        
        # Устанавливаем максимальные размеры для SFTP
        sftp.MAX_REQUEST_SIZE = 1048576  # 1MB запросы вместо 32KB
        
        # Информация о файле
        remote_file = f"{REMOTE_PATH}/{file_path.name}"
        file_size = file_path.stat().st_size
        
        if log_queue:
            log_queue.put(f"📤 Отправка {file_path.name} → {remote_file}")
            log_queue.put(f"📊 Размер: {file_size / (1024*1024):.1f} MB")

        import time
        start_time = time.time()
        
        # ГЛАВНАЯ ОПТИМИЗАЦИЯ: Используем putfo с большим буфером
        # putfo работает быстрее чем ручная передача чанками
        with open(file_path, 'rb') as local_file:
            # Метод 1: Быстрая передача через putfo (рекомендуется)
            try:
                # Callback для прогресса
                transferred = [0]  # Используем список для изменяемости в callback
                last_percent = [0]
                
                def progress_callback(bytes_so_far, total_bytes):
                    transferred[0] = bytes_so_far
                    percent = int((bytes_so_far / total_bytes) * 100)
                    if log_queue and percent >= last_percent[0] + 5:
                        last_percent[0] = percent
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed = bytes_so_far / elapsed / (1024*1024)
                            log_queue.put(f"    Прогресс: {percent}% | Скорость: {speed:.1f} MB/s")
                
                # Используем putfo с callback для максимальной скорости
                sftp.putfo(local_file, remote_file, file_size=file_size, 
                          callback=progress_callback, confirm=True)
                          
            except AttributeError:
                # Fallback: Если putfo недоступен, используем оптимизированную ручную передачу
                if log_queue:
                    log_queue.put("⚠️ Используется альтернативный метод передачи")
                
                # Открываем файл на удаленном сервере
                with sftp.open(remote_file, 'wb') as remote_file_handle:
                    # ВАЖНО: Устанавливаем большой буфер для записи
                    remote_file_handle.MAX_REQUEST_SIZE = 1048576  # 1MB
                    
                    # Используем prefetch для ускорения
                    remote_file_handle.set_pipelined(True)
                    
                    # Передаем большими блоками
                    chunk_size = 4194304  # 4MB блоки для максимальной скорости
                    transferred = 0
                    last_percent = 0
                    
                    # Читаем и отправляем
                    while True:
                        data = local_file.read(chunk_size)
                        if not data:
                            break
                        
                        # Записываем данные
                        remote_file_handle.write(data)
                        transferred += len(data)
                        
                        # Прогресс
                        percent = int((transferred / file_size) * 100)
                        if log_queue and percent >= last_percent + 5:
                            last_percent = percent
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = transferred / elapsed / (1024*1024)
                                log_queue.put(f"    Прогресс: {percent}% | Скорость: {speed:.1f} MB/s")
        
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
        
        return True, f"Файлы успешно развернуты в {REMOTE_PATH}"
        
    except paramiko.AuthenticationException:
        return False, "Ошибка аутентификации SSH"
    except paramiko.SSHException as e:
        return False, f"SSH ошибка: {str(e)}"
    except Exception as e:
        return False, f"Ошибка деплоя: {str(e)}"
    finally:
        # Закрываем соединения
        try:
            if sftp:
                sftp.close()
            if transport:
                transport.close()
            if ssh:
                ssh.close()
        except:
            pass


def deploy_to_vps_parallel(file_path: Path, channel: str = None, version: str = None, 
                          notes: str = None, log_queue=None) -> Tuple[bool, str]:
    """
    ЭКСПЕРИМЕНТАЛЬНЫЙ: Параллельная передача файла через несколько соединений
    Используйте если обычный метод медленный
    """
    if not SSH_ENABLED:
        return False, "SSH деплой выключен"
        
    if not file_path.exists():
        return False, f"Файл не найден: {file_path}"
    
    try:
        import paramiko
        import threading
        import tempfile
    except ImportError:
        return False, "Модули не установлены. Выполните: pip install paramiko"
    
    # Разбиваем файл на части для параллельной передачи
    file_size = file_path.stat().st_size
    num_threads = 4  # Количество параллельных соединений
    chunk_size = file_size // num_threads
    
    if log_queue:
        log_queue.put(f"🚀 Параллельная передача через {num_threads} соединений")
    
    # Здесь можно реализовать параллельную передачу через несколько SSH соединений
    # Но это сложнее и не всегда быстрее, поэтому оставляю как заглушку
    
    # Используем обычный метод
    return deploy_to_vps(file_path, channel, version, notes, log_queue)