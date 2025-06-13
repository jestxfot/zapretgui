import os
import json
import uuid
import hashlib
import tempfile
import requests
import time
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from log import log

import subprocess, winreg, platform, socket

class DonateChecker:
    def __init__(self, server_url: str = None):
        """
        Инициализирует проверяльщик подписки с защищенным UUID.
        """
        # Получаем UUID машины на основе аппаратного отпечатка (БЕЗ сохранения в реестр)
        self.local_uuid = self._generate_machine_uuid()
        
        # URL с данными подписчиков
        self.subscribers_url = "https://gitflic.ru/project/megacompacy/test/blob/raw?file=donate.json"
        
        # Настройки кэширования
        cache_dir = tempfile.gettempdir()
        self.cache_file = os.path.join(cache_dir, "zapret_subscription_cache.json")
        self.cache_timeout = 10 * 60  # 10 минут
        
        # Настройки сети
        self.request_timeout = 15
        self.max_retries = 3

    def _run_powershell_command(self, command: str, timeout: int = 5) -> Optional[str]:
        """
        Выполняет PowerShell команду и возвращает результат.
        
        Args:
            command: PowerShell команда
            timeout: Таймаут выполнения
            
        Returns:
            Результат выполнения или None при ошибке
        """
        try:
            # Используем PowerShell вместо WMIC
            full_command = [
                'powershell.exe', 
                '-NoProfile', 
                '-NonInteractive', 
                '-WindowStyle', 'Hidden',
                '-Command', 
                command
            ]
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0 and result.stdout.strip():
                output = result.stdout.strip()
                # Очищаем от лишних пробелов и переносов
                cleaned_output = ' '.join(output.split())
                return cleaned_output if len(cleaned_output) > 2 else None
                
        except Exception as e:
            log(f"Ошибка выполнения PowerShell команды: {e}", level="DEBUG")
            
        return None

    def _get_registry_value(self, hkey, subkey: str, value_name: str) -> Optional[str]:
        """
        Получает значение из реестра Windows.
        
        Args:
            hkey: Раздел реестра (например, winreg.HKEY_LOCAL_MACHINE)
            subkey: Подключ
            value_name: Имя значения
            
        Returns:
            Значение из реестра или None
        """
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                if isinstance(value, str) and len(value.strip()) > 2:
                    return value.strip()
        except Exception:
            pass
        return None

    def _get_stable_machine_fingerprint(self) -> str:
        """
        Создает СТАБИЛЬНЫЙ отпечаток машины без использования WMIC.
        Использует PowerShell и реестр Windows.
        
        Returns:
            str: Стабильный отпечаток машины
        """
        try:
            fingerprint_parts = []
            
            # 5. Серийный номер системы через реестр
            try:
                system_serial = self._get_registry_value(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\BIOS",
                    "SystemProductName"
                )
                if system_serial and system_serial != "To be filled by O.E.M.":
                    fingerprint_parts.append(f"system_serial:{system_serial}")
            except:
                pass
            
            # 6. BIOS информация через реестр
            try:
                bios_vendor = self._get_registry_value(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\BIOS",
                    "SystemManufacturer"
                )
                if bios_vendor:
                    fingerprint_parts.append(f"bios_vendor:{bios_vendor}")
            except:
                pass
            
            # 11. Machine GUID из реестра (очень стабильный)
            try:
                machine_guid = self._get_registry_value(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                    "MachineGuid"
                )
                if machine_guid:
                    fingerprint_parts.append(f"machine_guid:{machine_guid}")
            except:
                pass
            
            # Объединяем все части
            fingerprint_string = "|".join(sorted(fingerprint_parts))
            
            # Создаем стабильный хеш
            fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
            
            #log(f"Стабильный отпечаток создан из {len(fingerprint_parts)} компонентов", level="DEBUG")
            #log(f"Компоненты: {[part.split(':')[0] for part in fingerprint_parts]}", level="DEBUG")
            
            return fingerprint_hash
                
        except Exception as e:
            log(f"Ошибка при создании отпечатка машины: {e}", level="ERROR")
            # Критический fallback
            try:
                emergency_data = f"{socket.gethostname()}:{platform.system()}:{os.path.dirname(__file__)}"
                return hashlib.sha256(emergency_data.encode()).hexdigest()[:16]
            except:
                return "critical_fallback_fp"

    def _generate_machine_uuid(self) -> str:
        """
        Генерирует UUID машины на основе аппаратного отпечатка.
        UUID НЕ СОХРАНЯЕТСЯ нигде и генерируется каждый раз заново.
        
        Returns:
            str: UUID машины
        """
        try:
            # Получаем стабильный отпечаток машины
            machine_fingerprint = self._get_stable_machine_fingerprint()
            
            # Создаем детерминированный UUID на основе отпечатка
            namespace = uuid.NAMESPACE_DNS
            protected_string = f"zapret_premium_machine_v4:{machine_fingerprint}"
            machine_uuid = str(uuid.uuid5(namespace, protected_string))
            
            #log(f"UUID машины сгенерирован на основе аппаратного отпечатка", level="DEBUG")
            return machine_uuid
            
        except Exception as e:
            log(f"Ошибка при генерации UUID машины: {e}", level="ERROR")
            # В крайнем случае создаем UUID на основе минимальных данных
            try:
                fallback_data = f"{socket.gethostname()}:{platform.system()}"
                fallback_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"zapret_fallback:{fallback_data}"))
                return fallback_uuid
            except:
                return str(uuid.uuid4())

    def _get_secret_salt(self) -> str:
        """
        Возвращает секретную соль для генерации подписи.
        ВАЖНО: Эта соль должна совпадать с серверной и никогда не раскрываться!
        
        Returns:
            str: Секретная соль
        """
        return "ZaPrEt_UlTrA_SeCrEt_SaLt_2025_v4_DoNoT_sHaRe_ThIs_KeY_AnYwHeRe_PREMIUM_VALIDATION"

    def _generate_uuid_signature(self, machine_uuid: str) -> str:
        """
        Генерирует подпись на основе UUID машины и секретной соли.
        
        Args:
            machine_uuid: UUID машины
            
        Returns:
            str: SHA256 подпись
        """
        try:
            secret_salt = self._get_secret_salt()
            # Создаем подпись: SHA256(UUID + SECRET_SALT + PREMIUM_MARKER)
            signature_string = f"{machine_uuid}{secret_salt}premium_user_validated"
            signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()
            
            log(f"Подпись сгенерирована для UUID", level="DEBUG")
            return signature
            
        except Exception as e:
            log(f"Ошибка при генерации подписи: {e}", level="ERROR")
            return ""

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """
        Загружает кэшированные данные подписчиков.
        
        Returns:
            Словарь с данными или None если кэш недоступен/устарел
        """
        try:
            if not os.path.exists(self.cache_file):
                return None
                
            # Проверяем возраст кэша
            cache_age = time.time() - os.path.getmtime(self.cache_file)
            if cache_age > self.cache_timeout:
                log("Кэш устарел", level="DEBUG")
                return None
                
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log("Данные загружены из кэша", level="DEBUG")
                return data
                
        except Exception as e:
            log(f"Ошибка при загрузке кэша: {e}", level="WARNING")
            return None

    def _save_cache(self, data: Dict[str, Any]) -> None:
        """
        Сохраняет данные в кэш.
        
        Args:
            data: Данные для сохранения
        """
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log("Данные сохранены в кэш", level="DEBUG")
        except Exception as e:
            log(f"Ошибка при сохранении кэша: {e}", level="WARNING")

    def _fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """
        Загружает данные подписчиков с сервера.
        
        Returns:
            Словарь с данными подписчиков или None при ошибке
        """
        for attempt in range(self.max_retries):
            try:
                log(f"Загрузка данных подписчиков (попытка {attempt + 1})", level="DEBUG")
                
                headers = {
                    'User-Agent': 'Zapret-Subscriber-Checker/1.0',
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
                
                response = requests.get(
                    self.subscribers_url,
                    headers=headers,
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                
                data = response.json()
                log("Данные подписчиков успешно загружены", level="INFO")
                return data
                
            except requests.exceptions.RequestException as e:
                log(f"Ошибка сети при загрузке данных (попытка {attempt + 1}): {e}", level="WARNING")
                if attempt == self.max_retries - 1:
                    log("Все попытки загрузки данных исчерпаны", level="ERROR")
            except json.JSONDecodeError as e:
                log(f"Ошибка парсинга JSON: {e}", level="ERROR")
                break
            except Exception as e:
                log(f"Неожиданная ошибка при загрузке данных: {e}", level="ERROR")
                break
                
        return None

    def _find_user_by_uuid(self, subscribers_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ищет пользователя по UUID в данных подписчиков.
        
        Args:
            subscribers_data: Данные с сервера
            
        Returns:
            Данные пользователя или None если не найден
        """
        try:
            subscribers = subscribers_data.get('subscribers', [])
            
            # Генерируем подпись для нашего UUID
            our_signature = self._generate_uuid_signature(self.local_uuid)
            
            for subscriber in subscribers:
                # Проверяем, совпадает ли подпись в данных с нашей подписью UUID
                actual_signature = subscriber.get('signature', '')
                
                if actual_signature == our_signature:
                    log(f"Пользователь найден по подписи UUID", level="INFO")
                    return subscriber
                        
        except Exception as e:
            log(f"Ошибка при поиске пользователя: {e}", level="ERROR")
            
        return None

    def _validate_user_data(self, user_data: Dict[str, Any]) -> bool:
        """
        Валидирует данные пользователя.
        
        Args:
            user_data: Данные пользователя
            
        Returns:
            bool: True если данные валидны
        """
        try:
            # Проверяем обязательные поля
            required_fields = ['id', 'premium', 'signature']
            if not all(field in user_data for field in required_fields):
                log("Отсутствуют обязательные поля", level="WARNING")
                return False
            
            # Проверяем статус premium
            if not user_data.get('premium', False):
                return False
            
            # Проверяем подпись - она должна соответствовать нашему UUID
            expected_signature = self._generate_uuid_signature(self.local_uuid)
            actual_signature = user_data.get('signature', '')
            
            if actual_signature != expected_signature:
                log("Неверная подпись пользователя", level="WARNING")
                return False
            
            # Проверяем срок действия
            expires = user_data.get('expires')
            if expires and expires != 'never':
                try:
                    expire_date = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                    if datetime.now() > expire_date.replace(tzinfo=None):
                        log("Подписка истекла", level="INFO")
                        return False
                except ValueError:
                    log(f"Неверный формат даты: {expires}", level="WARNING")
                    return False
            
            return True
            
        except Exception as e:
            log(f"Ошибка при валидации данных: {e}", level="ERROR")
            return False

    def _calculate_days_remaining(self, user_data: Dict[str, Any]) -> Optional[int]:
        """
        Вычисляет количество дней до окончания подписки.
        
        Args:
            user_data: Данные пользователя
            
        Returns:
            int: Количество дней до окончания или None если бессрочная
        """
        try:
            expires = user_data.get('expires')
            if not expires or expires == 'never':
                return None
                
            expire_date = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            current_date = datetime.now()
            
            if expire_date.tzinfo:
                expire_date = expire_date.replace(tzinfo=None)
                
            days_diff = (expire_date - current_date).days
            return max(0, days_diff)
            
        except Exception as e:
            log(f"Ошибка при вычислении дней: {e}", level="WARNING")
            return None

    def check_subscription_status(self, use_cache: bool = True) -> Tuple[bool, str, Optional[int]]:
        """
        Проверяет статус подписки пользователя.
        
        Args:
            use_cache: Использовать ли кэш для проверки
            
        Returns:
            Tuple[bool, str, Optional[int]]: (активна ли подписка, сообщение, дни до окончания)
        """
        try:
            # Загружаем данные
            subscription_data = None
            
            if use_cache:
                subscription_data = self._load_cache()
                
            if not subscription_data:
                subscription_data = self._fetch_subscription_data()
                if subscription_data:
                    self._save_cache(subscription_data)
                elif use_cache:
                    # Fallback на кэш если сервер недоступен
                    subscription_data = self._load_cache()
            
            if not subscription_data:
                return False, "Не удалось получить данные подписки", None
            
            # Ищем пользователя по UUID
            user_data = self._find_user_by_uuid(subscription_data)
            
            if not user_data:
                log(f"Подписка не найдена для данной машины", level="INFO")
                return False, "Подписка не найдена", None
            
            # Валидируем данные
            if not self._validate_user_data(user_data):
                return False, "Недействительная подписка", None
            
            # Вычисляем оставшиеся дни
            days_remaining = self._calculate_days_remaining(user_data)
            
            log(f"Подписка активна", level="INFO")
            
            if days_remaining is not None:
                return True, f"Подписка активна (осталось {days_remaining} дней)", days_remaining
            else:
                return True, "Подписка активна (бессрочная)", None
                
        except Exception as e:
            log(f"Ошибка при проверке подписки: {e}", level="ERROR")
            return False, f"Ошибка проверки: {str(e)}", None

    def get_machine_uuid(self) -> str:
        """
        Возвращает UUID текущей машины.
        
        Returns:
            str: UUID машины
        """
        return self.local_uuid

    def clear_cache(self) -> None:
        """
        Очищает кэш подписки.
        """
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                log("Кэш подписки очищен", level="INFO")
        except Exception as e:
            log(f"Ошибка при очистке кэша: {e}", level="WARNING")

def check_premium_access(server_url: str = None) -> Tuple[bool, Optional[int]]:
    """
    Упрощенная функция для быстрой проверки премиум доступа.
    
    Args:
        server_url: URL сервера (не используется в новой версии)
        
    Returns:
        Tuple[bool, Optional[int]]: (True если активная подписка, дни до окончания)
    """
    try:
        checker = DonateChecker()
        is_premium, _, days_remaining = checker.check_subscription_status()
        return is_premium, days_remaining
    except Exception as e:
        log(f"Ошибка при проверке премиум доступа: {e}", level="ERROR")
        return False, None

def get_current_machine_uuid() -> str:
    """
    Возвращает UUID текущей машины.
    
    Returns:
        str: UUID машины
    """
    try:
        checker = DonateChecker()
        return checker.get_machine_uuid()
    except Exception as e:
        log(f"Ошибка при получении UUID машины: {e}", level="ERROR")
        return "Ошибка получения UUID"

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # Нужно добавить: pip install python-dateutil

def generate_signature_for_uuid(machine_uuid: str, months: int = None, user_id: str = None) -> str:
    """
    Служебная функция для генерации подписи для конкретного UUID.
    Используется администратором для создания записей на сервере.
    
    Args:
        machine_uuid: UUID машины
        months: Количество месяцев подписки (None для бессрочной)
        user_id: ID пользователя (опционально для удобства)
        
    Returns:
        str: SHA256 подпись
    """
    try:
        checker = DonateChecker()
        secret_salt = checker._get_secret_salt()
        signature_string = f"{machine_uuid}{secret_salt}premium_user_validated"
        signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()
        
        # Вычисляем дату истечения
        if months is None:
            expires_date = "never"
            expires_iso = "never"
        else:
            current_date = datetime.now()
            expires_date = current_date + relativedelta(months=months)
            expires_iso = expires_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        print(f"UUID: {machine_uuid}")
        print(f"Signature: {signature}")
        print(f"Subscription period: {months if months else 'Forever'} {'months' if months and months != 1 else 'month' if months == 1 else ''}")
        
        if months:
            print(f"Expires: {expires_date.strftime('%d.%m.%Y %H:%M')} ({expires_iso})")
        else:
            print(f"Expires: Never")
            
        print("\nJSON entry for server:")
        print(f'{{')
        print(f'    "id": "{user_id if user_id else "USER_ID_HERE"}",')
        print(f'    "premium": true,')
        print(f'    "expires": "{expires_iso}",')
        print(f'    "signature": "{signature}",')
        print(f'    "plan": "premium",')
        
        if months:
            print(f'    "notes": "{months} months subscription from {datetime.now().strftime("%d.%m.%Y")}"')
        else:
            print(f'    "notes": "Lifetime subscription"')
            
        print(f'}}')
        
        return signature
        
    except Exception as e:
        log(f"Ошибка при генерации подписи: {e}", level="ERROR")
        return ""

def create_subscription_entry(machine_uuid: str, months: int = None, user_id: str = None, plan: str = "premium") -> Dict[str, Any]:
    """
    Создает полную запись подписки для добавления на сервер.
    
    Args:
        machine_uuid: UUID машины
        months: Количество месяцев подписки (None для бессрочной)
        user_id: ID пользователя
        plan: Тип плана подписки
        
    Returns:
        Dict с полной записью подписки
    """
    try:
        checker = DonateChecker()
        signature = checker._generate_uuid_signature(machine_uuid)
        
        # Вычисляем дату истечения
        if months is None:
            expires_iso = "never"
            notes = "Lifetime subscription"
        else:
            current_date = datetime.now()
            expires_date = current_date + relativedelta(months=months)
            expires_iso = expires_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            notes = f"{months} months subscription from {current_date.strftime('%d.%m.%Y')}"
        
        entry = {
            "id": user_id if user_id else f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "premium": True,
            "expires": expires_iso,
            "signature": signature,
            "plan": plan,
            "notes": notes
        }
        
        return entry
        
    except Exception as e:
        log(f"Ошибка при создании записи подписки: {e}", level="ERROR")
        return {}

def generate_subscription_variants(machine_uuid: str, user_id: str = None):
    """
    Генерирует несколько вариантов подписки для выбора.
    
    Args:
        machine_uuid: UUID машины
        user_id: ID пользователя
    """
    try:
        print("=" * 60)
        print(f"SUBSCRIPTION VARIANTS FOR UUID: {machine_uuid}")
        print("=" * 60)
        
        variants = [
            (1, "1 месяц"),
            (3, "3 месяца"),
            (6, "6 месяцев"),
            (12, "1 год"),
            (24, "2 года"),
            (None, "Бессрочная")
        ]
        
        for months, description in variants:
            print(f"\n--- {description.upper()} ---")
            entry = create_subscription_entry(machine_uuid, months, user_id)
            
            if entry:
                print(json.dumps(entry, indent=2, ensure_ascii=False))
                
                if months:
                    expires_date = datetime.now() + relativedelta(months=months)
                    print(f"Истекает: {expires_date.strftime('%d.%m.%Y %H:%M')}")
                else:
                    print("Истекает: Никогда")
                    
            print("-" * 40)
            
    except Exception as e:
        log(f"Ошибка при генерации вариантов подписки: {e}", level="ERROR")

# Для тестирования
if __name__ == "__main__":
    checker = DonateChecker()
    machine_uuid = "07062779-3f9a-5610-8a58-a6e0d0738658" #checker.get_machine_uuid()

    generate_signature_for_uuid(machine_uuid, months=1, user_id="premium_user_002")