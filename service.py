import subprocess
import time, winreg

import winreg

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
    def __init__(self, winws_exe, bin_folder, lists_folder, status_callback=None, ui_callback=None, service_name="ZapretCensorliber"):
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
        self.ui_callback = ui_callback
        self.service_name = service_name
    
    def set_status(self, text):
        """Отображает статусное сообщение"""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)
    
    def check_service_exists(self):
        """
        Проверяет наличие автозапуска (обратная совместимость)
        
        Returns:
            bool: True если автозапуск настроен через любой метод, иначе False
        """
        # Просто делегируем вызов новому методу для обеспечения обратной совместимости
        return self.check_autostart_exists()

    def setup_autostart_for_exe(self, selected_mode=None):
        """
        Настраивает автозапуск приложения через ярлык в реестре Windows
        
        Args:
            selected_mode (str): Выбранная стратегия обхода блокировок
        
        Returns:
            bool: True если автозапуск успешно настроен, иначе False
        """
        try:
            from log import log
            import sys, os
            import pythoncom
            from win32com.client import Dispatch
            
            # Пути к exe и директории
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)
            
            # Создаем путь для ярлыка в папке пользователя
            shortcut_path = os.path.join(
                os.path.expanduser("~"), 
                "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", 
                "Programs", "Startup", "ZapretGUI.lnk"
            )
            
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
            
            # Создаем ярлык
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe_path
            shortcut.Arguments = "--tray"
            shortcut.WorkingDirectory = exe_dir
            shortcut.WindowStyle = 7  # 7 = Minimized
            shortcut.save()
            
            # Сохраняем выбранную стратегию в реестр
            if selected_mode:
                # Создаем ключ Zapret, если он не существует
                reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Zapret")
                # Сохраняем стратегию
                winreg.SetValueEx(reg_key, "LastStrategy", 0, winreg.REG_SZ, selected_mode)
                winreg.CloseKey(reg_key)
            
            log(f"Автозапуск настроен через ярлык: {shortcut_path}", level="INFO")
            self.set_status("Автозапуск успешно настроен")
            return True
            
        except Exception as e:
            from log import log
            log(f"Ошибка при настройке автозапуска: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка: {str(e)}")
            return False
        
    def check_autostart_registry_exists(self):
        """
        Проверяет, настроен ли автозапуск приложения через реестр Windows
        
        Returns:
            bool: True если автозапуск настроен, иначе False
        """
        try:
            # Открываем ключ автозапуска в реестре
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                # Пытаемся прочитать значение
                value, _ = winreg.QueryValueEx(key, "ZapretGUI")
                
                # Если значение существует и содержит путь к exe, автозапуск настроен
                return value and (".exe" in value.lower())
        
        except FileNotFoundError:
            # Ключ или значение не найдены
            return False
        except Exception as e:
            from log import log
            log(f"Ошибка при проверке автозапуска: {str(e)}", level="ERROR")
            return False

    def remove_autostart_registry(self):
        """
        Удаляет автозапуск приложения из реестра Windows и удаляет ярлык из папки автозапуска
        
        Returns:
            bool: True если автозапуск успешно удален, иначе False
        """
        try:
            from log import log
            import os
            
            # 1. Удаляем запись из реестра
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                # Удаляем значение
                try:
                    winreg.DeleteValue(key, "ZapretGUI")
                    log("Автозапуск удален из реестра", level="INFO")
                except FileNotFoundError:
                    # Значение уже удалено
                    pass
                
            # 2. Удаляем ярлык из папки автозапуска
            shortcut_path = os.path.join(
                os.path.expanduser("~"), 
                "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", 
                "Programs", "Startup", "ZapretGUI.lnk"
            )
            
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                    log(f"Ярлык автозапуска удален: {shortcut_path}", level="INFO")
                except Exception as e:
                    log(f"Не удалось удалить ярлык автозапуска: {str(e)}", level="WARNING")
                    # Продолжаем выполнение - это не критическая ошибка
            
            self.set_status("Автозапуск успешно удален")
            return True
            
        except Exception as e:
            from log import log
            log(f"Ошибка при удалении автозапуска: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка: {str(e)}")
            return False


    def check_autostart_exists(self):
        """
        Проверяет наличие автозапуска через любой метод
        (реестр, ярлык, планировщик или службу Windows)
        
        Returns:
            bool: True если автозапуск настроен, иначе False
        """
        import os
        
        # Проверяем наличие ярлыка в папке автозапуска
        shortcut_path = os.path.join(
            os.path.expanduser("~"), 
            "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", 
            "Programs", "Startup", "ZapretGUI.lnk"
        )
        if os.path.exists(shortcut_path):
            return True
        
        # Сначала проверяем реестр (новый метод)
        if self.check_autostart_registry_exists():
            return True
            
        # Затем проверяем планировщик задач (устаревший метод)
        if self.check_scheduler_task_exists():
            return True
            
        # Наконец, проверяем службу Windows (самый устаревший метод)
        return self.check_windows_service_exists()

    
    def check_scheduler_task_exists(self):
        """
        Проверяет наличие задачи в планировщике задач Windows
        
        Returns:
            bool: True если задача существует, иначе False
        """
        try:
            task_name = "ZapretCensorliber"
            check_cmd = f'schtasks /Query /TN "{task_name}" 2>nul'
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            return result.returncode == 0
        except:
            return False
            
    def check_windows_service_exists(self):
        """
        Проверяет наличие службы Windows
        
        Returns:
            bool: True если служба существует, иначе False
        """
        try:
            service_result = subprocess.run(
                f'sc query {self.service_name}',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )
            return service_result.returncode == 0 and "STATE" in service_result.stdout
        except:
            return False

    def remove_autostart(self):
        """
        Удаляет все механизмы автозапуска (реестр, планировщик, служба)
        
        Returns:
            bool: True если все механизмы успешно удалены, иначе False
        """
        try:
            from log import log
            log("Удаление всех механизмов автозапуска...", level="INFO")
            
            # Удаляем из планировщика
            task_removed = self.remove_scheduler_task()
            
            # Удаляем службу Windows
            service_removed = self.remove_legacy_windows_service()
            
            # Удаляем из реестра
            registry_removed = self.remove_autostart_registry()
            
            # Возвращаем True, если хотя бы один метод был успешно удален
            return task_removed or service_removed or registry_removed
            
        except Exception as e:
            from log import log
            log(f"Ошибка при удалении автозапуска: {str(e)}", level="ERROR")
            return False
            
    def remove_scheduler_task(self):
        """
        Удаляет задачу из планировщика задач Windows
        
        Returns:
            bool: True если задача успешно удалена или не существовала, иначе False
        """
        try:
            from log import log
            task_name = "ZapretCensorliber"
            
            # Проверяем существование задачи
            check_cmd = f'schtasks /Query /TN "{task_name}" 2>nul'
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                log("Найдена задача в планировщике, удаляем...", level="INFO")
                delete_cmd = f'schtasks /Delete /TN "{task_name}" /F'
                subprocess.run(delete_cmd, shell=True, check=False)
                return True
            else:
                # Задача не существует
                return True
                
        except Exception as e:
            from log import log
            log(f"Ошибка при удалении задачи из планировщика: {str(e)}", level="ERROR")
            return False


    def remove_legacy_windows_service(self) -> bool:
        """
        Принудительно удаляет службу Windows ZapretCensorliber, если она ещё
        осталась от старых версий.

        Returns:
            bool: True если службы нет или она успешно удалена, иначе False
        """
        try:
            from log import log
            svc = self.service_name  # обычно 'ZapretCensorliber'

            # 1) проверяем, существует ли служба
            query = subprocess.run(
                f'sc query "{svc}"',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )

            if query.returncode != 0:
                # Служба не найдена - нечего удалять
                return True

            # 2) пытаемся остановить
            self.set_status("Остановка устаревшей службы…")
            log(f"Останавливаем службу {svc}", level="INFO")
            subprocess.run(f'sc stop "{svc}"', shell=True, capture_output=True)

            time.sleep(1.0)  # даём время на остановку

            # 3) удаляем службу
            self.set_status("Удаление устаревшей службы…")
            log(f"Удаляем службу {svc}", level="INFO")
            delete = subprocess.run(
                f'sc delete "{svc}"',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )

            if delete.returncode == 0:
                log("Служба успешно удалена", level="INFO")
                self.set_status("Служба успешно удалена")
                return True
            else:
                err = delete.stderr.strip() or delete.stdout.strip()
                log(f"Ошибка удаления службы: {err}", level="ERROR")
                self.set_status(f"Ошибка удаления службы: {err}")
                return False

        except Exception as e:
            from log import log
            log(f"remove_legacy_windows_service: {e}", level="ERROR")
            self.set_status(f"Ошибка: {e}")
            return False
            
    def get_current_service_config(self):
        """
        Получает текущую конфигурацию стратегии из реестра
        
        Returns:
            str: Имя стратегии или None, если не удалось определить
        """
        try:
            # Проверяем существование автозапуска
            if not self.check_autostart_exists():
                return None  # Автозапуск не настроен
            
            # Получаем конфигурацию из реестра
            config = get_config_from_registry()
            return config if config else "Пользовательская"
                
        except Exception as e:
            from log import log
            log(f"Ошибка при определении конфигурации: {str(e)}", level="ERROR")
            return "Неизвестная"