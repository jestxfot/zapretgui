import os
import time
import subprocess
import win32con
from log import *

class DPIStarter:
    """Класс для запуска и управления процессами DPI."""
    
    def __init__(self, winws_exe, bin_folder, lists_folder, status_callback=None):
        """
        Инициализирует DPIStarter.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            bin_folder (str): Путь к папке с бинарными файлами
            lists_folder (str): Путь к папке со списками
            status_callback (callable): Функция обратного вызова для отображения статуса
        """
        self.winws_exe = winws_exe
        self.bin_folder = bin_folder
        self.lists_folder = lists_folder
        self.status_callback = status_callback
    
    def set_status(self, text):
        """Отображает статусное сообщение."""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)
    
    def download_files(self, download_urls):
        """
        Скачивает необходимые файлы.
        
        Args:
            download_urls (dict): Словарь с URL для скачивания
        
        Returns:
            bool: True при успешном скачивании, False при ошибке
        """
        # Эта функция может вызывать внешний загрузчик
        # или иметь собственную реализацию загрузки файлов
        from downloader import download_files
        return download_files(
            bin_folder=self.bin_folder,
            lists_folder=self.lists_folder,
            download_urls=download_urls,
            status_callback=self.set_status
        )
    
    def stop_dpi(self):
        """
        Останавливает процесс DPI и связанные службы.
        
        Returns:
            bool: True при успешной остановке, False при ошибке
        """
        try:
            # Проверяем наличие службы ZapretCensorliber
            service_name = "ZapretCensorliber"
            check_service_cmd = f'sc query "{service_name}"'
            result = subprocess.run(check_service_cmd, shell=True, capture_output=True, text=True)
            
            # Более надежная проверка на существование службы
            service_exists = False
            if result.returncode == 0:  # Команда выполнилась успешно
                service_exists = True
            elif "1060" not in result.stderr and "1060" not in result.stdout:
                # Если код ошибки не содержит 1060 (служба не существует)
                log(f"Ошибка при выполнении команды: {result.stderr}")
                service_exists = True
            
            if service_exists:
                # Более детальное сообщение об ошибке
                self.set_status("Пожалуйста, сначала ОТКЛЮЧИТЕ АВТОЗАПУСК!")
                # Показываем сообщение в консоль для отладки
                log(f"Обнаружена служба {service_name}. Выход из stop_dpi().")
                log(f"Результат команды sc query: {result.stdout}")
                return False

            log("Служба ZapretCensorliber не найдена, продолжаем остановку DPI.")   
            self.set_status("Останавливаю DPI и связанные службы...")

            # Проверяем запущен ли процесс winws.exe
            is_running = self.check_process_running()
            
            if is_running:
                self.set_status("Останавливаю запущенный процесс DPI...")
                # Останавливаем процесс winws.exe
                subprocess.run("taskkill /IM winws.exe /F", shell=True, check=False)
                log("Процесс winws.exe остановлен")
            else:
                self.set_status("Процесс DPI не запущен")
                log("Процесс winws.exe не запущен, нет необходимости в остановке")
            
            # Проверяем наличие служб, связанных с DPI
            services_found = False
            
            # Список служб для проверки, остановки и удаления
            services = ["Zapret", "WinDivert", "WinDivert14", "GoodbyeDPI"]
            
            # Сначала проверяем, есть ли вообще службы для остановки
            for service in services:
                check_cmd = f'sc query "{service}"'
                check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                
                # Если служба существует
                if "1060" not in check_result.stderr and "1060" not in check_result.stdout:
                    services_found = True
                    break
            
            if services_found:
                self.set_status("Останавливаю связанные службы...")
                
                # Останавливаем и удаляем службы
                for service in services:
                    try:
                        # Проверяем существует ли служба
                        check_cmd = f'sc query "{service}"'
                        check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                        
                        # Если служба не существует (код 1060), пропускаем
                        service_check_exists = True
                        if "1060" in check_result.stderr or "1060" in check_result.stdout:
                            log(f"Служба {service} не найдена, пропускаем.")
                            service_check_exists = False
                        
                        if not service_check_exists:
                            continue
                        
                        # Останавливаем службу
                        stop_cmd = f'net stop "{service}"'
                        subprocess.run(stop_cmd, shell=True, check=False, 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        # Удаляем службу
                        delete_cmd = f'sc delete "{service}"'
                        subprocess.run(delete_cmd, shell=True, check=False,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        log(f"Служба {service} остановлена и удалена")
                        self.set_status(f"Служба {service} остановлена и удалена")
                    except Exception as e:
                        # Игнорируем ошибки при остановке/удалении служб
                        log(f"Ошибка при остановке/удалении службы {service}: {str(e)}")
                        pass
                
                self.set_status("Связанные службы остановлены")
            else:
                log("Связанные службы не найдены")
            
            # Проверяем, действительно ли процесс остановлен
            if is_running:
                time.sleep(0.5)  # Даем время на завершение процесса
                if self.check_process_running():
                    # Если процесс все еще запущен, пробуем еще раз с другими параметрами
                    log("Процесс winws.exe все еще запущен, пробуем альтернативный метод остановки")
                    try:
                        # Пробуем остановить все экземпляры с /T (остановка дерева процессов)
                        subprocess.run("taskkill /IM winws.exe /F /T", shell=True, check=False)
                        time.sleep(0.3)
                        
                        # Если не помогло, ищем PID и останавливаем конкретно его
                        if self.check_process_running():
                            result = subprocess.run(
                                'tasklist /FI "IMAGENAME eq winws.exe" /NH',
                                shell=True, capture_output=True, text=True
                            )
                            
                            pid_line = [line for line in result.stdout.split('\n') if "winws.exe" in line]
                            if pid_line:
                                pid_parts = pid_line[0].split()
                                if len(pid_parts) >= 2:
                                    pid = pid_parts[1]
                                    subprocess.run(f"taskkill /PID {pid} /F", shell=True, check=False)
                                    log(f"Остановлен процесс с PID {pid}")
                    except Exception as e:
                        log(f"Ошибка при альтернативной остановке: {str(e)}")
            
            # Финальная проверка
            if self.check_process_running():
                log("ВНИМАНИЕ: Не удалось полностью остановить процесс winws.exe")
                self.set_status("Внимание: Процесс не был полностью остановлен")
                # Но все равно возвращаем True, так как мы попытались остановить
                return True
            
            # Если мы дошли до сюда, значит процесс точно остановлен
            self.set_status("Программа и связанные службы остановлены")
            return True
        except Exception as e:
            error_msg = f"Ошибка при остановке DPI: {str(e)}"
            log(error_msg)  # Логируем ошибку
            self.set_status(error_msg)
            return False

    def start_dpi(self, mode, dpi_commands, download_urls=None):
        """
        Запускает DPI с выбранной конфигурацией.
        
        Args:
            mode (str): Название режима запуска
            dpi_commands (dict): Словарь с настройками команд для разных режимов
            download_urls (dict, optional): URL для скачивания файлов, если они отсутствуют
        
        Returns:
            bool: True при успешном запуске, False при ошибке
        """
        try:
            # Сначала останавливаем предыдущий процесс
            self.stop_dpi()
            time.sleep(0.1)  # Небольшая пауза
            
            # Проверяем существование папок и создаем при необходимости
            if not os.path.exists(self.bin_folder):
                os.makedirs(self.bin_folder, exist_ok=True)
                self.set_status(f"Создана папка {self.bin_folder}")
                log(f"Создана папка {self.bin_folder}")
                
            if not os.path.exists(self.lists_folder):
                os.makedirs(self.lists_folder, exist_ok=True)
                self.set_status(f"Создана папка {self.lists_folder}")
                log(f"Создана папка {self.lists_folder}")
            
            # Проверяем наличие исполняемого файла
            exe_path = os.path.abspath(self.winws_exe)
            if not os.path.exists(exe_path):
                if download_urls and self.download_files(download_urls):
                    self.set_status("Необходимые файлы скачаны")
                    log(f"Необходимые файлы скачаны")
                else:
                    log(f"Файл {exe_path} не найден и не может быть скачан")
                    raise FileNotFoundError(f"Файл {exe_path} не найден и не может быть скачан")
            
            # Получаем командную строку из настроек
            command_string = dpi_commands.get(mode, "")
            
            # Если передана строка, разбиваем на аргументы
            if isinstance(command_string, str):
                command_args = command_string.split()
            else:
                command_args = command_string.copy()  # Создаем копию списка
            
            # Обрабатываем аргументы с путями к файлам
            for i, arg in enumerate(command_args):
                if ".txt" in arg or ".bin" in arg:
                    if "=" in arg:
                        prefix, filename = arg.split("=", 1)
                        if ".txt" in filename:
                            full_path = os.path.join(os.path.abspath(self.lists_folder), os.path.basename(filename))
                            # Проверяем существование файла и создаем если нужно
                            if not os.path.exists(full_path):
                                with open(full_path, 'w', encoding='utf-8') as f:
                                    f.write("# Автоматически созданный файл\n")
                            # Заменяем путь к файлу
                            command_args[i] = f"{prefix}={full_path}"
                        elif ".bin" in filename:
                            full_path = os.path.join(os.path.abspath(self.bin_folder), os.path.basename(filename))
                            command_args[i] = f"{prefix}={full_path}"
            
            # Формируем окончательную команду
            command = [exe_path] + command_args
            
            log(exe_path)  # Логируем путь к исполняемому файлу
            log(command_args)  # Логируем аргументы
            log(command)  # Логируем команду для отладки
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32con.SW_HIDE  # Полностью скрываем окно
            
            process = subprocess.Popen(
                command,
                startupinfo=startupinfo,
                cwd=os.getcwd()
            )

            log(f"Запущен процесс: {process.pid}")
            
            if process.poll() is None:
                self.set_status(f"Запущен {mode}")
                log(f"ZAPRET УСПЕШНО ЗАПУЩЕН {mode}")
                return True
            else:
                log(f"Ошибка при запуске {mode}: {process.returncode}")
                raise Exception("Не удалось запустить процесс")
                    
        except Exception as e:
            error_msg = f"Ошибка при запуске {mode}: {str(e)}"
            log(error_msg)  # Логируем ошибку
            self.set_status(error_msg)
            return False
    def check_process_running(self):
        """
        Улучшенная проверка запущен ли процесс DPI с подробной диагностикой.
        
        Returns:
            bool: True если процесс запущен, False если не запущен
        """
        try:
            log("Начинаю проверку наличия процесса winws.exe...")
            
            # Метод 1: Проверка через tasklist
            log("Метод 1: Проверка через tasklist")
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq winws.exe" /NH',
                shell=True, 
                capture_output=True, 
                text=True,
                encoding='cp866'  # Используем кодировку cp866 для корректного отображения русских символов
            )
            
            log(f"Результат команды tasklist: {result.stdout.strip()}")
            
            if "winws.exe" in result.stdout:
                log("Процесс winws.exe найден через tasklist")
                pid_line = [line for line in result.stdout.split('\n') if "winws.exe" in line]
                
                if pid_line:
                    log(f"Строка с информацией о процессе: {pid_line[0]}")
                    pid_parts = pid_line[0].split()
                    
                    if len(pid_parts) >= 2:
                        pid = pid_parts[1]
                        log(f"Найден PID процесса: {pid}")
                        return True
                
                log("Процесс найден, но не удалось определить PID")
                return True  # Процесс найден, даже если мы не смогли извлечь PID
            
            # Метод 2: Проверка через PowerShell (работает лучше на некоторых системах)
            log("Метод 2: Проверка через PowerShell")
            try:
                ps_cmd = 'powershell -Command "Get-Process -Name winws -ErrorAction SilentlyContinue | Select-Object Id"'
                ps_result = subprocess.run(
                    ps_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                log(f"Результат PowerShell: {ps_result.stdout.strip()}")
                
                # Если есть любая строка, содержащая число после Id
                if any(line.strip().isdigit() for line in ps_result.stdout.split('\n') if line.strip()):
                    log("Процесс winws.exe найден через PowerShell")
                    return True
            except Exception as ps_error:
                log(f"Ошибка при проверке через PowerShell: {str(ps_error)}")
            
            # Метод 3: Проверка через wmic (работает даже на старых системах)
            log("Метод 3: Проверка через wmic")
            try:
                wmic_result = subprocess.run(
                    'wmic process where "name=\'winws.exe\'" get processid',
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                log(f"Результат wmic: {wmic_result.stdout.strip()}")
                
                lines = [line.strip() for line in wmic_result.stdout.split('\n') if line.strip()]
                # Проверяем есть ли более одной строки (заголовок + данные)
                if len(lines) > 1:
                    log("Процесс winws.exe найден через wmic")
                    return True
            except Exception as wmic_error:
                log(f"Ошибка при проверке через wmic: {str(wmic_error)}")
                
            # Метод 4: Проверка через простую команду findstr
            log("Метод 4: Проверка через tasklist и findstr")
            try:
                findstr_result = subprocess.run(
                    'tasklist | findstr "winws"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                log(f"Результат findstr: {findstr_result.stdout.strip()}")
                
                if findstr_result.stdout.strip():
                    log("Процесс winws.exe найден через findstr")
                    return True
            except Exception as findstr_error:
                log(f"Ошибка при проверке через findstr: {str(findstr_error)}")
            
            # Проверка существования файла блокировки
            # Некоторые процессы создают файлы блокировки, которые можно проверить
            try:
                lock_file = os.path.join(os.path.dirname(self.winws_exe), "winws.lock")
                if os.path.exists(lock_file):
                    log(f"Найден файл блокировки {lock_file}, процесс запущен")
                    return True
            except Exception as lock_error:
                log(f"Ошибка при проверке файла блокировки: {str(lock_error)}")
            
            # Если все методы не нашли процесс
            log("Процесс winws.exe НЕ найден ни одним из методов")
            return False
            
        except Exception as e:
            log(f"Общая ошибка при проверке статуса процесса: {str(e)}")
            return False
    def force_stop_all_instances(self):
        """
        Усиленный метод для принудительного завершения процесса winws.exe
        с использованием нескольких техник.
        """
        try:
            log("Запускаю принудительное завершение всех экземпляров winws.exe...")
            
            # Шаг 1: Обнаружение PID процесса
            active_pids = []
            
            # Получаем все PID через PowerShell (самый надежный метод)
            try:
                ps_cmd = 'powershell -Command "Get-Process -Name winws -ErrorAction SilentlyContinue | Select-Object Id | Format-Table -HideTableHeaders"'
                ps_result = subprocess.run(
                    ps_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                for line in ps_result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and line.isdigit():
                        active_pids.append(line)
                        log(f"Обнаружен активный процесс winws.exe с PID: {line}")
            except Exception as ps_error:
                log(f"Ошибка при получении PID через PowerShell: {str(ps_error)}")
            
            # Если PID не найдены, попробуем другие методы
            if not active_pids:
                log("PID не найдены через PowerShell, пробуем tasklist...")
                try:
                    result = subprocess.run(
                        'tasklist /FI "IMAGENAME eq winws.exe" /NH /FO CSV',
                        shell=True, 
                        capture_output=True, 
                        text=True
                    )
                    
                    for line in result.stdout.split('\n'):
                        if "winws.exe" in line:
                            parts = line.split(',')
                            if len(parts) >= 2:
                                pid = parts[1].strip('"')
                                if pid.isdigit():
                                    active_pids.append(pid)
                                    log(f"Обнаружен процесс через tasklist с PID: {pid}")
                except Exception as task_error:
                    log(f"Ошибка при получении PID через tasklist: {str(task_error)}")
            
            # Шаг 2: Принудительное завершение по каждому PID с повышенными привилегиями
            success = False
            
            if active_pids:
                log(f"Найдено процессов для завершения: {len(active_pids)}")
                
                for pid in active_pids:
                    log(f"Попытка принудительного завершения процесса с PID {pid}...")
                    
                    # Метод 1: taskkill с приоритетом по PID, не по имени
                    try:
                        log(f"Метод 1: Использую taskkill /PID {pid} /F /T")
                        subprocess.run(f"taskkill /PID {pid} /F /T", shell=True, check=False)
                        time.sleep(0.5)
                    except Exception as e:
                        log(f"Ошибка при taskkill по PID: {str(e)}")
                    
                    # Метод 2: Использование PowerShell для завершения (может работать при проблемах с taskkill)
                    try:
                        log(f"Метод 2: Использую PowerShell Stop-Process для PID {pid}")
                        ps_kill = f'powershell -Command "Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"'
                        subprocess.run(ps_kill, shell=True, check=False)
                        time.sleep(0.5)
                    except Exception as e:
                        log(f"Ошибка при PowerShell Stop-Process: {str(e)}")
                    
                    # Метод 3: Использование команды wmic (работает лучше на старых системах)
                    try:
                        log(f"Метод 3: Использую wmic для завершения PID {pid}")
                        wmic_cmd = f'wmic process where ProcessId="{pid}" call terminate'
                        subprocess.run(wmic_cmd, shell=True, check=False)
                        time.sleep(0.5)
                    except Exception as e:
                        log(f"Ошибка при wmic terminate: {str(e)}")
                    
                    # Метод 4: Использование pskill из PsTools (если доступен)
                    try:
                        log(f"Метод 4: Пробую использовать pskill для PID {pid}")
                        subprocess.run(f"pskill {pid}", shell=True, check=False)
                        time.sleep(0.5)
                    except Exception as e:
                        log(f"Не удалось использовать pskill: {str(e)}")
                    
                    # Проверяем, завершился ли процесс
                    try:
                        log(f"Проверка завершения процесса с PID {pid}...")
                        check_cmd = f'powershell -Command "Get-Process -Id {pid} -ErrorAction SilentlyContinue"'
                        check_result = subprocess.run(
                            check_cmd,
                            shell=True,
                            capture_output=True,
                            text=True
                        )
                        
                        if check_result.stdout.strip():
                            log(f"ВНИМАНИЕ: Процесс с PID {pid} всё еще активен!")
                        else:
                            log(f"Процесс с PID {pid} успешно завершен")
                            success = True
                    except Exception as e:
                        log(f"Ошибка при проверке завершения: {str(e)}")
            else:
                log("Не найдено процессов winws.exe для завершения")
                success = True
            
            # Шаг 3: Принудительное завершение любых оставшихся процессов
            try:
                log("Дополнительная попытка завершения всех процессов с именем winws.exe...")
                subprocess.run("taskkill /IM winws.exe /F", shell=True, check=False)
            except Exception as e:
                log(f"Ошибка при финальном taskkill: {str(e)}")
            
            # Шаг 4: Проверяем, успешно ли завершены все процессы
            time.sleep(1.0)
            final_check = self.check_process_running()
            if final_check:
                log("КРИТИЧЕСКАЯ ОШИБКА: Процесс winws.exe всё еще работает после всех попыток завершения!")
                log("Создаем специальный файл-маркер для signaling...")
                
                # Создаем файл-маркер, говорящий основной программе использовать обходной метод
                try:
                    marker_file = os.path.join(os.path.dirname(self.winws_exe), "force_restart_needed.txt")
                    with open(marker_file, 'w') as f:
                        f.write(f"Процесс не может быть остановлен, PID: {','.join(active_pids)}")
                except Exception as e:
                    log(f"Ошибка при создании маркера: {str(e)}")
                
                return False
            else:
                log("Все экземпляры winws.exe успешно завершены")
                return True
                
        except Exception as e:
            log(f"Общая ошибка в force_stop_all_instances: {str(e)}")
            return False