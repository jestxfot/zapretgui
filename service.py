import os
import subprocess
import time, winreg

# Константы для работы с реестром
REGISTRY_KEY = r"SOFTWARE\Zapret"
CONFIG_VALUE = "ZapretServiceConfig"

def save_config_to_registry(config_name):
    """Сохраняет имя конфигурации в реестр Windows"""
    try:
        # Пытаемся открыть существующий ключ
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_WRITE)
        except FileNotFoundError:
            # Если ключ не существует, создаем его
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        
        # Записываем значение
        winreg.SetValueEx(key, CONFIG_VALUE, 0, winreg.REG_SZ, config_name)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении конфигурации в реестр: {str(e)}")
        return False

def get_config_from_registry():
    """Получает имя конфигурации из реестра Windows"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, CONFIG_VALUE)
        winreg.CloseKey(key)
        return value
    except FileNotFoundError:
        # Ключ или значение не найдены
        return None
    except Exception as e:
        print(f"Ошибка при получении конфигурации из реестра: {str(e)}")
        return None

class ServiceManager:
    def __init__(self, winws_exe, bin_folder, lists_folder, status_callback=None, service_name="ZapretCensorliber"):
        """
        Инициализирует менеджер служб.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            bin_folder (str): Путь к папке с бинарными файлами
            lists_folder (str): Путь к папке со списками
            status_callback (callable): Функция обратного вызова для отображения статуса
            service_name (str): Имя службы
        """
        self.winws_exe = winws_exe
        self.bin_folder = bin_folder
        self.lists_folder = lists_folder
        self.status_callback = status_callback
        self.service_name = service_name
    
    def set_status(self, text):
        """Отображает статусное сообщение"""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)
    
    def check_service_exists(self):
        """Проверяет наличие автозапуска (обратная совместимость)"""
        # Просто делегируем вызов новому методу для обеспечения обратной совместимости
        return self.check_autostart_exists()

    def install_service(self, command_args, config_name=""):
        """
        Устанавливает службу Windows для автоматического запуска DPI.
        
        Args:
            command_args (list): Аргументы командной строки для winws.exe
            config_name (str, optional): Имя конфигурации для отображения в сообщениях
            
        Returns:
            bool: True если служба успешно установлена, False в случае ошибки
        """
        try:
            # Если command_args переданы как строка, разбиваем на список
            if isinstance(command_args, str):
                command_args = command_args.split()

            # Проверяем путь на наличие пробелов
            current_path = os.path.dirname(os.path.abspath(self.winws_exe))
            if " " in current_path:
                error_msg = (
                    "Ошибка: Невозможно установить службу, так как путь к программе содержит пробелы:\n"
                    f"{current_path}\n\n"
                    "Пожалуйста, переместите программу в папку без пробелов в пути "
                    "(например, в корень диска C:\\Zapret) и повторите попытку."
                )
                self.set_status("Ошибка: Путь содержит пробелы")
                
                # Используем QMessageBox для вывода сообщения
                from PyQt5.QtWidgets import QMessageBox
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("Ошибка пути")
                msg_box.setText(error_msg)
                msg_box.exec_()
                
                return False
                
            # Проверяем существует ли служба
            if self.check_service_exists():
                self.set_status("Служба уже существует. Удаление...")
                stop_cmd = f'sc stop "{self.service_name}"'
                subprocess.run(stop_cmd, shell=True, capture_output=True)
                time.sleep(0.1)
                delete_cmd = f'sc delete "{self.service_name}"'
                delete_result = subprocess.run(delete_cmd, shell=True, capture_output=True, text=True)
                if delete_result.returncode != 0:
                    self.set_status("Не удалось удалить существующую службу")
                time.sleep(0.1)

            exe_path = os.path.abspath(self.winws_exe)
            processed_args = []
            for arg in command_args:
                if ".txt" in arg or ".bin" in arg:
                    if "=" in arg:
                        prefix, filename = arg.split("=", 1)
                        if ".txt" in filename:
                            full_path = os.path.join(os.path.abspath(self.lists_folder), os.path.basename(filename))
                            processed_args.append(f"{prefix}={full_path}")
                        elif ".bin" in filename:
                            full_path = os.path.join(os.path.abspath(self.bin_folder), os.path.basename(filename))
                            processed_args.append(f"{prefix}={full_path}")
                        else:
                            processed_args.append(arg)
                    else:
                        processed_args.append(arg)
                else:
                    processed_args.append(arg)

            args_str = " ".join(processed_args)
            service_command = f'"{exe_path}" {args_str}'

            # Создаем службу без описания
            create_cmd = (
                f'sc create "{self.service_name}" type= own binPath= "{service_command}" '
                f'start= auto DisplayName= "{self.service_name}"'
            )
            print(f"DEBUG: Service command: {create_cmd}")
            create_result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
            if create_result.returncode == 0:
                # Устанавливаем описание службы отдельной командой
                desc_cmd = f'sc description "{self.service_name}" "Служба для работы Zapret DPI https://t.me/bypassblock"'
                subprocess.run(desc_cmd, shell=True, capture_output=True, text=True)
                
                # Сохраняем конфигурацию в реестр
                save_config_to_registry(config_name if config_name else "Пользовательская")
                subprocess.run("taskkill /IM winws.exe /F", shell=True, check=False)
                time.sleep(0.1)
                # Запускаем службу
                start_cmd = f'sc start "{self.service_name}"'
                start_result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True)
                if start_result.returncode == 0:
                    self.set_status(f"Служба установлена и запущена\nКонфиг: {config_name}")
                    return True
                else:
                    self.set_status("Служба создана, но не удалось запустить её")
                    return False
            else:
                error_output = create_result.stderr.strip() if create_result.stderr else create_result.stdout.strip()
                self.set_status(f"Ошибка при создании службы: {error_output}")
                return False
        except Exception as e:
            self.set_status(f"Ошибка при установке службы: {str(e)}")
            return False

    def install_task_scheduler(self, bat_file_path, config_name, strategy_id=None):
        """
        Создает задачу в планировщике заданий Windows для автозапуска BAT-файла
        """
        try:
            from log import log
            
            # Проверяем наличие файла
            if not os.path.exists(bat_file_path):
                log(f"BAT-файл не найден: {bat_file_path}", level="ERROR")
                self.set_status(f"Ошибка: BAT-файл не найден")
                return False
            
            # Имя задачи
            task_name = "ZapretCensorliber"
            
            # Проверяем, существует ли уже задача и удаляем ее
            self.set_status("Проверка существующих задач...")
            check_cmd = f'schtasks /Query /TN "{task_name}" 2>nul'
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                log("Задача ZapretCensorliber уже существует, удаляем...", level="INFO")
                self.set_status("Удаление существующей задачи...")
                delete_cmd = f'schtasks /Delete /TN "{task_name}" /F'
                subprocess.run(delete_cmd, shell=True, check=False)
                time.sleep(1)  # Даем время на удаление задачи
            
            # Создаем конфигурационный файл для хранения информации о стратегии
            config_file_path = os.path.join(self.bin_folder, "autostart_config.txt")
            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write(f"strategy_name={config_name}\n")
                f.write(f"strategy_id={strategy_id or 'unknown'}\n")
                f.write(f"bat_file={bat_file_path}\n")
                f.write(f"installed={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"type=task_scheduler\n")
            
            # Создаем CMD-файл для запуска стратегии
            launcher_cmd_path = os.path.join(self.bin_folder, "autostart_launcher.cmd")
            with open(launcher_cmd_path, 'w', encoding='utf-8') as f:
                f.write(f"""@echo off
    rem Zapret DPI Autostart Launcher
    cd /d "{os.path.dirname(bat_file_path)}"
    start /b "" "{os.path.basename(bat_file_path)}"
    exit
    """)
            
            # Полный путь к батнику запуска
            abs_cmd_path = os.path.abspath(launcher_cmd_path)
            
            # Создаем задачу в планировщике с запуском при старте системы
            # /RL HIGHEST = запуск с повышенными правами
            # /SC ONSTART = запуск при старте системы
            # /RU SYSTEM = запуск от имени системы
            # /NP = без запроса пароля
            
            log(f"Создание задачи в планировщике для: {abs_cmd_path}", level="INFO")
            
            # Формируем команду
            create_cmd = (
                f'schtasks /Create /SC ONSTART /TN "{task_name}" '
                f'/TR "cmd.exe /c \\"\\"\\"{abs_cmd_path}\\"\\"\\"" '
                f'/RL HIGHEST /RU SYSTEM /F /NP /V1'
            )
            
            log(f"Команда создания задачи: {create_cmd}", level="INFO")
            
            # Создаем задачу
            self.set_status("Создание задачи в планировщике...")
            result = subprocess.run(create_cmd, shell=True, check=False, capture_output=True, text=True, encoding='cp866')
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                log(f"Ошибка при создании задачи: {error_msg}", level="ERROR")
                self.set_status(f"Ошибка: не удалось создать задачу")
                return False
            
            log(f"Результат создания задачи: {result.stdout}", level="INFO")
            
            # Запускаем задачу сразу
            self.set_status("Запуск задачи...")
            run_cmd = f'schtasks /Run /TN "{task_name}"'
            subprocess.run(run_cmd, shell=True, check=False)
            
            # Сохраняем информацию о конфигурации в реестр
            save_config_to_registry(config_name)
            
            # Проверяем, запустился ли процесс
            time.sleep(2)  # Даем время на запуск
            
            from start import DPIStarter
            dpi_starter = DPIStarter(self.winws_exe, self.bin_folder, self.lists_folder)
            if dpi_starter.check_process_running():
                log("Процесс winws.exe успешно запущен через планировщик", level="INFO")
                self.set_status(f"Автозапуск успешно настроен с режимом: {config_name}")
                return True
            else:
                log("Задача создана, но процесс не запустился автоматически", level="WARNING")
                self.set_status(f"Автозапуск настроен, но требуется перезагрузка")
                return True
            
        except Exception as e:
            from log import log
            log(f"Ошибка при настройке автозапуска: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка: {str(e)}")
            return False

    def remove_service(self):
        """Удаляет автозапуск DPI"""
        try:
            from log import log
            
            # Имя задачи
            task_name = "ZapretCensorliber"
            
            # Проверяем существование задачи
            check_cmd = f'schtasks /Query /TN "{task_name}" 2>nul'
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if result.returncode != 0:
                log("Задача автозапуска не установлена, нечего удалять", level="INFO")
                self.set_status("Автозапуск не настроен")
                return True
            
            # Удаляем задачу
            self.set_status("Удаление автозапуска...")
            log("Удаляем задачу автозапуска ZapretCensorliber", level="INFO")
            
            delete_cmd = f'schtasks /Delete /TN "{task_name}" /F'
            result = subprocess.run(delete_cmd, shell=True, check=False, capture_output=True, text=True, encoding='cp866')
            
            if result.returncode != 0:
                log(f"Ошибка при удалении задачи: {result.stderr or result.stdout}", level="ERROR")
                self.set_status(f"Ошибка при удалении автозапуска")
                return False
            
            # Удаляем конфигурационный файл автозапуска, если он существует
            config_file_path = os.path.join(self.bin_folder, "autostart_config.txt")
            if os.path.exists(config_file_path):
                try:
                    os.remove(config_file_path)
                except Exception as e:
                    log(f"Ошибка при удалении конфигурационного файла: {str(e)}", level="WARNING")
            
            # Удаляем файл запуска
            launcher_cmd_path = os.path.join(self.bin_folder, "autostart_launcher.cmd")
            if os.path.exists(launcher_cmd_path):
                try:
                    os.remove(launcher_cmd_path)
                except Exception as e:
                    log(f"Ошибка при удалении файла запуска: {str(e)}", level="WARNING")
            
            log("Автозапуск успешно удален", level="INFO")
            self.set_status("Автозапуск успешно удален")
            return True
            
        except Exception as e:
            from log import log
            log(f"Ошибка при удалении автозапуска: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка при удалении автозапуска: {str(e)}")
            return False
    
    def check_autostart_exists(self):
        """Проверяет, настроен ли автозапуск Zapret через любой механизм (служба или планировщик)"""
        try:
            # Сначала проверяем наличие задачи в планировщике - прямой запрос
            task_name = "ZapretCensorliber"
            check_cmd = f'schtasks /Query /TN "{task_name}" 2>nul'
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, encoding='cp866')
            
            if result.returncode == 0:
                # Выводим детали задачи для отладки
                from log import log
                log(f"Обнаружена задача планировщика: {task_name}", level="DEBUG")
                return True
                
            # Затем проверяем наличие службы Windows
            service_result = subprocess.run(
                'sc query ZapretCensorliber',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )
            
            if service_result.returncode == 0 and "STATE" in service_result.stdout:
                # Выводим детали службы для отладки
                from log import log
                log(f"Обнаружена служба Windows: ZapretCensorliber", level="DEBUG")
                return True
                
            return False
        except Exception as e:
            from log import log
            log(f"Ошибка при проверке автозапуска: {str(e)}", level="ERROR")
            return False
    
    def get_current_service_config(self):
        """
        Получает текущую конфигурацию запущенной службы ZapretCensorliber из реестра
        
        Returns:
            str: Имя стратегии или None, если службы нет или не удалось определить
        """
        try:
            # Проверяем существование службы
            if not self.check_service_exists():
                return None  # Служба не существует
            
            # Получаем конфигурацию из реестра
            config = get_config_from_registry()
            return config if config else "Пользовательская"
                
        except Exception as e:
            print(f"Ошибка при определении конфигурации службы: {str(e)}")
            return "Неизвестная"