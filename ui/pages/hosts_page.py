# ui/pages/hosts_page.py
"""Страница управления Hosts файлом - разблокировка сервисов"""

import os
import re
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QComboBox
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from log import log
from utils import get_system32_path


FLUENT_COMBO_STYLE = """
QComboBox {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    color: #ffffff;
    padding: 6px 28px 6px 12px;
    font-size: 12px;
    font-weight: 600;
    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
}
QComboBox:hover {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
}
QComboBox:focus {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid #60cdff;
}
QComboBox:on {
    background: rgba(96, 205, 255, 0.12);
    border: 1px solid rgba(96, 205, 255, 0.35);
}
QComboBox::drop-down {
    border: none;
    width: 26px;
    subcontrol-origin: padding;
    subcontrol-position: right center;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid rgba(255, 255, 255, 0.65);
    margin-right: 10px;
}
QComboBox::down-arrow:on {
    border-top-color: #60cdff;
}
QComboBox QAbstractItemView,
QComboBox QListView {
    background-color: #373737;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item,
QComboBox QListView::item {
    background: transparent;
    color: #ffffff;
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 24px;
}
QComboBox QAbstractItemView::item:hover,
QComboBox QListView::item:hover {
    background: rgba(255, 255, 255, 0.10);
}
QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:selected {
    background: rgba(96, 205, 255, 0.20);
    color: #ffffff;
}
"""

_DNS_PROFILE_IP_SUFFIX = re.compile(r"\s*\(\s*(?:\d{1,3}\.){3}\d{1,3}\s*\)\s*$")


def _format_dns_profile_label(profile_name: str) -> str:
    label = (profile_name or "").strip()
    if not label:
        return ""
    return _DNS_PROFILE_IP_SUFFIX.sub("", label).strip()

# Импортируем сервисы и домены
try:
    from hosts.proxy_domains import (
        QUICK_SERVICES,
        get_dns_profiles,
        get_all_services,
        get_service_has_geohide_ips,
        get_service_available_dns_profiles,
        get_service_domains,
        load_user_hosts_selection,
        save_user_hosts_selection,
    )
except ImportError:
    QUICK_SERVICES = []
    def get_dns_profiles(): return []
    def get_all_services(): return []
    def get_service_has_geohide_ips(s): return False
    def get_service_available_dns_profiles(s): return []
    def get_service_domains(s): return {}
    def load_user_hosts_selection(): return {}
    def save_user_hosts_selection(*args, **kwargs): return False



class HostsWorker(QObject):
    """Воркер для асинхронных операций с hosts файлом"""
    finished = pyqtSignal(bool, str)
    
    def __init__(self, hosts_manager, operation, payload=None):
        super().__init__()
        self.hosts_manager = hosts_manager
        self.operation = operation
        self.payload = payload
        
    def run(self):
        try:
            success = False
            message = ""
            
            if self.operation == 'apply_selection':
                service_dns = self.payload or {}
                success = self.hosts_manager.apply_service_dns_selections(service_dns)
                message = "Применено" if success else "Ошибка"

            elif self.operation == 'clear_all':
                success = self.hosts_manager.clear_hosts_file()
                message = "Hosts очищен" if success else "Ошибка"
                        
            elif self.operation == 'adobe_add':
                success = self.hosts_manager.add_adobe_domains()
                message = "Adobe заблокирован" if success else "Ошибка"
                
            elif self.operation == 'adobe_remove':
                success = self.hosts_manager.remove_adobe_domains()
                message = "Adobe разблокирован" if success else "Ошибка"
            
            self.finished.emit(success, message)
            
        except Exception as e:
            log(f"Ошибка в HostsWorker: {e}", "ERROR")
            self.finished.emit(False, str(e))


