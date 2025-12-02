# ui/pages/autostart_page.py
"""Страница настроек автозапуска"""

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMessageBox, QFrame
)
import qtawesome as qta
import os

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from log import log


class AutostartOptionCard(QFrame):
    """Карточка опции автозапуска"""
    
    clicked = pyqtSignal()
    
    def __init__(self, icon_name: str, title: str, description: str, 
                 accent: bool = False, recommended: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("autostartOption")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._accent = accent
        self._recommended = recommended
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)
        
        # Иконка
        icon_label = QLabel()
        icon_color = '#60cdff' if accent else '#ffffff'
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(28, 28))
        icon_label.setFixedSize(36, 36)
        layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {'#60cdff' if accent else '#ffffff'};
                font-size: 14px;
                font-weight: 600;
            }}
        """)
        title_layout.addWidget(title_label)
        
        if recommended:
            rec_label = QLabel("Рекомендуется")
            rec_label.setStyleSheet("""
                QLabel {
                    background-color: #2e7d32;
                    color: white;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 8px;
                    border-radius: 8px;
                }
            """)
            title_layout.addWidget(rec_label)
            
        title_layout.addStretch()
        text_layout.addLayout(title_layout)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
        """)
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        # Стрелка
        arrow = QLabel()
        arrow.setPixmap(qta.icon('fa5s.chevron-right', color='rgba(255,255,255,0.4)').pixmap(16, 16))
        layout.addWidget(arrow)
        
        self._update_style()
        
    def _update_style(self):
        if self._accent:
            if self._hovered:
                bg = "rgba(96, 205, 255, 0.15)"
                border = "rgba(96, 205, 255, 0.4)"
            else:
                bg = "rgba(96, 205, 255, 0.08)"
                border = "rgba(96, 205, 255, 0.3)"
        else:
            if self._hovered:
                bg = "rgba(255, 255, 255, 0.08)"
                border = "rgba(255, 255, 255, 0.15)"
            else:
                bg = "rgba(255, 255, 255, 0.04)"
                border = "rgba(255, 255, 255, 0.08)"
                
        self.setStyleSheet(f"""
            QFrame#autostartOption {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AutostartPage(BasePage):
    """Страница настроек автозапуска"""
    
    # Сигналы для связи с main.py
    autostart_enabled = pyqtSignal()
    autostart_disabled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("Автозапуск", "Настройка автоматического запуска Zapret", parent)
        
        self._app_instance = None
        self.strategy_name = None
        self.bat_folder = None
        self.json_folder = None
        
        self._build_ui()
    
    @property
    def app_instance(self):
        """Ленивая инициализация app_instance"""
        if self._app_instance is None:
            self._auto_init()
        return self._app_instance
    
    @app_instance.setter
    def app_instance(self, value):
        self._app_instance = value
    
    def _auto_init(self):
        """Автоматическая инициализация из parent или глобального контекста"""
        try:
            from config import BAT_FOLDER, INDEXJSON_FOLDER
            
            # Ищем главное приложение через цепочку parent
            widget = self.parent()
            while widget is not None:
                # LupiDPIApp имеет атрибут dpi_controller
                if hasattr(widget, 'dpi_controller'):
                    self._app_instance = widget
                    log("AutostartPage: app_instance найден через parent", "DEBUG")
                    break
                widget = widget.parent() if hasattr(widget, 'parent') else None
            
            # Устанавливаем папки
            if self.bat_folder is None:
                self.bat_folder = BAT_FOLDER
            if self.json_folder is None:
                self.json_folder = INDEXJSON_FOLDER
                
            # Обновляем имя стратегии
            if self._app_instance and self.strategy_name is None:
                if hasattr(self._app_instance, 'current_strategy_label'):
                    self.strategy_name = self._app_instance.current_strategy_label.text()
                    if self.strategy_name == "Автостарт DPI отключен":
                        from config import get_last_strategy
                        self.strategy_name = get_last_strategy()
                    self.current_strategy_label.setText(self.strategy_name or "Не выбрана")
                    
        except Exception as e:
            log(f"AutostartPage._auto_init ошибка: {e}", "WARNING")
        
    def set_app_instance(self, app):
        """Устанавливает ссылку на главное приложение"""
        self._app_instance = app
        
    def set_folders(self, bat_folder: str, json_folder: str):
        """Устанавливает папки для BAT режима"""
        self.bat_folder = bat_folder
        self.json_folder = json_folder
        
    def _ensure_folders_initialized(self):
        """Гарантирует что папки инициализированы"""
        if self.bat_folder is None or self.json_folder is None:
            from config import BAT_FOLDER, INDEXJSON_FOLDER
            if self.bat_folder is None:
                self.bat_folder = BAT_FOLDER
                log(f"AutostartPage: bat_folder установлен из config: {BAT_FOLDER}", "DEBUG")
            if self.json_folder is None:
                self.json_folder = INDEXJSON_FOLDER
                log(f"AutostartPage: json_folder установлен из config: {INDEXJSON_FOLDER}", "DEBUG")
        
    def set_strategy_name(self, name: str):
        """Устанавливает имя текущей стратегии"""
        self.strategy_name = name
        if hasattr(self, 'current_strategy_label'):
            self.current_strategy_label.setText(name or "Не выбрана")
        
    def _build_ui(self):
        # ═══════════════════════════════════════════════════════════
        # Статус автозапуска
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Статус")
        
        status_card = SettingsCard()
        
        status_layout = QHBoxLayout()
        status_layout.setSpacing(14)
        
        self.status_icon = QLabel()
        self.status_icon.setPixmap(qta.icon('fa5s.circle', color='#888888').pixmap(20, 20))
        self.status_icon.setFixedSize(24, 24)
        status_layout.addWidget(self.status_icon)
        
        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(4)
        
        self.status_label = QLabel("Автозапуск отключён")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 15px;
                font-weight: 600;
            }
        """)
        status_text_layout.addWidget(self.status_label)
        
        self.status_desc = QLabel("Zapret не запускается автоматически")
        self.status_desc.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
        """)
        status_text_layout.addWidget(self.status_desc)
        
        status_layout.addLayout(status_text_layout, 1)
        
        # Кнопка отключения (видна только когда автозапуск включен)
        self.disable_btn = ActionButton("Отключить", "fa5s.times")
        self.disable_btn.setFixedHeight(36)
        self.disable_btn.setVisible(False)
        self.disable_btn.clicked.connect(self._on_disable_clicked)
        status_layout.addWidget(self.disable_btn)
        
        status_card.add_layout(status_layout)
        self.add_widget(status_card)
        
        self.add_spacing(20)
        
        # ═══════════════════════════════════════════════════════════
        # Режим запуска
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Режим")
        
        mode_card = SettingsCard()
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(12)
        
        mode_icon = QLabel()
        mode_icon.setPixmap(qta.icon('fa5s.cog', color='#60cdff').pixmap(18, 18))
        mode_icon.setFixedSize(22, 22)
        mode_layout.addWidget(mode_icon)
        
        mode_text = QLabel("Текущий режим:")
        mode_text.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px;")
        mode_layout.addWidget(mode_text)
        
        self.mode_label = QLabel("Загрузка...")
        self.mode_label.setStyleSheet("color: #60cdff; font-size: 13px; font-weight: 600;")
        mode_layout.addWidget(self.mode_label)
        
        mode_layout.addSpacing(20)
        
        strategy_text = QLabel("Стратегия:")
        strategy_text.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px;")
        mode_layout.addWidget(strategy_text)
        
        self.current_strategy_label = QLabel("Не выбрана")
        self.current_strategy_label.setWordWrap(True)  # Перенос текста
        self.current_strategy_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500;")
        mode_layout.addWidget(self.current_strategy_label, 1)
        
        mode_card.add_layout(mode_layout)
        self.add_widget(mode_card)
        
        self.add_spacing(20)
        
        # ═══════════════════════════════════════════════════════════
        # Варианты автозапуска
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Выберите тип автозапуска")
        
        # GUI автозапуск
        self.gui_option = AutostartOptionCard(
            "fa5s.desktop",
            "Автозапуск программы Zapret",
            "Запускает главное окно программы при входе в Windows. "
            "Вы сможете управлять DPI из системного трея.",
            accent=True
        )
        self.gui_option.clicked.connect(self._on_gui_autostart)
        self.add_widget(self.gui_option)
        
        self.add_spacing(12)
        
        # Контейнер для опций стратегий
        self.strategies_container = QWidget()
        self.strategies_layout = QVBoxLayout(self.strategies_container)
        self.strategies_layout.setContentsMargins(0, 0, 0, 0)
        self.strategies_layout.setSpacing(12)
        
        # Служба Windows (для Direct режима)
        self.service_option = AutostartOptionCard(
            "fa5s.server",
            "Служба Windows",
            "Создает настоящую службу Windows для запуска winws.exe. "
            "Самый надежный способ — работает даже если никто не вошел в систему.",
            recommended=True
        )
        self.service_option.clicked.connect(self._on_service_autostart)
        self.strategies_layout.addWidget(self.service_option)
        
        # Задача при входе
        self.logon_option = AutostartOptionCard(
            "fa5s.user",
            "Задача при входе пользователя",
            "Создает задачу планировщика для запуска DPI при входе пользователя в систему."
        )
        self.logon_option.clicked.connect(self._on_logon_autostart)
        self.strategies_layout.addWidget(self.logon_option)
        
        # Задача при загрузке
        self.boot_option = AutostartOptionCard(
            "fa5s.power-off",
            "Задача при загрузке системы",
            "Создает задачу планировщика для запуска DPI при загрузке Windows (до входа пользователя)."
        )
        self.boot_option.clicked.connect(self._on_boot_autostart)
        self.strategies_layout.addWidget(self.boot_option)
        
        self.add_widget(self.strategies_container)
        
        self.add_spacing(20)
        
        # ═══════════════════════════════════════════════════════════
        # Информация
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Информация")
        
        info_card = SettingsCard()
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        
        # Подсказка
        tip_layout = QHBoxLayout()
        tip_layout.setSpacing(10)
        
        tip_icon = QLabel()
        tip_icon.setPixmap(qta.icon('fa5s.lightbulb', color='#ffc107').pixmap(18, 18))
        tip_icon.setFixedSize(22, 22)
        tip_layout.addWidget(tip_icon)
        
        tip_text = QLabel(
            "💡 <b>Рекомендация:</b> Для максимальной надежности используйте "
            "«Служба Windows» — она запускается раньше всех программ и автоматически "
            "перезапускается при сбоях."
        )
        tip_text.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")
        tip_text.setWordWrap(True)
        tip_layout.addWidget(tip_text, 1)
        
        info_layout.addLayout(tip_layout)
        info_card.add_layout(info_layout)
        self.add_widget(info_card)
        
        # Обновляем режим
        self._update_mode()
        
    def _update_mode(self):
        """Обновляет отображение режима"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            
            if method == "direct":
                self.mode_label.setText("Прямой запуск (Zapret 2)")
                # Показываем все опции для Direct
                self.service_option.setVisible(True)
            else:
                self.mode_label.setText("Классический (BAT файлы)")
                # Для BAT режима скрываем службу Windows
                self.service_option.setVisible(False)
                
        except Exception as e:
            log(f"Ошибка обновления режима: {e}", "WARNING")
            self.mode_label.setText("Неизвестно")
    
    def update_status(self, enabled: bool, strategy_name: str = None, autostart_type: str = None):
        """Обновляет отображение статуса автозапуска"""
        if enabled:
            self.status_label.setText("Автозапуск включён")
            
            type_desc = ""
            if autostart_type:
                type_map = {
                    "service": "как служба Windows",
                    "logon": "при входе пользователя",
                    "boot": "при загрузке системы",
                    "gui": "программа Zapret"
                }
                type_desc = type_map.get(autostart_type, "")
                
            desc = f"Zapret запускается автоматически"
            if type_desc:
                desc += f" {type_desc}"
            self.status_desc.setText(desc)
            
            self.status_icon.setPixmap(qta.icon('fa5s.check-circle', color='#6ccb5f').pixmap(20, 20))
            self.disable_btn.setVisible(True)
        else:
            self.status_label.setText("Автозапуск отключён")
            self.status_desc.setText("Zapret не запускается автоматически")
            self.status_icon.setPixmap(qta.icon('fa5s.circle', color='#888888').pixmap(20, 20))
            self.disable_btn.setVisible(False)
            
        if strategy_name:
            self.current_strategy_label.setText(strategy_name)
            
        # Обновляем режим при каждом обновлении статуса
        self._update_mode()
    
    def _on_disable_clicked(self):
        """Отключение автозапуска"""
        try:
            from autostart.autostart_remove import AutoStartCleaner
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Отключение автозапуска")
            msg.setText("Отключить автозапуск Zapret?")
            msg.setInformativeText("Все задачи и службы автозапуска будут удалены.")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                cleaner = AutoStartCleaner()
                removed = cleaner.run()  # Метод называется run(), не remove_all()
                
                if removed:
                    self.update_status(False)
                    self.autostart_disabled.emit()
                    QMessageBox.information(
                        self, "Успешно",
                        "✅ Автозапуск отключён!\n\n"
                        f"Удалено записей: {removed}"
                    )
                else:
                    QMessageBox.information(
                        self, "Информация",
                        "Записей автозапуска не найдено."
                    )
                    
        except Exception as e:
            log(f"Ошибка отключения автозапуска: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Не удалось отключить автозапуск:\n{e}")
    
    def _on_gui_autostart(self):
        """Автозапуск GUI программы"""
        try:
            from autostart.autostart_exe import setup_autostart_for_exe
            
            ok = setup_autostart_for_exe(
                selected_mode=self.strategy_name or "Default",
                status_cb=lambda msg: log(msg, "INFO"),
            )
            
            if ok:
                self.update_status(True, self.strategy_name, "gui")
                self.autostart_enabled.emit()
                QMessageBox.information(
                    self, "Успешно",
                    "✅ Автозапуск программы настроен!\n\n"
                    "Программа будет запускаться при входе в Windows\n"
                    "и будет доступна в системном трее."
                )
            else:
                QMessageBox.critical(
                    self, "Ошибка",
                    "❌ Не удалось настроить автозапуск.\n\n"
                    "Проверьте права администратора."
                )
                
        except Exception as e:
            log(f"Ошибка автозапуска GUI: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")
    
    def _on_service_autostart(self):
        """Создание службы Windows"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            
            if method == "direct":
                self._setup_direct_service()
            else:
                self._setup_bat_service()
                
        except Exception as e:
            log(f"Ошибка создания службы: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")
    
    def _on_logon_autostart(self):
        """Задача при входе пользователя"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            
            if method == "direct":
                self._setup_direct_logon_task()
            else:
                self._setup_bat_logon_task()
                
        except Exception as e:
            log(f"Ошибка создания задачи: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")
    
    def _on_boot_autostart(self):
        """Задача при загрузке системы"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            
            if method == "direct":
                self._setup_direct_boot_task()
            else:
                self._setup_bat_service()  # Для BAT это служба
                
        except Exception as e:
            log(f"Ошибка создания задачи: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")
    
    def _setup_direct_service(self):
        """Служба Windows для Direct режима"""
        from autostart.autostart_direct import collect_direct_strategy_args
        from autostart.autostart_direct_service import setup_direct_service
        
        if not self.app_instance:
            QMessageBox.critical(self, "Ошибка", "Приложение не инициализировано")
            return
        
        # Подтверждение
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Создание службы Windows")
        msg.setText("Создать службу Windows для Zapret?")
        msg.setInformativeText(
            "Текущий процесс будет остановлен и перезапущен как служба.\n\n"
            "Это обеспечит автоматический запуск при загрузке системы."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return
        
        args, name, winws_exe = collect_direct_strategy_args(self.app_instance)
        
        if not args or not winws_exe:
            QMessageBox.critical(self, "Ошибка", "Не удалось собрать аргументы стратегии")
            return
        
        ok = setup_direct_service(
            winws_exe=winws_exe,
            strategy_args=args,
            strategy_name=name,
            ui_error_cb=lambda msg: QMessageBox.critical(self, "Ошибка", msg)
        )
        
        if ok:
            self.update_status(True, name, "service")
            self.autostart_enabled.emit()
            QMessageBox.information(
                self, "Успешно",
                "✅ Служба Windows создана!\n\n"
                "Zapret будет автоматически запускаться\n"
                "при загрузке системы.\n\n"
                "• Работает до входа в систему\n"
                "• Автоматически перезапускается при сбоях"
            )
    
    def _setup_direct_logon_task(self):
        """Задача при входе для Direct режима"""
        from autostart.autostart_direct import collect_direct_strategy_args, setup_direct_autostart_task
        
        if not self.app_instance:
            QMessageBox.critical(self, "Ошибка", "Приложение не инициализировано")
            return
        
        args, name, winws_exe = collect_direct_strategy_args(self.app_instance)
        
        if not args or not winws_exe:
            QMessageBox.critical(self, "Ошибка", "Не удалось собрать аргументы стратегии")
            return
        
        ok = setup_direct_autostart_task(
            winws_exe=winws_exe,
            strategy_args=args,
            strategy_name=name,
            ui_error_cb=lambda msg: QMessageBox.critical(self, "Ошибка", msg)
        )
        
        if ok:
            self.update_status(True, name, "logon")
            self.autostart_enabled.emit()
            QMessageBox.information(
                self, "Успешно",
                "✅ Задача автозапуска создана!\n\n"
                "DPI будет запускаться при входе в систему."
            )
    
    def _setup_direct_boot_task(self):
        """Задача при загрузке для Direct режима"""
        from autostart.autostart_direct import collect_direct_strategy_args, setup_direct_autostart_service
        
        if not self.app_instance:
            QMessageBox.critical(self, "Ошибка", "Приложение не инициализировано")
            return
        
        args, name, winws_exe = collect_direct_strategy_args(self.app_instance)
        
        if not args or not winws_exe:
            QMessageBox.critical(self, "Ошибка", "Не удалось собрать аргументы стратегии")
            return
        
        ok = setup_direct_autostart_service(
            winws_exe=winws_exe,
            strategy_args=args,
            strategy_name=name,
            ui_error_cb=lambda msg: QMessageBox.critical(self, "Ошибка", msg)
        )
        
        if ok:
            self.update_status(True, name, "boot")
            self.autostart_enabled.emit()
            QMessageBox.information(
                self, "Успешно",
                "✅ Задача автозапуска создана!\n\n"
                "DPI будет запускаться при загрузке Windows\n"
                "(до входа пользователя)."
            )
    
    def _setup_bat_logon_task(self):
        """Задача при входе для BAT режима"""
        from pathlib import Path
        from autostart.autostart_strategy import setup_autostart_for_strategy
        from config import get_last_strategy
        
        # Инициализируем папки если не установлены
        self._ensure_folders_initialized()
        
        if not self.bat_folder or not self.json_folder:
            QMessageBox.critical(self, "Ошибка", "Папки не настроены")
            return
        
        # Для BAT режима используем сохранённую стратегию, а не "Прямой запуск"
        bat_strategy_name = self.strategy_name
        if bat_strategy_name in ("Прямой запуск", "COMBINED_DIRECT", None, ""):
            bat_strategy_name = get_last_strategy()
            if bat_strategy_name in ("COMBINED_DIRECT", None, ""):
                QMessageBox.critical(
                    self, "Ошибка", 
                    "Для BAT режима необходимо сначала выбрать стратегию.\n\n"
                    "Откройте меню 'Стратегии' и выберите BAT стратегию."
                )
                return
        
        index_json_path = (Path(self.json_folder) / "index.json").resolve()
        
        ok = setup_autostart_for_strategy(
            selected_mode=bat_strategy_name,
            bat_folder=self.bat_folder,
            index_path=str(index_json_path),
            ui_error_cb=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
        )
        
        if ok:
            self.update_status(True, bat_strategy_name, "logon")
            self.autostart_enabled.emit()
            QMessageBox.information(
                self, "Успешно",
                f"✅ Автозапуск стратегии настроен!\n\n"
                f"Стратегия «{bat_strategy_name}» будет\n"
                "запускаться при входе в Windows."
            )
    
    def _setup_bat_service(self):
        """Служба для BAT режима"""
        from pathlib import Path
        from autostart.autostart_service import setup_service_for_strategy
        from config import get_last_strategy
        
        # Инициализируем папки если не установлены
        self._ensure_folders_initialized()
        
        if not self.bat_folder or not self.json_folder:
            QMessageBox.critical(self, "Ошибка", "Папки не настроены")
            return
        
        # Для BAT режима используем сохранённую стратегию, а не "Прямой запуск"
        bat_strategy_name = self.strategy_name
        if bat_strategy_name in ("Прямой запуск", "COMBINED_DIRECT", None, ""):
            bat_strategy_name = get_last_strategy()
            if bat_strategy_name in ("COMBINED_DIRECT", None, ""):
                QMessageBox.critical(
                    self, "Ошибка", 
                    "Для BAT режима необходимо сначала выбрать стратегию.\n\n"
                    "Откройте меню 'Стратегии' и выберите BAT стратегию."
                )
                return
        
        index_json_path = (Path(self.json_folder) / "index.json").resolve()
        
        ok = setup_service_for_strategy(
            selected_mode=bat_strategy_name,
            bat_folder=self.bat_folder,
            index_path=str(index_json_path),
            ui_error_cb=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
        )
        
        if ok:
            self.update_status(True, bat_strategy_name, "service")
            self.autostart_enabled.emit()
            QMessageBox.information(
                self, "Успешно",
                f"✅ Служба Windows создана!\n\n"
                f"Стратегия «{bat_strategy_name}» будет\n"
                "запускаться как служба Windows."
            )
