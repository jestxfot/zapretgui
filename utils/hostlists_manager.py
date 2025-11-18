# utils/hostlists_manager.py

import os
import json
from datetime import datetime
from typing import Set, List, Dict
from log import log
from config import OTHER_PATH, OTHER2_PATH, reg
from .BASE_DOMAINS_TEXT import BASE_DOMAINS_TEXT # Базовые домены (всегда включены)

# Ключи реестра для хостлистов
_HOSTLISTS_KEY = r"Software\ZapretReg2"
_HOSTLISTS_SERVICES = "HostlistsServices"  # JSON строка с выбранными сервисами
_HOSTLISTS_CUSTOM = "HostlistsCustom"      # JSON строка с пользовательскими доменами

# Предустановленные домены сервисов
PREDEFINED_DOMAINS = {
    'pinterest': {
        'name': '🖼 Pinterest',
        'domains': [
            'pinterest.com',
            'pinimg.com',
            'pinterest.co.uk',
            'pinterest.co',
            'pinterest.ca',
            'pinterest.de',
            'pinterest.fr',
            'pinterest.it',
            'pinterest.es',
            'pinterest.ru',
            'akamai.net',
            'akamaized.net',
            'akamaiedge.net'
        ]
    },
    'reddit': {
        'name': '👽 Reddit',
        'domains': [
            'reddit.com',
            'redd.it',
            'redditmedia.com',
            'redditstatic.com',
            'redditgifts.com',
            'redditinc.com',
            'reddit.co',
            'reddit.co.uk'
        ]
    },
    'roblox': {
        'name': '🎮 Roblox',
        'domains': [
            'roblox.com',
            'robloxcdn.com',
            'robloxgames.com',
            'robloxlabs.com',
            'robloxapi.com',
            'roblox.net',
            'roblox.org',
            'rbxcdn.com',
            'rblx.co',
            'rblxcloud.com'
        ]
    },
    'Rockstar & Epic Games': {
        'name': '🎮 Rockstar & Epic Games',
        'domains': [
            'epicgames.com',
            'cdn1.unrealengine.com',
            'cdn2.unrealengine.com',
            'epicgames-download1.akamaized.net',
            'fortnite.com',
            'rockstargames.com'
        ]
    },
    'whatsapp': {
        'name': '💬 WhatsApp', 
        'domains': [
            'whatsapp.com',
            'whatsapp.net',
            'wa.me',
            'web.whatsapp.com',
            'www.whatsapp.com',
            'api.whatsapp.com',
            'chat.whatsapp.com',
            'w1.web.whatsapp.com',
            'w2.web.whatsapp.com',
            'w3.web.whatsapp.com',
            'w4.web.whatsapp.com',
            'w5.web.whatsapp.com',
            'w6.web.whatsapp.com',
            'w7.web.whatsapp.com',
            'w8.web.whatsapp.com'
        ]
    }
}

def get_base_domains() -> List[str]:
    """Возвращает список базовых доменов"""
    try:
        # Пробуем импортировать
        from utils import BASE_DOMAINS_TEXT
        
        # Парсим домены
        domains = [
            domain.strip() 
            for domain in BASE_DOMAINS_TEXT.strip().split('\n') 
            if domain.strip() and not domain.strip().startswith('#')
        ]
        
        log(f"get_base_domains: извлечено {len(domains)} доменов", "DEBUG")
        
        # Если доменов мало - что-то не так
        if len(domains) < 5:
            log(f"⚠ WARNING: Только {len(domains)} доменов в BASE_DOMAINS_TEXT", "WARNING")
            return []  # Вернем пустой список, чтобы сработал fallback
        
        return domains
        
    except Exception as e:
        log(f"❌ Ошибка в get_base_domains: {e}", "ERROR")
        return []

