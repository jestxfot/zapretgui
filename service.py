import subprocess
import winreg

class ServiceManager:
    def __init__(self, winws_exe, bin_folder, status_callback=None, ui_callback=None, service_name="ZapretCensorliber"):
        """
        Инициализирует менеджер служб.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            bin_folder (str): Путь к папке с бинарными файлами
            status_callback (callable): Функция обратного вызова для отображения статуса
            service_name (str): Имя службы
        """
        self.winws_exe = winws_exe
        self.bin_folder = bin_folder
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

    def check_autostart_exists(self) -> bool:
        """
        True → хоть один механизм автозапуска найден.
        """
        try:
            from pathlib import Path
            import os
            startup_dir = (
                Path(os.environ["APPDATA"])
                / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            )
            # ярлыки
            for lnk in ("ZapretGUI.lnk", "ZapretStrategy.lnk"):
                if (startup_dir / lnk).exists():
                    return True

            # запись в реестре (новый метод)
            if self.check_autostart_registry_exists():
                return True

            # задачи планировщика (старые / новые)
            if self.check_scheduler_task_exists():
                return True

            # старая служба
            return self.check_windows_service_exists()

        except Exception:
            from log import log
            log("check_autostart_exists: необработанная ошибка", level="ERROR")
            return False
    
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