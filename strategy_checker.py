# strategy_checker.py
"""
Модуль для проверки и анализа текущей стратегии DPI.
Поддерживает BAT стратегии, встроенные и комбинированные стратегии.
"""

import os
import re
import shlex
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from config import get_last_strategy, BAT_FOLDER
from log import log
from strategy_menu import get_strategy_launch_method


@dataclass
class StrategyAnalysis:
    """Результат анализа флагов стратегии"""
    hostlists: List[str] = field(default_factory=list)
    ipsets: List[str] = field(default_factory=list)
    filters: List[str] = field(default_factory=list)
    dpi_techniques: List[str] = field(default_factory=list)
    special_params: List[str] = field(default_factory=list)
    lua_params: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'hostlists': self.hostlists,
            'ipsets': self.ipsets,
            'filters': self.filters,
            'dpi_techniques': self.dpi_techniques,
            'special_params': self.special_params,
            'lua_params': self.lua_params,
        }


def analyze_args(args: List[str]) -> StrategyAnalysis:
    """
    Анализирует список аргументов стратегии.
    
    Единая функция для анализа - используется и для direct, и для BAT.
    """
    analysis = StrategyAnalysis()
    
    # Паттерны для разных типов аргументов
    patterns = {
        # Hostlists
        r'^--hostlist=(.+)$': lambda m: analysis.hostlists.append(m.group(1)),
        r'^--hostlist-domains=(.+)$': lambda m: analysis.hostlists.append(f"domains:{m.group(1)}"),
        r'^--hostlist-exclude=(.+)$': lambda m: analysis.hostlists.append(f"exclude:{m.group(1)}"),
        
        # IPsets
        r'^--ipset=(.+)$': lambda m: analysis.ipsets.append(m.group(1)),
        r'^--ipset-ip=(.+)$': lambda m: analysis.ipsets.append(f"ip:{m.group(1)}"),
        r'^--ipset-exclude=(.+)$': lambda m: analysis.ipsets.append(f"exclude:{m.group(1)}"),
        
        # Filters
        r'^--filter-tcp=(.+)$': lambda m: analysis.filters.append(f"TCP:{m.group(1)}"),
        r'^--filter-udp=(.+)$': lambda m: analysis.filters.append(f"UDP:{m.group(1)}"),
        r'^--filter-l7=(.+)$': lambda m: analysis.filters.append(f"L7:{m.group(1)}"),
        r'^--filter-l3=(.+)$': lambda m: analysis.filters.append(f"L3:{m.group(1)}"),
        
        # DPI techniques
        r'^--dpi-desync=(.+)$': lambda m: analysis.dpi_techniques.append(f"desync:{m.group(1)}"),
        r'^--dpi-desync-split-pos=(.+)$': lambda m: analysis.dpi_techniques.append(f"split-pos:{m.group(1)}"),
        r'^--dpi-desync-split-seqovl=(.+)$': lambda m: analysis.dpi_techniques.append(f"seqovl:{m.group(1)}"),
        r'^--dpi-desync-fooling=(.+)$': lambda m: analysis.dpi_techniques.append(f"fooling:{m.group(1)}"),
        r'^--dpi-desync-repeats=(.+)$': lambda m: analysis.dpi_techniques.append(f"repeats:{m.group(1)}"),
        r'^--dpi-desync-ttl=(.+)$': lambda m: analysis.dpi_techniques.append(f"ttl:{m.group(1)}"),
        r'^--dpi-desync-autottl$': lambda m: analysis.dpi_techniques.append("autottl"),
        r'^--dpi-desync-autottl=(.+)$': lambda m: analysis.dpi_techniques.append(f"autottl:{m.group(1)}"),
        r'^--dpi-desync-fake-(.+)$': lambda m: analysis.dpi_techniques.append(f"fake-{m.group(1).split('=')[0]}"),
        r'^--dpi-desync-any-protocol$': lambda m: analysis.dpi_techniques.append("any-protocol"),
        
        # Special params
        r'^--dup=(.+)$': lambda m: analysis.special_params.append(f"dup:{m.group(1)}"),
        r'^--dup-autottl$': lambda m: analysis.special_params.append("dup-autottl"),
        r'^--dup-cutoff=(.+)$': lambda m: analysis.special_params.append(f"dup-cutoff:{m.group(1)}"),
        r'^--dup-fooling=(.+)$': lambda m: analysis.special_params.append(f"dup-fooling:{m.group(1)}"),
        r'^--new$': lambda m: analysis.special_params.append("--new"),
        r'^--out-range=(.+)$': lambda m: analysis.special_params.append(f"out-range:{m.group(1)}"),
        r'^--wssize': lambda m: analysis.special_params.append("wssize"),
        
        # Lua params (Zapret 2)
        r'^--lua-init=(.+)$': lambda m: analysis.lua_params.append(f"init:{os.path.basename(m.group(1))}"),
        r'^--lua-desync=(.+)$': lambda m: analysis.lua_params.append(f"desync:{m.group(1)}"),
        r'^--payload=(.+)$': lambda m: analysis.lua_params.append(f"payload:{m.group(1)}"),
    }
    
    for arg in args:
        for pattern, handler in patterns.items():
            match = re.match(pattern, arg)
            if match:
                handler(match)
                break
    
    return analysis


