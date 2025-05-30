# hosts.py

import ctypes
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from .proxy_domains import PROXY_DOMAINS
from .menu import HostsSelectorDialog
from log import log

HOSTS_PATH = Path(r"C:\Windows\System32\drivers\etc\hosts")

def check_hosts_file_name():
    """Проверяет правильность написания имени файла hosts"""
    hosts_dir = Path(r"C:\Windows\System32\drivers\etc")
    
    # Проверяем, есть ли файл с неправильным названием HOSTS
    hosts_upper = hosts_dir / "HOSTS"
    if hosts_upper.exists():
        log("Обнаружен файл HOSTS (с большими буквами) - это неправильно!", level="WARNING")
        return False, "Файл должен называться 'hosts' (с маленькими буквами), а не 'HOSTS'"
    
    # Проверяем правильный файл hosts
    hosts_lower = hosts_dir / "hosts"
    if hosts_lower.exists():
        return True, None
    else:
        return False, "Файл hosts не найден"
    
class HostsManager:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback

    # ------------------------- HostsSelectorDialog -------------------------
    def show_hosts_selector_dialog(self, parent=None):
        """Показывает диалог выбора доменов для hosts"""
        from PyQt6.QtWidgets import QDialog

        current_active = set()
        if self.is_proxy_domains_active():
            # Получаем текущие активные домены из hosts файла
            try:
                content = HOSTS_PATH.read_text(encoding="utf-8")
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
        """Есть ли хотя бы один из наших доменов в hosts?"""
        try:
            content = HOSTS_PATH.read_text(encoding="utf-8")
            return any(domain in content for domain in PROXY_DOMAINS)
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
                    self.show_popup_message("Неправильное название файла", full_error_msg, "warning")
                else:
                    # Файл не найден
                    self.show_popup_message("Ошибка", error_msg, "critical")
                log(error_msg)
                return False
            
            # Проверяем возможность чтения
            HOSTS_PATH.read_text(encoding="utf-8")
            
            # Проверяем возможность записи (пробуем открыть в режиме добавления)
            with HOSTS_PATH.open("a", encoding="utf-8") as f:
                pass
            
            return True
            
        except PermissionError:
            error_msg = f"Нет прав доступа к файлу hosts.\nТребуются права администратора для изменения файла:\n{HOSTS_PATH}"
            log(f"Нет прав доступа к файлу hosts: {HOSTS_PATH}")
            self.show_popup_message("Ошибка доступа", error_msg, "warning")
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

    def apply_selected_domains(self, selected_domains):
        """Применяет выбранные домены к файлу hosts"""
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
        
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
            
            # Добавляем только выбранные домены
            with HOSTS_PATH.open("a", encoding="utf-8", newline="\n") as f:
                f.write(f"\n# Proxy domains added by ZapretGUI\n")
                for domain, ip in selected_proxy_domains.items():
                    f.write(f"{ip} {domain}\n")
            
            count = len(selected_proxy_domains)
            self.set_status(f"Файл hosts обновлён: добавлено {count} записей")
            log(f"Добавлены выбранные домены: {selected_proxy_domains}")
            
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
            
    # ----------------------- модификация -----------------------

    def remove_proxy_domains(self) -> bool:
        """Убираем старые записи."""
        # Проверяем доступность файла hosts перед операцией
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
            
        try:
            lines = HOSTS_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
            domains = set(PROXY_DOMAINS.keys())

            new_lines = [
                line
                for line in lines
                if not (
                    line.strip()
                    and not line.lstrip().startswith("#")
                    and len(line.split()) >= 2
                    and line.split()[1] in domains
                )
            ]

            HOSTS_PATH.write_text("".join(new_lines), encoding="utf-8")
            self.set_status("Файл hosts обновлён: прокси-домены удалены")
            log("Прокси-домены удалены из hosts")
            return True

        except PermissionError:
            self._no_perm()
            return False
        except Exception as e:
            self.set_status(f"Ошибка при обновлении hosts: {e}")
            log(f"Ошибка при обновлении hosts: {e}")
            return False

    def add_proxy_domains(self) -> bool:
        """
        1. Удаляем старые записи (если были).
        2. Добавляем свежие в конец hosts.
        """
        # Проверяем доступность файла hosts перед операцией
        if not self.is_hosts_file_accessible():
            self.set_status("Файл hosts недоступен для изменения")
            return False
            
        if not self.remove_proxy_domains():     # не смогли удалить → дальше смысла нет
            return False

        try:
            with HOSTS_PATH.open("a", encoding="utf-8", newline="\n") as f:
                for domain, ip in PROXY_DOMAINS.items():
                    f.write(f"{ip} {domain}\n")

            self.set_status(f"Файл hosts обновлён: добавлено {len(PROXY_DOMAINS)} записей")
            log(f"Добавлены домены: {PROXY_DOMAINS}")
            return True

        except PermissionError:
            self._no_perm()
            return False
        except Exception as e:
            self.set_status(f"Ошибка при обновлении hosts: {e}")
            log(f"Ошибка при обновлении hosts: {e}")
            return False

    # ------------------------- utils -------------------------

    def _no_perm(self):
        msg = "Ошибка доступа: требуются права администратора"
        self.set_status(msg)
        log(msg)