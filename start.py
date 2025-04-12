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

            # Более надежный способ остановки процесса winws.exe
            max_attempts = 3
            for attempt in range(max_attempts):
                # Стандартная остановка
                subprocess.run("taskkill /IM winws.exe /F", shell=True, check=False)
                
                # Проверяем, остановился ли процесс
                if not self.check_process_running():
                    break
                    
                # Если процесс всё еще работает, пробуем найти PID и остановить по PID
                if attempt > 0:
                    try:
                        result = subprocess.run(
                            'tasklist /FI "IMAGENAME eq winws.exe" /FO CSV /NH',
                            shell=True, 
                            capture_output=True, 
                            text=True
                        )
                        
                        for line in result.stdout.splitlines():
                            if "winws.exe" in line:
                                try:
                                    # CSV формат: "winws.exe","1234","Console",...
                                    parts = line.strip('"').split('","')
                                    if len(parts) >= 2:
                                        pid = parts[1]
                                        # Останавливаем по PID с повышенным приоритетом
                                        subprocess.run(f"taskkill /PID {pid} /F /T", shell=True, check=False)
                                except:
                                    pass
                    except:
                        pass
                
                # Ждем немного перед следующей попыткой
                time.sleep(0.3)
            
            # Если после всех попыток процесс всё еще работает, выводим предупреждение
            if self.check_process_running():
                self.set_status("Предупреждение: Не удалось полностью остановить winws.exe")            

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
        """Запускает процесс DPI с указанной конфигурацией"""
        try:
            self.set_status("Подготовка запуска...")
            self.force_stop_all_instances()  # Заменяем 
    
            # Проверка и повторная попытка остановки, если процесс всё еще запущен
            if self.check_process_running():
                self.set_status("Повторная попытка остановки предыдущих процессов...")
                time.sleep(0.3)  # Увеличиваем время ожидания
                self.force_stop_all_instances()
                
                # Если после двух попыток процесс все еще запущен, выводим предупреждение
                if self.check_process_running():
                    print("ВНИМАНИЕ: Не удалось полностью остановить winws.exe. Продолжаем запуск.")

            # Проверяем наличие необходимых файлов
            if download_urls and not os.path.exists(self.winws_exe):
                self.set_status("Скачивание необходимых файлов...")
                if not self.download_files(download_urls):
                    self.set_status("Не удалось скачать необходимые файлы")
                    return False

                # Проверяем существование папок и создаем при необходимости
                if not os.path.exists(self.bin_folder):
                    os.makedirs(self.bin_folder, exist_ok=True)
                    self.set_status(f"Создана папка {self.bin_folder}")
            
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
                cwd=os.getcwd(),
                shell=False
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
        """Проверяет запущен ли процесс winws.exe - улучшенная версия"""
        try:
            # Метод 1: Проверка через tasklist (стандартный)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32con.SW_HIDE
            
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq winws.exe" /NH /FO CSV',
                shell=True, 
                startupinfo=startupinfo,
                capture_output=True, 
                text=True
            )
            
            if "winws.exe" in result.stdout:
                return True
                
            # Метод 2: Проверка через WMI - более надежный на некоторых системах
            try:
                wmi_result = subprocess.run(
                    'wmic process where "name=\'winws.exe\'" get processid',
                    shell=True,
                    startupinfo=startupinfo,
                    capture_output=True,
                    text=True
                )
                
                if "ProcessId" in wmi_result.stdout and len(wmi_result.stdout.strip().splitlines()) > 1:
                    return True
            except:
                pass
                
            # Метод 3: Проверка через PowerShell
            try:
                ps_cmd = 'powershell -Command "Get-Process -Name \'winws\' -ErrorAction SilentlyContinue"'
                ps_result = subprocess.run(
                    ps_cmd,
                    shell=True,
                    startupinfo=startupinfo,
                    capture_output=True,
                    text=True
                )
                
                if "HandleCount" in ps_result.stdout:  # Признак найденного процесса
                    return True
            except:
                pass
                
            return False
            
        except Exception as e:
            print(f"Ошибка при проверке процесса: {str(e)}")
            # В случае ошибки проверки предполагаем, что процесс не запущен
            return False
    
    def force_stop_all_instances(self):
        """
        Агрессивно останавливает все процессы winws.exe
        без проверки на их состояние
        """
        try:
            # Создаем объект для скрытия окон консоли
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32con.SW_HIDE  # Полностью скрываем окно
            
            # Метод 1: taskkill с разными флагами (используем subprocess.run вместо os.system)
            subprocess.run("taskkill /IM winws.exe /F /T", shell=True, 
                        startupinfo=startupinfo, check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Метод 2: PowerShell для более агрессивной остановки (скрываем окно)
            powershell_cmd = 'powershell -WindowStyle Hidden -Command "Get-Process -Name \'winws\' -ErrorAction SilentlyContinue | ForEach-Object { $_.Kill() }"'
            subprocess.run(powershell_cmd, shell=True, startupinfo=startupinfo, check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Метод 3: Использование WMI для принудительной остановки
            wmi_cmd = 'wmic process where name="winws.exe" call terminate'
            subprocess.run(wmi_cmd, shell=True, startupinfo=startupinfo, check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Ждем немного перед продолжением
            time.sleep(0.3)
            
            # Получаем список всех PID процессов winws.exe (скрываем окно)
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq winws.exe" /FO CSV /NH',
                shell=True, 
                startupinfo=startupinfo,
                capture_output=True, 
                text=True
            )
            
            # Если процессы всё ещё есть, пробуем остановить каждый отдельно
            if "winws.exe" in result.stdout:
                # Находим все PID
                pids = []
                for line in result.stdout.splitlines():
                    if "winws.exe" in line:
                        try:
                            parts = line.strip('"').split('","')
                            if len(parts) >= 2:
                                pids.append(parts[1])
                        except:
                            pass
                
                # Если нашли PID, останавливаем каждый отдельно
                for pid in pids:
                    # ИСПРАВЛЕНИЕ: используем subprocess.run вместо os.system
                    subprocess.run(f"taskkill /PID {pid} /F /T", shell=True, 
                                startupinfo=startupinfo, check=False,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # Также используем PowerShell с более жестким методом (скрываем окно)
                    ps_cmd = f'powershell -WindowStyle Hidden -Command "Get-Process -Id {pid} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Kill($true) }}"'
                    subprocess.run(ps_cmd, shell=True, startupinfo=startupinfo, check=False,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Ещё раз ждем
                time.sleep(0.3)
            
            # Пытаемся сбросить порты (скрываем окно)
            subprocess.run("netsh int ipv4 reset", shell=True, 
                        startupinfo=startupinfo, check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Получаем список всех PID процессов winws.exe
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq winws.exe" /FO CSV /NH',
                shell=True, 
                capture_output=True, 
                text=True
            )
            
            # Если процессы всё ещё есть, пробуем остановить каждый отдельно
            if "winws.exe" in result.stdout:
                # Находим все PID
                pids = []
                for line in result.stdout.splitlines():
                    if "winws.exe" in line:
                        try:
                            parts = line.strip('"').split('","')
                            if len(parts) >= 2:
                                pids.append(parts[1])
                        except:
                            pass
                
                # Если нашли PID, останавливаем каждый отдельно
                for pid in pids:
                    # Используем несколько методов для каждого PID
                    os.system(f"taskkill /PID {pid} /F /T")
                    
                    # Также используем PowerShell с более жестким методом
                    ps_cmd = f'powershell -Command "Get-Process -Id {pid} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Kill($true) }}"'
                    subprocess.run(ps_cmd, shell=True, check=False)
                
                # Ещё раз ждем
                time.sleep(0.3)
            
            # Пытаемся сбросить порты
            subprocess.run("netsh int ipv4 reset", shell=True, check=False)
            
            # Проверка файла на доступность записи
            try:
                if os.path.exists(self.winws_exe):
                    # Пытаемся открыть файл на запись
                    with open(self.winws_exe, "a+b") as f:
                        pass  # Если открылся, значит процесс не использует файл
            except PermissionError:
                # Если файл все еще занят, используем еще один подход через admin API
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name']):
                        if 'winws' in proc.info['name'].lower():
                            proc.kill()
                except:
                    # В крайнем случае, пытаемся переименовать файл временно
                    try:
                        temp_name = self.winws_exe + ".tmp"
                        os.rename(self.winws_exe, temp_name)
                        os.rename(temp_name, self.winws_exe)
                    except:
                        pass
            
            return True
        except Exception as e:
            print(f"Ошибка при принудительной остановке winws.exe: {str(e)}")
            return False
    
    def quick_stop_all_instances(self):
        """Быстрая остановка всех процессов winws.exe без лишних проверок"""
        try:
            # Единая команда taskkill с максимальными привилегиями
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32con.SW_HIDE
            
            # Используем несколько методов для надежности без чрезмерных проверок
            # Команда 1: taskkill
            subprocess.run("taskkill /IM winws.exe /F /T", 
                        shell=True, 
                        startupinfo=startupinfo,
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        check=False)
                        
            # Команда 2: PowerShell (более надежный метод)
            powershell_cmd = 'powershell -WindowStyle Hidden -Command "Get-Process -Name \'winws\' -ErrorAction SilentlyContinue | ForEach-Object { $_.Kill() }"'
            subprocess.run(powershell_cmd, 
                        shell=True, 
                        startupinfo=startupinfo,
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        check=False)
                        
            # Небольшая пауза для завершения процессов
            time.sleep(0.2)
            
            return True
        except Exception as e:
            print(f"Ошибка в quick_stop_all_instances: {str(e)}")
            return False