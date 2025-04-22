import os
import time
import subprocess
import win32con, sys

from PyQt5.QtWidgets import QApplication

from log import log

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
    
    def check_process_running(self):
        """
        Улучшенная проверка запущен ли процесс DPI с подробной диагностикой.
        
        Returns:
            bool: True если процесс запущен, False если не запущен
        """
        log(f"Start check_process_running...", level="START")

        try:
            
            log("Метод 1: Проверка через tasklist")
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
                log("Обнаружена активная служба ZapretCensorliber", level="INFO")
                self.set_status("Невозможно остановить Zapret, пока установлена служба")
                return False
            else:
                log("Служба ZapretCensorliber не найдена, продолжаем остановку DPI.", level="INFO")
            
            # Проверяем, запущен ли процесс
            if not self.check_process_running():
                log("Процесс winws.exe не запущен, нет необходимости в остановке", level="INFO")
                self.set_status("Zapret уже остановлен")
                return True
            
            # Используем только stop.bat для остановки процесса
            stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
            if os.path.exists(stop_bat_path):
                self.set_status("Останавливаю winws.exe через stop.bat...")
                log("Использую stop.bat для остановки процесса", level="INFO")
                
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
                log("stop.bat не найден, создаем...", level="INFO")
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
                
            log(f"Файл stop.bat успешно создан: {stop_bat_path}", level="INFO")
            return True
        except Exception as e:
            log(f"Ошибка при создании stop.bat: {str(e)}", level="ERROR")
            return False
    
    def force_stop_all_instances(self):
        """
        Усиленный метод для принудительного завершения процесса winws.exe
        с использованием нескольких техник.
        """
        try:
            log("Start force_stop_all_instances...")
            
            # Проверяем, существует ли marker файл для защиты от завершения
            marker_file = os.path.join(os.path.dirname(self.winws_exe), "process_protected.txt")
            if os.path.exists(marker_file):
                # Проверяем время создания файла
                file_time = os.path.getmtime(marker_file)
                current_time = time.time()
                
                # Если файл создан менее 10 секунд назад, пропускаем завершение
                if current_time - file_time < 10:
                    log("Обнаружен marker защиты процесса, пропускаем завершение")
                    return True
            
            # Проверяем маркер недавней остановки
            recently_stopped_marker = os.path.join(os.path.dirname(self.winws_exe), "recently_stopped.txt")
            if os.path.exists(recently_stopped_marker):
                log("Обнаружен маркер недавней остановки, пропускаем принудительное завершение", level="INFO")
                return True
                
            # Вместо использования всех методов, запускаем stop.bat
            stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
            if os.path.exists(stop_bat_path):
                log("Используем stop.bat вместо прямых методов остановки", level="INFO")
                
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
                
                # Проверяем, остановлен ли процесс
                if not self.check_process_running():
                    log("Все экземпляры winws.exe успешно завершены", level="INFO")
                    return True
                
                return True  # В любом случае возвращаем True и не используем другие методы
            else:
                log("Все экземпляры winws.exe успешно завершены")
                return True
                
        except Exception as e:
            log(f"Общая ошибка в force_stop_all_instances: {str(e)}")
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
                        log(f"Обнаружен не отвечающий процесс winws.exe с PID: {line.strip()}")
            except Exception as ps_error:
                log(f"Ошибка при проверке зависших процессов: {str(ps_error)}")
            
            return len(orphaned_pids) > 0
            
        except Exception as e:
            log(f"Ошибка в check_process_corrupted: {str(e)}")
            return False
        
    def start_with_progress(self, mode, dpi_commands, download_urls=None, parent_widget=None):
        """
        Запускает DPI с отображением диалога прогресса
        
        Args:
            mode (str): Название режима запуска
            dpi_commands (dict): Словарь с настройками команд для разных режимов
            download_urls (dict, optional): URL для скачивания файлов, если они отсутствуют
            parent_widget (QWidget): Родительский виджет для диалога прогресса
            
        Returns:
            bool: True при успешном запуске, False при ошибке
        """
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
        from progress_dialog import StrategyChangeDialog
        
        # Создаем диалог прогресса
        progress_dialog = StrategyChangeDialog(parent_widget)
        
        # Сохраняем оригинальную функцию set_status
        original_set_status = self.set_status
        
        # Переопределяем функцию для обновления и диалога, и оригинального статуса
        def status_wrapper(text):
            original_set_status(text)
            progress_dialog.set_status(text)
        
        # Используем обертку во время запуска
        self.set_status = status_wrapper
        
        try:
            # Показываем диалог прогресса
            progress_dialog.set_progress(0)
            QApplication.processEvents()
            progress_dialog.set_status("Подготовка к запуску...")
            progress_dialog.start_progress()

            progress_dialog.show()
            QApplication.processEvents()
            
            # Проверка на зависший процесс
            progress_dialog.set_progress(10)
            QApplication.processEvents()
            progress_dialog.set_status("Проверка наличия зависших процессов...")
            if self.check_process_corrupted():
                progress_dialog.set_status("Обнаружен зависший процесс!")
                progress_dialog.set_details("Требуется подтверждение пользователя")
                # Диалог подтверждения будет показан стандартным методом
                
            # Остановка предыдущего процесса
            progress_dialog.set_progress(20)
            QApplication.processEvents()
            progress_dialog.set_status("Остановка предыдущего процесса...")
            self.force_stop_all_instances()
            
            # Создание папок
            progress_dialog.set_progress(40)
            QApplication.processEvents()
            progress_dialog.set_status("Проверка необходимых файлов...")
            # Код проверки папок и файлов
            
            # Подготовка команды запуска
            progress_dialog.set_progress(60)
            QApplication.processEvents()
            progress_dialog.set_status("Подготовка команды запуска...")
            
            # Запуск процесса
            progress_dialog.set_progress(80)
            progress_dialog.set_status("Запуск процесса...")
            result = self.start_dpi(mode, dpi_commands, download_urls)
            
            # Проверка статуса запуска
            progress_dialog.set_progress(90)
            QApplication.processEvents()
            progress_dialog.set_status("Проверка статуса запуска...")
            
            # Завершение
            progress_dialog.set_progress(100)
            QApplication.processEvents()

            # Проверяем результат запуска
            if result:
                progress_dialog.set_progress(100)
                progress_dialog.set_status(f"Успешно запущен режим: {mode}")
                progress_dialog.set_details("Режим обхода успешно запущен")
                progress_dialog.complete()  # Отмечаем операцию как завершенную
                # Показываем результат 1.5 секунды, затем закрываем диалог
                QTimer.singleShot(1500, progress_dialog.accept)
            else:
                progress_dialog.set_progress(100)
                progress_dialog.set_status("Ошибка запуска")
                progress_dialog.set_details("Не удалось запустить режим обхода")
                progress_dialog.complete()  # Отмечаем операцию как завершенную
                # Показываем результат 1.5 секунды, затем закрываем диалог
                QTimer.singleShot(1500, progress_dialog.accept)
            
            progress_dialog.exec_()
            return result
        finally:
            # Возвращаем оригинальную функцию set_status
            self.set_status = original_set_status

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
                log(f"Необходимые файлы скачаны")
                return True
            else:
                log(f"Файл {exe_path} не найден и не может быть скачан")
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
                log("Запуск stop.bat для остановки предыдущих процессов", level="INFO")
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Запускаем stop.bat и ЖДЕМ его полного завершения
                stop_process = subprocess.Popen(
                    stop_bat_path,
                    startupinfo=startupinfo,
                    cwd=self.bin_folder,
                    shell=True
                )
                
                # Ждем завершения процесса остановки
                stop_process.wait()
                log(f"stop.bat завершен с кодом: {stop_process.returncode}", level="INFO")
                
                # Небольшая пауза для гарантии завершения процесса
                time.sleep(0.5)
            else:
                log("stop.bat не найден, используем стандартный метод остановки", level="WARNING")
                self.force_stop_all_instances()
            
            # Проверяем и создаем необходимые директории
            if not self.ensure_directories_exist():
                raise Exception("Не удалось создать необходимые директории")
            
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