import os
import time
import subprocess
import win32con, sys

from PyQt5.QtWidgets import QApplication

from log import log

class DPIStarter:
    """Класс для запуска и управления процессами DPI."""
    
    def __init__(self, winws_exe, bin_folder, lists_folder, status_callback=None, debug_mode=False):
        """
        Инициализирует DPIStarter.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            bin_folder (str): Путь к папке с бинарными файлами
            lists_folder (str): Путь к папке со списками
            status_callback (callable): Функция обратного вызова для отображения статуса
            debug_mode (bool): Флаг режима отладки, определяет видимость консоли
        """
        self.winws_exe = winws_exe
        self.bin_folder = bin_folder
        self.lists_folder = lists_folder
        self.status_callback = status_callback
        self.debug_mode = debug_mode
    
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
    
    def check_process_running(self):
        """
        Улучшенная проверка запущен ли процесс DPI с подробной диагностикой.
        
        Returns:
            bool: True если процесс запущен, False если не запущен
        """
        log(f"=================== check_process_running ==========================", level="START")

        try:
            
            log("Метод 1: Проверка через tasklist", level="START")
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq winws.exe" /NH',
                shell=True, 
                capture_output=True, 
                text=True,
                encoding='cp866'  # Используем кодировку cp866 для корректного отображения русских символов
            )
            
            #log(f"Результат команды tasklist: {result.stdout.strip()}")
            
            if "winws.exe" in result.stdout:
                pid_line = [line for line in result.stdout.split('\n') if "winws.exe" in line]
                
                if pid_line:
                    #log(f"Строка с информацией о процессе: {pid_line[0]}")
                    pid_parts = pid_line[0].split()
                    
                    if len(pid_parts) >= 2:
                        pid = pid_parts[1]
                        log(f"Найден PID процесса: {pid}", level="START")
                        return True
                
                log("Процесс найден, но не удалось определить PID", level="START")
                return True  # Процесс найден, даже если мы не смогли извлечь PID
            
            # Метод 2: Проверка через PowerShell (работает лучше на некоторых системах)
            log("Метод 2: Проверка через PowerShell", level="START")
            try:
                ps_cmd = 'powershell -Command "Get-Process -Name winws -ErrorAction SilentlyContinue | Select-Object Id"'
                ps_result = subprocess.run(
                    ps_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                log(f"Результат PowerShell: {ps_result.stdout.strip()}", level="START")
                
                # Если есть любая строка, содержащая число после Id
                if any(line.strip().isdigit() for line in ps_result.stdout.split('\n') if line.strip()):
                    log("Процесс winws.exe найден через PowerShell", level="START")
                    return True
            except Exception as ps_error:
                log(f"Ошибка при проверке через PowerShell: {str(ps_error)}", level="START")
            
            # Метод 3: Проверка через wmic (работает даже на старых системах)
            log("Метод 3: Проверка через wmic", level="START")
            try:
                wmic_result = subprocess.run(
                    'wmic process where "name=\'winws.exe\'" get processid',
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                log(f"Результат wmic: {wmic_result.stdout.strip()}", level="START")
                
                lines = [line.strip() for line in wmic_result.stdout.split('\n') if line.strip()]
                # Проверяем есть ли более одной строки (заголовок + данные)
                if len(lines) > 1:
                    log("Процесс winws.exe найден через wmic", level="START")
                    return True
            except Exception as wmic_error:
                log(f"Ошибка при проверке через wmic: {str(wmic_error)}", level="START")
                
            # Метод 4: Проверка через простую команду findstr
            log("Метод 4: Проверка через tasklist и findstr", level="START")
            try:
                findstr_result = subprocess.run(
                    'tasklist | findstr "winws"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                log(f"Результат findstr: {findstr_result.stdout.strip()}", level="START")
                
                if findstr_result.stdout.strip():
                    log("Процесс winws.exe найден через findstr", level="START")
                    return True
            except Exception as findstr_error:
                log(f"Ошибка при проверке через findstr: {str(findstr_error)}", level="START")
            
            # Проверка существования файла блокировки
            # Некоторые процессы создают файлы блокировки, которые можно проверить
            try:
                lock_file = os.path.join(os.path.dirname(self.winws_exe), "winws.lock")
                if os.path.exists(lock_file):
                    log(f"Найден файл блокировки {lock_file}, процесс запущен", level="START")
                    return True
            except Exception as lock_error:
                log(f"Ошибка при проверке файла блокировки: {str(lock_error)}", level="START")
            
            # Если все методы не нашли процесс
            log("Процесс winws.exe НЕ найден ни одним из методов", level="START")
            return False
            
        except Exception as e:
            log(f"Общая ошибка при проверке статуса процесса: {str(e)}", level="START")
            return False
        
    def stop_dpi(self):
        """
        Останавливает процесс DPI.
        
        Returns:
            bool: True при успешной остановке, False при ошибке
        """
        try:
            log("======================== Stop DPI ========================", level="START")
            
            # Проверяем наличие службы
            service_exists = False
            try:
                from service import ServiceManager
                service_manager = ServiceManager(
                    winws_exe=self.winws_exe,
                    bin_folder=self.bin_folder,
                    lists_folder=self.lists_folder,
                    status_callback=self.set_status
                )
                service_exists = service_manager.check_service_exists()
            except Exception as e:
                log(f"Ошибка при проверке службы: {str(e)}", level="ERROR")
                
            if service_exists:
                log("Обнаружена активная служба ZapretCensorliber", level="START")
                self.set_status("Невозможно остановить Zapret, пока установлена служба")
                return False
            else:
                log("Служба ZapretCensorliber не найдена, продолжаем остановку DPI.", level="START")
            
            # Проверяем, запущен ли процесс
            if not self.check_process_running():
                log("Процесс winws.exe не запущен, нет необходимости в остановке", level="START")
                self.set_status("Zapret уже остановлен")
                return True
            
            # Используем только stop.bat для остановки процесса
            stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
            if os.path.exists(stop_bat_path):
                self.set_status("Останавливаю winws.exe через stop.bat...")
                log("Использую stop.bat для остановки процесса", level="START")
                
                # Создаем startupinfo для скрытия окна командной строки
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Запускаем stop.bat
                process = subprocess.Popen(
                    stop_bat_path,
                    startupinfo=startupinfo,
                    cwd=self.bin_folder,
                    shell=True
                )
                
                # Ждем завершения процесса с таймаутом 5 секунд
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    log("Таймаут ожидания stop.bat", level="WARNING")
                    # Продолжаем выполнение, не ждем полного завершения
                
                # Даем время на завершение процессов
                time.sleep(1)
                
                # Проверяем, остановлен ли процесс
                if not self.check_process_running():
                    self.set_status("Zapret успешно остановлен")
                    return True
                else:
                    log("Процесс winws.exe не был остановлен через stop.bat, но мы не будем использовать другие методы", level="WARNING")
                    self.set_status("Zapret не удалось остановить через stop.bat")
                    return False
            else:
                # Если stop.bat не найден, создаем его
                log("stop.bat не найден, создаем...", level="START")
                self.create_stop_bat()
                return self.stop_dpi()  # Рекурсивно вызываем метод после создания файла
                
            return True
        except Exception as e:
            error_msg = f"Ошибка при остановке DPI: {str(e)}"
            log(error_msg, level="ERROR")
            self.set_status(error_msg)
            return False

    def create_stop_bat(self):
        """Создает файл stop.bat, если он не существует"""
        try:
            stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
            
            # Содержимое stop.bat
            stop_bat_content = """@echo off
    REM stop.bat - останавливает все экземпляры winws.exe
    REM VERSION: 1.0
    REM Дата обновления: 2025-04-22

    echo Остановка всех процессов winws.exe...

    REM Метод 1: taskkill
    taskkill /F /IM winws.exe /T

    REM Метод 2: через PowerShell
    powershell -Command "Get-Process winws -ErrorAction SilentlyContinue | Stop-Process -Force"

    REM Метод 3: через wmic
    wmic process where name='winws.exe' call terminate

    REM Добавляем паузу для стабильности
    timeout /t 1 /nobreak >nul

    echo Остановка процессов завершена.
    exit /b 0
    """
            
            # Создаем директорию при необходимости
            os.makedirs(os.path.dirname(stop_bat_path), exist_ok=True)
            
            # Записываем файл
            with open(stop_bat_path, 'w', encoding='utf-8') as f:
                f.write(stop_bat_content)
                
            log(f"Файл stop.bat успешно создан: {stop_bat_path}", level="START")
            return True
        except Exception as e:
            log(f"Ошибка при создании stop.bat: {str(e)}", level="ERROR")
            return False
  
    def check_process_corrupted(self):
        """
        Проверяет, находится ли процесс winws.exe в состоянии, когда его нельзя завершить
        (зависший/заблокированный процесс).
        
        Returns:
            bool: True если процесс найден и он "зависший", False в противном случае
        """
        try:
            marker_file = os.path.join(os.path.dirname(self.winws_exe), "force_restart_needed.txt")
            if os.path.exists(marker_file):
                log("Обнаружен маркер зависшего процесса!")
                return True
                
            # Проверка на "бесхозные" процессы
            orphaned_pids = []
            
            # Получаем все PID через PowerShell
            try:
                ps_cmd = 'powershell -Command "Get-Process -Name winws | Where-Object {$_.Responding -eq $false} | Select-Object Id | Format-Table -HideTableHeaders"'
                ps_result = subprocess.run(
                    ps_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                
                for line in ps_result.stdout.strip().split('\n'):
                    if line.strip() and line.strip().isdigit():
                        orphaned_pids.append(line.strip())
                        log(f"Обнаружен не отвечающий процесс winws.exe с PID: {line.strip()}", level="START")
            except Exception as ps_error:
                log(f"Ошибка при проверке зависших процессов: {str(ps_error)}", level="START")
            
            return len(orphaned_pids) > 0
            
        except Exception as e:
            log(f"Ошибка в check_process_corrupted: {str(e)}")
            return False

    def start_with_progress(self, mode, dpi_commands, download_urls=None, parent_widget=None):
        """
        Запускает DPI с выбранной конфигурацией и показывает прогресс.
        
        Args:
            mode (str): Название режима запуска
            dpi_commands (dict): Словарь с настройками команд для разных режимов
            download_urls (dict, optional): URL для скачивания файлов, если они отсутствуют
            parent_widget (QWidget, optional): Родительский виджет для диалога прогресса
        
        Returns:
            bool: True при успешном запуске, False при ошибке
        """
        try:
            log(f"======================== Start DPI {mode} ========================", level="START")
            self.set_status("Подготовка запуска...")
            
            # Сначала останавливаем все процессы через stop.bat
            stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
            
            # Если stop.bat существует, запускаем его
            if os.path.exists(stop_bat_path):
                log("Запуск stop.bat для остановки предыдущих процессов", level="START")
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                stop_process = subprocess.Popen(
                    stop_bat_path,
                    startupinfo=startupinfo,
                    cwd=self.bin_folder,
                    shell=True
                )
                
                # Ждем завершения процесса остановки
                try:
                    stop_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    log("Таймаут ожидания stop.bat", level="WARNING")
                
                log(f"stop.bat завершен с кодом: {stop_process.returncode}", level="START")
            else:
                # Создаем stop.bat, если он не существует
                self.create_stop_bat()
            
            # Проверяем и скачиваем необходимые файлы
            if not self.download_files(download_urls):
                self.set_status("Не удалось скачать необходимые файлы")
                return False
            
            # Проверяем наличие команды для выбранного режима
            if mode not in dpi_commands:
                error_msg = f"Неизвестный режим запуска: {mode}"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                return False
            
            # Получаем аргументы командной строки для выбранного режима
            cmd_args = dpi_commands[mode]
            
            # Проверяем наличие исполняемого файла
            exe_path = os.path.abspath(self.winws_exe)
            if not os.path.exists(exe_path):
                error_msg = f"Исполняемый файл не найден: {exe_path}"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                return False
            
            # Логируем команду
            log(exe_path, level="INFO")
            log(str(cmd_args), level="INFO")
            
            # Создаем список аргументов
            cmd = [exe_path] + cmd_args
            log(str(cmd), level="INFO")
            
            # Создаем startupinfo для скрытия окна консоли
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Настройка отображения консоли в зависимости от режима отладки
            startupinfo = None
            if not self.debug_mode:
                # Только в обычном режиме скрываем консоль
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = win32con.SW_HIDE
                log("Запуск в обычном режиме (консоль скрыта)", level="START")
            else:
                # В режиме отладки показываем консоль
                log("ЗАПУСК В РЕЖИМЕ ОТЛАДКИ - КОНСОЛЬ БУДЕТ ОТОБРАЖАТЬСЯ", level="DEBUG")
                self.set_status("Запуск в режиме отладки (консоль будет видна)")
            
            # Запускаем процесс
            process = subprocess.Popen(
                cmd, 
                startupinfo=startupinfo,  # Будет None в режиме отладки
                cwd=self.bin_folder,
                shell=False
            )

            log(f"Запущен процесс: {process.pid}", level="START")
            
            # Проверяем, запустился ли процесс
            if process.poll() is not None:
                error_msg = f"Процесс завершился сразу после запуска с кодом {process.returncode}"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                return False
            
            # Проверяем, запущен ли процесс winws.exe
            if self.check_process_running():
                log("ZAPRET УСПЕШНО ЗАПУЩЕН ", level="START")
                self.set_status("Zapret успешно запущен")
                return True
            else:
                error_msg = "Не удалось запустить процесс winws.exe"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Ошибка при запуске DPI: {str(e)}"
            log(error_msg, level="ERROR")
            self.set_status(error_msg)
            return False
    
    def ensure_directories_exist(self):
        """Проверяет и создает необходимые директории.
        
        Returns:
            bool: True при успешном создании директорий
        """
        try:
            for folder in [self.bin_folder, self.lists_folder]:
                if not os.path.exists(folder):
                    os.makedirs(folder, exist_ok=True)
                    self.set_status(f"Создана папка {folder}")
                    log(f"Создана папка {folder}")
            return True
        except Exception as e:
            log(f"Ошибка при создании директорий: {str(e)}", level="ERROR")
            return False

    def ensure_executable_exists(self, download_urls=None):
        """Проверяет наличие исполняемого файла и скачивает при необходимости.
        
        Args:
            download_urls (dict, optional): URL для скачивания файлов, если они отсутствуют
            
        Returns:
            bool: True если файл существует или успешно скачан, False в противном случае
            
        Raises:
            FileNotFoundError: Если файл не найден и не может быть скачан
        """
        exe_path = os.path.abspath(self.winws_exe)
        if not os.path.exists(exe_path):
            if download_urls and self.download_files(download_urls):
                self.set_status("Необходимые файлы скачаны")
                log(f"Необходимые файлы скачаны", level="START")
                return True
            else:
                log(f"Файл {exe_path} не найден и не может быть скачан", level="START")
                raise FileNotFoundError(f"Файл {exe_path} не найден и не может быть скачан")
        return True
    
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
            log(f"======================== Start DPI {mode} ========================", level="START")
            self.set_status("Подготовка запуска...")

            # Используем stop.bat для надежной остановки всех процессов
            stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
            
            # Проверяем существование stop.bat
            if os.path.exists(stop_bat_path):
                self.set_status("Останавливаю предыдущие процессы...")
                log("Запуск stop.bat для остановки предыдущих процессов", level="START")
                
                # Создаем startupinfo для скрытия окна командной строки
                stop_startupinfo = subprocess.STARTUPINFO()
                stop_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                stop_startupinfo.wShowWindow = win32con.SW_HIDE
                
                # Запускаем stop.bat и ЖДЕМ его полного завершения
                stop_process = subprocess.Popen(
                    stop_bat_path,
                    startupinfo=stop_startupinfo,
                    cwd=self.bin_folder,
                    shell=True
                )
                
                # Ждем завершения процесса остановки
                stop_process.wait()
                log(f"stop.bat завершен с кодом: {stop_process.returncode}", level="START")
                
                # Небольшая пауза для гарантии завершения процесса
                time.sleep(0.5)
            else:
                log("stop.bat не найден", level="WARNING")
                # Создаем stop.bat, если он не существует
                self.create_stop_bat()
            
            # Проверяем наличие исполняемого файла
            self.ensure_executable_exists(download_urls)
            exe_path = os.path.abspath(self.winws_exe)
            
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
            
            log(f"Исполняемый файл: {exe_path}")  # Логируем путь к исполняемому файлу
            log(f"Аргументы команды: {command_args}")  # Логируем аргументы
            log(f"Полная команда: {command}")  # Логируем команду для отладки
            
            # Настройка отображения консоли в зависимости от режима отладки
            startupinfo = None
            if not self.debug_mode:
                # Только в обычном режиме скрываем консоль
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = win32con.SW_HIDE
                log("Запуск в обычном режиме (консоль скрыта)", level="START")
            else:
                # В режиме отладки показываем консоль
                log("ЗАПУСК В РЕЖИМЕ ОТЛАДКИ - КОНСОЛЬ БУДЕТ ОТОБРАЖАТЬСЯ", level="DEBUG")
                self.set_status("Запуск в режиме отладки (консоль будет видна)")
            
            # Запускаем процесс
            process = subprocess.Popen(
                command,
                startupinfo=startupinfo,  # Будет None в режиме отладки
                cwd=os.getcwd()
            )

            log(f"Запущен процесс с PID: {process.pid}")
            
            if process.poll() is None:
                self.set_status(f"Запущен {mode}")
                log(f"ZAPRET УСПЕШНО ЗАПУЩЕН {mode}", level="START")
                return True
            else:
                log(f"Ошибка при запуске {mode}: {process.returncode}", level="START")
                raise Exception("Не удалось запустить процесс")
                    
        except Exception as e:
            log(f"Ошибка при запуске {mode}: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка при запуске {mode}: {str(e)}")
            return False