def rebuild_hostlists_from_registry():
    """Перестраивает файлы other.txt и other2.txt из настроек в реестре"""
    try:
        log("Перестройка хостлистов из реестра...", "INFO")
        
        # Загружаем настройки из реестра
        selected_services, custom_domains = load_hostlists_settings()
        
        # Создаем папку lists если её нет
        os.makedirs(os.path.dirname(OTHER_PATH), exist_ok=True)
        
        # --- Перестраиваем other.txt ---
        # Получаем базовые домены
        base_domains = get_base_domains()
        log(f"Базовых доменов из BASE_DOMAINS_TEXT: {len(base_domains)}", "DEBUG")
        
        # ✅ ВАЖНОЕ ИСПРАВЛЕНИЕ: Если базовых доменов нет или их мало - используем встроенные
        if len(base_domains) < 5:  # Меньше 5 доменов - явно что-то не так
            log("BASE_DOMAINS_TEXT пуст или содержит мало доменов, используем встроенные", "⚠ WARNING")
            
            # Пробуем еще раз импортировать напрямую
            try:
                from BASE_DOMAINS_TEXT import BASE_DOMAINS_TEXT
                direct_domains = [
                    line.strip() 
                    for line in BASE_DOMAINS_TEXT.strip().split('\n')
                    if line.strip() and not line.strip().startswith('#')
                ]
                if len(direct_domains) > 5:
                    base_domains = direct_domains
                    log(f"Прямой импорт успешен: {len(base_domains)} доменов", "INFO")
                else:
                    raise ValueError("Недостаточно доменов")
            except:
                log("Ошибка при прямом импорте базовых доменов", "❌ ERROR")

        # Создаем набор всех доменов
        all_domains = set(base_domains)
        log(f"Добавлено базовых доменов: {len(all_domains)}", "INFO")
        
        # Добавляем домены выбранных сервисов
        for service_id in selected_services:
            if service_id in PREDEFINED_DOMAINS:
                service_domains = PREDEFINED_DOMAINS[service_id]['domains']
                all_domains.update(service_domains)
                log(f"Добавлены домены сервиса {PREDEFINED_DOMAINS[service_id]['name']}: {len(service_domains)} шт.", "DEBUG")
        
        # ✅ ВАЖНО: Проверяем что есть домены для записи
        if not all_domains:
            log("КРИТИЧЕСКАЯ ОШИБКА: Нет доменов для записи в other.txt!", "❌ ERROR")
            # Аварийный минимум
            all_domains = {'youtube.com', 'googlevideo.com', 'discord.com'}
        
        # Записываем other.txt
        with open(OTHER_PATH, 'w', encoding='utf-8') as f:
            for domain in sorted(all_domains):
                f.write(f"{domain}\n")
        
        log(f"✅ Создан other.txt: {len(all_domains)} доменов", "SUCCESS")
        
        # Проверяем что файл действительно записан и не пустой
        with open(OTHER_PATH, 'r', encoding='utf-8') as f:
            verification = f.read()
            lines = [l for l in verification.split('\n') if l.strip()]
            if not lines:
                log("❌ ОШИБКА: other.txt записан, но оказался пустым!", "ERROR")
            else:
                log(f"✅ Проверка: other.txt содержит {len(lines)} строк", "DEBUG")
        
        # --- Перестраиваем other2.txt ---
        with open(OTHER2_PATH, 'w', encoding='utf-8') as f:
            for domain in sorted(custom_domains):
                f.write(f"{domain}\n")
        
        log(f"✅ Создан other2.txt: {len(custom_domains)} доменов", "SUCCESS")
        
        return True
        
    except Exception as e:
        log(f"❌ Ошибка перестройки хостлистов: {e}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        return False

def save_hostlists_settings(selected_services: Set[str], custom_domains: List[str]) -> bool:
    """Сохраняет настройки хостлистов в реестр"""
    try:
        # Сохраняем выбранные сервисы
        services_json = json.dumps(list(selected_services))
        if not reg(_HOSTLISTS_KEY, _HOSTLISTS_SERVICES, services_json):
            log("Ошибка сохранения сервисов в реестр", "❌ ERROR")
            return False
        
        # Сохраняем пользовательские домены
        custom_json = json.dumps(custom_domains)
        if not reg(_HOSTLISTS_KEY, _HOSTLISTS_CUSTOM, custom_json):
            log("Ошибка сохранения пользовательских доменов в реестр", "❌ ERROR")
            return False
        
        log(f"Сохранено в реестр: {len(selected_services)} сервисов, {len(custom_domains)} доменов", "INFO")
        return True
        
    except Exception as e:
        log(f"Ошибка сохранения настроек хостлистов: {e}", "❌ ERROR")
        return False

def load_hostlists_settings() -> tuple[Set[str], List[str]]:
    """Загружает настройки хостлистов из реестра"""
    selected_services = set()
    custom_domains = []
    
    try:
        # Загружаем выбранные сервисы
        services_json = reg(_HOSTLISTS_KEY, _HOSTLISTS_SERVICES)
        if services_json:
            services_list = json.loads(services_json)
            selected_services = set(services_list)
            log(f"Загружено из реестра: {len(selected_services)} сервисов", "DEBUG")
        
        # Загружаем пользовательские домены
        custom_json = reg(_HOSTLISTS_KEY, _HOSTLISTS_CUSTOM)
        if custom_json:
            custom_domains = json.loads(custom_json)
            log(f"Загружено из реестра: {len(custom_domains)} пользовательских доменов", "DEBUG")
            
    except Exception as e:
        log(f"Ошибка загрузки настроек хостлистов: {e}", "⚠ WARNING")
    
    return selected_services, custom_domains

def ensure_hostlists_exist():
    """Проверяет существование файлов хостлистов и создает их если нужно"""
    try:
        # Создаем папку lists если её нет
        os.makedirs(os.path.dirname(OTHER_PATH), exist_ok=True)
        
        # Если файлы существуют и не пустые - не трогаем
        other_exists = os.path.exists(OTHER_PATH) and os.path.getsize(OTHER_PATH) > 0
        other2_exists = os.path.exists(OTHER2_PATH)  # other2.txt может быть пустым
        
        if other_exists and other2_exists:
            log("Файлы хостлистов существуют", "DEBUG")
            return True
        
        # Если файлов нет - создаем из реестра или с дефолтными значениями
        log("Создание отсутствующих файлов хостлистов...", "INFO")
        
        if not other_exists:
            # Пробуем загрузить из реестра
            selected_services, _ = load_hostlists_settings()
            
            # Если в реестре пусто - используем дефолтные значения
            if not selected_services:
                log("Настройки хостлистов не найдены в реестре, используем базовые", "INFO")
            
            # Создаем other.txt
            all_domains = set(get_base_domains())
            
            for service_id in selected_services:
                if service_id in PREDEFINED_DOMAINS:
                    all_domains.update(PREDEFINED_DOMAINS[service_id]['domains'])
            
            with open(OTHER_PATH, 'w', encoding='utf-8') as f:
                for domain in sorted(all_domains):
                    f.write(f"{domain}\n")
            
            log(f"Создан other.txt с {len(all_domains)} доменами", "✅ SUCCESS")
        
        if not other2_exists:
            # Создаем пустой other2.txt если его нет
            with open(OTHER2_PATH, 'w', encoding='utf-8') as f:
                # Загружаем пользовательские домены из реестра
                _, custom_domains = load_hostlists_settings()
                for domain in sorted(custom_domains):
                    f.write(f"{domain}\n")
            
            log(f"Создан other2.txt", "✅ SUCCESS")
        
        return True
        
    except Exception as e:
        log(f"Ошибка создания файлов хостлистов: {e}", "❌ ERROR")
        return False

def startup_hostlists_check():
    """Проверка и восстановление хостлистов при запуске программы"""
    try:
        log("=== Проверка хостлистов при запуске ===", "🔧 HOSTLISTS")
        
        # 1. Проверяем существование файлов
        ensure_hostlists_exist()
        
        # ✅ НОВОЕ: Всегда проверяем валидность other.txt
        if os.path.exists(OTHER_PATH):
            with open(OTHER_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = [l.strip() for l in content.split('\n') 
                        if l.strip() and not l.strip().startswith('#')]
                
                if not lines:
                    log("other.txt пуст или содержит только комментарии, пересоздаем", "⚠ WARNING")
                    # Принудительно пересоздаем файлы
                    rebuild_hostlists_from_registry()
                    return True
        
        # 2. Если есть настройки в реестре - применяем их
        selected_services, custom_domains = load_hostlists_settings()
        
        if selected_services or custom_domains:
            log(f"Найдены настройки в реестре: {len(selected_services)} сервисов, {len(custom_domains)} доменов", "INFO")
            rebuild_hostlists_from_registry()
        else:
            log("Настройки хостлистов в реестре не найдены", "INFO")
            # ✅ НОВОЕ: Если реестр пуст, но файл невалидный - пересоздаем с базовыми
            rebuild_hostlists_from_registry()
        
        return True
        
    except Exception as e:
        log(f"Ошибка при проверке хостлистов: {e}", "❌ ERROR")
        return False