class HostsPage(BasePage):
    """Страница управления Hosts файлом"""
    
    def __init__(self, parent=None):
        super().__init__("Hosts", "Управление разблокировкой сервисов через hosts файл", parent)
        
        self.hosts_manager = None
        self.service_combos = {}
        self.service_icon_labels = {}
        self.service_icon_base_colors = {}
        self._worker = None
        self._thread = None
        self._applying = False
        self._active_domains_cache = None  # Кеш активных доменов
        self._last_error = None  # Последняя ошибка
        self.error_panel = None  # Панель ошибок
        self._service_dns_selection = load_user_hosts_selection()
        
        self._init_hosts_manager()
        self._build_ui()
        
    def _init_hosts_manager(self):
        try:
            from hosts.hosts import HostsManager
            self.hosts_manager = HostsManager(status_callback=lambda m: log(f"Hosts: {m}", "INFO"))
        except Exception as e:
            log(f"Ошибка инициализации HostsManager: {e}", "ERROR")
    
    def _invalidate_cache(self):
        """Сбрасывает кеш активных доменов"""
        self._active_domains_cache = None
            
    def _get_active_domains(self) -> set:
        """Возвращает активные домены с кешированием (чтобы не читать hosts 28 раз)"""
        if self._active_domains_cache is not None:
            return self._active_domains_cache
        if self.hosts_manager:
            try:
                # Пробуем прочитать hosts файл напрямую для проверки доступа
                hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
                with open(hosts_path, 'r', encoding='utf-8') as f:
                    f.read()
                self._hide_error()
                self._active_domains_cache = self.hosts_manager.get_active_domains()
                return self._active_domains_cache
            except PermissionError:
                hosts_path = os.path.join(get_system32_path(), "drivers", "etc", "hosts")
                self._show_error(
                    "Нет доступа к файлу hosts. Запустите программу от имени администратора.\n"
                    f"Путь: {hosts_path}"
                )
                return set()
            except Exception as e:
                self._show_error(f"Ошибка чтения hosts: {e}")
                return set()
        return set()
    
    def _build_ui(self):
        # Панель ошибок (скрыта по умолчанию)
        self._build_error_panel()
        
        # Проверяем доступ сразу при загрузке
        self._check_hosts_access()
        
        # Информационная заметка
        self._build_info_note()
        self.add_spacing(4)
        
        # Предупреждение о браузере
        self._build_browser_warning()
        self.add_spacing(6)
        
        # Статус
        self._build_status_section()
        self.add_spacing(6)
        
        # Сервисы (выбор DNS-профиля по каждому сервису)
        self._build_services_selectors()
        self.add_spacing(6)
        
        # Adobe
        self._build_adobe_section()
        self.add_spacing(6)
        
        # Кнопки
        self._build_actions()
        
    def _build_error_panel(self):
        """Панель для отображения ошибок доступа к hosts"""
        self.error_panel = QWidget()
        error_layout = QVBoxLayout(self.error_panel)
        error_layout.setContentsMargins(12, 10, 12, 10)
        error_layout.setSpacing(8)

        # Верхняя строка с иконкой, текстом и кнопкой закрытия
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Иконка ошибки
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.exclamation-triangle', color='#ff5252').pixmap(20, 20))
        top_row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # Текст ошибки
        self.error_text = QLabel()
        self.error_text.setWordWrap(True)
        self.error_text.setStyleSheet("color: #ff5252; font-size: 12px; background: transparent;")
        top_row.addWidget(self.error_text, 1)

        # Кнопка закрыть
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon('fa5s.times', color='#808080'))
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 10px; }
        """)
        close_btn.clicked.connect(lambda: self.error_panel.hide())
        top_row.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

        error_layout.addLayout(top_row)

        # Кнопка восстановления прав
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(30, 0, 0, 0)  # Отступ слева под иконку

        self.restore_btn = QPushButton(" Восстановить права доступа")
        self.restore_btn.setIcon(qta.icon('fa5s.wrench', color='white'))
        self.restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_btn.setFixedHeight(28)
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 152, 0, 0.8);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 152, 0, 1);
            }
            QPushButton:disabled {
                background-color: rgba(255, 152, 0, 0.4);
            }
        """)
        self.restore_btn.clicked.connect(self._restore_hosts_permissions)
        btn_row.addWidget(self.restore_btn)
        btn_row.addStretch()

        error_layout.addLayout(btn_row)

        self.error_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 82, 82, 0.15);
                border: 1px solid rgba(255, 82, 82, 0.4);
                border-radius: 8px;
            }
        """)

        self.error_panel.hide()  # Скрыта по умолчанию
        self.add_widget(self.error_panel)
        
    def _show_error(self, message: str):
        """Показывает ошибку на панели"""
        self._last_error = message
        self.error_text.setText(message)
        self.error_panel.show()

    def _hide_error(self):
        """Скрывает панель ошибок"""
        self._last_error = None
        self.error_panel.hide()

    def _restore_hosts_permissions(self):
        """Восстанавливает права доступа к файлу hosts"""
        self.restore_btn.setEnabled(False)
        self.restore_btn.setText(" Восстановление...")

        try:
            from hosts.hosts import restore_hosts_permissions
            success, message = restore_hosts_permissions()

            if success:
                self._hide_error()
                self._invalidate_cache()
                self._update_ui()
                QMessageBox.information(
                    self, "Успех",
                    "Права доступа к файлу hosts успешно восстановлены!"
                )
            else:
                self._show_error(message)
                QMessageBox.warning(
                    self, "Ошибка",
                    f"Не удалось восстановить права:\n{message}\n\n"
                    "Попробуйте временно отключить защиту файла hosts "
                    "в настройках антивируса (Kaspersky, Dr.Web и т.д.)"
                )
        except Exception as e:
            log(f"Ошибка при восстановлении прав: {e}", "ERROR")
            self._show_error(f"Ошибка: {e}")
        finally:
            self.restore_btn.setEnabled(True)
            self.restore_btn.setText(" Восстановить права доступа")
    
    def _check_hosts_access(self):
        """Проверяет доступ к hosts файлу при загрузке страницы"""
        try:
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            with open(hosts_path, 'r', encoding='utf-8') as f:
                f.read()
            self._hide_error()
        except PermissionError:
            self._show_error(
                "Нет доступа к файлу hosts. Скорее всего антивирус заблокировал его для записи."
            )
        except Exception as e:
            self._show_error(f"Ошибка чтения hosts: {e}")
        
    def _build_info_note(self):
        """Информационная заметка о том, зачем нужен hosts"""
        info_card = SettingsCard()
        
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)
        
        # Иконка лампочки
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.lightbulb', color='#ffc107').pixmap(20, 20))
        icon_label.setFixedSize(24, 24)
        info_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        
        # Текст пояснения
        info_text = QLabel(
            "Некоторые сервисы (ChatGPT, Spotify и др.) сами блокируют доступ из России — "
            "это не блокировка РКН. Решается не через Zapret, а через проксирование: "
            "домены направляются через отдельный прокси-сервер в файле hosts."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("""
            color: rgba(255, 255, 255, 0.75);
            font-size: 11px;
            line-height: 1.4;
        """)
        info_layout.addWidget(info_text, 1)
        
        info_card.add_layout(info_layout)
        self.add_widget(info_card)
        
    def _build_browser_warning(self):
        """Предупреждение о необходимости перезапуска браузера"""
        warning_layout = QHBoxLayout()
        warning_layout.setContentsMargins(12, 4, 12, 4)
        warning_layout.setSpacing(10)
        
        # Иконка предупреждения
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.sync-alt', color='#ff9800').pixmap(16, 16))
        warning_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Текст предупреждения
        warning_text = QLabel(
            "После добавления или удаления доменов необходимо перезапустить браузер, "
            "чтобы изменения вступили в силу."
        )
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet("color: rgba(255, 152, 0, 0.85); font-size: 11px; background: transparent;")
        warning_layout.addWidget(warning_text, 1)
        
        # Простой контейнер без фона
        warning_widget = QWidget()
        warning_widget.setLayout(warning_layout)
        warning_widget.setStyleSheet("background: transparent;")
        
        self.add_widget(warning_widget)
        
    def _build_status_section(self):
        status_card = SettingsCard()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)
        
        active = self._get_active_domains()
        
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {'#6ccb5f' if active else '#888'}; font-size: 12px;")
        status_layout.addWidget(self.status_dot)
        
        self.status_label = QLabel(f"Активно {len(active)} доменов" if active else "Нет активных")
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 12px;")
        status_layout.addWidget(self.status_label, 1)
        
        status_card.add_layout(status_layout)
        self.add_widget(status_card)

    def _configure_fluent_combo(self, combo: QComboBox) -> None:
        combo.setStyleSheet(FLUENT_COMBO_STYLE)
        combo.setFixedHeight(32)
        combo.setCursor(Qt.CursorShape.PointingHandCursor)

    def _get_dns_profile_families(self) -> tuple[str | None, list[str]]:
        profiles = list(get_dns_profiles() or [])

        zapret = next((p for p in profiles if "zapret" in (p or "").strip().lower()), None)

        def is_direct(profile_name: str) -> bool:
            s = (profile_name or "").strip().lower()
            return (
                "без прокси" in s
                or "из файла" in s
                or "no proxy" in s
                or "direct" in s
            )

        direct = next((p for p in profiles if is_direct(p)), None)
        geohide_candidates = [p for p in profiles if p and p != zapret and p != direct]
        return zapret, geohide_candidates

    def _bulk_apply_dns_profile(self, service_names: list[str], profile_name: str) -> None:
        if self._applying:
            return

        changed = False
        for service_name in service_names:
            combo = self.service_combos.get(service_name)
            if not combo:
                continue

            available = list(get_service_available_dns_profiles(service_name) or [])

            target_profile = profile_name if profile_name in available else ""
            target_idx = combo.findData(target_profile) if target_profile else 0
            if target_idx < 0:
                target_idx = 0

            if combo.currentIndex() != target_idx:
                combo.blockSignals(True)
                combo.setCurrentIndex(target_idx)
                combo.blockSignals(False)
                changed = True

            if not target_profile:
                if service_name in self._service_dns_selection:
                    self._service_dns_selection.pop(service_name, None)
                    changed = True
            else:
                if self._service_dns_selection.get(service_name) != target_profile:
                    self._service_dns_selection[service_name] = target_profile
                    changed = True

            self._update_profile_row_visual(service_name)

        if not changed:
            return

        save_user_hosts_selection(self._service_dns_selection)
        self._apply_current_selection()
	        
    def _build_services_selectors(self):
        OFF_LABEL = "Откл."

        # Карта иконок/цветов по сервису (если есть в QUICK_SERVICES)
        ui_map = {name: (icon_name, icon_color) for icon_name, name, icon_color in QUICK_SERVICES}

        # Все сервисы (с выбором DNS)
        all_services = list(get_all_services() or [])
        ordered_services: list[str] = []
        for _icon, name, _color in QUICK_SERVICES:
            if name in all_services and name not in ordered_services:
                ordered_services.append(name)
        for name in all_services:
            if name not in ordered_services:
                ordered_services.append(name)

        def is_ai_service(name: str) -> bool:
            s = (name or "").strip().lower()
            return any(
                k in s
                for k in (
                    "chatgpt",
                    "openai",
                    "gemini",
                    "claude",
                    "copilot",
                    "grok",
                    "manus",
                )
            )

        no_geohide: list[str] = []
        ai: list[str] = []
        other: list[str] = []
        for service_name in ordered_services:
            if not get_service_has_geohide_ips(service_name):
                no_geohide.append(service_name)
            elif is_ai_service(service_name):
                ai.append(service_name)
            else:
                other.append(service_name)

        self.add_section_title("Сервисы")

        self._building_services_ui = True
        try:
            def add_group(title: str, names: list[str]) -> None:
                if not names:
                    return

                card = SettingsCard()

                header = QHBoxLayout()
                header.setContentsMargins(0, 0, 0, 0)
                header.setSpacing(10)

                title_label = QLabel(title)
                title_label.setStyleSheet(
                    """
                    QLabel {
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                    }
                    """
                )
                header.addWidget(title_label, 1, Qt.AlignmentFlag.AlignVCenter)

                group_combo = QComboBox()
                self._configure_fluent_combo(group_combo)
                group_combo.setMinimumWidth(180)
                group_combo.addItem("Для категории…", None)
                zapret_profile, geohide_profiles = self._get_dns_profile_families()
                if zapret_profile:
                    group_combo.addItem(
                        f"Все → {_format_dns_profile_label(zapret_profile)}",
                        zapret_profile,
                    )
                for p in geohide_profiles:
                    group_combo.addItem(
                        f"GeoHide → {_format_dns_profile_label(p)}",
                        p,
                    )

                def on_group_combo_changed(_index: int, c=group_combo, n=tuple(names)) -> None:
                    profile_name = c.currentData()
                    if isinstance(profile_name, str) and profile_name.strip():
                        self._bulk_apply_dns_profile(list(n), profile_name.strip())
                    c.blockSignals(True)
                    c.setCurrentIndex(0)
                    c.blockSignals(False)

                group_combo.currentIndexChanged.connect(on_group_combo_changed)
                header.addWidget(group_combo, 0, Qt.AlignmentFlag.AlignVCenter)

                card.add_layout(header)

                for service_name in names:
                    row = QHBoxLayout()
                    row.setContentsMargins(0, 0, 0, 0)
                    row.setSpacing(10)

                    icon_name, icon_color = ui_map.get(service_name, ("fa5s.globe", "#60cdff"))

                    icon_label = QLabel()
                    icon_label.setFixedSize(20, 20)
                    row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

                    name_label = QLabel(service_name)
                    name_label.setStyleSheet("color: #fff; font-size: 12px; font-weight: 600;")
                    row.addWidget(name_label, 1, Qt.AlignmentFlag.AlignVCenter)

                    combo = QComboBox()
                    self._configure_fluent_combo(combo)
                    combo.setMinimumWidth(220)

                    # Откл. + доступные профили
                    available = get_service_available_dns_profiles(service_name) or []
                    combo.addItem(OFF_LABEL, None)
                    for profile_name in available:
                        combo.addItem(_format_dns_profile_label(profile_name), profile_name)

                    saved = (self._service_dns_selection or {}).get(service_name, "")
                    saved_idx = combo.findData(saved)
                    if saved_idx >= 0:
                        combo.setCurrentIndex(saved_idx)
                    else:
                        combo.setCurrentIndex(0)
                        self._service_dns_selection.pop(service_name, None)

                    combo.currentIndexChanged.connect(
                        lambda _idx, s=service_name, c=combo: self._on_profile_changed(s, c.currentData())
                    )
                    row.addWidget(combo, 0, Qt.AlignmentFlag.AlignVCenter)

                    card.add_layout(row)

                    self.service_combos[service_name] = combo
                    self.service_icon_labels[service_name] = icon_label
                    self.service_icon_base_colors[service_name] = icon_color

                    self._update_profile_row_visual(service_name)

                self.add_widget(card)

            add_group("Без прокси IP", no_geohide)
            add_group("ИИ", ai)
            add_group("Остальные", other)
        finally:
            self._building_services_ui = False
        
    def _build_adobe_section(self):
        self.add_section_title("Дополнительно")
        
        adobe_card = SettingsCard()
        
        # Описание для чего нужна блокировка
        desc_label = QLabel("⚠️ Блокирует серверы проверки активации Adobe. Включите, если у вас установлена пиратская версия.")
        desc_label.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 10px; margin-bottom: 6px;")
        desc_label.setWordWrap(True)
        adobe_card.add_widget(desc_label)
        
        adobe_layout = QHBoxLayout()
        adobe_layout.setContentsMargins(0, 0, 0, 0)
        adobe_layout.setSpacing(8)
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.puzzle-piece', color='#ff0000').pixmap(20, 20))
        adobe_layout.addWidget(icon_label)
        
        title = QLabel("Блокировка Adobe")
        title.setStyleSheet("color: #fff; font-size: 12px; font-weight: 600;")
        adobe_layout.addWidget(title, 1)
        
        is_adobe_active = self.hosts_manager.is_adobe_domains_active() if self.hosts_manager else False
        
        self.adobe_status = QLabel("Активно" if is_adobe_active else "Откл.")
        self.adobe_status.setStyleSheet(f"color: {'#6ccb5f' if is_adobe_active else 'rgba(255,255,255,0.5)'}; font-size: 11px;")
        adobe_layout.addWidget(self.adobe_status)
        
        self.adobe_btn = QPushButton("Откл." if is_adobe_active else "Вкл.")
        self.adobe_btn.setFixedSize(50, 24)
        self.adobe_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adobe_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#dc3545' if is_adobe_active else '#28a745'};
                color: white; border: none; border-radius: 4px; font-size: 10px;
            }}
            QPushButton:hover {{ background-color: {'#c82333' if is_adobe_active else '#218838'}; }}
        """)
        self.adobe_btn.clicked.connect(self._toggle_adobe)
        adobe_layout.addWidget(self.adobe_btn)
        
        adobe_card.add_layout(adobe_layout)
        self.add_widget(adobe_card)
        
    def _build_actions(self):
        actions_card = SettingsCard()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        
        # Очистить
        clear_btn = QPushButton("Очистить")
        clear_btn.setIcon(qta.icon('fa5s.trash-alt', color='white'))
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 53, 69, 0.7);
                color: white; border: none;
                border-radius: 4px; font-size: 11px; padding: 4px 10px;
            }
            QPushButton:hover { background-color: rgba(220, 53, 69, 0.9); }
        """)
        clear_btn.clicked.connect(self._clear_hosts)
        actions_layout.addWidget(clear_btn)
        
        actions_layout.addStretch()
        
        # Открыть файл
        open_btn = QPushButton(" Открыть")
        open_btn.setIcon(qta.icon('fa5s.external-link-alt', color='white'))
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.08);
                color: #fff; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; font-size: 11px; padding: 6px 10px;
            }
            QPushButton:hover { background-color: rgba(255,255,255,0.12); }
        """)
        open_btn.clicked.connect(self._open_hosts_file)
        actions_layout.addWidget(open_btn)
        
        actions_card.add_layout(actions_layout)
        self.add_widget(actions_card)
        
    # ═══════════════════════════════════════════════════════════════
    # ОБРАБОТЧИКИ
    # ═══════════════════════════════════════════════════════════════
    
    def _on_profile_changed(self, service_name: str, selected_profile: object):
        if getattr(self, "_building_services_ui", False):
            self._update_profile_row_visual(service_name)
            return
        if self._applying:
            self._update_profile_row_visual(service_name)
            return

        profile_name = selected_profile.strip() if isinstance(selected_profile, str) else ""
        if not profile_name:
            self._service_dns_selection.pop(service_name, None)
        else:
            self._service_dns_selection[service_name] = profile_name

        save_user_hosts_selection(self._service_dns_selection)
        self._update_profile_row_visual(service_name)
        self._apply_current_selection()

    def _update_profile_row_visual(self, service_name: str):
        OFF_LABEL = "Откл."
        combo = self.service_combos.get(service_name)
        icon_label = self.service_icon_labels.get(service_name)
        base_color = self.service_icon_base_colors.get(service_name, "#60cdff")
        if not combo or not icon_label:
            return

        selected = combo.currentText().strip()
        enabled = bool(selected) and selected != OFF_LABEL
        color = base_color if enabled else "#808080"
        icon_name = None
        for i_name, n, _c in QUICK_SERVICES:
            if n == service_name:
                icon_name = i_name
                break
        try:
            icon = qta.icon(icon_name or "fa5s.globe", color=color)
        except Exception:
            icon = qta.icon("fa5s.globe", color=color)
        icon_label.setPixmap(icon.pixmap(18, 18))

    def _apply_current_selection(self):
        if self._applying:
            return
        self._run_operation('apply_selection', dict(self._service_dns_selection))
        
    def _clear_hosts(self):
        """Очищает hosts"""
        if self._applying:
            return
            
        reply = QMessageBox.question(
            self, "Очистка hosts",
            "Удалить все записи из hosts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_operation('clear_all')
            
    def _open_hosts_file(self):
        try:
            import ctypes
            import os
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            if os.path.exists(hosts_path):
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "notepad.exe", hosts_path, None, 1)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть: {e}")
            
    def _toggle_adobe(self):
        if self._applying:
            return
        is_active = self.hosts_manager.is_adobe_domains_active() if self.hosts_manager else False
        self._run_operation('adobe_remove' if is_active else 'adobe_add')
        
    def _run_operation(self, operation: str, payload=None):
        if not self.hosts_manager or self._applying:
            return
            
        self._applying = True
        
        self._worker = HostsWorker(self.hosts_manager, operation, payload)
        self._thread = QThread()
        
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_operation_complete)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self._thread.start()
        
    def _on_operation_complete(self, success: bool, message: str):
        self._applying = False
        
        # Сбрасываем кеш и обновляем UI
        self._invalidate_cache()
        self._update_ui()
        
        if success:
            self._hide_error()
        else:
            # Показываем ошибку на панели
            if "Permission denied" in message or "Access" in message:
                self._show_error(
                    "Нет доступа к файлу hosts. Запустите программу от имени администратора."
                )
            else:
                self._show_error(f"Ошибка: {message}")
            
    def _update_ui(self):
        """Обновляет весь UI"""
        active = self._get_active_domains()
        
        # Статус
        if active:
            self.status_dot.setStyleSheet("color: #6ccb5f; font-size: 12px;")
            self.status_label.setText(f"Активно {len(active)} доменов")
        else:
            self.status_dot.setStyleSheet("color: #888; font-size: 12px;")
            self.status_label.setText("Нет активных")
        
        # Обновляем иконки под текущие выборы
        for name in list(self.service_combos.keys()):
            self._update_profile_row_visual(name)
        
        # Adobe
        is_adobe = self.hosts_manager.is_adobe_domains_active() if self.hosts_manager else False
        self.adobe_status.setText("Активно" if is_adobe else "Откл.")
        self.adobe_status.setStyleSheet(f"color: {'#6ccb5f' if is_adobe else 'rgba(255,255,255,0.5)'}; font-size: 11px;")
        self.adobe_btn.setText("Откл." if is_adobe else "Вкл.")
        self.adobe_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#dc3545' if is_adobe else '#28a745'};
                color: white; border: none; border-radius: 4px; font-size: 10px;
            }}
            QPushButton:hover {{ background-color: {'#c82333' if is_adobe else '#218838'}; }}
        """)
        
    def refresh(self):
        """Обновляет страницу (сбрасывает кеш и перечитывает hosts)"""
        self._invalidate_cache()
        self._update_ui()
    
    def cleanup(self):
        """Очистка потоков при закрытии"""
        from log import log
        try:
            if self._thread and self._thread.isRunning():
                log("Останавливаем hosts worker...", "DEBUG")
                self._thread.quit()
                if not self._thread.wait(2000):
                    log("⚠ Hosts worker не завершился, принудительно завершаем", "WARNING")
                    try:
                        self._thread.terminate()
                        self._thread.wait(500)
                    except:
                        pass
        except Exception as e:
            log(f"Ошибка при очистке hosts_page: {e}", "DEBUG")
