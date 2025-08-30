import ctypes
import stat
import os
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from .proxy_domains import PROXY_DOMAINS
from .menu import HostsSelectorDialog
from log import log

HOSTS_PATH = Path(r"C:\Windows\System32\drivers\etc\hosts")

def check_hosts_file_name():
    """Проверяет правильность написания имени файла hosts"""
    hosts_dir = Path(r"C:\Windows\System32\drivers\etc")
    
    # ✅ НОВОЕ: Создаем директорию если её нет
    if not hosts_dir.exists():
        try:
            hosts_dir.mkdir(parents=True, exist_ok=True)
            log(f"Создана директория: {hosts_dir}")
        except Exception as e:
            log(f"Не удалось создать директорию: {e}", "❌ ERROR")
            return False, f"Не удалось создать директорию etc: {e}"
    
    # Сначала проверяем правильный файл hosts
    hosts_lower = hosts_dir / "hosts"
    if hosts_lower.exists():
        # Дополнительно проверяем кодировку файла
        try:
            hosts_lower.read_text(encoding="utf-8-sig")
            return True, None
        except UnicodeDecodeError:
            # Файл существует, но с проблемами кодировки
            log("Файл hosts существует, но содержит некорректные символы", level="⚠ WARNING")
            return False, "Файл hosts содержит некорректные символы и не может быть прочитан в UTF-8"
    
    # Если правильного файла нет, проверяем есть ли неправильный HOSTS
    hosts_upper = hosts_dir / "HOSTS"
    if hosts_upper.exists():
        log("Обнаружен файл HOSTS (с большими буквами) - это неправильно!", level="⚠ WARNING")
        return False, "Файл должен называться 'hosts' (с маленькими буквами), а не 'HOSTS'"
    
    # ✅ НОВОЕ: Если файла нет вообще - это нормально, мы его создадим
    return True, None  # Изменено с False на True

def is_file_readonly(filepath):
    """Проверяет, установлен ли атрибут 'только для чтения' у файла"""
    try:
        file_stat = os.stat(filepath)
        return not (file_stat.st_mode & stat.S_IWRITE)
    except Exception as e:
        log(f"Ошибка при проверке атрибутов файла: {e}")
        return False

def remove_readonly_attribute(filepath):
    """Снимает атрибут 'только для чтения' с файла"""
    try:
        # Получаем текущие атрибуты файла
        file_stat = os.stat(filepath)
        # Добавляем право на запись
        os.chmod(filepath, file_stat.st_mode | stat.S_IWRITE)
        log(f"Атрибут 'только для чтения' снят с файла: {filepath}")
        return True
    except Exception as e:
        log(f"Ошибка при снятии атрибута 'только для чтения': {e}")
        return False

def safe_read_hosts_file():
    """Безопасно читает файл hosts с обработкой различных кодировок"""
    hosts_path = HOSTS_PATH
    
    # ✅ НОВОЕ: Проверяем существование файла
    if not hosts_path.exists():
        log(f"Файл hosts не существует, создаем новый: {hosts_path}")
        try:
            # Создаем директорию если её нет
            hosts_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Создаем пустой файл hosts с базовым содержимым
            default_content = """# Copyright (c) 1993-2009 Microsoft Corp.
#
# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.
#
# This file contains the mappings of IP addresses to host names. Each
# entry should be kept on an individual line. The IP address should
# be placed in the first column followed by the corresponding host name.
# The IP address and the host name should be separated by at least one
# space.
#
# Additionally, comments (such as these) may be inserted on individual
# lines or following the machine name denoted by a '#' symbol.
#
# For example:
#
#      102.54.94.97     rhino.acme.com          # source server
#       38.25.63.10     x.acme.com              # x client host

# localhost name resolution is handled within DNS itself.
#	127.0.0.1       localhost
#	::1             localhost
"""
            hosts_path.write_text(default_content, encoding='utf-8-sig')
            log("Файл hosts успешно создан с базовым содержимым")
            return default_content
            
        except Exception as e:
            log(f"Ошибка при создании файла hosts: {e}", "❌ ERROR")
            return None
    
    # Если файл существует, пробуем прочитать с разными кодировками
    encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'cp866', 'latin1']
    
    for encoding in encodings:
        try:
            content = hosts_path.read_text(encoding=encoding)
            log(f"Файл hosts успешно прочитан с кодировкой: {encoding}")
            return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            log(f"Ошибка при чтении файла hosts с кодировкой {encoding}: {e}")
            continue
    
    # Если ни одна кодировка не подошла, пробуем с игнорированием ошибок
    try:
        content = hosts_path.read_text(encoding='utf-8', errors='ignore')
        log("Файл hosts прочитан с игнорированием ошибок кодировки", level="⚠ WARNING")
        return content
    except Exception as e:
        log(f"Критическая ошибка при чтении файла hosts: {e}", "❌ ERROR")
        return None