class StrategyChecker:
    """Класс для проверки и анализа стратегий"""
    
    def __init__(self):
        self.launch_method = get_strategy_launch_method()
    
    def check_current_strategy(self) -> Dict:
        """
        Проверяет текущую выбранную стратегию.
        
        Returns:
            Dict с информацией о стратегии
        """
        try:
            result = {
                'name': 'Неизвестная',
                'type': 'unknown',
                'method': self.launch_method,
                'file_status': 'N/A',
                'details': {}
            }
            
            if self.launch_method in ('direct', 'direct_orchestra', 'direct_zapret1'):
                result.update(self._check_direct_strategy())
            else:
                result.update(self._check_bat_strategy())
            
            return result
            
        except Exception as e:
            log(f"Ошибка проверки стратегии: {e}", "ERROR")
            return {
                'name': f'Ошибка: {e}',
                'type': 'error',
                'method': self.launch_method,
                'file_status': 'error',
                'details': {'error': str(e)}
            }
    
    def _check_direct_strategy(self) -> Dict:
        """Проверка стратегии в direct режиме"""
        try:
            from strategy_menu.preset_configuration_zapret2 import strategy_selections
            from strategy_menu.preset_configuration_zapret2.command_builder import build_full_command
            from strategy_menu.strategies_registry import registry

            selections = strategy_selections.get_all()

            # Получаем полную командную строку
            combined = build_full_command(selections)
            
            # Собираем информацию о категориях
            active_categories = []
            strategy_names = []
            
            for category_key in registry.get_all_category_keys():
                strategy_id = selections.get(category_key)
                if strategy_id and strategy_id != "none":
                    category_info = registry.get_category_info(category_key)
                    strategy_name = registry.get_strategy_name_safe(category_key, strategy_id)
                    if category_info:
                        active_categories.append(category_info.full_name)
                        strategy_names.append(f"{category_info.full_name}: {strategy_name}")
            
            # Анализируем аргументы
            args_str = combined.get('args', '')
            args_list = args_str.split() if args_str else []
            analysis = analyze_args(args_list)
            
            # Определяем подтип
            method_display = {
                'direct': 'direct',
                'direct_orchestra': 'orchestra',
                'direct_zapret1': 'zapret1',
            }.get(self.launch_method, 'direct')
            
            return {
                'name': combined.get('description', 'Комбинированная стратегия'),
                'type': 'combined',
                'method': method_display,
                'file_status': 'N/A',
                'details': {
                    'active_categories': active_categories,
                    'strategy_names': strategy_names,
                    'selections': selections,
                    'args_count': len(args_list),
                    'args_length': len(args_str),
                    **analysis.to_dict()
                }
            }
            
        except Exception as e:
            log(f"Ошибка проверки direct стратегии: {e}", "DEBUG")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            return {
                'name': 'Direct стратегия (ошибка)',
                'type': 'direct',
                'method': 'direct',
                'file_status': 'error',
                'details': {'error': str(e)}
            }
    
    def _check_bat_strategy(self) -> Dict:
        """Проверка BAT стратегии"""
        try:
            strategy_name = get_last_strategy()
            strategy_file = self._find_strategy_file(strategy_name)
            file_status = 'found' if strategy_file else 'not_found'
            
            details = {'strategy_name': strategy_name}
            
            if strategy_file and os.path.exists(strategy_file):
                try:
                    with open(strategy_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
                        content = f.read()
                    
                    details['file_size'] = os.path.getsize(strategy_file)
                    details['file_path'] = strategy_file
                    
                    # Ищем версию
                    for line in content.split('\n'):
                        if 'VERSION:' in line:
                            details['version'] = line.split('VERSION:')[1].strip()
                            break
                    
                    # Анализируем команды winws
                    winws_commands = self._extract_winws_commands(content)
                    details['commands_count'] = len(winws_commands)
                    
                    if winws_commands:
                        # Анализируем первую команду
                        args = self._parse_bat_command(winws_commands[0])
                        analysis = analyze_args(args)
                        details.update(analysis.to_dict())
                        
                except Exception as e:
                    log(f"Ошибка чтения BAT файла: {e}", "DEBUG")
                    details['read_error'] = str(e)
            
            return {
                'name': strategy_name,
                'type': 'bat',
                'method': 'bat',
                'file_status': file_status,
                'details': details
            }
            
        except Exception as e:
            log(f"Ошибка проверки BAT стратегии: {e}", "DEBUG")
            return {
                'name': 'BAT стратегия (ошибка)',
                'type': 'bat',
                'method': 'bat',
                'file_status': 'error',
                'details': {'error': str(e)}
            }
    
    def _parse_bat_command(self, command: str) -> List[str]:
        """Парсит команду из BAT файла в список аргументов"""
        try:
            parts = shlex.split(command, posix=False)
            
            # Фильтруем служебные части
            result = []
            skip_next = False
            for part in parts:
                if skip_next:
                    skip_next = False
                    continue
                lower = part.lower()
                if 'winws.exe' in lower or 'winws2.exe' in lower:
                    continue
                if lower in ('start', '/min', '/b', '^'):
                    skip_next = (lower == 'start')
                    continue
                if part.startswith('%') or part.endswith('%'):
                    continue  # Пропускаем переменные BAT
                result.append(part)
            
            return result
        except Exception as e:
            log(f"Ошибка парсинга BAT команды: {e}", "DEBUG")
            return []
    
    def _extract_winws_commands(self, bat_content: str) -> List[str]:
        """Извлекает команды winws из BAT файла"""
        commands = []
        for line in bat_content.split('\n'):
            line = line.strip()
            lower = line.lower()
            if ('winws.exe' in lower or 'winws2.exe' in lower) and \
               not line.startswith('::') and not lower.startswith('rem '):
                commands.append(line)
        return commands
    
    def _find_strategy_file(self, strategy_name: str) -> Optional[str]:
        """Ищет файл стратегии в папке bat"""
        try:
            if not os.path.exists(BAT_FOLDER):
                return None
            
            # Сначала точное совпадение
            for file in os.listdir(BAT_FOLDER):
                if file.lower().endswith('.bat'):
                    if strategy_name.lower() in file.lower():
                        return os.path.join(BAT_FOLDER, file)
            
            # Fallback - первый .bat файл
            for file in os.listdir(BAT_FOLDER):
                if file.lower().endswith('.bat'):
                    return os.path.join(BAT_FOLDER, file)
            
            return None
        except Exception as e:
            log(f"Ошибка поиска файла стратегии: {e}", "DEBUG")
            return None
    
    def format_strategy_info(self, info: Dict) -> List[str]:
        """Форматирует информацию о стратегии для вывода"""
        lines = []
        details = info.get('details', {})
        
        # Заголовок
        lines.append("═" * 50)
        lines.append("📋 ИНФОРМАЦИЯ О СТРАТЕГИИ")
        lines.append("═" * 50)
        
        # Основная информация
        lines.append(f"  Название:    {info['name']}")
        lines.append(f"  Тип:         {self._format_type(info['type'])}")
        lines.append(f"  Метод:       {self._format_method(info['method'])}")
        
        if info['file_status'] != 'N/A':
            icon = "✅" if info['file_status'] == 'found' else "❌"
            lines.append(f"  Файл:        {icon} {info['file_status']}")
        
        # Статистика для combined
        if info['type'] == 'combined':
            if details.get('active_categories'):
                lines.append(f"  Категорий:   {len(details['active_categories'])}")
            if details.get('args_count'):
                lines.append(f"  Аргументов:  {details['args_count']}")
            if details.get('args_length'):
                lines.append(f"  Длина команды: {details['args_length']} символов")
        
        # Для BAT
        if info['type'] == 'bat':
            if details.get('version'):
                lines.append(f"  Версия:      {details['version']}")
            if details.get('file_size'):
                lines.append(f"  Размер:      {details['file_size'] / 1024:.1f} KB")
            if details.get('commands_count'):
                lines.append(f"  Команд:      {details['commands_count']}")
        
        lines.append("")
        
        # Детали по категориям
        if details.get('strategy_names'):
            lines.append("📂 АКТИВНЫЕ СТРАТЕГИИ:")
            for name in details['strategy_names'][:10]:
                lines.append(f"   • {name}")
            if len(details['strategy_names']) > 10:
                lines.append(f"   ... и ещё {len(details['strategy_names']) - 10}")
            lines.append("")
        
        # Фильтры
        if details.get('filters'):
            lines.append(f"🔍 Фильтры ({len(details['filters'])}):")
            lines.append(f"   {', '.join(details['filters'][:8])}")
            if len(details['filters']) > 8:
                lines.append(f"   ... и ещё {len(details['filters']) - 8}")
        
        # DPI техники
        if details.get('dpi_techniques'):
            lines.append(f"⚡ DPI техники ({len(details['dpi_techniques'])}):")
            for tech in details['dpi_techniques'][:6]:
                lines.append(f"   • {tech}")
            if len(details['dpi_techniques']) > 6:
                lines.append(f"   ... и ещё {len(details['dpi_techniques']) - 6}")
        
        # Lua параметры (Zapret 2)
        if details.get('lua_params'):
            lines.append(f"🔧 Lua параметры ({len(details['lua_params'])}):")
            for param in details['lua_params'][:5]:
                lines.append(f"   • {param}")
        
        # Специальные параметры
        if details.get('special_params'):
            sp = details['special_params']
            # Подсчитываем --new как индикатор multi-strategy
            new_count = sp.count('--new')
            other_params = [p for p in sp if p != '--new']
            
            if new_count:
                lines.append(f"📌 Multi-strategy: {new_count + 1} блоков")
            if other_params:
                lines.append(f"📌 Спец. параметры: {', '.join(other_params[:5])}")
        
        lines.append("═" * 50)
        return lines
    
    def _format_type(self, type_str: str) -> str:
        """Форматирует тип стратегии"""
        return {
            'bat': '📄 BAT файл',
            'builtin': '⚡ Встроенная',
            'combined': '🔀 Комбинированная',
            'direct': '🎯 Прямая',
            'unknown': '❓ Неизвестный',
            'error': '❌ Ошибка'
        }.get(type_str, type_str)
    
    def _format_method(self, method: str) -> str:
        """Форматирует метод запуска"""
        return {
            'bat': '📄 BAT файл',
            'direct': '🎯 Zapret 2 (Прямой)',
            'orchestra': '🎼 Zapret 2 (Оркестратор)',
            'zapret1': '📟 Zapret 1 (Совместимость)',
            'unknown': '❓ Неизвестный'
        }.get(method, method)


# ═══════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def check_and_log_strategy() -> Dict:
    """Проверяет текущую стратегию и выводит в лог"""
    checker = StrategyChecker()
    info = checker.check_current_strategy()
    
    for line in checker.format_strategy_info(info):
        log(line, "INFO")
    
    return info


def get_strategy_summary() -> str:
    """Возвращает краткую сводку о текущей стратегии"""
    checker = StrategyChecker()
    info = checker.check_current_strategy()
    
    if info['type'] == 'combined':
        count = len(info['details'].get('active_categories', []))
        method = info.get('method', 'direct')
        method_label = {'orchestra': '🎼', 'zapret1': '📟'}.get(method, '🔀')
        return f"{method_label} Комбинированная ({count} категорий)"
    elif info['type'] == 'bat':
        return f"📄 {info['name']}"
    else:
        return info['name']


def get_strategy_args_preview(max_length: int = 200) -> str:
    """Возвращает превью аргументов командной строки"""
    try:
        from strategy_menu.preset_configuration_zapret2 import strategy_selections
        from strategy_menu.preset_configuration_zapret2.command_builder import build_full_command

        selections = strategy_selections.get_all()
        result = build_full_command(selections)
        args = result.get('args', '')
        
        if len(args) > max_length:
            return args[:max_length] + "..."
        return args
    except Exception as e:
        return f"(ошибка: {e})"