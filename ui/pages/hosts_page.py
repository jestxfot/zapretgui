# ui/pages/hosts_page.py
"""Страница управления Hosts файлом - разблокировка сервисов"""

import os
import re
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QComboBox, QScrollArea, QFrame, QLayout, QCheckBox
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from ui.pages.strategies_page_base import ResetActionButton
from log import log
from utils import get_system32_path

try:
    # Simple Win11 toggle without text (QCheckBox-based).
    from ui.pages.dpi_settings_page import Win11ToggleSwitch as Win11ToggleSwitchNoText
except Exception:
    Win11ToggleSwitchNoText = QCheckBox  # type: ignore[misc,assignment]


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

FLUENT_CHIP_STYLE = """
QPushButton {
    background-color: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.7);
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
    text-decoration: none;
}
QPushButton:hover {
    color: #60cdff;
    text-decoration: underline;
}
QPushButton:pressed {
    color: rgba(96, 205, 255, 0.8);
}
QPushButton:disabled {
    color: rgba(255, 255, 255, 0.35);
}
"""

_DNS_PROFILE_IP_SUFFIX = re.compile(r"\s*\(\s*(?:\d{1,3}\.){3}\d{1,3}\s*\)\s*$")


def _format_dns_profile_label(profile_name: str) -> str:
    label = (profile_name or "").strip()
    if not label:
        return ""
    return _DNS_PROFILE_IP_SUFFIX.sub("", label).strip()


