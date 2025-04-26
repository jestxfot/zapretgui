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
        self.ui_callback     = ui_callback
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

    def install_autostart_by_strategy(
            self,
            selected_mode: str,
            strategy_manager,
            index_path: str | None = None) -> bool:
        """
        • selected_mode   – ID, «красивое» имя из index.json, либо *.bat
        • strategy_manager – объект StrategyManager (скачивает при надобности)
        • index_path      – явный путь к bin/index.json (по-умолч. self.bin_folder)
        """
        try:
            from log import log
            import json, os, traceback

            # ── служебная утилита --------------------------------------------------
            def _abs_bat(bat: str) -> str:
                """делаем абсолютный путь + убираем дубликат bin\\"""               
                if os.path.isabs(bat):
                    return os.path.normpath(bat)

                # убираем ведущий bin/
                while bat.lower().startswith(("bin\\", "bin/")):
                    bat = bat[4:]
                return os.path.normpath(os.path.join(self.bin_folder, bat))

            # ── 1. index.json ------------------------------------------------------
            if not index_path:
                index_path = os.path.join(self.bin_folder, "index.json")

            if not hasattr(self, "_strategy_index"):
                with open(index_path, "r", encoding="utf-8") as f:
                    self._strategy_index = json.load(f)
            strategies: dict = self._strategy_index

            # ── 2. сопоставляем selected_mode → bat_file + strategy_id -------------
            bat_file = None
            strategy_id = None

            # ID
            if selected_mode in strategies:
                strategy_id = selected_mode
                bat_file = strategies[strategy_id]["file_path"]

            # красивое имя
            if not bat_file:
                for sid, info in strategies.items():
                    if info.get("name", "").strip().lower() == selected_mode.strip().lower():
                        strategy_id, bat_file = sid, info["file_path"]
                        break

            # пользователь дал *.bat
            if not bat_file and selected_mode.lower().endswith(".bat"):
                bat_file = selected_mode   # strategy_id остаётся None

            if not bat_file:
                log(f"Не смогли сопоставить '{selected_mode}' с .bat", level="ERROR")
                self.set_status("Ошибка: стратегия не найдена")
                return False

            # ── 3. скачиваем батник при необходимости --------------------------------
            if strategy_id and strategy_manager:
                dl_path = strategy_manager.download_strategy(strategy_id)
                if dl_path:  # может вернуть None при ошибке
                    bat_file = dl_path

            # ── 4. нормализуем путь --------------------------------------------------
            bat_path = _abs_bat(bat_file)

            if not os.path.isfile(bat_path):
                log(f"BAT-файл не найден: {bat_path}", level="ERROR")
                self.set_status("Ошибка: файл стратегии не найден")
                return False

            log(f"Настройка автозапуска для BAT: {bat_path}", level="INFO")

            # ── 5. создаём задачу планировщика --------------------------------------
            ok = self.install_task_scheduler(
                bat_file_path=bat_path,
                config_name=selected_mode,
                strategy_id=strategy_id
            )
            return ok

        except Exception as e:
            from log import log
            log(f"install_autostart_by_strategy: {e}", level="ERROR")
            log(traceback.format_exc(), level="DEBUG")
            self.set_status(f"Ошибка: {e}")
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
            
            # Получаем абсолютный путь к BAT-файлу и его директорию
            abs_bat_path = os.path.abspath(bat_file_path)
            working_dir = os.path.dirname(abs_bat_path)
            
            log(f"Создание задачи в планировщике для BAT-файла: {abs_bat_path}", level="INFO")
            
            # Формируем команду (запускаем BAT-файл напрямую)
            # Для корректной работы нужно установить рабочую директорию
            create_cmd = (
                f'schtasks /Create /SC ONSTART /TN "{task_name}" '
                f'/TR "\"{abs_bat_path}\"" '
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
    
    # ------------------------------------------------------------------
    #  НОВЫЙ МЕТОД:  удаляет устаревшую Windows-службу ZapretCensorliber
    # ------------------------------------------------------------------
    def remove_legacy_windows_service(self) -> bool:
        """
        Принудительно удаляет службу Windows ZapretCensorliber, если она ещё
        осталась от старых версий (автозапуск теперь через планировщик).

        Возвращает:
            True  – если службы нет или она успешно удалена
            False – если возникла ошибка
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
                log(f"Служба {svc} не найдена – ничего удалять", level="INFO")
                self.set_status("Служба не найдена")
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