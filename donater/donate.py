#donate/donate.py
import csv
import datetime as dt
import io
import re
import requests
from requests.adapters import HTTPAdapter, Retry
import winreg
from typing import Optional, Dict, Any, Tuple
from log import log
import time
from net_helpers import HTTP

RAW_CSV_URL = (
    "https://zapretdpi.ru/"
    "/subscriptions.csv"
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
REGISTRY_KEY = r"SOFTWARE\ZapretGUI"
EMAIL_VALUE_NAME = "UserEmail2"

class DonateChecker:
    # --- новый "глобальный" кэш на процесс -----------------------------
    _CSV_CACHE_TTL = 15 * 60            # 15 минут
    _csv_cache: tuple[float, str] | None = None
    # -------------------------------------------------------------------

    def __init__(self):
        # один Session на весь объект
        retries = Retry(
            total          = 3,             # 3 попытки
            backoff_factor = 1,             # 1-2-4 c
            status_forcelist = (502, 503, 504, 522, 524)
        )
        self._ses = requests.Session()
        self._ses.mount("https://", HTTPAdapter(max_retries=retries))

    def _pick_key(self, keys, *variants):
        """Находит ключ в словаре по вариантам названий"""
        for v in variants:
            for k in keys:
                if v in k.lower():
                    return k
        return None

    # -------------------------------------------------------------------
    def fetch_csv(self) -> str:
        try:
            resp = HTTP.get(RAW_CSV_URL, timeout=(5, 30))
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            raise RuntimeError(f"Сетевой сбой: {e}") from e

    def find_row(self, csv_text: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Находит ПОСЛЕДНЮЮ по времени строку пользователя по email или имени"""
        rdr = csv.DictReader(io.StringIO(csv_text), delimiter=';')
        mode = "email" if EMAIL_RE.match(identifier) else "nick"
        
        found_rows = []
        for row in rdr:
            if mode == "email":
                k = self._pick_key(row.keys(), "email")
            else:
                k = self._pick_key(row.keys(), "имя пользователя", "name")
            if k and row[k].strip().lower() == identifier.lower():
                found_rows.append(row)
        
        if not found_rows:
            return None
        
        def get_sort_key(row):
            # Сначала по end_date (активные подписки без end_date - в конец)
            end_date = self.parse_end_date(row)
            start_date = self.parse_start_date(row)
            
            if end_date is None:  # Активная подписка
                return (dt.date.max, start_date or dt.date.min)
            else:  # Завершенная подписка
                return (end_date, start_date or dt.date.min)
        
        found_rows.sort(key=get_sort_key)
        
        # Возвращаем самую свежую запись
        return found_rows[-1]

    def parse_start_date(self, row: dict) -> Optional[dt.date]:
        """Парсит дату начала подписки"""
        k = self._pick_key(row.keys(), "start_date", "дата начала")
        if not k: 
            return None
        val = row[k].strip()
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    def parse_end_date(self, row: dict) -> Optional[dt.date]:
        """Парсит дату окончания подписки"""
        k = self._pick_key(row.keys(), "end_date", "дата окончания")
        if not k:
            return None
        val = row[k].strip()
        if val == "-" or not val:
            return None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    def get_subscription_period(self, row: dict) -> int:
        """Определяет период подписки в днях на основе цены"""
        price_key = self._pick_key(row.keys(), "user_price", "цена пользователя", "цена")
        if not price_key:
            return 30
        
        try:
            user_price = float(row[price_key].replace(',', '.'))
            if user_price >= 570:  # год
                return 365
            elif user_price >= 290:  # полгода
                return 180
            elif user_price >= 147:  # 3 месяца
                return 90
            elif user_price >= 95:   # 2 месяца
                return 60
            else:
                return 30  # месяц
        except (ValueError, AttributeError):
            return 30

    def get_level(self, row: dict) -> str:
        """Получает уровень подписки"""
        k = self._pick_key(row.keys(), "level_name", "уровень", "название уровня")
        return row.get(k, "").strip() or "–"

    def save_email_to_registry(self, email: str) -> bool:
        """Сохраняет email в реестр Windows"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                winreg.SetValueEx(key, EMAIL_VALUE_NAME, 0, winreg.REG_SZ, email)
            log(f"Email сохранен в реестр: {email}", level="INFO")
            return True
        except Exception as e:
            log(f"Ошибка сохранения email в реестр: {e}", level="ERROR")
            return False

    def get_email_from_registry(self) -> Optional[str]:
        """Получает email из реестра Windows"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                email, _ = winreg.QueryValueEx(key, EMAIL_VALUE_NAME)
                log(f"Email загружен из реестра: {email}", level="INFO")
                return email
        except (FileNotFoundError, OSError):
            log("Email не найден в реестре", level="INFO")
            return None
        except Exception as e:
            log(f"Ошибка чтения email из реестра: {e}", level="ERROR")
            return None

    def check_subscription_status(self, use_cache: bool = True) -> Tuple[bool, str, Optional[int]]:
        """
        Проверяет статус подписки пользователя.
        Совместимая версия для старого интерфейса.
        
        Args:
            use_cache: Использовать ли кэш
            
        Returns:
            Tuple[bool, str, Optional[int]]: (premium статус, сообщение, дни до окончания)
        """
        try:
            email = self.get_email_from_registry()
            if not email:
                return False, "Email не найден в реестре", None
            
            result = self.check_user_subscription(email)
            
            is_premium = (result['found'] and 
                         result['days_remaining'] is not None and 
                         result['days_remaining'] > 0) or \
                        (result['found'] and "включен" in result['status'].lower())
            
            return is_premium, result['status'], result['days_remaining']
            
        except Exception as e:
            log(f"Ошибка при проверке статуса подписки: {e}", level="ERROR")
            return False, f"Ошибка проверки: {str(e)}", None

    def check_user_subscription(self, email: str) -> Dict[str, Any]:
        """
        Проверяет статус подписки пользователя по email
        
        Returns:
            Dict с информацией о подписке:
            - found: bool - найден ли пользователь
            - level: str - уровень подписки
            - days_remaining: int|None - дней осталось
            - status: str - текстовый статус
            - auto_payment: bool - включен ли автоплатеж
        """
        try:
            csv_text = self.fetch_csv()
            row = self.find_row(csv_text, email)
            
            if not row:
                return {
                    'found': False,
                    'level': '–',
                    'days_remaining': None,
                    'status': 'Пользователь не найден',
                    'auto_payment': False
                }
            
            level = self.get_level(row)
            end_date = self.parse_end_date(row)
            start_date = self.parse_start_date(row)
            
            type_key = self._pick_key(row.keys(), "type", "тип")
            sub_type = row.get(type_key, "").strip().lower() if type_key else ""
            
            today = dt.date.today()
            
            if end_date:
                # Пользователь отписался
                days = (end_date - today).days
                if days < 0:
                    status = "Подписка истекла"
                    days_remaining = 0
                else:
                    status = f"Осталось {days} дн. (автоплатеж отключен 😢)"
                    days_remaining = days
                auto_payment = False
            elif sub_type == "subscription" and start_date:
                # Активная подписка
                period_days = self.get_subscription_period(row)
                due = start_date + dt.timedelta(days=period_days)
                days = (due - today).days
                if days >= 0:
                    status = f"Осталось {days} дн. (автоплатеж включен 😊)"
                    days_remaining = days
                else:
                    status = "Подписка истекла"
                    days_remaining = 0
                auto_payment = True
            else:
                # Не подписан или другой тип
                status = "Не подписан"
                days_remaining = None
                auto_payment = False
            
            return {
                'found': True,
                'level': level,
                'days_remaining': days_remaining,
                'status': status,
                'auto_payment': auto_payment
            }
            
        except Exception as e:
            log(f"Ошибка при проверке подписки: {e}", level="ERROR")
            return {
                'found': False,
                'level': '–',
                'days_remaining': None,
                'status': f'Ошибка проверки: {str(e)}',
                'auto_payment': False
            }

def check_premium_access(email: str = None) -> Tuple[bool, Optional[int]]:
    """
    Упрощенная функция для быстрой проверки премиум доступа.
    
    Args:
        email: Email пользователя (если None, берется из реестра)
        
    Returns:
        Tuple[bool, Optional[int]]: (True если активная подписка, дни до окончания)
    """
    try:
        checker = DonateChecker()
        
        if not email:
            email = checker.get_email_from_registry()
            if not email:
                return False, None
        
        result = checker.check_user_subscription(email)
        
        # Считаем подписку активной если найден пользователь и есть дни или статус не "истекла"/"не подписан"
        is_active = (result['found'] and 
                    result['days_remaining'] is not None and 
                    result['days_remaining'] > 0) or \
                   (result['found'] and "включен" in result['status'].lower())
        
        return is_active, result['days_remaining']
        
    except Exception as e:
        log(f"Ошибка при проверке премиум доступа: {e}", level="ERROR")
        return False, None