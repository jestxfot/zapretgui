# strategy_checker.py
"""
Модуль для проверки и анализа текущей стратегии DPI
Поддерживает BAT стратегии, встроенные и кастомные комбинированные стратегии
"""

import os
import json
from typing import Dict, Optional, Tuple, List
from config import (
    get_last_strategy,
    BAT_FOLDER
)
from log import log
from strategy_menu import get_strategy_launch_method


class StrategyChecker:
    """Класс для проверки и анализа стратегий"""
    
    def __init__(self):
        self.launch_method = get_strategy_launch_method()
        self.current_strategy = None
        self.strategy_type = None  # 'bat', 'builtin', 'combined'
        self.strategy_details = {}
        
    def check_current_strategy(self) -> Dict:
        """
        Проверяет текущую выбранную стратегию
        
        Returns:
            Dict с информацией о стратегии:
            - name: название стратегии
            - type: тип ('bat', 'builtin', 'combined')
            - method: метод запуска ('bat', 'direct')
            - file_status: статус файла ('found', 'not_found', 'N/A')
            - details: дополнительные детали
        """
        try:
            result = {
                'name': 'Неизвестная',
                'type': 'unknown',
                'method': self.launch_method,
                'file_status': 'N/A',
                'details': {}
            }
            
            if self.launch_method == 'direct':
                result.update(self._check_direct_strategy())
            else:
                result.update(self._check_bat_strategy())
                
            return result
            
        except Exception as e:
            log(f"Ошибка проверки стратегии: {e}", "❌ ERROR")
            return {
                'name': f'Ошибка: {e}',
                'type': 'error',
                'method': self.launch_method,
                'file_status': 'error',
                'details': {}
            }
    
    def _check_direct_strategy(self) -> Dict:
        """Проверка стратегии в direct режиме"""
        try:
            # Получаем выборы категорий
            from strategy_menu import get_direct_strategy_selections
            selections = get_direct_strategy_selections()
            
            # Это комбинированная стратегия
            from strategy_menu.strategy_lists_separated import (
                YOUTUBE_STRATEGIES, YOUTUBE_QUIC_STRATEGIES, GOOGLEVIDEO_STRATEGIES, DISCORD_STRATEGIES, 
                DISCORD_VOICE_STRATEGIES, IPSET_TCP_STRATEGIES, IPSET_UDP_STRATEGIES,
                combine_strategies
            )

            from strategy_menu import OTHER_STRATEGIES
            
            # Получаем комбинированную конфигурацию
            combined = combine_strategies(
                selections.get('youtube'),
                selections.get('youtube_udp'),
                selections.get('googlevideo_tcp'),
                selections.get('discord'),
                selections.get('discord_voice'),
                selections.get('other'),
                selections.get('ipset'),
                selections.get('ipset_udp'),
            )
            
            # Формируем детали
            active_categories = []
            strategy_names = []
            
            # YouTube
            if selections.get('youtube') and selections['youtube'] != 'youtube_none':
                active_categories.append('YouTube')
                yt_strat = YOUTUBE_STRATEGIES.get(selections['youtube'])
                if yt_strat:
                    strategy_names.append(f"YT: {yt_strat.get('name', selections['youtube'])}")

            # YouTube QUIC
            if selections.get('youtube_udp') and selections['youtube_udp'] != 'youtube_udp_none':
                active_categories.append('YouTube QUIC')
                ytu_strat = YOUTUBE_QUIC_STRATEGIES.get(selections['youtube_udp'])
                if ytu_strat:
                    strategy_names.append(f"YTU: {ytu_strat.get('name', selections['youtube_udp'])}")
            
            # GoogleVideo
            if selections.get('googlevideo_tcp') and selections['googlevideo_tcp'] != 'googlevideo_none':
                active_categories.append('GoogleVideo')
                gv_strat = GOOGLEVIDEO_STRATEGIES.get(selections['googlevideo_tcp'])
                if gv_strat:
                    strategy_names.append(f"GV: {gv_strat.get('name', selections['googlevideo_tcp'])}")

            # Discord
            if selections.get('discord') and selections['discord'] != 'discord_none':
                active_categories.append('Discord')
                dc_strat = DISCORD_STRATEGIES.get(selections['discord'])
                if dc_strat:
                    strategy_names.append(f"DC: {dc_strat.get('name', selections['discord'])}")
            
            # Discord Voice
            if selections.get('discord_voice') and selections['discord_voice'] != 'discord_voice_none':
                active_categories.append('Discord Voice')
                dv_strat = DISCORD_VOICE_STRATEGIES.get(selections['discord_voice'])
                if dv_strat:
                    strategy_names.append(f"DV: {dv_strat.get('name', selections['discord_voice'])}")
            
            # Other
            if selections.get('other') and selections['other'] != 'other_none':
                active_categories.append('Остальные')
                ot_strat = OTHER_STRATEGIES.get(selections['other'])
                if ot_strat:
                    strategy_names.append(f"Other: {ot_strat.get('name', selections['other'])}")

            # IPset
            if selections.get('ipset') and selections['ipset'] != 'ipset_none':
                active_categories.append('IPset')
                i_strat = IPSET_TCP_STRATEGIES.get(selections['ipset'])
                if i_strat:
                    strategy_names.append(f"IPset: {i_strat.get('name', selections['ipset'])}")

            # IPset UDP
            if selections.get('ipset_udp') and selections['ipset_udp'] != 'ipset_udp_none':
                active_categories.append('IPset UDP')
                iu_strat = IPSET_UDP_STRATEGIES.get(selections['ipset_udp'])
                if iu_strat:
                    strategy_names.append(f"IPset UDP: {iu_strat.get('name', selections['ipset_udp'])}")
            
            # Подсчитываем параметры
            args_list = combined['args'].split() if combined['args'] else []
            
            # Анализируем флаги
            flags_analysis = self._analyze_strategy_flags(args_list)
            
            return {
                'name': combined['description'],
                'type': 'combined',
                'method': 'direct',
                'file_status': 'N/A',
                'details': {
                    'active_categories': active_categories,
                    'strategy_names': strategy_names,
                    'selections': selections,
                    'args_count': len(args_list),
                    'hostlists': flags_analysis.get('hostlists', []),
                    'key_flags': flags_analysis.get('key_flags', []),
                    'ports': flags_analysis.get('ports', []),
                    'special_params': flags_analysis.get('special_params', [])
                }
            }
            
        except Exception as e:
            log(f"Ошибка проверки direct стратегии: {e}", "DEBUG")
            return {
                'name': 'Direct стратегия (ошибка чтения)',
                'type': 'direct',
                'method': 'direct',
                'file_status': 'error',
                'details': {'error': str(e)}
            }
    
    def _check_bat_strategy(self) -> Dict:
        """Проверка BAT стратегии"""
        try:
            strategy_name = get_last_strategy()
            
            # Ищем файл стратегии
            strategy_file = self._find_strategy_file(strategy_name)
            file_status = 'found' if strategy_file else 'not_found'
            
            details = {}
            
            if strategy_file and os.path.exists(strategy_file):
                # Читаем содержимое файла
                try:
                    with open(strategy_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
                        content = f.read()
                    
                    # Анализируем содержимое
                    details['file_size'] = os.path.getsize(strategy_file)
                    details['file_path'] = strategy_file
                    
                    # Ищем версию
                    for line in content.split('\n'):
                        if 'VERSION:' in line:
                            details['version'] = line.split('VERSION:')[1].strip()
                            break
                    
                    # Анализируем команды winws
                    winws_commands = self._extract_winws_commands(content)
                    if winws_commands:
                        details['commands_count'] = len(winws_commands)
                        
                        # Анализируем флаги из первой команды
                        if winws_commands:
                            flags_analysis = self._analyze_bat_command(winws_commands[0])
                            details.update(flags_analysis)
                            
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
    
    def _analyze_strategy_flags(self, args_list: List[str]) -> Dict:
        """Анализирует флаги стратегии"""
        analysis = {
            'hostlists': [],
            'key_flags': [],
            'ports': [],
            'special_params': []
        }
        
        i = 0
        while i < len(args_list):
            arg = args_list[i]
            
            # Хостлисты
            if arg.startswith('--hostlist='):
                hostlist = arg.split('=', 1)[1]
                analysis['hostlists'].append(hostlist)
            
            # Порты
            elif arg in ['--port', '--dport']:
                if i + 1 < len(args_list):
                    port = args_list[i + 1]
                    analysis['ports'].append(f"{arg}={port}")
                    i += 1
            
            # Ключевые флаги обхода
            elif arg in ['--split-pos', '--split-http-req', '--split-tls',
                        '--disorder', '--fake-http', '--fake-tls',
                        '--tlsrec', '--tamper']:
                if i + 1 < len(args_list) and not args_list[i + 1].startswith('-'):
                    analysis['key_flags'].append(f"{arg} {args_list[i + 1]}")
                    i += 1
                else:
                    analysis['key_flags'].append(arg)
            
            # Специальные параметры
            elif arg.startswith('--wssize='):
                analysis['special_params'].append(arg)
            elif arg.startswith('--ipset='):
                analysis['special_params'].append(arg)
            elif arg.startswith('--md5sig'):
                analysis['special_params'].append(arg)
            
            i += 1
        
        return analysis
    
    def _analyze_bat_command(self, command: str) -> Dict:
        """Анализирует команду из BAT файла"""
        import shlex
        
        try:
            # Парсим команду
            parts = shlex.split(command, posix=False)
            
            # Убираем путь к exe и start /min если есть
            filtered_parts = []
            skip_next = False
            for part in parts:
                if skip_next:
                    skip_next = False
                    continue
                if 'winws.exe' in part.lower():
                    continue
                if part.lower() in ['start', '/min', '/b']:
                    skip_next = (part.lower() == 'start')
                    continue
                filtered_parts.append(part)
            
            # Анализируем флаги
            return self._analyze_strategy_flags(filtered_parts)
            
        except Exception as e:
            log(f"Ошибка анализа BAT команды: {e}", "DEBUG")
            return {}
    
    def _extract_winws_commands(self, bat_content: str) -> List[str]:
        """Извлекает команды winws из BAT файла"""
        commands = []
        
        for line in bat_content.split('\n'):
            line = line.strip()
            if 'winws.exe' in line.lower() and not line.startswith('::') and not line.startswith('REM'):
                commands.append(line)
        
        return commands
    
    def _find_strategy_file(self, strategy_name: str) -> Optional[str]:
        """Ищет файл стратегии в папке bat"""
        try:
            if not os.path.exists(BAT_FOLDER):
                return None
            
            # Ищем файлы .bat
            for file in os.listdir(BAT_FOLDER):
                if file.lower().endswith('.bat'):
                    file_path = os.path.join(BAT_FOLDER, file)
                    
                    # Простое сопоставление по имени
                    if strategy_name.lower() in file.lower():
                        return file_path
            
            # Если не нашли по имени, возвращаем первый .bat файл
            for file in os.listdir(BAT_FOLDER):
                if file.lower().endswith('.bat'):
                    return os.path.join(BAT_FOLDER, file)
            
            return None
            
        except Exception as e:
            log(f"Ошибка поиска файла стратегии: {e}", "DEBUG")
            return None
    
    def format_strategy_info(self, info: Dict) -> List[str]:
        """Форматирует информацию о стратегии для вывода в лог"""
        lines = []
        
        lines.append("📋 ИНФОРМАЦИЯ О СТРАТЕГИИ:")
        lines.append(f"   Название: {info['name']}")
        lines.append(f"   Тип: {self._format_type(info['type'])}")
        lines.append(f"   Метод запуска: {self._format_method(info['method'])}")
        
        if info['file_status'] != 'N/A':
            status_icon = "✅" if info['file_status'] == 'found' else "❌"
            lines.append(f"   Файл стратегии: {status_icon} {info['file_status']}")
        
        details = info.get('details', {})
        
        # Для комбинированных стратегий
        if info['type'] == 'combined' and details:
            if details.get('active_categories'):
                lines.append(f"   Активные категории: {', '.join(details['active_categories'])}")
            
            if details.get('strategy_names'):
                lines.append("   Используемые стратегии:")
                for name in details['strategy_names']:
                    lines.append(f"      • {name}")
            
            if details.get('args_count'):
                lines.append(f"   Количество аргументов: {details['args_count']}")
        
        # Анализ флагов
        if details.get('hostlists'):
            lines.append(f"   Хостлисты: {', '.join(details['hostlists'])}")
        
        if details.get('key_flags'):
            lines.append("   Ключевые флаги обхода:")
            for flag in details['key_flags'][:5]:  # Показываем первые 5
                lines.append(f"      • {flag}")
            if len(details['key_flags']) > 5:
                lines.append(f"      ... и еще {len(details['key_flags']) - 5}")
        
        if details.get('ports'):
            lines.append(f"   Порты: {', '.join(details['ports'][:3])}")
        
        if details.get('special_params'):
            lines.append(f"   Специальные параметры: {', '.join(details['special_params'])}")
        
        # Для BAT стратегий
        if info['type'] == 'bat' and details:
            if details.get('version'):
                lines.append(f"   Версия: {details['version']}")
            
            if details.get('file_size'):
                lines.append(f"   Размер файла: {details['file_size']} байт")
            
            if details.get('commands_count'):
                lines.append(f"   Команд winws: {details['commands_count']}")
        
        return lines
    
    def _format_type(self, type_str: str) -> str:
        """Форматирует тип стратегии"""
        types = {
            'bat': 'BAT файл',
            'builtin': 'Встроенная',
            'combined': 'Комбинированная',
            'direct': 'Прямая',
            'unknown': 'Неизвестный',
            'error': 'Ошибка'
        }
        return types.get(type_str, type_str)
    
    def _format_method(self, method: str) -> str:
        """Форматирует метод запуска"""
        methods = {
            'bat': 'Классический (BAT)',
            'direct': 'Прямой запуск',
            'unknown': 'Неизвестный'
        }
        return methods.get(method, method)