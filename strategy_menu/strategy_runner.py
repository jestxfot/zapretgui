# strategy_menu/strategy_runner.py

import os
import subprocess
import ctypes
import shlex
from typing import Dict, Optional, Any, List
from log import log

# Импортируем стратегии из отдельного файла
from .strategy_definitions import (
    get_strategy_by_id,
    get_all_strategies,
    get_strategy_args,
    get_strategy_metadata,
    extract_host_lists_from_args,
    extract_ports_from_args,
    extract_domains_from_args,
    validate_strategy
)

from .constants import SW_HIDE, CREATE_NO_WINDOW, STARTF_USESHOWWINDOW


def apply_wssize_parameter(args: list) -> list:
    """
    Применяет параметр --wssize=1:6 к аргументам стратегии если включено в настройках
    
    Args:
        args: Список аргументов командной строки
        
    Returns:
        Модифицированный список аргументов с добавленным --wssize=1:6
    """
    from config import get_wssize_enabled
    
    # Если wssize выключен, возвращаем аргументы без изменений
    if not get_wssize_enabled():
        return args
    
    # Создаем новый список аргументов
    new_args = []
    wssize_added = False
    wssize_positions = []  # Запоминаем где добавили wssize
    
    i = 0
    while i < len(args):
        arg = args[i]
        new_args.append(arg)
        
        # Проверяем, является ли это --filter-tcp с портом 443
        if arg.startswith("--filter-tcp="):
            # Извлекаем порты из аргумента
            ports_part = arg.split("=", 1)[1]
            ports = []
            
            # Парсим порты (могут быть: 443 или 80,443 или 443,444-65535)
            for port_spec in ports_part.split(","):
                if "-" in port_spec:
                    # Диапазон портов
                    start, end = port_spec.split("-")
                    if int(start) <= 443 <= int(end):
                        ports.append("443")
                else:
                    # Одиночный порт
                    if port_spec.strip() == "443":
                        ports.append("443")
            
            # Если среди портов есть 443
            if "443" in ports:
                # Проверяем, не добавлен ли уже wssize после этого фильтра
                next_arg = args[i + 1] if i + 1 < len(args) else None
                if next_arg != "--wssize=1:6":
                    new_args.append("--wssize=1:6")
                    wssize_positions.append(len(new_args) - 1)
                    wssize_added = True
                    log(f"Добавлен параметр --wssize=1:6 после {arg}", "DEBUG")
        
        i += 1
    
    # Если в стратегии нет явного filter-tcp с портом 443, добавляем глобальное правило
    if not wssize_added:
        # Ищем подходящее место для вставки
        insert_index = _find_wssize_insert_position(new_args)
        
        # Вставляем правило для tcp 443
        new_args.insert(insert_index, "--filter-tcp=443")
        new_args.insert(insert_index + 1, "--wssize=1:6")
        
        # Если после места вставки нет --new, добавляем его
        if insert_index + 2 >= len(new_args) or new_args[insert_index + 2] != "--new":
            new_args.insert(insert_index + 2, "--new")
        
        log("Добавлено глобальное правило --filter-tcp=443 --wssize=1:6 --new", "DEBUG")
    
    # Логируем итоговое количество добавлений
    if wssize_positions:
        log(f"Параметр --wssize=1:6 добавлен в {len(wssize_positions)} мест(а)", "INFO")
    
    return new_args

