# utils/ipsets_manager.py

import os
import json
from typing import Set, List, Dict
from log import log
from config import LISTS_FOLDER, reg

# Пути к файлам
IPSET_ALL_PATH = os.path.join(LISTS_FOLDER, "ipset-base.txt")
IPSET_ALL2_PATH = os.path.join(LISTS_FOLDER, "ipset-all2.txt")

# Ключи реестра
_IPSETS_KEY = r"Software\Zapret"
_IPSETS_SERVICES = "IpsetsServices"  # JSON строка с выбранными сервисами
_IPSETS_CUSTOM = "IpsetsCustom"      # JSON строка с пользовательскими IP

# Базовые IP диапазоны (всегда включены в ipset-base.txt)
BASE_IPS_TEXT = """
# Cloudflare DNS
1.1.1.1
1.1.1.2
1.1.1.3
1.0.0.1
1.0.0.2
1.0.0.3
"""

# Предустановленные IP диапазоны сервисов
PREDEFINED_IP_RANGES = {
    'discord': {
        'name': '🎮 Discord',
        'ranges': [
            '162.159.128.0/20',
            '162.159.200.0/21',
            '162.159.216.0/21',
            '162.159.160.0/20',
            '162.159.176.0/20',
            '162.159.192.0/20'
        ]
    },
    'twitter': {
        'name': '🐦 Twitter/X',
        'ranges': [
            '104.244.42.0/24',
            '104.244.43.0/24',
            '104.244.44.0/24',
            '104.244.45.0/24',
            '104.244.46.0/24',
            '192.133.76.0/22',
            '199.16.156.0/22',
            '199.59.148.0/22',
            '199.96.56.0/22',
            '202.160.128.0/22',
            '209.237.192.0/19'
        ]
    },
    'facebook': {
        'name': '📘 Facebook/Meta',
        'ranges': [
            '31.13.24.0/21',
            '31.13.64.0/18',
            '45.64.40.0/22',
            '66.220.144.0/20',
            '69.63.176.0/20',
            '69.171.224.0/19',
            '74.119.76.0/22',
            '102.132.96.0/20',
            '103.4.96.0/22',
            '129.134.0.0/16',
            '157.240.0.0/16',
            '173.252.64.0/18',
            '179.60.192.0/22',
            '185.60.216.0/22',
            '204.15.20.0/22'
        ]
    }
}

def get_base_ips() -> List[str]:
    """Возвращает список базовых IP"""
    ips = []
    for line in BASE_IPS_TEXT.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            ips.append(line)
    return ips

def save_ipsets_settings(selected_services: Set[str], custom_ips: List[str]) -> bool:
    """Сохраняет настройки IPsets в реестр"""
    try:
        # Сохраняем выбранные сервисы
        services_json = json.dumps(list(selected_services))
        if not reg(_IPSETS_KEY, _IPSETS_SERVICES, services_json):
            log("Ошибка сохранения IP сервисов в реестр", "❌ ERROR")
            return False
        
        # Сохраняем пользовательские IP
        custom_json = json.dumps(custom_ips)
        if not reg(_IPSETS_KEY, _IPSETS_CUSTOM, custom_json):
            log("Ошибка сохранения пользовательских IP в реестр", "❌ ERROR")
            return False
        
        log(f"Сохранено в реестр: {len(selected_services)} IP сервисов, {len(custom_ips)} IP адресов", "INFO")
        return True
        
    except Exception as e:
        log(f"Ошибка сохранения настроек IPsets: {e}", "❌ ERROR")
        return False

def load_ipsets_settings() -> tuple[Set[str], List[str]]:
    """Загружает настройки IPsets из реестра"""
    selected_services = set()
    custom_ips = []
    
    try:
        # Загружаем выбранные сервисы
        services_json = reg(_IPSETS_KEY, _IPSETS_SERVICES)
        if services_json:
            services_list = json.loads(services_json)
            selected_services = set(services_list)
            log(f"Загружено из реестра: {len(selected_services)} IP сервисов", "DEBUG")
        
        # Загружаем пользовательские IP
        custom_json = reg(_IPSETS_KEY, _IPSETS_CUSTOM)
        if custom_json:
            custom_ips = json.loads(custom_json)
            log(f"Загружено из реестра: {len(custom_ips)} пользовательских IP", "DEBUG")
            
    except Exception as e:
        log(f"Ошибка загрузки настроек IPsets: {e}", "⚠ WARNING")
    
    return selected_services, custom_ips