def safe_write_hosts_file(content):
    """Безопасно записывает файл hosts с правильной кодировкой"""
    try:
        # Проверяем атрибут "только для чтения" перед записью
        if is_file_readonly(HOSTS_PATH):
            log("Файл hosts имеет атрибут 'только для чтения', пытаемся снять...")
            if not remove_readonly_attribute(HOSTS_PATH):
                log("Не удалось снять атрибут 'только для чтения'")
                return False
        
        HOSTS_PATH.write_text(content, encoding="utf-8-sig", newline='\n')
        return True
    except PermissionError:
        log("Ошибка доступа при записи файла hosts (возможно, нет прав администратора)")
        return False
    except Exception as e:
        log(f"Ошибка при записи файла hosts: {e}")
        return False
    
class HostsManager:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        # 🆕 При инициализации проверяем и удаляем api.github.com
        self.check_and_remove_github_api()

    # 🆕 НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С api.github.com
    def check_github_api_in_hosts(self):
        """Проверяет, есть ли запись api.github.com в hosts файле"""
        try:
            content = safe_read_hosts_file()
            if content is None:
                return False
                
            lines = content.splitlines()
            
            for line in lines:
                line = line.strip()
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue
                    
                # Разбиваем строку на части (IP домен)
                parts = line.split()
                if len(parts) >= 2:
                    domain = parts[1]  # Второй элемент - это домен
                    if domain.lower() == "api.github.com":
                        return True
                        
            return False
        except Exception as e:
            log(f"Ошибка при проверке api.github.com в hosts: {e}")
            return False

    def remove_github_api_from_hosts(self):
        """Принудительно удаляет запись api.github.com из hosts файла"""
        try:
            content = safe_read_hosts_file()
            if content is None:
                log("Не удалось прочитать файл hosts для удаления api.github.com")
                return False
                
            lines = content.splitlines(keepends=True)
            new_lines = []
            removed_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                # Пропускаем пустые строки и комментарии
                if not line_stripped or line_stripped.startswith('#'):
                    new_lines.append(line)
                    continue
                    
                # Разбиваем строку на части (IP домен)
                parts = line_stripped.split()
                if len(parts) >= 2:
                    domain = parts[1]  # Второй элемент - это домен
                    if domain.lower() == "api.github.com":
                        # Нашли запись api.github.com - не добавляем её в новый файл
                        removed_lines.append(line_stripped)
                        log(f"Удаляем из hosts: {line_stripped}")
                        continue
                
                # Добавляем все остальные строки
                new_lines.append(line)
            
            if removed_lines:
                # Убираем лишние пустые строки в конце файла
                while new_lines and new_lines[-1].strip() == "":
                    new_lines.pop()
                
                # Оставляем одну пустую строку в конце, если файл не пустой
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines[-1] += '\n'
                elif new_lines:
                    new_lines.append('\n')

                if not safe_write_hosts_file("".join(new_lines)):
                    log("Не удалось записать файл hosts после удаления api.github.com")
                    return False
                
                log(f"✅ Удалена запись api.github.com из hosts файла: {removed_lines}")
                self.set_status("Запись api.github.com удалена из hosts файла")
                return True
            else:
                log("Запись api.github.com не найдена в hosts файле")
                return True  # Не ошибка, просто нет записи
                
        except PermissionError:
            log("Нет прав для удаления api.github.com из hosts файла")
            return False
        except Exception as e:
            log(f"Ошибка при удалении api.github.com из hosts: {e}")
            return False

    def check_and_remove_github_api(self):
        """Проверяет и при необходимости удаляет api.github.com из hosts"""
        try:
            # Импортируем функцию для проверки настройки реестра
            from config import get_remove_github_api
            
            # Проверяем, разрешено ли удаление GitHub API
            if not get_remove_github_api():
                log("⚙️ Удаление api.github.com отключено в настройках")
                return
                
            if self.check_github_api_in_hosts():
                log("🔍 Обнаружена запись api.github.com в hosts файле - принудительно удаляем...")
                if self.remove_github_api_from_hosts():
                    log("✅ Запись api.github.com успешно удалена из hosts")
                else:
                    log("❌ Не удалось удалить api.github.com из hosts")
            else:
                log("✅ Запись api.github.com не найдена в hosts файле")
        except Exception as e:
            log(f"Ошибка при проверке/удалении api.github.com: {e}")

    # ------------------------- HostsSelectorDialog -------------------------
    def show_hosts_selector_dialog(self, parent=None):
        """Показывает диалог выбора доменов для hosts"""
        from PyQt6.QtWidgets import QDialog

        current_active = set()
        if self.is_proxy_domains_active():
            # Получаем текущие активные домены из hosts файла
            try:
                content = HOSTS_PATH.read_text(encoding="utf-8-sig")
                for domain in PROXY_DOMAINS.keys():
                    if domain in content:
                        current_active.add(domain)
            except Exception as e:
                log(f"Ошибка при чтении hosts: {e}")
        
        dialog = HostsSelectorDialog(parent, current_active)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_domains = dialog.get_selected_domains()
            return self.apply_selected_domains(selected_domains)
        return False
    
    # ------------------------- сервис -------------------------

    def set_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    # ------------------------- проверки -------------------------

    def is_proxy_domains_active(self) -> bool:
        """Проверяет, есть ли активные (НЕ закомментированные) записи наших доменов в hosts"""
        try:
            content = safe_read_hosts_file()
            if content is None:
                return False
                
            lines = content.splitlines()
            domains = set(PROXY_DOMAINS.keys())
            
            for line in lines:
                line = line.strip()
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue
                    
                # Разбиваем строку на части (IP домен)
                parts = line.split()
                if len(parts) >= 2:
                    domain = parts[1]  # Второй элемент - это домен
                    if domain in domains:
                        # Найден активный (не закомментированный) домен
                        return True
                        
            return False
        except Exception as e:
            log(f"Ошибка при проверке hosts: {e}")
            return False

    def is_hosts_file_accessible(self) -> bool:
        """Проверяет, доступен ли файл hosts для чтения и записи."""
        try:
            # Проверяем правильность написания имени файла
            is_correct, error_msg = check_hosts_file_name()
            if not is_correct:
                log(error_msg)
                return False
            
            # ✅ НОВОЕ: Если файла нет, создаем его
            if not HOSTS_PATH.exists():
                log("Файл hosts не существует, будет создан при первой записи")
                # Проверяем, можем ли мы создать файл
                try:
                    # Пробуем создать временный файл в той же директории
                    test_file = HOSTS_PATH.parent / "test_write_permission.tmp"
                    test_file.write_text("test", encoding="utf-8")
                    test_file.unlink()  # Удаляем тестовый файл
                    return True
                except PermissionError:
                    log("Нет прав для создания файла hosts. Требуются права администратора.")
                    return False
            
            # Проверяем возможность чтения с безопасной функцией
            content = safe_read_hosts_file()
            if content is None:
                return False
                    
            # Проверяем атрибут "только для чтения"
            if is_file_readonly(HOSTS_PATH):
                log("Файл hosts имеет атрибут 'только для чтения'")
            
            # Проверяем возможность записи (пробуем открыть в режиме добавления)
            try:
                with HOSTS_PATH.open("a", encoding="utf-8-sig") as f:
                    pass
            except PermissionError:
                # Если не можем открыть для записи, но файл НЕ readonly, 
                # значит действительно нет прав администратора
                if not is_file_readonly(HOSTS_PATH):
                    raise
                # Если файл readonly, попробуем снять атрибут
                log("Не удается открыть файл для записи из-за атрибута 'только для чтения'")
            
            return True
            
        except PermissionError:
            log(f"Нет прав доступа к файлу hosts: {HOSTS_PATH}")
            return False
        except FileNotFoundError:
            log(f"Файл hosts не найден: {HOSTS_PATH}")
            return False
        except Exception as e:
            log(f"Ошибка при проверке доступности hosts: {e}")
            return False

    def _no_perm(self):
        """Обработка ошибки прав доступа"""
        self.set_status("Нет прав для изменения файла hosts")
        log("Нет прав для изменения файла hosts")

    def add_proxy_domains(self) -> bool:
        """Добавляет домены в hosts файл"""
        log("🟡 add_proxy_domains начат", "DEBUG")
        
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
        
        # ✅ Вызываем check_and_remove_github_api только один раз в начале
        self.check_and_remove_github_api()
        
        try:
            # Сначала удаляем старые записи
            content = safe_read_hosts_file()
            if content is None:
                return False
            
            # Удаляем старые записи вручную
            lines = content.splitlines(keepends=True)
            domains_to_remove = set(PROXY_DOMAINS.keys())
            
            new_lines = []
            for line in lines:
                if (line.strip() and 
                    not line.lstrip().startswith("#") and 
                    len(line.split()) >= 2 and 
                    line.split()[1] in domains_to_remove):
                    continue
                new_lines.append(line)
            
            # Убираем лишние пустые строки
            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()
            
            # Добавляем новые домены
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append('\n')
            
            for domain, ip in PROXY_DOMAINS.items():
                new_lines.append(f"{ip} {domain}\n")
            
            # Записываем
            if not safe_write_hosts_file("".join(new_lines)):
                return False
            
            self.set_status(f"Файл hosts обновлён: добавлено {len(PROXY_DOMAINS)} записей")
            log(f"✅ Добавлены домены: {list(PROXY_DOMAINS.keys())[:5]}...", "DEBUG")
            return True
            
        except PermissionError:
            log("Ошибка прав доступа в add_proxy_domains", "ERROR")
            self._no_perm()
            return False
        except Exception as e:
            log(f"Ошибка в add_proxy_domains: {e}", "ERROR")
            return False

    def remove_proxy_domains(self) -> bool:
        """Удаляет домены из hosts файла"""
        log("🟡 remove_proxy_domains начат", "DEBUG")
        
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
        
        # ✅ НЕ вызываем check_and_remove_github_api здесь
        
        try:
            content = safe_read_hosts_file()
            if content is None:
                return False
            
            lines = content.splitlines(keepends=True)
            domains = set(PROXY_DOMAINS.keys())
            
            new_lines = []
            removed_count = 0
            
            for line in lines:
                if (line.strip() and 
                    not line.lstrip().startswith("#") and 
                    len(line.split()) >= 2 and 
                    line.split()[1] in domains):
                    removed_count += 1
                    continue
                new_lines.append(line)
            
            # Убираем лишние пустые строки
            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()
            
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            
            if not safe_write_hosts_file("".join(new_lines)):
                return False
            
            self.set_status(f"Файл hosts обновлён: удалено {removed_count} записей")
            log(f"✅ Удалено {removed_count} доменов", "DEBUG")
            return True
            
        except PermissionError:
            log("Ошибка прав доступа в remove_proxy_domains", "ERROR")
            self._no_perm()
            return False
        except Exception as e:
            log(f"Ошибка в remove_proxy_domains: {e}", "ERROR")
            return False
    
    def apply_selected_domains(self, selected_domains):
        """Применяет выбранные домены к файлу hosts"""
        log(f"🟡 apply_selected_domains начат: {len(selected_domains)} доменов", "DEBUG")
        
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
        
        # Создаем временный словарь только с выбранными доменами
        selected_proxy_domains = {
            domain: ip for domain, ip in PROXY_DOMAINS.items() 
            if domain in selected_domains
        }
        
        if not selected_proxy_domains:
            log("Нет выбранных доменов, удаляем все", "DEBUG")
            return self.remove_proxy_domains()
        
        try:
            # Читаем текущее содержимое
            content = safe_read_hosts_file()
            if content is None:
                self.set_status("Не удалось прочитать файл hosts")
                return False
            
            # Удаляем старые записи ВРУЧНУЮ
            lines = content.splitlines(keepends=True)
            domains_to_remove = set(PROXY_DOMAINS.keys())
            
            new_lines = []
            for line in lines:
                if (line.strip() and 
                    not line.lstrip().startswith("#") and 
                    len(line.split()) >= 2 and 
                    line.split()[1] in domains_to_remove):
                    continue
                new_lines.append(line)
            
            # Убираем лишние пустые строки в конце
            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()
            
            # Добавляем выбранные домены
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            
            new_lines.append('\n')  # Разделитель
            
            for domain, ip in selected_proxy_domains.items():
                new_lines.append(f"{ip} {domain}\n")
            
            # Записываем результат
            final_content = "".join(new_lines)
            
            if not safe_write_hosts_file(final_content):
                self.set_status("Не удалось записать файл hosts")
                return False
            
            count = len(selected_proxy_domains)
            self.set_status(f"Файл hosts обновлён: добавлено {count} записей")
            log(f"✅ Добавлены выбранные домены: {list(selected_proxy_domains.keys())}", "DEBUG")
            
            log(f"🟡 apply_selected_domains завершен успешно", "DEBUG")
            return True
            
        except PermissionError:
            log("🟡 Ошибка прав доступа", "DEBUG") 
            self._no_perm()
            return False
        except Exception as e:
            error_msg = f"Ошибка при обновлении hosts: {e}"
            self.set_status(error_msg)
            log(error_msg, "ERROR")
            return False