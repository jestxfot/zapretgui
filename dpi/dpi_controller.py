"""
Контроллер для управления DPI - содержит всю логику запуска и остановки
"""

from PyQt6.QtCore import QThread, QObject, pyqtSignal, QMetaObject, Qt, Q_ARG
from strategy_menu import get_strategy_launch_method
from log import log
from dpi.process_health_check import diagnose_startup_error
import time

class DPIStartWorker(QObject):
    """Worker для асинхронного запуска DPI"""
    finished = pyqtSignal(bool, str)  # success, error_message
    progress = pyqtSignal(str)        # status_message
    
    def __init__(self, app_instance, selected_mode, launch_method):
        super().__init__()
        self.app_instance = app_instance
        self.selected_mode = selected_mode
        self.launch_method = launch_method
        self.dpi_starter = app_instance.dpi_starter

    def _get_winws_exe(self) -> str:
        """Возвращает правильный путь к winws exe в зависимости от launch_method"""
        from config.config import get_winws_exe_for_method
        # Используем переданный launch_method так как он известен при создании worker'а
        return get_winws_exe_for_method(self.launch_method)

    def run(self):
        try:
            self.progress.emit("Подготовка к запуску...")
            
            # Проверяем, не запущен ли уже процесс
            if self.dpi_starter.check_process_running_wmi(silent=True):
                skip_stop = False

                # direct_zapret2: если запущен ТОТ ЖЕ preset (@preset-zapret2.txt),
                # не останавливаем и не перезапускаем — просто "подключаемся".
                try:
                    mode_param = self.selected_mode
                    if (
                        self.launch_method in ("direct_zapret2", "direct_zapret2_orchestra")
                        and isinstance(mode_param, dict)
                        and mode_param.get("is_preset_file")
                    ):
                        preset_path = (mode_param.get("preset_path") or "").strip()
                        if preset_path:
                            from launcher_common import get_strategy_runner

                            runner = get_strategy_runner(self._get_winws_exe())
                            if hasattr(runner, "find_running_preset_pid"):
                                pid = runner.find_running_preset_pid(preset_path)
                                if pid:
                                    log(
                                        f"Preset уже запущен (PID: {pid}), пропускаем остановку",
                                        "INFO",
                                    )
                                    skip_stop = True
                except Exception:
                    pass

                if not skip_stop:
                    self.progress.emit("Останавливаем предыдущий процесс...")

                # Останавливаем через соответствующий метод
                if (not skip_stop) and self.launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                    from launcher_common import get_strategy_runner
                    runner = get_strategy_runner(self._get_winws_exe())
                    runner.stop()
                elif not skip_stop:
                    from dpi.stop import stop_dpi
                    stop_dpi(self.app_instance)

                # Ждём пока процесс действительно остановится (до 5 секунд)
                if not skip_stop:
                    max_wait = 10
                    for attempt in range(max_wait):
                        time.sleep(0.5)
                        if not self.dpi_starter.check_process_running_wmi(silent=True):
                            log(f"✅ Предыдущий процесс остановлен (попытка {attempt + 1})", "DEBUG")
                            break
                    else:
                        log("⚠️ Процесс не остановился за 5 секунд, принудительное завершение...", "WARNING")
                        import subprocess
                        try:
                            subprocess.run(['taskkill', '/F', '/IM', 'winws.exe'],
                                           capture_output=True, timeout=3)
                            subprocess.run(['taskkill', '/F', '/IM', 'winws2.exe'],
                                           capture_output=True, timeout=3)
                            time.sleep(1)
                        except Exception as e:
                            log(f"Ошибка taskkill: {e}", "DEBUG")

                    # Дополнительная пауза для освобождения WinDivert
                    time.sleep(0.5)

            self.progress.emit("Запуск DPI...")
            
            # Выбираем метод запуска
            if self.launch_method == "orchestra":
                success = self._start_orchestra()
            elif self.launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                # direct_zapret2_orchestra работает так же как direct, но с другим набором стратегий
                # direct_zapret1 работает так же как direct, но использует winws.exe и tcp_zapret1.json
                success = self._start_direct()
            else:
                success = self._start_bat()
            
            if success:
                self.progress.emit("DPI успешно запущен")
                self.finished.emit(True, "")
            else:
                # В некоторых ситуациях старт "не был даже начат" (например, args пустые).
                # Тогда нельзя эмитить success=True, иначе дальше появится ложная ошибка
                # "процесс не найден после старта".
                fatal_reason = ""
                try:
                    mode_param = self.selected_mode
                    if isinstance(mode_param, dict) and self.launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                        if mode_param.get("is_preset_file"):
                            preset_path = (mode_param.get("preset_path") or "").strip()
                            if not preset_path:
                                fatal_reason = "❌ Ошибка: не указан путь к preset файлу"
                        elif mode_param.get("is_combined"):
                            args_str = (mode_param.get("args") or "").strip()
                            if not args_str:
                                fatal_reason = "⚠️ Выберите хотя бы одну категорию для запуска"
                            else:
                                if self.launch_method == "direct_zapret1":
                                    has_filters = any(f in args_str for f in ["--wf-tcp=", "--wf-udp="])
                                else:
                                    has_filters = any(f in args_str for f in ["--wf-tcp-out", "--wf-udp-out", "--wf-raw-part"])
                                if not has_filters:
                                    fatal_reason = "⚠️ Выберите хотя бы одну категорию для запуска"
                except Exception:
                    fatal_reason = ""

                if fatal_reason:
                    self.progress.emit(fatal_reason)
                    self.finished.emit(False, fatal_reason)
                else:
                    # Не показываем ошибку на splash screen — ProcessMonitor обновит UI
                    # когда процесс запустится или упадёт
                    self.progress.emit("Ожидание запуска DPI...")
                    self.finished.emit(True, "")  # Не блокируем splash screen ошибкой
                
        except Exception as e:
            # Диагностируем ошибку и выводим понятное сообщение
            exe_path = getattr(self.dpi_starter, 'winws_exe', None)
            diagnosis = diagnose_startup_error(e, exe_path)
            for line in diagnosis.split('\n'):
                log(line, "❌ ERROR")
            self.finished.emit(False, diagnosis.split('\n')[0])  # Первая строка как краткое сообщение

    def _start_direct(self):
        """Запуск через прямой метод (StrategyRunner)"""
        try:
            from launcher_common import get_strategy_runner

            # Получаем runner
            runner = get_strategy_runner(self._get_winws_exe())

            mode_param = self.selected_mode

            # ✅ НОВЫЙ РЕЖИМ: Запуск из готового preset файла (без реестра)
            if isinstance(mode_param, dict) and mode_param.get('is_preset_file'):
                preset_path = mode_param.get('preset_path', '')
                strategy_name = mode_param.get('name', 'Пресет')

                log(f"Запуск из preset файла: {preset_path}", "INFO")

                if not preset_path:
                    log("Путь к preset файлу не указан", "❌ ERROR")
                    self.progress.emit("❌ Ошибка: не указан путь к preset файлу")
                    return False

                import os
                if not os.path.exists(preset_path):
                    log(f"Preset файл не найден: {preset_path}", "❌ ERROR")
                    self.progress.emit("❌ Preset файл не найден")
                    return False

                # Запускаем напрямую через @file (hot-reload будет работать!)
                success = runner.start_from_preset_file(preset_path, strategy_name)

                if success:
                    log(f"Пресет '{strategy_name}' успешно запущен", "✅ SUCCESS")
                    return True
                else:
                    log("Не удалось запустить пресет", "❌ ERROR")
                    self.progress.emit("❌ Ошибка запуска. Попробуйте перезапустить программу")
                    return False

            # Обработка комбинированных стратегий
            elif isinstance(mode_param, dict) and mode_param.get('is_combined'):
                strategy_name = mode_param.get('name', 'Комбинированная стратегия')
                args_str = mode_param.get('args', '')
                
                log(f"Запуск комбинированной стратегии: {strategy_name}", "INFO")
                
                if not args_str:
                    log("Отсутствуют аргументы для комбинированной стратегии", "❌ ERROR")
                    self.progress.emit("❌ Ошибка: не заданы аргументы стратегии")
                    return False
                
                # ✅ Проверка наличия WinDivert фильтров (без них winws не запустится)
                if self.launch_method == "direct_zapret1":
                    # Zapret 1 (winws.exe) использует синтаксис --wf-tcp= / --wf-udp=
                    has_filters = any(f in args_str for f in ['--wf-tcp=', '--wf-udp='])
                else:
                    # Zapret 2 (winws2.exe) использует --wf-tcp-out= / --wf-udp-out= / --wf-raw-part=
                    has_filters = any(f in args_str for f in ['--wf-tcp-out', '--wf-udp-out', '--wf-raw-part'])
                if not has_filters:
                    if self.launch_method == "direct_zapret1":
                        log("Нет активных WinDivert фильтров (--wf-tcp=, --wf-udp=)", "❌ ERROR")
                    else:
                        log("Нет активных WinDivert фильтров (--wf-tcp-out, --wf-udp-out, --wf-raw-part)", "❌ ERROR")
                    self.progress.emit("⚠️ Выберите хотя бы одну категорию для запуска")
                    return False
                
                # Парсим аргументы (posix=False для Windows чтобы сохранить бэкслеши в путях)
                import shlex
                try:
                    custom_args = shlex.split(args_str, posix=False)
                    log(f"Аргументы комбинированной стратегии ({len(custom_args)} шт.)", "DEBUG")
                    
                    # Запускаем стратегию напрямую через runner
                    # Runner теперь автоматически делает retry при ошибке WinDivert
                    success = runner.start_strategy_custom(custom_args, strategy_name)
                    
                    if success:
                        log("Комбинированная стратегия успешно запущена", "✅ SUCCESS")
                        return True
                    else:
                        # Даём понятную подсказку пользователю
                        log("Не удалось запустить комбинированную стратегию", "❌ ERROR")
                        self.progress.emit("❌ Ошибка запуска. Попробуйте перезапустить программу или ПК")
                        return False
                        
                except Exception as parse_error:
                    log(f"Ошибка парсинга аргументов: {parse_error}", "❌ ERROR")
                    self.progress.emit(f"❌ Ошибка в параметрах стратегии")
                    return False
            
            # Для Direct режима поддерживаются только комбинированные стратегии
            else:
                log(f"Direct режим поддерживает только комбинированные стратегии, получен: {type(mode_param)}", "❌ ERROR")
                self.progress.emit("❌ Неподдерживаемый тип стратегии")
                return False
                
        except Exception as e:
            # Диагностируем ошибку и выводим понятное сообщение
            exe_path = self._get_winws_exe() if hasattr(self.app_instance, 'dpi_starter') else None
            diagnosis = diagnose_startup_error(e, exe_path)
            for line in diagnosis.split('\n'):
                log(line, "❌ ERROR")
            self.progress.emit(diagnosis.split('\n')[0])  # Первая строка как статус
            return False

    def _start_bat(self):
        """Запуск через старый метод (.bat файлы)"""
        try:
            # Нормализуем selected_mode
            mode_param = self.selected_mode
            
            if isinstance(mode_param, dict):
                mode_param = mode_param.get('name') or 'default'
            elif mode_param is None:
                mode_param = 'default'
            
            log(f"Запуск BAT стратегии: {mode_param}", "DEBUG")
            
            # Используем BatDPIStart для BAT режима
            result = self.app_instance.dpi_starter.start_dpi(selected_mode=mode_param)
            
            # Добавляем дополнительную проверку с несколькими попытками
            if result:
                import time
                
                # Даем процессу время на инициализацию - несколько проверок
                max_checks = 5
                for attempt in range(max_checks):
                    time.sleep(0.4)  # Проверяем каждые 400мс
                    
                    if self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                        log(f"✅ Процесс winws.exe успешно запущен и работает (попытка {attempt + 1})", "✅ SUCCESS")
                        return True
                
                # Если после всех проверок процесс не найден
                log("❌ DPI не запустился - процесс не найден после старта", "❌ ERROR")
                
                # Диагностика причин падения
                try:
                    from dpi.process_health_check import check_common_crash_causes
                    causes = check_common_crash_causes()
                    if causes:
                        log(f"💡 Возможные причины падения:\n{causes}", "INFO")
                except Exception as e:
                    log(f"Ошибка диагностики: {e}", "DEBUG")
                
                # Пытаемся получить детальную информацию из событий Windows
                try:
                    import subprocess
                    result = subprocess.run(
                        ['wevtutil', 'qe', 'Application', '/c:5', '/rd:true', '/f:text'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.stdout and 'winws' in result.stdout.lower():
                        log(f"События Windows: {result.stdout[:500]}", "DEBUG")
                except:
                    pass
                return False
            
            return result
            
        except Exception as e:
            # Диагностируем ошибку и выводим понятное сообщение
            exe_path = self._get_winws_exe() if hasattr(self.app_instance, 'dpi_starter') else None
            diagnosis = diagnose_startup_error(e, exe_path)
            for line in diagnosis.split('\n'):
                log(line, "❌ ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            return False

    def _start_orchestra(self):
        """Запуск через оркестратор автоматического обучения"""
        try:
            from orchestra import OrchestraRunner

            log("Запуск оркестратора...", "INFO")

            # Создаём или получаем runner
            if not hasattr(self.app_instance, 'orchestra_runner') or self.app_instance.orchestra_runner is None:
                self.app_instance.orchestra_runner = OrchestraRunner()

            runner = self.app_instance.orchestra_runner

            # Подключаем callback для логов через сигнал Qt (thread-safe)
            # emit_log() эмитит сигнал с QueuedConnection - безопасно из любого потока
            has_attr = hasattr(self.app_instance, 'orchestra_page')
            page_exists = self.app_instance.orchestra_page if has_attr else None
            print(f"[DEBUG _start_orchestra] has_attr={has_attr}, page_exists={page_exists}")  # DEBUG
            if has_attr and page_exists:
                runner.set_output_callback(self.app_instance.orchestra_page.emit_log)
            else:
                log("orchestra_page не существует при старте, callback будет установлен позже", "WARNING")

            # Запускаем (prepare + start)
            if runner.start():
                log("Оркестратор успешно запущен", "✅ SUCCESS")

                # Запускаем мониторинг на странице оркестра (через main thread!)
                # ВАЖНО: start_monitoring() запускает QTimer, который нельзя создавать из другого потока
                if hasattr(self.app_instance, 'orchestra_page') and self.app_instance.orchestra_page:
                    QMetaObject.invokeMethod(
                        self.app_instance.orchestra_page,
                        "start_monitoring",
                        Qt.ConnectionType.QueuedConnection
                    )

                return True
            else:
                log("Не удалось запустить оркестратор", "❌ ERROR")
                return False

        except Exception as e:
            # Диагностируем ошибку и выводим понятное сообщение
            exe_path = self._get_winws_exe() if hasattr(self.app_instance, 'dpi_starter') else None
            diagnosis = diagnose_startup_error(e, exe_path)
            for line in diagnosis.split('\n'):
                log(line, "❌ ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            return False


class DPIStopWorker(QObject):
    """Worker для асинхронной остановки DPI"""
    finished = pyqtSignal(bool, str)  # success, error_message
    progress = pyqtSignal(str)        # status_message

    def __init__(self, app_instance, launch_method):
        super().__init__()
        self.app_instance = app_instance
        self.launch_method = launch_method

    def _get_winws_exe(self) -> str:
        """Возвращает правильный путь к winws exe в зависимости от launch_method"""
        from config.config import get_winws_exe_for_method
        # Используем переданный launch_method так как он известен при создании worker'а
        return get_winws_exe_for_method(self.launch_method)

    def run(self):
        try:
            self.progress.emit("Остановка DPI...")
            
            # Проверяем, запущен ли процесс
            if not self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                self.progress.emit("DPI уже остановлен")
                self.finished.emit(True, "DPI уже был остановлен")
                return
            
            self.progress.emit("Завершение процессов...")
            
            # Выбираем метод остановки
            if self.launch_method == "orchestra":
                success = self._stop_orchestra()
            elif self.launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                success = self._stop_direct()
            else:
                success = self._stop_bat()
            
            if success:
                self.progress.emit("DPI успешно остановлен")
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "Не удалось полностью остановить процесс")
                
        except Exception as e:
            error_msg = f"Ошибка остановки DPI: {str(e)}"
            log(error_msg, "❌ ERROR")
            self.finished.emit(False, error_msg)
    
    def _stop_direct(self):
        """Остановка через новый метод"""
        try:
            from launcher_common import get_strategy_runner
            from utils.process_killer import kill_winws_all

            runner = get_strategy_runner(self._get_winws_exe())
            success = runner.stop()
            
            # Дополнительно убиваем все процессы через Win API
            if not success or self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                kill_winws_all()
            
            # Проверяем результат
            return not self.app_instance.dpi_starter.check_process_running_wmi(silent=True)
            
        except Exception as e:
            log(f"Ошибка прямой остановки: {e}", "❌ ERROR")
            return False
    
    def _stop_bat(self):
        """Остановка через старый метод"""
        try:
            from dpi.stop import stop_dpi
            stop_dpi(self.app_instance)

            # Проверяем результат
            return not self.app_instance.dpi_starter.check_process_running_wmi(silent=True)

        except Exception as e:
            log(f"Ошибка остановки через .bat: {e}", "❌ ERROR")
            return False

    def _stop_orchestra(self):
        """Остановка оркестратора"""
        try:
            from utils.process_killer import kill_winws_all

            # Останавливаем через runner если есть
            if hasattr(self.app_instance, 'orchestra_runner') and self.app_instance.orchestra_runner:
                self.app_instance.orchestra_runner.stop()

                # Останавливаем мониторинг на странице оркестра
                if hasattr(self.app_instance, 'orchestra_page'):
                    self.app_instance.orchestra_page.stop_monitoring()

            # Дополнительно убиваем все процессы через Win API
            if self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                kill_winws_all()

            # Проверяем результат
            return not self.app_instance.dpi_starter.check_process_running_wmi(silent=True)

        except Exception as e:
            log(f"Ошибка остановки оркестратора: {e}", "❌ ERROR")
            return False


class StopAndExitWorker(QObject):
    """Worker для остановки DPI и выхода из программы"""
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.launch_method = get_strategy_launch_method()

    def _get_winws_exe(self) -> str:
        """Возвращает правильный путь к winws exe в зависимости от launch_method"""
        from config.config import get_winws_exe_for_method
        # Используем launch_method определённый в __init__
        return get_winws_exe_for_method(self.launch_method)

    def run(self):
        try:
            self.progress.emit("Остановка DPI перед закрытием...")

            # Выбираем метод остановки
            if self.launch_method == "orchestra":
                # Останавливаем оркестратор
                if hasattr(self.app_instance, 'orchestra_runner') and self.app_instance.orchestra_runner:
                    self.app_instance.orchestra_runner.stop()
                # Дополнительная очистка
                from utils.process_killer import kill_winws_all
                kill_winws_all()
            elif self.launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                from launcher_common import get_strategy_runner
                runner = get_strategy_runner(self._get_winws_exe())
                runner.stop()

                # Дополнительная очистка
                from dpi.stop import stop_dpi_direct
                stop_dpi_direct(self.app_instance)
            else:
                from dpi.stop import stop_dpi
                stop_dpi(self.app_instance)

            self.progress.emit("Завершение работы...")
            self.finished.emit()
            
        except Exception as e:
            log(f"Ошибка при остановке перед закрытием: {e}", "❌ ERROR")
            self.finished.emit()


class DPIController:
    """Основной контроллер для управления DPI"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self._dpi_start_thread = None
        self._dpi_stop_thread = None
        self._stop_exit_thread = None

    def start_dpi_async(self, selected_mode=None, launch_method=None):
        """Асинхронно запускает DPI без блокировки UI

        Args:
            selected_mode: Стратегия для запуска
            launch_method: Метод запуска ("direct_zapret2" или "bat"). Если None - читается из реестра
        """
        # Проверка на уже запущенный поток
        try:
            if self._dpi_start_thread and self._dpi_start_thread.isRunning():
                log("Запуск DPI уже выполняется", "DEBUG")
                return
        except RuntimeError:
            self._dpi_start_thread = None

        # Проверяем выбранный метод запуска (явно переданный или из реестра)
        if launch_method is None:
            launch_method = get_strategy_launch_method()
        log(f"Используется метод запуска: {launch_method}", "INFO")

        # Для оркестра не нужно выбирать стратегию - он работает автоматически
        if launch_method == "orchestra":
            selected_mode = {'is_orchestra': True, 'name': 'Оркестр'}

        # ✅ ИСПРАВЛЕНИЕ: Если стратегия не выбрана - используем готовый preset файл
        elif selected_mode is None or selected_mode == 'default':
            if launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                # Для Direct режимов используем готовый preset файл.
                # direct_zapret2: управляется PresetManager (active preset)
                # direct_zapret2_orchestra/direct_zapret1: один файл в MAIN_DIRECTORY
                from pathlib import Path
                from config import MAIN_DIRECTORY

                preset_name = "Default"
                if launch_method == "direct_zapret2":
                    from preset_zapret2 import get_active_preset_path, get_active_preset_name
                    preset_path = get_active_preset_path()
                    preset_name = get_active_preset_name() or "Default"
                elif launch_method == "direct_zapret2_orchestra":
                    preset_path = Path(MAIN_DIRECTORY) / "preset-zapret2-orchestra.txt"
                    preset_name = "Orchestra"
                else:  # direct_zapret1
                    preset_path = Path(MAIN_DIRECTORY) / "preset-zapret1.txt"
                    preset_name = "Zapret 1"

                if not preset_path.exists():
                    log(f"Preset файл не найден: {preset_path}", "❌ ERROR")
                    self.app.set_status("❌ Preset файл не найден. Создайте пресет в настройках")
                    if hasattr(self.app, 'ui_manager'):
                        self.app.ui_manager.update_ui_state(running=False)
                    return

                # Проверяем что файл не пустой
                try:
                    content = preset_path.read_text(encoding='utf-8').strip()

                    # 🧹 Sanitize placeholder categories that reference non-existent stub lists.
                    # If preset contains `lists/unknown.txt` or `lists/ipset-unknown.txt`,
                    # drop that whole category to prevent winws2 from exiting immediately.
                    if launch_method in ("direct_zapret2", "direct_zapret2_orchestra"):
                        content_l = content.lower()
                        if ("unknown.txt" in content_l) or ("ipset-unknown.txt" in content_l):
                            try:
                                from preset_zapret2.txt_preset_parser import (
                                    parse_preset_file,
                                    generate_preset_file,
                                )

                                data = parse_preset_file(preset_path)
                                if generate_preset_file(data, preset_path, atomic=True):
                                    content = preset_path.read_text(encoding="utf-8").strip()
                            except Exception as e:
                                log(f"Ошибка очистки preset файла от unknown.txt: {e}", "DEBUG")
                    # Проверяем наличие WinDivert фильтров
                    if launch_method == "direct_zapret1":
                        # Zapret 1 (winws.exe) использует синтаксис --wf-tcp= / --wf-udp=
                        has_filters = any(f in content for f in ['--wf-tcp=', '--wf-udp='])
                    else:
                        # Zapret 2 (winws2.exe) использует --wf-tcp-out= / --wf-udp-out= / --wf-raw-part=
                        has_filters = any(f in content for f in ['--wf-tcp-out', '--wf-udp-out', '--wf-raw-part'])
                    if not has_filters:
                        log("Preset файл не содержит активных фильтров", "WARNING")
                        self.app.set_status("⚠️ Выберите хотя бы одну категорию для запуска")
                        if hasattr(self.app, 'ui_manager'):
                            self.app.ui_manager.update_ui_state(running=False)
                        return
                except Exception as e:
                    log(f"Ошибка чтения preset файла: {e}", "❌ ERROR")
                    self.app.set_status(f"❌ Ошибка чтения preset: {e}")
                    if hasattr(self.app, 'ui_manager'):
                        self.app.ui_manager.update_ui_state(running=False)
                    return

                selected_mode = {
                    'is_preset_file': True,
                    'name': f"Пресет: {preset_name}",
                    'preset_path': str(preset_path)
                }
                log(f"Используется preset файл: {preset_path}", "INFO")
                
            else:  # BAT режим
                # Для BAT режима берем последнюю выбранную стратегию из реестра
                from config import get_last_strategy
                
                last_strategy_name = get_last_strategy()
                log(f"Последняя использованная стратегия из реестра: {last_strategy_name}", "DEBUG")
                
                if last_strategy_name and hasattr(self.app, 'strategy_manager'):
                    try:
                        strategies = self.app.strategy_manager.get_local_strategies_only()
                        
                        # Ищем стратегию по имени
                        found_strategy = None
                        for sid, sinfo in strategies.items():
                            if sinfo.get('name') == last_strategy_name:
                                found_strategy = sinfo
                                break
                        
                        if found_strategy:
                            selected_mode = found_strategy
                            log(f"Используется сохраненная стратегия: {found_strategy.get('name')}", "INFO")
                        else:
                            # Если сохраненная стратегия не найдена, ищем рекомендуемую
                            log(f"Стратегия '{last_strategy_name}' не найдена, ищем рекомендуемую", "⚠ WARNING")
                            
                            # Ищем рекомендуемую стратегию
                            for sid, sinfo in strategies.items():
                                if sinfo.get('label') == 'recommended':
                                    selected_mode = sinfo
                                    log(f"Используется рекомендуемая стратегия: {sinfo.get('name')}", "INFO")
                                    break
                            
                            # Если не нашли рекомендуемую, берем первую
                            if not selected_mode and strategies:
                                selected_mode = next(iter(strategies.values()))
                                log(f"Используется первая доступная стратегия: {selected_mode.get('name')}", "INFO")
                            
                            if not selected_mode:
                                log("Нет доступных стратегий в папке bat", "❌ ERROR")
                                self.app.set_status("❌ Нет доступных стратегий")
                                return
                                
                    except Exception as e:
                        log(f"Ошибка получения стратегии из реестра: {e}", "❌ ERROR")
                        self.app.set_status(f"❌ Ошибка: {e}")
                        return
                else:
                    # Если в реестре ничего нет, ищем рекомендуемую
                    if hasattr(self.app, 'strategy_manager'):
                        try:
                            strategies = self.app.strategy_manager.get_local_strategies_only()
                            
                            # Ищем рекомендуемую стратегию
                            for sid, sinfo in strategies.items():
                                if sinfo.get('label') == 'recommended':
                                    selected_mode = sinfo
                                    log(f"Используется рекомендуемая стратегия: {sinfo.get('name')}", "INFO")
                                    break
                            
                            # Если не нашли рекомендуемую, берем первую
                            if not selected_mode and strategies:
                                selected_mode = next(iter(strategies.values()))
                                log(f"Используется первая доступная стратегия: {selected_mode.get('name')}", "INFO")
                            
                            if not selected_mode:
                                log("Нет доступных стратегий", "❌ ERROR")
                                self.app.set_status("❌ Нет доступных стратегий")
                                return
                                
                        except Exception as e:
                            log(f"Ошибка получения стратегий: {e}", "❌ ERROR")
                            self.app.set_status(f"❌ Ошибка: {e}")
                            return
                    else:
                        log("strategy_manager недоступен", "❌ ERROR")
                        self.app.set_status("❌ Менеджер стратегий недоступен")
                        return
        
        # ✅ ОБРАБОТКА всех типов стратегий (остальной код без изменений)
        mode_name = "Неизвестная стратегия"
        
        if isinstance(selected_mode, dict) and selected_mode.get('is_combined'):
            # Комбинированная стратегия
            mode_name = selected_mode.get('name', 'Комбинированная стратегия')
            log(f"Обработка комбинированной стратегии: {mode_name}", "DEBUG")
            
            # Сохраняем выборы в реестр для будущего использования
            if 'selections' in selected_mode:
                from strategy_menu import set_direct_strategy_selections
                selections = selected_mode['selections']
                set_direct_strategy_selections(selections)
            
        elif isinstance(selected_mode, tuple) and len(selected_mode) == 2:
            # Встроенная стратегия (ID, название)
            strategy_id, strategy_name = selected_mode
            mode_name = strategy_name
            log(f"Обработка встроенной стратегии: {strategy_name} (ID: {strategy_id})", "DEBUG")
            
        elif isinstance(selected_mode, dict):
            # BAT стратегия (отдельный ключ реестра)
            mode_name = selected_mode.get('name', str(selected_mode))
            log(f"Обработка BAT стратегии: {mode_name}", "DEBUG")
            
            # Сохраняем имя BAT стратегии в реестр для будущего использования
            from config.reg import set_last_bat_strategy
            set_last_bat_strategy(mode_name)
            
        elif isinstance(selected_mode, str):
            # Строковое название (BAT стратегия)
            mode_name = selected_mode
            log(f"Обработка BAT стратегии по имени: {mode_name}", "DEBUG")
            
            # Сохраняем имя BAT стратегии в реестр
            from config.reg import set_last_bat_strategy
            set_last_bat_strategy(mode_name)
        
        # Показываем состояние запуска
        if launch_method == "orchestra":
            method_name = "оркестр"
        elif launch_method == "direct_zapret2":
            method_name = "прямой"
        elif launch_method == "direct_zapret2_orchestra":
            method_name = "оркестратор Z2"
        elif launch_method == "direct_zapret1":
            method_name = "прямой Z1"
        else:
            method_name = "классический"
        self.app.set_status(f"🚀 Запуск DPI ({method_name}): {mode_name}")
        
        # ✅ Показываем спиннер загрузки
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'strategies_page'):
            self.app.main_window.strategies_page.show_loading()
        
        # ✅ Показываем индикатор загрузки на страницах
        if hasattr(self.app, 'control_page'):
            self.app.control_page.set_loading(True, "Запуск Zapret...")
        if hasattr(self.app, 'zapret2_direct_control_page'):
            try:
                self.app.zapret2_direct_control_page.set_loading(True, "Запуск Zapret...")
            except Exception:
                pass
        if hasattr(self.app, 'home_page'):
            self.app.home_page.set_loading(True, "Запуск Zapret...")
        
        # Блокируем кнопки во время операции
        if hasattr(self.app, 'start_btn'):
            self.app.start_btn.setEnabled(False)
        if hasattr(self.app, 'stop_btn'):
            self.app.stop_btn.setEnabled(False)
        
        # Создаем поток и worker
        self._dpi_start_thread = QThread()
        self._dpi_start_worker = DPIStartWorker(self.app, selected_mode, launch_method)
        self._dpi_start_worker.moveToThread(self._dpi_start_thread)
        
        # Подключение сигналов
        self._dpi_start_thread.started.connect(self._dpi_start_worker.run)
        self._dpi_start_worker.progress.connect(self.app.set_status)
        self._dpi_start_worker.finished.connect(self._on_dpi_start_finished)
        
        # Очистка ресурсов
        def cleanup_start_thread():
            try:
                if self._dpi_start_thread:
                    self._dpi_start_thread.quit()
                    self._dpi_start_thread.wait(2000)
                    self._dpi_start_thread = None
                    
                if hasattr(self, '_dpi_start_worker'):
                    self._dpi_start_worker.deleteLater()
                    self._dpi_start_worker = None
            except Exception as e:
                log(f"Ошибка при очистке потока запуска: {e}", "❌ ERROR")
        
        self._dpi_start_worker.finished.connect(cleanup_start_thread)
        
        # Запускаем поток
        self._dpi_start_thread.start()
        
        log(f"Запуск асинхронного старта DPI: {mode_name} (метод: {method_name})", "INFO")    

    def stop_dpi_async(self):
        """Асинхронно останавливает DPI без блокировки UI"""
        # Проверка на уже запущенный поток
        try:
            if self._dpi_stop_thread and self._dpi_stop_thread.isRunning():
                log("Остановка DPI уже выполняется", "DEBUG")
                return
        except RuntimeError:
            self._dpi_stop_thread = None
        
        launch_method = get_strategy_launch_method()

        # Показываем состояние остановки
        if launch_method == "orchestra":
            method_name = "оркестр"
        elif launch_method == "direct_zapret2":
            method_name = "прямой"
        elif launch_method == "direct_zapret2_orchestra":
            method_name = "оркестратор Z2"
        elif launch_method == "direct_zapret1":
            method_name = "прямой Z1"
        else:
            method_name = "классический"
        self.app.set_status(f"🛑 Остановка DPI ({method_name})...")
        
        # ✅ Показываем спиннер загрузки
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'strategies_page'):
            self.app.main_window.strategies_page.show_loading()
        
        # ✅ Показываем индикатор загрузки на страницах
        if hasattr(self.app, 'control_page'):
            self.app.control_page.set_loading(True, "Остановка Zapret...")
        if hasattr(self.app, 'zapret2_direct_control_page'):
            try:
                self.app.zapret2_direct_control_page.set_loading(True, "Остановка Zapret...")
            except Exception:
                pass
        if hasattr(self.app, 'home_page'):
            self.app.home_page.set_loading(True, "Остановка Zapret...")
        
        # Блокируем кнопки во время операции
        if hasattr(self.app, 'start_btn'):
            self.app.start_btn.setEnabled(False)
        if hasattr(self.app, 'stop_btn'):
            self.app.stop_btn.setEnabled(False)
        
        # Создаем поток и worker
        self._dpi_stop_thread = QThread()
        self._dpi_stop_worker = DPIStopWorker(self.app, launch_method)
        self._dpi_stop_worker.moveToThread(self._dpi_stop_thread)
        
        # Подключение сигналов
        self._dpi_stop_thread.started.connect(self._dpi_stop_worker.run)
        self._dpi_stop_worker.progress.connect(self.app.set_status)
        self._dpi_stop_worker.finished.connect(self._on_dpi_stop_finished)
        
        # Очистка ресурсов
        def cleanup_stop_thread():
            try:
                if self._dpi_stop_thread:
                    self._dpi_stop_thread.quit()
                    self._dpi_stop_thread.wait(2000)
                    self._dpi_stop_thread = None
                    
                if hasattr(self, '_dpi_stop_worker'):
                    self._dpi_stop_worker.deleteLater()
                    self._dpi_stop_worker = None
            except Exception as e:
                log(f"Ошибка при очистке потока остановки: {e}", "❌ ERROR")
        
        self._dpi_stop_worker.finished.connect(cleanup_stop_thread)
        
        # Устанавливаем флаг ручной остановки
        self.app.manually_stopped = True
        
        # Запускаем поток
        self._dpi_stop_thread.start()
        
        log(f"Запуск асинхронной остановки DPI (метод: {method_name})", "INFO")
    
    def stop_and_exit_async(self):
        """Асинхронно останавливает DPI и закрывает программу"""
        self.app._is_exiting = True
        
        # Создаем worker и поток
        self._stop_exit_thread = QThread()
        self._stop_exit_worker = StopAndExitWorker(self.app)
        self._stop_exit_worker.moveToThread(self._stop_exit_thread)
        
        # Подключаем сигналы
        self._stop_exit_thread.started.connect(self._stop_exit_worker.run)
        self._stop_exit_worker.progress.connect(self.app.set_status)
        self._stop_exit_worker.finished.connect(self._on_stop_and_exit_finished)
        self._stop_exit_worker.finished.connect(self._stop_exit_thread.quit)
        self._stop_exit_worker.finished.connect(self._stop_exit_worker.deleteLater)
        self._stop_exit_thread.finished.connect(self._stop_exit_thread.deleteLater)
        
        # Запускаем поток
        self._stop_exit_thread.start()
    
    def _on_dpi_start_finished(self, success, error_message):
        """Обрабатывает завершение асинхронного запуска DPI"""
        try:
            # Восстанавливаем кнопки
            if hasattr(self.app, 'start_btn'):
                self.app.start_btn.setEnabled(True)
            if hasattr(self.app, 'stop_btn'):
                self.app.stop_btn.setEnabled(True)
            
            # ✅ Скрываем индикатор загрузки на страницах
            if hasattr(self.app, 'control_page'):
                self.app.control_page.set_loading(False)
            if hasattr(self.app, 'zapret2_direct_control_page'):
                try:
                    self.app.zapret2_direct_control_page.set_loading(False)
                except Exception:
                    pass
            if hasattr(self.app, 'home_page'):
                self.app.home_page.set_loading(False)
            
            # ✅ Показываем галочку успеха (скрываем спиннер)
            if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'strategies_page'):
                self.app.main_window.strategies_page.show_success()
            
            if success:
                # ✅ РЕАЛЬНАЯ ПРОВЕРКА: процесс действительно запущен?
                # Retry with short delays to handle race condition where
                # winws2.exe hasn't appeared in the process table yet.
                is_actually_running = self.app.dpi_starter.check_process_running_wmi(silent=True)
                if not is_actually_running:
                    import time
                    for _retry in range(3):
                        time.sleep(0.3)
                        is_actually_running = self.app.dpi_starter.check_process_running_wmi(silent=True)
                        if is_actually_running:
                            break
                
                if is_actually_running:
                    log("DPI запущен асинхронно", "INFO")
                    self.app.set_status("✅ DPI успешно запущен")
                        
                    # ✅ ИСПОЛЬЗУЕМ UI MANAGER вместо app.update_ui
                    if hasattr(self.app, 'ui_manager'):
                        self.app.ui_manager.update_ui_state(running=True)
                    
                    # ✅ ИСПОЛЬЗУЕМ PROCESS MONITOR MANAGER вместо app.on_process_status_changed
                    if hasattr(self.app, 'process_monitor_manager'):
                        self.app.process_monitor_manager.on_process_status_changed(True)
                    
                    # Устанавливаем флаг намеренного запуска
                    self.app.intentional_start = True
                    
                    # Перезапускаем Discord если нужно
                    from discord.discord_restart import get_discord_restart_setting
                    if not self.app.first_start and get_discord_restart_setting():
                        if hasattr(self.app, 'discord_manager'):
                            self.app.discord_manager.restart_discord_if_running()
                    else:
                        self.app.first_start = False
                else:
                    # Процесс не запустился или сразу упал
                    log("DPI не запустился - процесс не найден после старта", "❌ ERROR")
                    self.app.set_status("❌ Процесс не запустился. Проверьте логи")
                    
                    if hasattr(self.app, 'ui_manager'):
                        self.app.ui_manager.update_ui_state(running=False)
                    if hasattr(self.app, 'process_monitor_manager'):
                        self.app.process_monitor_manager.on_process_status_changed(False)
                    
            else:
                log(f"Ошибка асинхронного запуска DPI: {error_message}", "❌ ERROR")
                self.app.set_status(f"❌ Ошибка запуска: {error_message}")
                
                # ✅ ИСПОЛЬЗУЕМ UI MANAGER вместо app.update_ui
                if hasattr(self.app, 'ui_manager'):
                    self.app.ui_manager.update_ui_state(running=False)
                
                # ✅ ИСПОЛЬЗУЕМ PROCESS MONITOR MANAGER
                if hasattr(self.app, 'process_monitor_manager'):
                    self.app.process_monitor_manager.on_process_status_changed(False)
                
        except Exception as e:
            log(f"Ошибка при обработке результата запуска DPI: {e}", "❌ ERROR")
            self.app.set_status(f"Ошибка: {e}")
    
    def _on_dpi_stop_finished(self, success, error_message):
        """Обрабатывает завершение асинхронной остановки DPI"""
        try:
            # Восстанавливаем кнопки
            if hasattr(self.app, 'start_btn'):
                self.app.start_btn.setEnabled(True)
            if hasattr(self.app, 'stop_btn'):
                self.app.stop_btn.setEnabled(True)
            
            # ✅ Скрываем индикатор загрузки на страницах
            if hasattr(self.app, 'control_page'):
                self.app.control_page.set_loading(False)
            if hasattr(self.app, 'zapret2_direct_control_page'):
                try:
                    self.app.zapret2_direct_control_page.set_loading(False)
                except Exception:
                    pass
            if hasattr(self.app, 'home_page'):
                self.app.home_page.set_loading(False)
            
            # ✅ Показываем галочку (скрываем спиннер)
            if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'strategies_page'):
                self.app.main_window.strategies_page.show_success()
            
            if success:
                # ✅ РЕАЛЬНАЯ ПРОВЕРКА: процесс действительно остановлен?
                is_still_running = self.app.dpi_starter.check_process_running_wmi(silent=True)
                
                if not is_still_running:
                    log("DPI остановлен асинхронно", "INFO")
                    if error_message:
                        self.app.set_status(f"✅ {error_message}")
                    else:
                        self.app.set_status("✅ DPI успешно остановлен")
                    
                    # ✅ ИСПОЛЬЗУЕМ UI MANAGER вместо app.update_ui
                    if hasattr(self.app, 'ui_manager'):
                        self.app.ui_manager.update_ui_state(running=False)
                    
                    # ✅ ИСПОЛЬЗУЕМ PROCESS MONITOR MANAGER
                    if hasattr(self.app, 'process_monitor_manager'):
                        self.app.process_monitor_manager.on_process_status_changed(False)
                else:
                    # Процесс всё ещё работает
                    log("DPI всё ещё работает после попытки остановки", "⚠ WARNING")
                    self.app.set_status("⚠ Процесс всё ещё работает")
                    
                    if hasattr(self.app, 'ui_manager'):
                        self.app.ui_manager.update_ui_state(running=True)
                    if hasattr(self.app, 'process_monitor_manager'):
                        self.app.process_monitor_manager.on_process_status_changed(True)
                
            else:
                log(f"Ошибка асинхронной остановки DPI: {error_message}", "❌ ERROR")
                self.app.set_status(f"❌ Ошибка остановки: {error_message}")
                
                # Проверяем реальный статус процесса
                is_running = self.app.dpi_starter.check_process_running_wmi(silent=True)
                
                # ✅ ИСПОЛЬЗУЕМ UI MANAGER вместо app.update_ui
                if hasattr(self.app, 'ui_manager'):
                    self.app.ui_manager.update_ui_state(running=is_running)
                
                # ✅ ИСПОЛЬЗУЕМ PROCESS MONITOR MANAGER
                if hasattr(self.app, 'process_monitor_manager'):
                    self.app.process_monitor_manager.on_process_status_changed(is_running)
                
        except Exception as e:
            log(f"Ошибка при обработке результата остановки DPI: {e}", "❌ ERROR")
            self.app.set_status(f"Ошибка: {e}")
    
    def _on_stop_and_exit_finished(self):
        """Завершает приложение после остановки DPI"""
        self.app.set_status("Завершение...")
        from PyQt6.QtWidgets import QApplication

        # Best-effort: close popups/tooltip windows and flush close events.
        # On some Windows setups, abrupt quit with translucent/frameless windows can leave "ghost" artifacts.
        try:
            if hasattr(self.app, "_dismiss_transient_ui_safe"):
                self.app._dismiss_transient_ui_safe(reason="stop_and_exit_finished")
        except Exception:
            pass
        try:
            QApplication.closeAllWindows()
            QApplication.processEvents()
        except Exception:
            pass

        QApplication.quit()
    
    def cleanup_threads(self):
        """Очищает все потоки при закрытии приложения"""
        try:
            if self._dpi_start_thread and self._dpi_start_thread.isRunning():
                log("Останавливаем поток запуска DPI...", "DEBUG")
                self._dpi_start_thread.quit()
                if not self._dpi_start_thread.wait(2000):
                    log("⚠ Поток запуска DPI не завершился, принудительно завершаем", "WARNING")
                    try:
                        self._dpi_start_thread.terminate()
                        self._dpi_start_thread.wait(500)
                    except:
                        pass
            
            if self._dpi_stop_thread and self._dpi_stop_thread.isRunning():
                log("Останавливаем поток остановки DPI...", "DEBUG")
                self._dpi_stop_thread.quit()
                if not self._dpi_stop_thread.wait(2000):
                    log("⚠ Поток остановки DPI не завершился, принудительно завершаем", "WARNING")
                    try:
                        self._dpi_stop_thread.terminate()
                        self._dpi_stop_thread.wait(500)
                    except:
                        pass
            
            # Обнуляем ссылки
            self._dpi_start_thread = None
            self._dpi_stop_thread = None

        except Exception as e:
            log(f"Ошибка при очистке потоков DPI контроллера: {e}", "❌ ERROR")

    def is_running(self) -> bool:
        """
        Проверяет запущен ли DPI процесс.

        Returns:
            True если процесс запущен, False иначе
        """
        return self.app.dpi_starter.check_process_running_wmi(silent=True)

    def restart_dpi_async(self):
        """
        Перезапускает DPI асинхронно (останавливает и снова запускает).

        Если DPI не запущен - просто запускает.
        Если запущен - останавливает, ждёт 500ms, затем запускает.
        """
        from PyQt6.QtCore import QTimer

        log("Перезапуск DPI...", "INFO")

        if self.is_running():
            # DPI запущен - останавливаем, потом запускаем через таймер
            log("DPI запущен, останавливаем перед перезапуском", "DEBUG")
            self.stop_dpi_async()

            # Запускаем снова через 500ms (чтобы остановка успела завершиться)
            QTimer.singleShot(500, lambda: self.start_dpi_async())
        else:
            # DPI не запущен - просто запускаем
            log("DPI не запущен, запускаем", "DEBUG")
            self.start_dpi_async()
