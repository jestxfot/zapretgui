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
    
    # Если ни того, ни другого нет
    return False, "Файл hosts не найден"

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
    
    # Список кодировок для попытки чтения
    encodings = ['utf-8', 'cp1251', 'cp866', 'latin1']
    
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
        log(f"Критическая ошибка при чтении файла hosts: {e}")
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

    def show_popup_message(self, title, message, icon_type="information"):
        """
        Показывает красиво оформленное сообщение с иконкой и стилизацией.
        
        Args:
            title: Заголовок окна
            message: Текст сообщения  
            icon_type: Тип иконки ("information", "warning", "critical", "question")
        """
        try:
            msg_box = QMessageBox()
            
            # Устанавливаем иконку в зависимости от типа
            icon_map = {
                "information": QMessageBox.Icon.Information,
                "warning": QMessageBox.Icon.Warning,
                "critical": QMessageBox.Icon.Critical,
                "question": QMessageBox.Icon.Question
            }
            msg_box.setIcon(icon_map.get(icon_type, QMessageBox.Icon.Information))
            
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            msg_box.exec()
            
        except Exception:
            # резервный вариант – системное окно
            # Определяем тип иконки для системного MessageBox
            system_icon_map = {
                "information": 0x40,  # MB_ICONINFORMATION
                "warning": 0x30,      # MB_ICONWARNING  
                "critical": 0x10,     # MB_ICONERROR
                "question": 0x20      # MB_ICONQUESTION
            }
            icon_flag = system_icon_map.get(icon_type, 0x40)
            ctypes.windll.user32.MessageBoxW(0, message, title, icon_flag)

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
            # Сначала проверяем правильность написания имени файла
            is_correct, error_msg = check_hosts_file_name()
            if not is_correct:
                if "HOSTS" in error_msg:
                    # Специальное сообщение для неправильного написания
                    full_error_msg = (
                        f"Обнаружен файл с неправильным названием!\n\n"
                        f"Файл должен называться 'hosts' (с маленькими буквами),\n"
                        f"а не 'HOSTS' (с большими буквами).\n\n"
                        f"Переименуйте файл 'HOSTS' в 'hosts' и попробуйте снова."
                    )
                    self.show_popup_message("Неправильное название файла", full_error_msg, "⚠ WARNING")
                elif "некорректные символы" in error_msg:
                    # Специальное сообщение для проблем с кодировкой
                    full_error_msg = (
                        f"Файл hosts содержит некорректные символы!\n\n"
                        f"Возможные причины:\n"
                        f"• Файл поврежден\n"
                        f"• Файл содержит символы в неподдерживаемой кодировке\n"
                        f"• Файл создан другой программой с неправильной кодировкой\n\n"
                        f"Рекомендуется пересоздать файл hosts или очистить его содержимое."
                    )
                    self.show_popup_message("Проблема с кодировкой файла", full_error_msg, "⚠ WARNING")
                else:
                    # Файл не найден
                    self.show_popup_message("Ошибка", error_msg, "critical")
                log(error_msg)
                return False
            
            # Проверяем возможность чтения с безопасной функцией
            content = safe_read_hosts_file()
            if content is None:
                return False
            
            # Проверяем атрибут "только для чтения"
            if is_file_readonly(HOSTS_PATH):
                log("Файл hosts имеет атрибут 'только для чтения'")
                # Показываем предупреждение пользователю
                warning_msg = (
                    f"Файл hosts имеет атрибут 'только для чтения'.\n\n"
                    f"Программа попытается автоматически снять этот атрибут\n"
                    f"при сохранении изменений.\n\n"
                    f"Если это не поможет, снимите атрибут вручную:\n"
                    f"1. Откройте свойства файла hosts\n"
                    f"2. Снимите галочку 'Только для чтения'"
                )
                self.show_popup_message("Файл только для чтения", warning_msg, "warning")
            
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
            error_msg = f"Нет прав доступа к файлу hosts.\nТребуются права администратора для изменения файла:\n{HOSTS_PATH}"
            log(f"Нет прав доступа к файлу hosts: {HOSTS_PATH}")
            self.show_popup_message("Ошибка доступа", error_msg, "⚠ WARNING")
            return False
        except FileNotFoundError:
            error_msg = f"Файл hosts не найден:\n{HOSTS_PATH}"
            log(f"Файл hosts не найден: {HOSTS_PATH}")
            self.show_popup_message("Файл не найден", error_msg, "critical")
            return False
        except Exception as e:
            error_msg = f"Ошибка при проверке доступности файла hosts:\n{e}"
            log(f"Ошибка при проверке доступности hosts: {e}")
            self.show_popup_message("Ошибка", error_msg, "critical")
            return False

    def _no_perm(self):
        """Обработка ошибки прав доступа"""
        error_msg = (
            f"Нет прав для изменения файла hosts.\n\n"
            f"Возможные причины:\n"
            f"• Программа запущена без прав администратора\n"
            f"• Файл hosts имеет атрибут 'только для чтения'\n"
            f"• Антивирус блокирует доступ к файлу\n\n"
            f"Решения:\n"
            f"1. Запустите программу от имени администратора\n"
            f"2. Проверьте свойства файла hosts и снимите галочку 'Только для чтения'\n"
            f"3. Временно отключите антивирус"
        )
        self.set_status("Нет прав для изменения файла hosts")
        self.show_popup_message("Ошибка доступа", error_msg, "warning")
        log("Нет прав для изменения файла hosts")

    def add_proxy_domains(self) -> bool:
        """
        1. Удаляем старые записи (если были).
        2. Проверяем и удаляем api.github.com (если есть).
        3. Добавляем свежие в конец hosts.
        """
        # Проверяем доступность файла hosts перед операцией
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
        
        # 🆕 Проверяем и удаляем api.github.com перед добавлением доменов
        self.check_and_remove_github_api()
            
        if not self.remove_proxy_domains():     # не смогли удалить → дальше смысла нет
            return False

        try:
            # Читаем текущее содержимое
            content = safe_read_hosts_file()
            if content is None:
                self.set_status("Не удалось прочитать файл hosts")
                return False
            
            # Добавляем наши домены
            new_content = content.rstrip()  # убираем лишние пробелы в конце
            if new_content:  # если файл не пустой
                new_content += '\n\n'  # добавляем разделитель
            
            for domain, ip in PROXY_DOMAINS.items():
                new_content += f"{ip} {domain}\n"

            if not safe_write_hosts_file(new_content):
                self.set_status("Не удалось записать файл hosts")
                return False

            self.set_status(f"Файл hosts обновлён: добавлено {len(PROXY_DOMAINS)} записей")
            log(f"Добавлены домены: {PROXY_DOMAINS}")
            
            # Выводим содержимое файла hosts в лог после добавления
            self._log_hosts_content("после добавления всех доменов")
            
            return True

        except PermissionError:
            self._no_perm()
            return False
        except Exception as e:
            self.set_status(f"Ошибка при обновлении hosts: {e}")
            log(f"Ошибка при обновлении hosts: {e}")
            return False

    def apply_selected_domains(self, selected_domains):
        """Применяет выбранные домены к файлу hosts"""
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
        
        # 🆕 Проверяем и удаляем api.github.com перед применением доменов
        self.check_and_remove_github_api()
        
        # Создаем временный словарь только с выбранными доменами
        selected_proxy_domains = {
            domain: ip for domain, ip in PROXY_DOMAINS.items() 
            if domain in selected_domains
        }
        
        if not selected_proxy_domains:
            # Если ничего не выбрано, просто удаляем все домены
            return self.remove_proxy_domains()
        
        try:
            # Удаляем все старые записи
            if not self.remove_proxy_domains():
                return False
            
            # Читаем текущее содержимое
            content = safe_read_hosts_file()
            if content is None:
                self.set_status("Не удалось прочитать файл hosts")
                return False
            
            # Добавляем только выбранные домены
            new_content = content.rstrip()  # убираем лишние пробелы в конце
            if new_content:  # если файл не пустой
                new_content += '\n\n'  # добавляем разделитель

            for domain, ip in selected_proxy_domains.items():
                new_content += f"{ip} {domain}\n"

            if not safe_write_hosts_file(new_content):
                self.set_status("Не удалось записать файл hosts")
                return False
            
            count = len(selected_proxy_domains)
            self.set_status(f"Файл hosts обновлён: добавлено {count} записей")
            log(f"Добавлены выбранные домены: {selected_proxy_domains}")
            
            # Выводим содержимое файла hosts в лог после добавления выбранных доменов
            self._log_hosts_content(f"после добавления выбранных доменов ({count} записей)")
            
            # Показываем сообщение об успехе
            self.show_popup_message(
                "Успех", 
                f"Файл hosts успешно обновлён.\nДобавлено доменов: {count}", 
                "information"
            )
            return True
            
        except PermissionError:
            self._no_perm()
            return False
        except Exception as e:
            error_msg = f"Ошибка при обновлении hosts: {e}"
            self.set_status(error_msg)
            log(error_msg)
            self.show_popup_message("Ошибка", error_msg, "critical")
            return False
    
    def remove_proxy_domains(self) -> bool:
        """Убираем старые записи и лишние пустые строки."""
        # Проверяем доступность файла hosts перед операцией
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
        
        # 🆕 Проверяем и удаляем api.github.com перед удалением доменов
        self.check_and_remove_github_api()
            
        try:
            content = safe_read_hosts_file()
            if content is None:
                self.set_status("Не удалось прочитать файл hosts")
                return False
                
            lines = content.splitlines(keepends=True)
            domains = set(PROXY_DOMAINS.keys())

            new_lines = []
            for line in lines:
                # Пропускаем наши записи доменов
                if (line.strip() and 
                    not line.lstrip().startswith("#") and 
                    len(line.split()) >= 2 and 
                    line.split()[1] in domains):
                    continue
                
                # Добавляем строку
                new_lines.append(line)

            # Убираем лишние пустые строки в конце файла
            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()
            
            # Оставляем одну пустую строку в конце, если файл не пустой
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            elif new_lines:
                new_lines.append('\n')

            if not safe_write_hosts_file("".join(new_lines)):
                self.set_status("Не удалось записать файл hosts")
                return False
                
            self.set_status("Файл hosts обновлён: прокси-домены удалены")
            log("Прокси-домены удалены из hosts")
            
            # Выводим содержимое файла hosts в лог после удаления
            self._log_hosts_content("после удаления доменов")
            
            return True

        except PermissionError:
            self._no_perm()
            return False
        except Exception as e:
            self.set_status(f"Ошибка при обновлении hosts: {e}")
            log(f"Ошибка при обновлении hosts: {e}")
            return False

    def _log_hosts_content(self, operation_description):
        """Выводит содержимое файла hosts в лог"""
        try:
            content = safe_read_hosts_file()
            if content is None:
                log(f"Не удалось прочитать файл hosts для вывода в лог {operation_description}")
                return
                
            log(f"Содержимое файла hosts {operation_description}:")
            log("=" * 50)
            
            # Выводим содержимое с нумерацией строк для удобства
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                log(f"{i:3d}: {line}")
            
            log("=" * 50)
            log(f"Всего строк в файле hosts: {len(lines)}")
            
            # Подсчитываем количество наших доменов
            our_domains_count = 0
            for line in lines:
                line = line.strip()
                if (line and not line.startswith("#") and 
                    len(line.split()) >= 2 and 
                    line.split()[1] in PROXY_DOMAINS):
                    our_domains_count += 1
            
            log(f"Количество наших прокси-доменов в файле: {our_domains_count}")
            
        except Exception as e:
            log(f"Ошибка при чтении файла hosts для вывода в лог: {e}")