# strategy_menu/strategy_runner.py

import os
import subprocess
import ctypes
import shlex
from typing import Dict, Optional, Any, List
from log import log

# Импортируем стратегии из отдельного файла
from strategy_menu.strategy_definitions import (
    get_strategy_by_id,
    get_all_strategies,
    get_strategy_args,
    get_strategy_metadata,
    extract_host_lists_from_args,
    extract_ports_from_args,
    extract_domains_from_args,
    validate_strategy
)

# Константы для скрытого запуска
SW_HIDE = 0
CREATE_NO_WINDOW = 0x08000000
STARTF_USESHOWWINDOW = 0x00000001

class StrategyRunner:
    """Класс для запуска стратегий напрямую через subprocess"""
    
    def __init__(self, winws_exe_path: str):
        """
        Args:
            winws_exe_path: Путь к winws.exe
        """
        self.winws_exe = os.path.abspath(winws_exe_path)
        self.running_process: Optional[subprocess.Popen] = None
        self.current_strategy_id: Optional[str] = None
        self.current_strategy_args: Optional[List[str]] = None
        
        # Проверяем существование exe
        if not os.path.exists(self.winws_exe):
            raise FileNotFoundError(f"winws.exe не найден: {self.winws_exe}")
        
        # ✅ ИСПРАВЛЕНИЕ: Определяем рабочую директорию правильно
        # winws.exe находится в exe/, а lists/ на уровень выше
        exe_dir = os.path.dirname(self.winws_exe)  # C:\ProgramData\ZapretDev\exe
        self.work_dir = os.path.dirname(exe_dir)   # C:\ProgramData\ZapretDev
        
        self.bin_dir = os.path.join(self.work_dir, "bin")      # C:\ProgramData\ZapretDev\bin
        self.lists_dir = os.path.join(self.work_dir, "lists")  # C:\ProgramData\ZapretDev\lists
        
        log(f"StrategyRunner инициализирован. winws.exe: {self.winws_exe}", "INFO")
        log(f"Рабочая директория: {self.work_dir}", "DEBUG")
        log(f"Папка lists: {self.lists_dir}", "DEBUG")
        log(f"Папка bin: {self.bin_dir}", "DEBUG")
    
    def _create_startup_info(self):
        """Создает STARTUPINFO для скрытого запуска процесса"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_HIDE
        return startupinfo
    
    def _resolve_file_paths(self, args: List[str]) -> List[str]:
        """
        Разрешает пути к файлам в аргументах, заменяя относительные пути на абсолютные
        
        Args:
            args: Список аргументов командной строки
            
        Returns:
            Список аргументов с разрешенными путями
        """
        resolved_args = []
        
        for arg in args:
            if any(arg.startswith(prefix) for prefix in [
                "--hostlist=", "--ipset=", "--hostlist-exclude=", "--ipset-exclude="
            ]):
                # Обрабатываем пути к хостлистам
                prefix, filename = arg.split("=", 1)
                if not os.path.isabs(filename):
                    full_path = os.path.join(self.lists_dir, filename)
                    resolved_args.append(f"{prefix}={full_path}")
                else:
                    resolved_args.append(arg)
                    
            elif any(arg.startswith(prefix) for prefix in [
                "--dpi-desync-fake-tls=", "--dpi-desync-fake-syndata=", 
                "--dpi-desync-fake-quic=", "--dpi-desync-fake-unknown-udp=",
                "--dpi-desync-split-seqovl-pattern="
            ]):
                # Обрабатываем пути к бинарным файлам
                prefix, filename = arg.split("=", 1)
                if filename.startswith("0x"):
                    # Это hex-значение, не путь к файлу
                    resolved_args.append(arg)
                elif not os.path.isabs(filename):
                    full_path = os.path.join(self.bin_dir, filename)
                    resolved_args.append(f"{prefix}={full_path}")
                else:
                    resolved_args.append(arg)
            else:
                resolved_args.append(arg)
        
        return resolved_args

    def _force_cleanup_windivert(self):
        """Принудительная очистка службы и драйвера WinDivert"""
        try:
            import subprocess
            import time
            
            log("Принудительная очистка WinDivert...", "DEBUG")
            
            # 1. Останавливаем службу
            subprocess.run(
                ["sc", "stop", "windivert"],
                capture_output=True,
                creationflags=0x08000000,
                timeout=5
            )
            
            time.sleep(0.5)
            
            # 2. Удаляем службу
            subprocess.run(
                ["sc", "delete", "windivert"],
                capture_output=True,
                creationflags=0x08000000,
                timeout=5
            )
            
            time.sleep(0.5)
            
            # 3. Убиваем все процессы winws.exe
            subprocess.run(
                ["taskkill", "/F", "/IM", "winws.exe", "/T"],
                capture_output=True,
                creationflags=0x08000000,
                timeout=5
            )
            
            # 4. Пытаемся выгрузить драйвер через fltmc
            try:
                subprocess.run(
                    ["fltmc", "unload", "windivert"],
                    capture_output=True,
                    creationflags=0x08000000,
                    timeout=5
                )
            except:
                pass
            
            log("Очистка WinDivert завершена", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при принудительной очистке WinDivert: {e}", "DEBUG")

    def start_strategy(self, strategy_id: str, custom_args: Optional[List[str]] = None) -> bool:
        """
        Запускает стратегию по ID или с кастомными аргументами
        """
        try:
            # Останавливаем предыдущий процесс если он есть
            if self.running_process and self.is_running():
                log("Останавливаем предыдущий процесс перед запуском нового", "INFO")
                self.stop()
            
            # ✅ ДОБАВИТЬ ДОПОЛНИТЕЛЬНУЮ ОЧИСТКУ WINDIVERT
            self._force_cleanup_windivert()
            
            # Небольшая пауза после очистки
            import time
            time.sleep(0.5)

            # Получаем аргументы
            if strategy_id == "custom" and custom_args:
                args = custom_args
                strategy_name = "Пользовательская стратегия"
                log(f"Запуск кастомной стратегии с {len(args)} аргументами", "INFO")
            else:
                strategy = get_strategy_by_id(strategy_id)
                if not strategy:
                    log(f"Стратегия не найдена: {strategy_id}", "❌ ERROR")
                    return False

                # Парсим строку аргументов в список
                args_str = strategy.get('args', '')
                if args_str:
                    # Заменяем переносы строк на пробелы
                    args_str = ' '.join(args_str.split())
                    import shlex
                    args = shlex.split(args_str)
                else:
                    args = []
                
                strategy_name = strategy.get('name', strategy_id)
                
                # Валидируем стратегию
                if not validate_strategy(strategy):
                    log(f"Стратегия {strategy_id} не прошла валидацию", "❌ ERROR")
                    return False
            
            if not args:
                log(f"Нет аргументов для стратегии: {strategy_id}", "❌ ERROR")
                return False
            
            # Разрешаем пути к файлам
            resolved_args = self._resolve_file_paths(args)
            
            # Формируем полную команду
            cmd = [self.winws_exe] + resolved_args
            
            log(f"Запуск стратегии '{strategy_name}' (ID: {strategy_id})", "INFO")
            log(f"Количество аргументов: {len(resolved_args)}", "DEBUG")
            
            # Логируем команду для отладки (первые 400 символов)
            cmd_str = ' '.join(cmd)
            if len(cmd_str) > 400:
                log(f"Команда: {cmd_str[:400]}...", "DEBUG")
            else:
                log(f"Команда: {cmd_str}", "DEBUG")
            
            # Запускаем процесс полностью скрыто
            self.running_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=self._create_startup_info(),
                creationflags=CREATE_NO_WINDOW,
                cwd=self.work_dir
            )
            
            # Сохраняем информацию о текущей стратегии
            self.current_strategy_id = strategy_id
            self.current_strategy_args = resolved_args.copy()
            
            # Проверяем что процесс запустился
            if self.running_process.poll() is None:
                log(f"Стратегия '{strategy_name}' успешно запущена (PID: {self.running_process.pid})", "✅ SUCCESS")
                
                # Логируем метаданные стратегии
                if strategy_id != "custom":
                    metadata = get_strategy_metadata(strategy_id)
                    host_lists = metadata.get('parsed_host_lists', [])
                    ports = metadata.get('parsed_ports', [])
                    if host_lists:
                        log(f"Используемые хостлисты: {', '.join(host_lists)}", "DEBUG")
                    if ports:
                        log(f"Фильтруемые порты: {', '.join(ports)}", "DEBUG")
                
                return True
            else:
                # Получаем код возврата и ошибки
                return_code = self.running_process.returncode
                try:
                    stdout, stderr = self.running_process.communicate(timeout=1)
                    if stderr:
                        log(f"Ошибка stderr: {stderr.decode('utf-8', errors='ignore')}", "❌ ERROR")
                    if stdout:
                        log(f"Вывод stdout: {stdout.decode('utf-8', errors='ignore')}", "DEBUG")
                except:
                    pass
                
                log(f"Процесс завершился сразу после запуска (код: {return_code})", "❌ ERROR")
                self.running_process = None
                self.current_strategy_id = None
                self.current_strategy_args = None
                return False
                
        except Exception as e:
            log(f"Ошибка запуска стратегии: {e}", "❌ ERROR")
            self.running_process = None
            self.current_strategy_id = None
            self.current_strategy_args = None
            return False
    
    def stop(self) -> bool:
        """Останавливает запущенный процесс"""
        try:
            success = True
            
            if self.running_process and self.is_running():
                pid = self.running_process.pid
                strategy_name = "неизвестная"
                
                if self.current_strategy_id:
                    strategy = get_strategy_by_id(self.current_strategy_id)
                    if strategy:
                        strategy_name = strategy.get('name', self.current_strategy_id)
                
                log(f"Остановка стратегии '{strategy_name}' (PID: {pid})", "INFO")
                
                # Сначала пробуем мягкую остановку
                self.running_process.terminate()
                
                # Ждем завершения до 5 секунд
                try:
                    self.running_process.wait(timeout=5)
                    log(f"Процесс остановлен (PID: {pid})", "✅ SUCCESS")
                except subprocess.TimeoutExpired:
                    # Принудительное завершение
                    log("Мягкая остановка не сработала, используем принудительную", "⚠ WARNING")
                    self.running_process.kill()
                    self.running_process.wait()
                    log(f"Процесс принудительно завершен (PID: {pid})", "✅ SUCCESS")
            else:
                log("Нет запущенного процесса для остановки", "INFO")
            
            # Дополнительно останавливаем службу WinDivert
            try:
                self._stop_windivert_service()
            except Exception as e:
                log(f"Ошибка при остановке WinDivert: {e}", "DEBUG")
                success = False
            
            # Дополнительно убиваем все процессы winws.exe
            try:
                self._kill_all_winws_processes()
            except Exception as e:
                log(f"Ошибка при завершении процессов winws: {e}", "DEBUG")
            
            # Очищаем состояние
            self.running_process = None
            self.current_strategy_id = None
            self.current_strategy_args = None
            
            return success
            
        except Exception as e:
            log(f"Ошибка остановки процесса: {e}", "❌ ERROR")
            return False
    
    def _stop_windivert_service(self):
        """Останавливает и удаляет службу WinDivert"""
        try:
            # Останавливаем службу
            result1 = subprocess.run(
                ["sc", "stop", "windivert"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=10
            )
            
            # Небольшая пауза
            import time
            time.sleep(1)
            
            # Удаляем службу
            result2 = subprocess.run(
                ["sc", "delete", "windivert"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=10
            )
            
            log("Служба WinDivert остановлена и удалена", "INFO")
            
        except subprocess.TimeoutExpired:
            log("Таймаут при остановке службы WinDivert", "⚠ WARNING")
        except Exception as e:
            log(f"Ошибка при остановке службы WinDivert: {e}", "DEBUG")
    
    def _kill_all_winws_processes(self):
        """Принудительно завершает все процессы winws.exe"""
        try:
            # Используем taskkill для надежности
            subprocess.run(
                ["taskkill", "/F", "/IM", "winws.exe", "/T"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=10
            )
            log("Все процессы winws.exe завершены", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при завершении процессов winws.exe: {e}", "DEBUG")
    
    def is_running(self) -> bool:
        """Проверяет, запущен ли процесс"""
        if not self.running_process:
            return False
        
        # Проверяем статус процесса
        poll_result = self.running_process.poll()
        is_running = poll_result is None
        
        if not is_running and self.current_strategy_id:
            log(f"Процесс стратегии завершился (код: {poll_result})", "⚠ WARNING")
        
        return is_running
    
    def get_current_strategy_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущей запущенной стратегии"""
        if not self.is_running() or not self.current_strategy_id:
            return {}
        
        strategy = get_strategy_by_id(self.current_strategy_id)
        if not strategy:
            return {
                'strategy_id': self.current_strategy_id,
                'name': 'Неизвестная стратегия',
                'pid': self.running_process.pid if self.running_process else None,
                'args_count': len(self.current_strategy_args) if self.current_strategy_args else 0
            }
        
        metadata = get_strategy_metadata(self.current_strategy_id)
        
        return {
            'strategy_id': self.current_strategy_id,
            'name': strategy.get('name'),
            'version': strategy.get('version'),
            'provider': strategy.get('provider'),
            'author': strategy.get('author'),
            'pid': self.running_process.pid if self.running_process else None,
            'args_count': len(self.current_strategy_args) if self.current_strategy_args else 0,
            'host_lists': metadata.get('parsed_host_lists', []),
            'ports': metadata.get('parsed_ports', []),
            'uses_quic': metadata.get('uses_quic', False),
            'uses_tls_fake': metadata.get('uses_tls_fake', False),
            'all_sites': strategy.get('all_sites', False)
        }
    
    def get_builtin_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает список встроенных стратегий с метаданными"""
        strategies = get_all_strategies()
        result = {}
        
        for strategy_id, strategy_data in strategies.items():
            metadata = get_strategy_metadata(strategy_id)
            result[strategy_id] = {
                **strategy_data,
                'metadata': {
                    'host_lists': metadata.get('parsed_host_lists', []),
                    'ports': metadata.get('parsed_ports', []),
                    'domains': metadata.get('parsed_domains', []),
                    'uses_quic': metadata.get('uses_quic', False),
                    'uses_tls_fake': metadata.get('uses_tls_fake', False),
                    'uses_autottl': metadata.get('uses_autottl', False)
                }
            }
        
        return result
    
    def parse_strategy_from_index(self, strategy_info: dict) -> Optional[List[str]]:
        """
        Парсит информацию о стратегии из index.json и возвращает аргументы
        
        Args:
            strategy_info: Словарь с информацией о стратегии из index.json
            
        Returns:
            Список аргументов командной строки или None
        """
        try:
            # Если есть готовые аргументы в JSON
            if "command_args" in strategy_info:
                args_str = strategy_info["command_args"]
                
                # Убираем winws.exe если он есть в начале
                if args_str.startswith("winws.exe"):
                    args_str = args_str[9:].strip()
                elif args_str.startswith("winws"):
                    args_str = args_str[5:].strip()
                
                # Используем shlex для правильного парсинга
                try:
                    args = shlex.split(args_str)
                    log(f"Парсинг аргументов из index.json: {len(args)} аргументов", "DEBUG")
                    return args
                except ValueError as e:
                    log(f"Ошибка shlex парсинга, используем split: {e}", "DEBUG")
                    # Fallback на простой split
                    args = args_str.split()
                    return args
            
            # Если аргументов нет, генерируем базовые на основе других полей
            log("Генерируем базовые аргументы на основе метаданных", "DEBUG")
            args = []
            
            # Порты
            ports = strategy_info.get("ports", [80, 443])
            if not isinstance(ports, list):
                ports = [ports]
            
            # TCP фильтр
            if ports:
                tcp_ports = [str(p) for p in ports if isinstance(p, int) and p <= 65535]
                if tcp_ports:
                    args.append(f"--filter-tcp={','.join(tcp_ports)}")
            
            # Базовые параметры десинхронизации
            args.extend([
                "--dpi-desync=fake,split2",
                "--dpi-desync-fooling=md5sig",
                "--dpi-desync-retrans=1",
                "--dpi-desync-repeats=6"
            ])
            
            # Хост-листы
            host_lists = strategy_info.get("host_lists", [])
            if isinstance(host_lists, str):
                host_lists = [host_lists]
            
            for host_list in host_lists:
                if host_list and host_list.strip():
                    args.append(f"--hostlist={host_list.strip()}")
            
            log(f"Сгенерировано {len(args)} базовых аргументов", "DEBUG")
            return args
            
        except Exception as e:
            log(f"Ошибка парсинга стратегии из index.json: {e}", "❌ ERROR")
            return None
    
    def validate_strategy_files(self, strategy_id: str) -> Dict[str, bool]:
        """
        Проверяет наличие всех необходимых файлов для стратегии
        
        Args:
            strategy_id: ID стратегии
            
        Returns:
            Словарь с результатами проверки файлов
        """
        result = {
            'all_files_exist': True,
            'missing_files': [],
            'existing_files': [],
            'host_lists_ok': True,
            'bin_files_ok': True
        }
        
        try:
            strategy = get_strategy_by_id(strategy_id)
            if not strategy:
                result['all_files_exist'] = False
                return result
            
            args = strategy.get('args', [])
            resolved_args = self._resolve_file_paths(args)
            
            # Проверяем файлы хостлистов
            for arg in resolved_args:
                if any(arg.startswith(prefix) for prefix in [
                    "--hostlist=", "--ipset=", "--hostlist-exclude=", "--ipset-exclude="
                ]):
                    _, filepath = arg.split("=", 1)
                    if os.path.exists(filepath):
                        result['existing_files'].append(filepath)
                    else:
                        result['missing_files'].append(filepath)
                        result['host_lists_ok'] = False
                        result['all_files_exist'] = False
            
            # Проверяем бинарные файлы
            for arg in resolved_args:
                if any(arg.startswith(prefix) for prefix in [
                    "--dpi-desync-fake-tls=", "--dpi-desync-fake-syndata=", 
                    "--dpi-desync-fake-quic=", "--dpi-desync-fake-unknown-udp=",
                    "--dpi-desync-split-seqovl-pattern="
                ]):
                    _, filepath = arg.split("=", 1)
                    if filepath.startswith("0x"):
                        # Это hex-значение, не файл
                        continue
                    if os.path.exists(filepath):
                        result['existing_files'].append(filepath)
                    else:
                        result['missing_files'].append(filepath)
                        result['bin_files_ok'] = False
                        result['all_files_exist'] = False
            
        except Exception as e:
            log(f"Ошибка при проверке файлов стратегии {strategy_id}: {e}", "❌ ERROR")
            result['all_files_exist'] = False
        
        return result
    
    def get_process_status(self) -> Dict[str, Any]:
        """Возвращает детальную информацию о статусе процесса"""
        status = {
            'is_running': False,
            'pid': None,
            'strategy_info': {},
            'uptime_seconds': 0,
            'memory_usage_mb': 0,
            'cpu_percent': 0.0
        }
        
        if not self.is_running():
            return status
        
        status['is_running'] = True
        status['pid'] = self.running_process.pid
        status['strategy_info'] = self.get_current_strategy_info()
        
        try:
            import psutil
            process = psutil.Process(self.running_process.pid)
            
            # Время работы
            create_time = process.create_time()
            import time
            status['uptime_seconds'] = int(time.time() - create_time)
            
            # Использование памяти (в MB)
            memory_info = process.memory_info()
            status['memory_usage_mb'] = round(memory_info.rss / 1024 / 1024, 1)
            
            # Использование CPU (%)
            status['cpu_percent'] = process.cpu_percent()
            
        except Exception as e:
            log(f"Не удалось получить системную информацию о процессе: {e}", "DEBUG")
        
        return status

# Глобальный экземпляр для использования в других модулях
_strategy_runner_instance: Optional[StrategyRunner] = None

def get_strategy_runner(winws_exe_path: str) -> StrategyRunner:
    """Получает или создает глобальный экземпляр StrategyRunner"""
    global _strategy_runner_instance
    if _strategy_runner_instance is None:
        _strategy_runner_instance = StrategyRunner(winws_exe_path)
    return _strategy_runner_instance

def reset_strategy_runner():
    """Сбрасывает глобальный экземпляр (для тестирования)"""
    global _strategy_runner_instance
    if _strategy_runner_instance:
        _strategy_runner_instance.stop()
    _strategy_runner_instance = None

# Утилитарные функции

def get_available_strategies_summary() -> Dict[str, int]:
    """Возвращает краткую сводку по доступным стратегиям"""
    from strategy_menu.strategy_definitions import get_strategies_stats
    return get_strategies_stats()

def find_strategy_by_name(name: str) -> Optional[str]:
    """Находит ID стратегии по её названию"""
    strategies = get_all_strategies()
    for strategy_id, strategy_data in strategies.items():
        if strategy_data.get('name', '').lower() == name.lower():
            return strategy_id
    return None

def get_recommended_strategy_id() -> Optional[str]:
    """Возвращает ID рекомендуемой стратегии по умолчанию"""
    from strategy_menu.strategy_definitions import get_recommended_strategies
    recommended = get_recommended_strategies()
    if recommended:
        # Возвращаем первую рекомендуемую
        return next(iter(recommended.keys()))
    
    # Если нет рекомендуемых, возвращаем первую доступную
    all_strategies = get_all_strategies()
    if all_strategies:
        return next(iter(all_strategies.keys()))
    
    return None

if __name__ == "__main__":
    # Тестирование
    try:
        # Тестовый путь (замените на реальный)
        test_winws_path = r"D:\Privacy\zapret\bin\winws.exe"
        
        if os.path.exists(test_winws_path):
            runner = StrategyRunner(test_winws_path)
            
            print("Доступные стратегии:")
            strategies = runner.get_builtin_strategies()
            for sid, sdata in strategies.items():
                print(f"  {sid}: {sdata['name']}")
            
            print(f"\nРекомендуемая стратегия: {get_recommended_strategy_id()}")
            print(f"Сводка по стратегиям: {get_available_strategies_summary()}")
            
        else:
            print(f"winws.exe не найден по пути: {test_winws_path}")
            
    except Exception as e:
        print(f"Ошибка тестирования: {e}")