class DangerResetActionButton(ResetActionButton):
    def _update_icon(self, rotation: int = 0):
        color = "white"
        icon_name = "fa5s.trash-alt"
        if rotation != 0:
            self.setIcon(qta.icon(icon_name, color=color, rotated=rotation))
        else:
            self.setIcon(qta.icon(icon_name, color=color))

    def _update_style(self):
        if self._pending:
            bg = "rgba(220, 53, 69, 0.98)" if self._hovered else "rgba(220, 53, 69, 0.90)"
            border = "1px solid rgba(255, 255, 255, 0.25)"
        else:
            bg = "rgba(220, 53, 69, 0.90)" if self._hovered else "rgba(220, 53, 69, 0.70)"
            border = "none"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: {border};
                border-radius: 4px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
        """)

# Импортируем сервисы и домены
try:
    from hosts.proxy_domains import (
        QUICK_SERVICES,
        get_dns_profiles,
        get_all_services,
        get_service_has_geohide_ips,
        get_service_available_dns_profiles,
        get_service_domain_ip_map,
        get_service_domain_names,
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
    def get_service_domain_ip_map(*args, **kwargs): return {}
    def get_service_domain_names(s): return []
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
                if success:
                    message = "Применено"
                else:
                    message = getattr(self.hosts_manager, "last_status", None) or "Ошибка"

            elif self.operation == 'clear_all':
                success = self.hosts_manager.clear_hosts_file()
                if success:
                    message = "Hosts очищен"
                else:
                    message = getattr(self.hosts_manager, "last_status", None) or "Ошибка"
                        
            elif self.operation == 'adobe_add':
                success = self.hosts_manager.add_adobe_domains()
                if success:
                    message = "Adobe заблокирован"
                else:
                    message = getattr(self.hosts_manager, "last_status", None) or "Ошибка"
                
            elif self.operation == 'adobe_remove':
                success = self.hosts_manager.remove_adobe_domains()
                if success:
                    message = "Adobe разблокирован"
                else:
                    message = getattr(self.hosts_manager, "last_status", None) or "Ошибка"
            
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
        self._current_operation = None
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

    def _get_hosts_path_str(self) -> str:
        try:
            if os.name == "nt":
                sys_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
                if sys_root:
                    return os.path.join(sys_root, "System32", "drivers", "etc", "hosts")
            return os.path.join(get_system32_path(), "drivers", "etc", "hosts")
        except Exception:
            return os.path.join(get_system32_path(), "drivers", "etc", "hosts")

    def _sync_selections_from_hosts(self) -> None:
        """
        Делает UI «источником истины» = реальный hosts.
        Сбрасывает combo/конфиг к тому, что реально присутствует в hosts сейчас.
        """
        if not self.hosts_manager:
            return

        try:
            active_domains_map = self.hosts_manager.get_active_domains_map() or {}
        except Exception:
            active_domains_map = {}

        def infer_profile_from_hosts(service_name: str, available_profiles: list[str]) -> str | None:
            if not active_domains_map or not available_profiles:
                return None

            best_profile: str | None = None
            best_matches = -1
            best_present = -1
            best_total = 0

            for profile_name in available_profiles:
                try:
                    domain_map = get_service_domain_ip_map(service_name, profile_name) or {}
                except Exception:
                    domain_map = {}
                if not domain_map:
                    continue

                total = len(domain_map)
                present = 0
                matches = 0
                for domain, ip in domain_map.items():
                    active_ip = active_domains_map.get(domain)
                    if active_ip is None:
                        continue
                    present += 1
                    if (active_ip or "").strip() == (ip or "").strip():
                        matches += 1

                if total and matches == total:
                    return profile_name

                if matches > best_matches or (matches == best_matches and present > best_present):
                    best_profile = profile_name
                    best_matches = matches
                    best_present = present
                    best_total = total

            if not best_profile:
                return None

            # Direct-only services: if at least one domain is present in hosts, keep them enabled.
            if len(available_profiles) == 1 and best_present > 0:
                return best_profile

            # Otherwise, require a reasonably confident match.
            if best_total and best_matches > 0 and (best_matches / best_total) >= 0.6:
                return best_profile

            return None

        def infer_direct_toggle_from_hosts(service_name: str) -> bool:
            """Для direct-only сервисов: включено, если хотя бы один домен сервиса есть в hosts."""
            try:
                for domain in (get_service_domain_names(service_name) or []):
                    if domain in active_domains_map:
                        return True
            except Exception:
                pass
            return False

        direct_profile = self._get_direct_profile_name()

        new_selection: dict[str, str] = {}

        was_building = getattr(self, "_building_services_ui", False)
        self._building_services_ui = True
        try:
            for service_name, combo in list(self.service_combos.items()):
                direct_only = not get_service_has_geohide_ips(service_name)

                available = list(get_service_available_dns_profiles(service_name) or [])
                inferred: str | None = None

                if direct_only:
                    enabled = infer_direct_toggle_from_hosts(service_name)
                    if isinstance(combo, QCheckBox):
                        can_toggle = bool(direct_profile and direct_profile in available)
                        combo.setEnabled(can_toggle)
                        combo.blockSignals(True)
                        combo.setChecked(bool(enabled and can_toggle))
                        combo.blockSignals(False)
                        if combo.isChecked() and direct_profile:
                            new_selection[service_name] = direct_profile
                        self._update_profile_row_visual(service_name)
                        continue
                    if enabled and direct_profile and direct_profile in available:
                        inferred = direct_profile
                else:
                    inferred = infer_profile_from_hosts(service_name, available)

                if inferred:
                    if isinstance(combo, QComboBox):
                        idx = combo.findData(inferred)
                        if idx >= 0:
                            combo.blockSignals(True)
                            combo.setCurrentIndex(idx)
                            combo.blockSignals(False)
                            new_selection[service_name] = inferred
                        else:
                            combo.blockSignals(True)
                            combo.setCurrentIndex(0)
                            combo.blockSignals(False)
                else:
                    if isinstance(combo, QComboBox):
                        combo.blockSignals(True)
                        combo.setCurrentIndex(0)
                        combo.blockSignals(False)
                    elif isinstance(combo, QCheckBox):
                        combo.blockSignals(True)
                        combo.setChecked(False)
                        combo.blockSignals(False)

                self._update_profile_row_visual(service_name)
        finally:
            self._building_services_ui = was_building

        self._service_dns_selection = new_selection
        save_user_hosts_selection(self._service_dns_selection)
            
    def _get_active_domains(self) -> set:
        """Возвращает активные домены с кешированием (чтобы не читать hosts 28 раз)"""
        if self._active_domains_cache is not None:
            return self._active_domains_cache
        if self.hosts_manager:
            try:
                writable = self.hosts_manager.is_hosts_file_accessible()
                if not writable:
                    hosts_path = self._get_hosts_path_str()
                    self._show_error(
                        "Нет доступа для изменения файла hosts.\n"
                        "Если файл редактируется вручную, возможно защитник/антивирус блокирует запись.\n"
                        f"Путь: {hosts_path}"
                    )
                else:
                    self._hide_error()

                # Даже если запись запрещена — чтение может работать: показываем реальное состояние.
                self._active_domains_cache = self.hosts_manager.get_active_domains()
                return self._active_domains_cache
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
                self._sync_selections_from_hosts()
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
            if self.hosts_manager and self.hosts_manager.is_hosts_file_accessible():
                self._hide_error()
            else:
                hosts_path = self._get_hosts_path_str()
                self._show_error(
                    "Нет доступа для изменения файла hosts. "
                    "Скорее всего защитник/антивирус заблокировал запись.\n"
                    f"Путь: {hosts_path}"
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

    def _make_fluent_chip(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(24)
        btn.setStyleSheet(FLUENT_CHIP_STYLE)
        return btn

    def _bulk_apply_dns_profile(self, service_names: list[str], profile_name: str | None) -> None:
        if self._applying:
            return

        changed = False
        skipped: list[str] = []
        for service_name in service_names:
            control = self.service_combos.get(service_name)
            if not control:
                continue

            available = list(get_service_available_dns_profiles(service_name) or [])

            target_profile = (profile_name or "").strip()
            if isinstance(control, QComboBox):
                if target_profile:
                    if target_profile not in available:
                        skipped.append(service_name)
                        continue
                    target_idx = control.findData(target_profile)
                    if target_idx < 0:
                        skipped.append(service_name)
                        continue
                else:
                    target_idx = 0

                if control.currentIndex() != target_idx:
                    control.blockSignals(True)
                    control.setCurrentIndex(target_idx)
                    control.blockSignals(False)
                    changed = True
            elif isinstance(control, QCheckBox):
                if target_profile and target_profile not in available:
                    skipped.append(service_name)
                    continue
                desired = bool(target_profile)
                if control.isChecked() != desired:
                    control.blockSignals(True)
                    control.setChecked(desired)
                    control.blockSignals(False)
                    changed = True
            else:
                continue

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
            if skipped:
                log(
                    "Hosts: профиль недоступен для: "
                    + ", ".join(skipped[:8])
                    + ("…" if len(skipped) > 8 else ""),
                    "DEBUG",
                )
            return

        self._apply_current_selection()
	        
    def _build_services_selectors(self):
        OFF_LABEL = "Откл."
        ON_LABEL = "Вкл."

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
        selection_migrated = False
        try:
            active_domains_map: dict[str, str] = {}
            try:
                if self.hosts_manager:
                    active_domains_map = self.hosts_manager.get_active_domains_map() or {}
            except Exception:
                active_domains_map = {}

            def normalize_profile_name(profile_name: str) -> str:
                return _format_dns_profile_label(profile_name).strip().lower()

            def infer_profile_from_hosts(service_name: str, available_profiles: list[str]) -> str | None:
                if not active_domains_map:
                    return None
                if not available_profiles:
                    return None

                best_profile: str | None = None
                best_matches = -1
                best_present = -1
                best_total = 0

                for profile_name in available_profiles:
                    try:
                        domain_map = get_service_domain_ip_map(service_name, profile_name) or {}
                    except Exception:
                        domain_map = {}
                    if not domain_map:
                        continue

                    total = len(domain_map)
                    present = 0
                    matches = 0
                    for domain, ip in domain_map.items():
                        active_ip = active_domains_map.get(domain)
                        if active_ip is None:
                            continue
                        present += 1
                        if (active_ip or "").strip() == (ip or "").strip():
                            matches += 1

                    if total and matches == total:
                        return profile_name

                    if matches > best_matches or (matches == best_matches and present > best_present):
                        best_profile = profile_name
                        best_matches = matches
                        best_present = present
                        best_total = total

                if not best_profile:
                    return None

                # Direct-only services: if at least one domain is present in hosts, keep them enabled.
                if len(available_profiles) == 1 and best_present > 0:
                    return best_profile

                # Otherwise, require a reasonably confident match.
                if best_total and best_matches > 0 and (best_matches / best_total) >= 0.6:
                    return best_profile

                return None

            direct_profile = self._get_direct_profile_name()

            def add_group(title: str, names: list[str], direct_only: bool = False) -> None:
                nonlocal selection_migrated
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
                header.addWidget(title_label, 0, Qt.AlignmentFlag.AlignVCenter)

                chips = QWidget()
                chips_layout = QHBoxLayout(chips)
                chips_layout.setContentsMargins(0, 0, 0, 0)
                chips_layout.setSpacing(4)
                chips_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
                chips_layout.addStretch(1)

                off_btn = self._make_fluent_chip(OFF_LABEL)
                off_btn.clicked.connect(lambda _checked=False, n=tuple(names): self._bulk_apply_dns_profile(list(n), None))
                chips_layout.addWidget(off_btn)

                if direct_only:
                    if direct_profile:
                        on_btn = self._make_fluent_chip(ON_LABEL)
                        on_btn.clicked.connect(
                            lambda _checked=False, n=tuple(names), p=direct_profile: self._bulk_apply_dns_profile(list(n), p)
                        )
                        chips_layout.addWidget(on_btn)
                else:
                    for profile_name in (get_dns_profiles() or []):
                        label = _format_dns_profile_label(profile_name)
                        if not label:
                            continue
                        btn = self._make_fluent_chip(label)
                        btn.clicked.connect(
                            lambda _checked=False, n=tuple(names), p=profile_name: self._bulk_apply_dns_profile(list(n), p)
                        )
                        chips_layout.addWidget(btn)

                chips_scroll = QScrollArea()
                chips_scroll.setFrameShape(QFrame.Shape.NoFrame)
                chips_scroll.setWidgetResizable(True)
                chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                chips_scroll.setFixedHeight(30)
                chips_scroll.setStyleSheet(
                    """
                    QScrollArea { background: transparent; border: none; }
                    QScrollArea QWidget { background: transparent; }
                    QScrollBar:horizontal {
                        height: 4px;
                        background: transparent;
                        margin: 0px;
                    }
                    QScrollBar::handle:horizontal {
                        background: rgba(255, 255, 255, 0.22);
                        border-radius: 2px;
                        min-width: 24px;
                    }
                    QScrollBar::handle:horizontal:hover { background: rgba(255, 255, 255, 0.32); }
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                        width: 0px;
                        height: 0px;
                        background: transparent;
                        border: none;
                    }
                    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
                    """
                )
                chips_scroll.setWidget(chips)

                header.addWidget(chips_scroll, 1, Qt.AlignmentFlag.AlignVCenter)

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

                    # Откл. + доступные профили
                    available = get_service_available_dns_profiles(service_name) or []

                    is_direct_only = not get_service_has_geohide_ips(service_name)
                    if is_direct_only:
                        toggle = Win11ToggleSwitchNoText()
                        can_toggle = bool(direct_profile and direct_profile in available)
                        toggle.setEnabled(can_toggle)

                        # Источник истины = реальный hosts: выбор в UI должен отражать то, что реально записано.
                        enabled = False
                        if can_toggle:
                            try:
                                enabled = any(
                                    (domain in active_domains_map)
                                    for domain in (get_service_domain_names(service_name) or [])
                                )
                            except Exception:
                                enabled = False

                        toggle.blockSignals(True)
                        toggle.setChecked(bool(enabled and can_toggle))
                        toggle.blockSignals(False)

                        if toggle.isChecked():
                            if self._service_dns_selection.get(service_name) != direct_profile:
                                self._service_dns_selection[service_name] = direct_profile  # type: ignore[arg-type]
                                selection_migrated = True
                        else:
                            if service_name in self._service_dns_selection:
                                self._service_dns_selection.pop(service_name, None)
                                selection_migrated = True

                        toggle.toggled.connect(
                            lambda checked, s=service_name: self._on_direct_toggle_changed(s, checked)
                        )

                        row.addWidget(toggle, 0, Qt.AlignmentFlag.AlignVCenter)
                        card.add_layout(row)
                        self.service_combos[service_name] = toggle
                    else:
                        combo = QComboBox()
                        self._configure_fluent_combo(combo)
                        combo.setMinimumWidth(220)
                        combo.addItem(OFF_LABEL, None)
                        for profile_name in available:
                            combo.addItem(_format_dns_profile_label(profile_name), profile_name)

                        # Источник истины = реальный hosts: выбор в UI должен отражать то, что реально записано.
                        inferred = infer_profile_from_hosts(service_name, available)

                        if inferred:
                            inferred_idx = combo.findData(inferred)
                            if inferred_idx >= 0:
                                combo.setCurrentIndex(inferred_idx)
                                if self._service_dns_selection.get(service_name) != inferred:
                                    self._service_dns_selection[service_name] = inferred
                                    selection_migrated = True
                            else:
                                combo.setCurrentIndex(0)
                                if service_name in self._service_dns_selection:
                                    self._service_dns_selection.pop(service_name, None)
                                    selection_migrated = True
                        else:
                            combo.setCurrentIndex(0)
                            if service_name in self._service_dns_selection:
                                self._service_dns_selection.pop(service_name, None)
                                selection_migrated = True

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

            add_group("Напрямую из hosts", no_geohide, direct_only=True)
            add_group("ИИ", ai)
            add_group("Остальные", other)

            if selection_migrated:
                save_user_hosts_selection(self._service_dns_selection)
        finally:
            self._building_services_ui = False

    def _get_direct_profile_name(self) -> str | None:
        """
        Профиль "direct"/"Вкл. (активировать hosts)" из каталога DNS.
        Нужен для сервисов без proxy/geohide IP (они должны работать как toggle).
        """
        try:
            for profile in (get_dns_profiles() or []):
                p = (profile or "").strip().lower()
                if not p:
                    continue
                if ("вкл. (активировать hosts)" in p) or ("direct" in p) or ("no proxy" in p):
                    return profile
        except Exception:
            pass
        return None

    def _on_direct_toggle_changed(self, service_name: str, checked: bool) -> None:
        if getattr(self, "_building_services_ui", False):
            self._update_profile_row_visual(service_name)
            return
        if self._applying:
            self._update_profile_row_visual(service_name)
            return

        direct_profile = self._get_direct_profile_name()
        if not direct_profile:
            # Strict: without an explicit "direct"/"Вкл. (активировать hosts)" profile we can never apply hosts.
            control = self.service_combos.get(service_name)
            if isinstance(control, QCheckBox):
                control.blockSignals(True)
                control.setChecked(False)
                control.blockSignals(False)
                control.setEnabled(False)
            self._service_dns_selection.pop(service_name, None)
            self._update_profile_row_visual(service_name)
            return

        if checked:
            self._service_dns_selection[service_name] = direct_profile
        else:
            self._service_dns_selection.pop(service_name, None)

        self._update_profile_row_visual(service_name)
        self._apply_current_selection()
        
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

        clear_note = QLabel(
            "⚠ «Очистить» полностью сбрасывает файл hosts к стандартному содержимому Windows "
            "и удаляет ВСЕ записи (включая добавленные вручную)."
        )
        clear_note.setWordWrap(True)
        clear_note.setStyleSheet("color: rgba(255, 152, 0, 0.85); font-size: 10px; margin-bottom: 6px;")
        actions_card.add_widget(clear_note)

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        
        # Очистить (двойное подтверждение без модального окна)
        clear_btn = DangerResetActionButton("Очистить", confirm_text="Сбросить hosts полностью?")
        clear_btn.reset_confirmed.connect(self._clear_hosts)
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

        self._update_profile_row_visual(service_name)
        self._apply_current_selection()

    def _update_profile_row_visual(self, service_name: str):
        OFF_LABEL = "Откл."
        combo = self.service_combos.get(service_name)
        icon_label = self.service_icon_labels.get(service_name)
        base_color = self.service_icon_base_colors.get(service_name, "#60cdff")
        if not combo or not icon_label:
            return

        enabled = False
        if isinstance(combo, QComboBox):
            selected = combo.currentText().strip()
            enabled = bool(selected) and selected != OFF_LABEL
        elif isinstance(combo, QCheckBox):
            enabled = bool(combo.isChecked())
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

        self._run_operation('clear_all')
            
    def _open_hosts_file(self):
        try:
            import ctypes
            import os
            hosts_path = self._get_hosts_path_str()
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
        self._current_operation = operation
        
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
        operation = self._current_operation
        self._current_operation = None
        self._applying = False
        
        # Сбрасываем кеш и обновляем UI
        self._invalidate_cache()
        self._update_ui()
        self._sync_selections_from_hosts()

        if success and operation == "clear_all":
            self._reset_all_service_profiles()
        
        if success:
            self._hide_error()
        else:
            hosts_path = self._get_hosts_path_str()
            self._show_error(f"{message}\nПуть: {hosts_path}")

    def _reset_all_service_profiles(self) -> None:
        """Сбрасывает выбор профилей в UI и user_hosts.ini (после очистки hosts)."""
        self._service_dns_selection = {}
        save_user_hosts_selection(self._service_dns_selection)

        was_building = getattr(self, "_building_services_ui", False)
        self._building_services_ui = True
        try:
            for control in self.service_combos.values():
                if isinstance(control, QComboBox):
                    control.blockSignals(True)
                    control.setCurrentIndex(0)
                    control.blockSignals(False)
                elif isinstance(control, QCheckBox):
                    control.blockSignals(True)
                    control.setChecked(False)
                    control.blockSignals(False)
        finally:
            self._building_services_ui = was_building

        for service_name in list(self.service_combos.keys()):
            self._update_profile_row_visual(service_name)
            
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
