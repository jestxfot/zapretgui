import os
import time
import subprocess
import win32con

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
                service_exists = True
            
            if service_exists:
                # Более детальное сообщение об ошибке
                self.set_status("Пожалуйста, сначала ОТКЛЮЧИТЕ АВТОЗАПУСК!")
                # Показываем сообщение в консоль для отладки
                print(f"Обнаружена служба ZapretCensorliber. Выход из stop_dpi().")
                print(f"Результат команды sc query: {result.stdout}")
                return False
                    
            self.set_status("Останавливаю DPI и связанные службы...")
            
            # Останавливаем процесс winws.exe
            subprocess.run("taskkill /IM winws.exe /F", shell=True, check=False)
            
            # Список служб для остановки и удаления
            services = ["Zapret", "WinDivert", "WinDivert14", "GoodbyeDPI"]
            
            # Останавливаем и удаляем службы
            for service in services:
                try:
                    # Проверяем существует ли служба
                    check_cmd = f'sc query "{service}"'
                    check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                    
                    # Если служба не существует (код 1060), пропускаем
                    service_check_exists = True
                    if "1060" in check_result.stderr or "1060" in check_result.stdout:
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
                                
                    self.set_status(f"Служба {service} остановлена и удалена")
                except Exception as e:
                    # Игнорируем ошибки при остановке/удалении служб
                    pass
            
            self.set_status("Программа и связанные службы остановлены")
            return True
        except Exception as e:
            error_msg = f"Ошибка при остановке DPI: {str(e)}"
            print(error_msg)
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
                
            if not os.path.exists(self.lists_folder):
                os.makedirs(self.lists_folder, exist_ok=True)
                self.set_status(f"Создана папка {self.lists_folder}")
            
            # Проверяем наличие исполняемого файла
            exe_path = os.path.abspath(self.winws_exe)
            if not os.path.exists(exe_path):
                if download_urls and self.download_files(download_urls):
                    self.set_status("Необходимые файлы скачаны")
                else:
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
            
            print("Запускаем команду:", command)  # Для отладки
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32con.SW_HIDE  # Полностью скрываем окно
            
            process = subprocess.Popen(
                command,
                startupinfo=startupinfo,
                cwd=os.getcwd()
            )
            
            if process.poll() is None:
                self.set_status(f"Запущен {mode}")
                return True
            else:
                raise Exception("Не удалось запустить процесс")
                    
        except Exception as e:
            error_msg = f"Ошибка при запуске {mode}: {str(e)}"
            print(error_msg)
            self.set_status(error_msg)
            return False

    def check_process_running(self):
        """
        Проверяет запущен ли процесс DPI.
        
        Returns:
            bool: True если процесс запущен, False если не запущен
        """
        try:
            # Проверяем наличие процесса в списке задач
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq winws.exe" /NH',
                shell=True, 
                capture_output=True, 
                text=True
            )
            
            if "winws.exe" in result.stdout:
                # Дополнительная проверка на "полумертвые" процессы
                # Получаем ID процесса
                pid_line = [line for line in result.stdout.split('\n') if "winws.exe" in line]
                if pid_line:
                    # Из строки "winws.exe                     1234 Console..." извлекаем PID
                    pid_parts = pid_line[0].split()
                    if len(pid_parts) >= 2:
                        pid = pid_parts[1]
                        
                        # Проверяем, не "zombie" ли это процесс
                        wmic_result = subprocess.run(
                            f'wmic process where ProcessID={pid} get ExecutablePath',
                            shell=True, 
                            capture_output=True, 
                            text=True
                        )
                        
                        # Если путь есть, процесс действительно работает
                        if self.winws_exe.lower() in wmic_result.stdout.lower():
                            return True
                
                # Если мы здесь, значит процесс есть, но его статус может быть неопределен
                # Используем еще одну проверку на активность
                return True
            return False
        except Exception as e:
            print(f"Ошибка при проверке статуса процесса: {e}")
            return False