def _find_wssize_insert_position(args: list) -> int:
    """
    Находит оптимальную позицию для вставки глобального правила wssize
    
    Args:
        args: Список аргументов
        
    Returns:
        Индекс для вставки
    """
    # Приоритеты для вставки:
    # 1. После последнего --wf-tcp (фильтр на уровне WinDivert)
    # 2. После последнего --wf-udp
    # 3. Перед первым --filter-tcp
    # 4. Перед первым --new
    # 5. В конец списка
    
    last_wf_index = -1
    first_filter_index = -1
    first_new_index = -1
    
    for i, arg in enumerate(args):
        if arg.startswith("--wf-tcp=") or arg.startswith("--wf-udp="):
            last_wf_index = i
        elif arg.startswith("--filter-tcp=") and first_filter_index == -1:
            first_filter_index = i
        elif arg == "--new" and first_new_index == -1:
            first_new_index = i
    
    # Определяем позицию вставки
    if last_wf_index != -1:
        # После последнего --wf-*
        return last_wf_index + 1
    elif first_filter_index != -1:
        # Перед первым --filter-tcp
        return first_filter_index
    elif first_new_index != -1:
        # Перед первым --new
        return first_new_index
    else:
        # В конец
        return len(args)
        
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
        resolved_args = []
        
        for arg in args:
            if any(arg.startswith(prefix) for prefix in [
                "--hostlist=", "--ipset=", "--hostlist-exclude=", "--ipset-exclude="
            ]):
                prefix, filename = arg.split("=", 1)
                
                # Убираем кавычки если они уже есть
                filename = filename.strip('"')
                
                if not os.path.isabs(filename):
                    full_path = os.path.join(self.lists_dir, filename)
                    # БЕЗ КАВЫЧЕК!
                    resolved_args.append(f'{prefix}={full_path}')
                else:
                    # БЕЗ КАВЫЧЕК!
                    resolved_args.append(f'{prefix}={filename}')
                    
            # То же самое для бинарных файлов
            elif any(arg.startswith(prefix) for prefix in [
                "--dpi-desync-fake-tls=", "--dpi-desync-fake-syndata=", 
                "--dpi-desync-fake-quic=", "--dpi-desync-fake-unknown-udp=",
                "--dpi-desync-split-seqovl-pattern="
            ]):
                prefix, filename = arg.split("=", 1)
                
                if filename.startswith("0x"):
                    resolved_args.append(arg)
                else:
                    filename = filename.strip('"')
                    
                    if not os.path.isabs(filename):
                        full_path = os.path.join(self.bin_dir, filename)
                        # БЕЗ КАВЫЧЕК!
                        resolved_args.append(f'{prefix}={full_path}')
                    else:
                        # БЕЗ КАВЫЧЕК!
                        resolved_args.append(f'{prefix}={filename}')
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

            # Обработка комбинированных стратегий
            if strategy_id == "custom_combined" and hasattr(self, '_combined_args_str'):
                # Используем сохраненную строку аргументов
                args_str = self._combined_args_str
                args = shlex.split(args_str)
                strategy_name = "Комбинированная стратегия"
                log(f"Запуск комбинированной стратегии с {len(args)} аргументами", "INFO")
            elif strategy_id == "custom" and custom_args:
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

            # Применяем Game Filter (расширение портов)
            resolved_args = apply_game_filter_parameter(resolved_args, self.lists_dir)

            # Применяем IPset списки (добавление ipset-all.txt)
            resolved_args = apply_ipset_lists_parameter(resolved_args, self.lists_dir)

            # Применяем параметр wssize если включен
            resolved_args = apply_wssize_parameter(resolved_args)

            # Формируем полную команду
            cmd = [self.winws_exe] + resolved_args
            
            log(f"Запуск стратегии '{strategy_name}' (ID: {strategy_id})", "INFO")
            log(f"Количество аргументов: {len(resolved_args)}", "DEBUG")
            
            # Логируем команду для отладки
            cmd_str = ' '.join(cmd)
            log(f"Команда: {cmd_str}", "DEBUG")
            
            # Запускаем процесс полностью скрыто
            self.running_process = subprocess.Popen(
                cmd,  # Передаем список напрямую
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=self._create_startup_info(),
                creationflags=CREATE_NO_WINDOW,
                cwd=self.work_dir
                # НЕ используем shell=True
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

def apply_game_filter_parameter(args: list, lists_dir: str) -> list:
    """
    Применяет Game Filter - добавляет порты 1024-65535 для стратегий с other.txt
    
    Args:
        args: Список аргументов командной строки
        lists_dir: Путь к директории с файлами списков
        
    Returns:
        Модифицированный список аргументов с расширенными портами
    """
    from config import get_game_filter_enabled
    
    # Если Game Filter выключен, возвращаем аргументы без изменений
    if not get_game_filter_enabled():
        return args
    
    new_args = []
    i = 0
    ports_modified = False
    
    while i < len(args):
        arg = args[i]
        new_args.append(arg)
        
        # Проверяем, является ли это --filter-tcp
        if arg.startswith("--filter-tcp="):
            # Проверяем, есть ли после него хостлисты other
            has_other_hostlist = False
            j = i + 1
            
            # Ищем хостлисты в следующих аргументах до --new
            while j < len(args) and args[j] != "--new":
                if "--hostlist=" in args[j]:
                    hostlist_value = args[j].split("=", 1)[1].strip('"')
                    hostlist_filename = os.path.basename(hostlist_value)
                    if hostlist_filename in ["other.txt", "other2.txt", "russia-blacklist.txt"]:
                        has_other_hostlist = True
                        break
                j += 1
            
            # Если нашли хостлисты other, расширяем порты
            if has_other_hostlist:
                ports_part = arg.split("=", 1)[1]
                ports_list = ports_part.split(",")
                
                # Добавляем диапазон портов для игр если его еще нет
                if "1024-65535" not in ports_list:
                    ports_list.append("1024-65535")
                    new_args[-1] = f"--filter-tcp={','.join(ports_list)}"
                    ports_modified = True
                    log(f"Game Filter: расширен диапазон портов до {','.join(ports_list)}", "INFO")
        
        i += 1
    
    if ports_modified:
        log("Game Filter применен (добавлены порты 1024-65535)", "✅ SUCCESS")
    
    return new_args

def apply_ipset_lists_parameter(args: list, lists_dir: str) -> list:
    """
    Добавляет --ipset=ipset-all.txt после хостлистов other.txt, other2.txt, russia-blacklist.txt
    ТОЛЬКО если они идут вместе в одном блоке
    
    Args:
        args: Список аргументов командной строки
        lists_dir: Путь к директории с файлами списков
        
    Returns:
        Модифицированный список аргументов с добавленным --ipset=ipset-all.txt
    """
    from config import get_ipset_lists_enabled
    
    # Если функция выключена, возвращаем аргументы без изменений
    if not get_ipset_lists_enabled():
        return args
    
    ipset_all_path = os.path.join(lists_dir, "ipset-all.txt")
    
    if not os.path.exists(ipset_all_path):
        log(f"Файл ipset-all.txt не найден: {ipset_all_path}", "⚠ WARNING")
        return args
    
    new_args = []
    i = 0
    ipset_added_count = 0
    
    while i < len(args):
        arg = args[i]
        new_args.append(arg)
        
        # Проверяем, является ли это хостлистом other/russia
        if arg.startswith("--hostlist="):
            hostlist_value = arg.split("=", 1)[1].strip('"')
            hostlist_filename = os.path.basename(hostlist_value)
            
            # Если это один из целевых хостлистов
            if hostlist_filename in ["other.txt", "other2.txt", "russia-blacklist.txt"]:
                # Собираем все последовательные хостлисты из нашего набора
                j = i + 1
                collected_hostlists = [hostlist_filename]
                last_hostlist_index = i
                
                while j < len(args):
                    next_arg = args[j]
                    
                    if next_arg.startswith("--hostlist="):
                        next_hostlist = next_arg.split("=", 1)[1].strip('"')
                        next_filename = os.path.basename(next_hostlist)
                        
                        if next_filename in ["other.txt", "other2.txt", "russia-blacklist.txt"]:
                            # Добавляем этот хостлист
                            new_args.append(next_arg)
                            collected_hostlists.append(next_filename)
                            last_hostlist_index = j
                            j += 1
                            i = j - 1  # Обновляем i
                        else:
                            # Это другой хостлист, прерываем
                            break
                    else:
                        # Не хостлист, прерываем
                        break
                
                # Добавляем ipset только если собрали БОЛЕЕ ОДНОГО хостлиста из нашего набора
                # ИЛИ если есть хотя бы russia-blacklist.txt (он обычно идет с other.txt)
                if len(collected_hostlists) > 1 or "russia-blacklist.txt" in collected_hostlists:
                    # Проверяем следующий аргумент после последнего хостлиста
                    next_idx = last_hostlist_index + 1 - len(new_args) + len(args)
                    
                    # Проверяем не добавлен ли уже ipset-all.txt
                    ipset_already_exists = False
                    if next_idx < len(args) and args[next_idx].startswith("--ipset="):
                        ipset_value = args[next_idx].split("=", 1)[1].strip('"')
                        if os.path.basename(ipset_value) == "ipset-all.txt":
                            ipset_already_exists = True
                    
                    if not ipset_already_exists:
                        # Добавляем ipset
                        new_args.append(f'--ipset={ipset_all_path}')
                        ipset_added_count += 1
                        log(f"Добавлен --ipset=ipset-all.txt после группы хостлистов: {', '.join(collected_hostlists)}", "DEBUG")
        
        i += 1
    
    if ipset_added_count > 0:
        log(f"IPset списки применены (добавлен ipset-all.txt в {ipset_added_count} место(а))", "✅ SUCCESS")
    
    return new_args