def rebuild_ipsets_from_registry():
    """Перестраивает файлы ipset-base.txt и ipset-all2.txt из настроек в реестре"""
    try:
        log("Перестройка IPsets из реестра...", "INFO")
        
        # Загружаем настройки из реестра
        selected_services, custom_ips = load_ipsets_settings()
        
        # Создаем папку lists если её нет
        os.makedirs(LISTS_FOLDER, exist_ok=True)
        
        # --- Перестраиваем ipset-base.txt (базовые + сервисы) ---
        all_ips = []
        
        # Добавляем базовые IP
        all_ips.extend(get_base_ips())
        
        # Добавляем IP диапазоны выбранных сервисов
        for service_id in selected_services:
            if service_id in PREDEFINED_IP_RANGES:
                service_ranges = PREDEFINED_IP_RANGES[service_id]['ranges']
                all_ips.extend(service_ranges)
                log(f"Добавлены IP диапазоны сервиса {service_id}: {len(service_ranges)} шт.", "DEBUG")
        
        # Записываем ipset-base.txt
        with open(IPSET_ALL_PATH, 'w', encoding='utf-8') as f:
            for ip in all_ips:
                f.write(f"{ip}\n")
        
        log(f"Создан ipset-base.txt: {len(all_ips)} записей", "✅ SUCCESS")
        
        # --- Создаем/обновляем ipset-all2.txt (пользовательские) ---
        with open(IPSET_ALL2_PATH, 'w', encoding='utf-8') as f:
            for ip in custom_ips:
                f.write(f"{ip}\n")
        
        log(f"Создан ipset-all2.txt: {len(custom_ips)} записей", "✅ SUCCESS")
        
        return True
        
    except Exception as e:
        log(f"Ошибка перестройки IPsets: {e}", "❌ ERROR")
        return False

def ensure_ipsets_exist():
    """Проверяет существование файлов IPsets и создает их если нужно"""
    try:
        # Создаем папку lists если её нет
        os.makedirs(LISTS_FOLDER, exist_ok=True)
        
        files_created = False
        
        # Проверяем ipset-base.txt
        if not os.path.exists(IPSET_ALL_PATH):
            log("Создание ipset-base.txt...", "INFO")
            
            # Создаем с базовыми IP
            with open(IPSET_ALL_PATH, 'w', encoding='utf-8') as f:
                f.write("# Базовые IP диапазоны\n\n")
                for ip in get_base_ips():
                    f.write(f"{ip}\n")
            
            log(f"Создан ipset-base.txt с базовыми IP", "✅ SUCCESS")
            files_created = True
        
        # Проверяем ipset-all2.txt
        if not os.path.exists(IPSET_ALL2_PATH):
            log("Создание ipset-all2.txt...", "INFO")
            
            # Загружаем пользовательские IP из реестра если есть
            _, custom_ips = load_ipsets_settings()
            
            with open(IPSET_ALL2_PATH, 'w', encoding='utf-8') as f:
                for ip in custom_ips:
                    f.write(f"{ip}\n")
            
            log(f"Создан ipset-all2.txt", "✅ SUCCESS")
            files_created = True
        
        return True
        
    except Exception as e:
        log(f"Ошибка создания файлов IPsets: {e}", "❌ ERROR")
        return False

def startup_ipsets_check():
    """Проверка и восстановление IPsets при запуске программы"""
    try:
        log("=== Проверка IPsets при запуске ===", "🔧 IPSETS")
        
        # 1. Проверяем существование файлов
        ensure_ipsets_exist()
        
        # 2. Если есть настройки в реестре - применяем их
        selected_services, custom_ips = load_ipsets_settings()
        
        if selected_services or custom_ips:
            log(f"Найдены настройки IPsets в реестре: {len(selected_services)} сервисов, {len(custom_ips)} IP", "INFO")
            # Перестраиваем файлы из реестра
            rebuild_ipsets_from_registry()
        else:
            log("Настройки IPsets в реестре не найдены, используются существующие файлы", "INFO")
        
        return True
        
    except Exception as e:
        log(f"Ошибка при проверке IPsets: {e}", "❌ ERROR")
        return False