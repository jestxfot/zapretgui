# hosts.py
import ctypes
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from proxy_domains import PROXY_DOMAINS
from log import log


HOSTS_PATH = Path(r"C:\Windows\System32\drivers\etc\hosts")


class HostsManager:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback

    # ------------------------- сервис -------------------------

    def set_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    def show_popup_message(self, title, message):
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception:
            # резервный вариант – системное окно
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)

    # ------------------------- проверки -------------------------

    def is_proxy_domains_active(self) -> bool:
        """Есть ли хотя бы один из наших доменов в hosts?"""
        try:
            content = HOSTS_PATH.read_text(encoding="utf-8")
            return any(domain in content for domain in PROXY_DOMAINS)
        except Exception as e:
            log(f"Ошибка при проверке hosts: {e}")
            return False

    # ----------------------- модификация -----------------------

    def remove_proxy_domains(self) -> bool:
        """Убираем старые записи."""
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