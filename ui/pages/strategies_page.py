# ui/pages/strategies_page.py
"""Страница выбора стратегий"""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QFrame, QScrollArea, QPushButton,
                             QSizePolicy, QMessageBox, QTextEdit, QApplication,
                             QButtonGroup, QStackedWidget)
from PyQt6.QtGui import QFont, QTextOption, QPainter, QColor, QPen
import qtawesome as qta
import os
import shlex
import math

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from log import log


class Win11Spinner(QWidget):
    """Спиннер в стиле Windows 11 - кольцо с бегущей точкой"""
    
    def __init__(self, size=20, color="#60cdff", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._size = size
        self._color = QColor(color)
        self._angle = 0
        self._arc_length = 90  # Длина дуги в градусах
        
        # Таймер для анимации
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        
    def start(self):
        """Запускает анимацию"""
        self._timer.start(16)  # ~60 FPS
        self.show()
        
    def stop(self):
        """Останавливает анимацию"""
        self._timer.stop()
        self.hide()
        
    def _rotate(self):
        self._angle = (self._angle + 6) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Рисуем фоновое кольцо (серое)
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        margin = 3
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.drawEllipse(rect)
        
        # Рисуем активную дугу (голубая)
        pen.setColor(self._color)
        painter.setPen(pen)
        
        # Qt рисует углы против часовой стрелки, начиная с 3 часов
        # Конвертируем в формат Qt: угол * 16 (Qt использует 1/16 градуса)
        start_angle = int((90 - self._angle) * 16)  # Начинаем с 12 часов
        span_angle = int(-self._arc_length * 16)  # По часовой стрелке
        
        painter.drawArc(rect, start_angle, span_angle)


class StatusIndicator(QWidget):
    """Индикатор статуса: галочка или спиннер"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Стек для переключения между галочкой и спиннером
        self.stack = QStackedWidget()
        self.stack.setFixedSize(20, 20)
        
        # Галочка
        self.check_icon = QLabel()
        self.check_icon.setPixmap(qta.icon('fa5s.check-circle', color='#6ccb5f').pixmap(20, 20))
        self.check_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.check_icon)
        
        # Спиннер
        self.spinner = Win11Spinner(20, "#60cdff")
        self.stack.addWidget(self.spinner)
        
        layout.addWidget(self.stack)
        
        # По умолчанию показываем галочку
        self.stack.setCurrentWidget(self.check_icon)
        
    def show_loading(self):
        """Показывает спиннер загрузки"""
        self.stack.setCurrentWidget(self.spinner)
        self.spinner.start()
        
    def show_success(self):
        """Показывает галочку успеха"""
        self.spinner.stop()
        self.stack.setCurrentWidget(self.check_icon)


class CommandLineWidget(QFrame):
    """Виджет командной строки - всегда развернутый"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_line = ""
        self.formatted_command = ""
        self._build_ui()
        
    def _build_ui(self):
        self.setStyleSheet("""
            CommandLineWidget {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        # Иконка терминала
        terminal_icon = QLabel()
        terminal_icon.setPixmap(qta.icon('fa5s.terminal', color='#60cdff').pixmap(14, 14))
        header_layout.addWidget(terminal_icon)
        
        title = QLabel("Командная строка")
        title.setStyleSheet("color: #60cdff; font-weight: 600; font-size: 12px;")
        header_layout.addWidget(title)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px;")
        header_layout.addWidget(self.info_label)
        
        header_layout.addStretch()
        
        # Кнопки
        btn_style = """
            QPushButton {
                background: rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.7);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }
        """
        
        copy_btn = QPushButton("CMD")
        copy_btn.setToolTip("Копировать для CMD")
        copy_btn.setStyleSheet(btn_style)
        copy_btn.clicked.connect(self._copy_to_clipboard)
        header_layout.addWidget(copy_btn)
        self.copy_btn = copy_btn
        
        copy_ps = QPushButton("PS")
        copy_ps.setToolTip("Копировать для PowerShell")
        copy_ps.setStyleSheet(btn_style)
        copy_ps.clicked.connect(self._copy_formatted)
        header_layout.addWidget(copy_ps)
        
        layout.addLayout(header_layout)
        
        # Текстовое поле - всегда видно
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 9))
        self.text_edit.setMinimumHeight(140)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: #1a1a1a;
                color: #d4d4d4;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
        layout.addWidget(self.text_edit, 1)  # stretch=1 чтобы занимало доступное место
            
    def generate_command(self):
        """Генерирует командную строку"""
        try:
            from strategy_menu import get_strategy_launch_method
            
            if get_strategy_launch_method() != "direct":
                self.text_edit.setPlainText("Командная строка доступна только в режиме 'Прямой запуск'")
                self.info_label.setText("BAT режим")
                return
                
            from strategy_menu.strategy_lists_separated import combine_strategies
            from strategy_menu.apply_filters import apply_all_filters
            from strategy_menu import get_direct_strategy_selections, get_default_selections
            from config import WINWS2_EXE, WINDIVERT_FILTER
            
            # Получаем выборы
            try:
                category_selections = get_direct_strategy_selections()
            except:
                category_selections = get_default_selections()
                
            if not category_selections:
                self.text_edit.setPlainText("Нет выбранных стратегий")
                return
                
            # Комбинируем стратегии
            combined = combine_strategies(**category_selections)
            args = shlex.split(combined['args'], posix=False)
            
            # Разрешаем пути
            exe_dir = os.path.dirname(WINWS2_EXE)
            work_dir = os.path.dirname(exe_dir)
            lists_dir = os.path.join(work_dir, "lists")
            bin_dir = os.path.join(work_dir, "bin")
            
            resolved_args = self._resolve_paths(args, lists_dir, bin_dir, WINDIVERT_FILTER)
            resolved_args = apply_all_filters(resolved_args, lists_dir)
            
            # Формируем команду
            cmd_parts = [WINWS2_EXE] + resolved_args
            full_cmd_parts = []
            for arg in cmd_parts:
                if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                    full_cmd_parts.append(f'"{arg}"')
                else:
                    full_cmd_parts.append(arg)
                    
            self.command_line = ' '.join(full_cmd_parts)
            self.formatted_command = self._format_for_display(full_cmd_parts)
            
            # Показываем в text_edit
            self.text_edit.setPlainText(self.formatted_command)
            self.info_label.setText(f"{len(self.command_line)} симв. | {len(resolved_args)} арг.")
            
        except Exception as e:
            log(f"Ошибка генерации команды: {e}", "ERROR")
            self.text_edit.setPlainText(f"Ошибка: {e}")
            
    def _resolve_paths(self, args, lists_dir, bin_dir, filter_dir):
        """Разрешает пути в аргументах"""
        resolved = []
        
        for arg in args:
            if arg.startswith("--wf-raw-part="):
                value = arg.split("=", 1)[1]
                if value.startswith("@"):
                    filename = value[1:].strip('"')
                    if not os.path.isabs(filename):
                        full_path = os.path.join(filter_dir, filename)
                        resolved.append(f'--wf-raw-part=@{full_path}')
                    else:
                        resolved.append(f'--wf-raw-part=@{filename}')
                else:
                    resolved.append(arg)
                    
            elif any(arg.startswith(p) for p in ["--hostlist=", "--ipset=", "--hostlist-exclude=", "--ipset-exclude="]):
                prefix, filename = arg.split("=", 1)
                filename = filename.strip('"')
                if not os.path.isabs(filename):
                    resolved.append(f'{prefix}={os.path.join(lists_dir, filename)}')
                else:
                    resolved.append(arg)
                    
            elif any(arg.startswith(p) for p in [
                "--dpi-desync-fake-tls=", "--dpi-desync-fake-quic=", "--dpi-desync-fake-syndata=",
                "--dpi-desync-fake-unknown-udp=", "--dpi-desync-split-seqovl-pattern=",
                "--dpi-desync-fake-http=", "--dpi-desync-fake-unknown=", "--dpi-desync-fakedsplit-pattern="
            ]):
                prefix, filename = arg.split("=", 1)
                if not filename.startswith("0x") and not filename.startswith("!") and not filename.startswith("^") and not os.path.isabs(filename):
                    resolved.append(f'{prefix}={os.path.join(bin_dir, filename.strip(chr(34)))}')
                else:
                    resolved.append(arg)
            else:
                resolved.append(arg)
                
        return resolved
        
    def _format_for_display(self, cmd_parts):
        """Форматирует для отображения с переносами"""
        if not cmd_parts:
            return ""
            
        lines = []
        current_line = []
        
        for i, arg in enumerate(cmd_parts):
            if i == 0:
                lines.append(arg)
                continue
                
            should_break = (
                arg == "--new" or
                arg.startswith("--filter-") or
                arg.startswith("--blob=") or
                arg.startswith("--lua-init=") or
                arg.startswith("--wf-")
            )
            
            if should_break:
                if current_line:
                    lines.append("  " + " ".join(current_line) + " `")
                    current_line = []
                if arg == "--new":
                    lines.append("  --new `")
                else:
                    current_line.append(arg)
            else:
                current_line.append(arg)
                
        if current_line:
            lines.append("  " + " ".join(current_line))
            
        if lines and lines[-1].endswith(" `"):
            lines[-1] = lines[-1][:-2]
            
        return "\n".join(lines)
        
    def _copy_to_clipboard(self):
        """Копирует однострочную команду"""
        if not self.command_line:
            self.generate_command()
        if self.command_line:
            QApplication.clipboard().setText(self.command_line)
            old_text = self.copy_btn.text()
            self.copy_btn.setText("✓")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText(old_text))
            
    def _copy_formatted(self):
        """Копирует форматированную команду"""
        if not self.formatted_command:
            self.generate_command()
        if self.formatted_command:
            QApplication.clipboard().setText(self.formatted_command)


class StrategiesPage(QWidget):
    """Страница стратегий - поддерживает оба режима: direct и bat"""
    
    launch_method_changed = pyqtSignal(str)
    strategy_selected = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self._strategy_widget = None
        self._bat_table = None
        self._initialized = False
        self._current_mode = None
        self.cmd_widget = None
        self._build_ui()
        
    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Заголовок страницы
        header = QWidget()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(32, 24, 32, 16)
        
        title = QLabel("Стратегии")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 28px;
                font-weight: 600;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
            }
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Настройка методов обхода блокировок")
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 13px;
            }
        """)
        header_layout.addWidget(subtitle)
        
        self.main_layout.addWidget(header)
        
        # Текущая стратегия
        current_widget = QWidget()
        current_widget.setStyleSheet("background-color: transparent;")
        current_layout = QHBoxLayout(current_widget)
        current_layout.setContentsMargins(32, 0, 32, 16)
        
        self.status_indicator = StatusIndicator()
        current_layout.addWidget(self.status_indicator)
        
        current_prefix = QLabel("Текущая:")
        current_prefix.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 14px;")
        current_layout.addWidget(current_prefix)
        
        self.current_strategy_label = QLabel("Не выбрана")
        self.current_strategy_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        current_layout.addWidget(self.current_strategy_label)
        
        current_layout.addStretch()
        
        # Счётчик избранных стратегий
        self.favorites_count_label = QLabel("")
        self.favorites_count_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-size: 13px;
                font-weight: 600;
                padding: 4px 12px;
                background: rgba(255, 193, 7, 0.1);
                border-radius: 12px;
            }
        """)
        self.favorites_count_label.hide()
        current_layout.addWidget(self.favorites_count_label)
        
        self.main_layout.addWidget(current_widget)
        
        # Прокручиваемая область для всего контента
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { 
                background: rgba(255,255,255,0.03); 
                width: 8px; 
                border-radius: 4px;
            }
            QScrollBar::handle:vertical { 
                background: rgba(255,255,255,0.15); 
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { 
                background: rgba(255,255,255,0.25); 
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        
        # Контейнер для контента (меняется в зависимости от режима)
        self.content_container = QWidget()
        self.content_container.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(32, 0, 32, 24)
        self.content_layout.setSpacing(12)
        
        # Плейсхолдер загрузки
        self.loading_label = QLabel("⏳ Загрузка...")
        self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 13px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.loading_label)
        
        self.scroll_area.setWidget(self.content_container)
        self.main_layout.addWidget(self.scroll_area, 1)
        
        # Совместимость со старым кодом
        self.select_strategy_btn = QPushButton()
        self.select_strategy_btn.hide()
        
        self.category_selections = {}
        
    def showEvent(self, event):
        """При показе страницы загружаем стратегии"""
        super().showEvent(event)
        if not self._initialized:
            self._initialized = True
            QTimer.singleShot(100, self._load_content)
            
    def _clear_content(self):
        """Очищает контент"""
        # Удаляем все виджеты из content_layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._strategy_widget = None
        self._bat_table = None
        self.cmd_widget = None
        self.loading_label = None
            
    def _load_content(self):
        """Загружает контент в зависимости от режима"""
        try:
            from strategy_menu import get_strategy_launch_method
            mode = get_strategy_launch_method()
            
            # Если режим не изменился и контент уже загружен - пропускаем
            if mode == self._current_mode and (self._strategy_widget or self._bat_table):
                return
                
            self._current_mode = mode
            self._clear_content()
            
            if mode == "direct":
                self._load_direct_mode()
            else:
                self._load_bat_mode()
                
        except Exception as e:
            log(f"Ошибка загрузки контента: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            
            self._clear_content()
            error_label = QLabel(f"❌ Ошибка загрузки: {e}")
            error_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(error_label)
            
    def _load_direct_mode(self):
        """Загружает интерфейс для direct режима (Zapret 2)"""
        try:
            from strategy_menu.animated_side_panel import AnimatedSidePanel
            from strategy_menu.strategies_registry import registry
            from strategy_menu import get_direct_strategy_selections, get_default_selections
            
            # Заголовок секции
            section_header = QLabel("Выберите стратегию для каждого типа трафика")
            section_header.setStyleSheet("""
                QLabel {
                    color: #60cdff;
                    font-size: 14px;
                    font-weight: 600;
                    padding-bottom: 8px;
                }
            """)
            self.content_layout.addWidget(section_header)
            
            # Панель действий
            actions_card = SettingsCard()
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(8)
            
            reload_btn = ActionButton("Обновить", "fa5s.sync-alt")
            reload_btn.clicked.connect(self._reload_strategies)
            actions_layout.addWidget(reload_btn)
            
            folder_btn = ActionButton("Папка", "fa5s.folder-open")
            folder_btn.clicked.connect(self._open_folder)
            actions_layout.addWidget(folder_btn)
            
            clear_btn = ActionButton("Сбросить", "fa5s.broom")
            clear_btn.clicked.connect(self._clear_all)
            actions_layout.addWidget(clear_btn)
            
            actions_layout.addStretch()
            actions_card.add_layout(actions_layout)
            self.content_layout.addWidget(actions_card)
            
            # Загружаем выборы
            try:
                self.category_selections = get_direct_strategy_selections()
            except:
                self.category_selections = get_default_selections()
            
            # Создаём панель с вкладками категорий
            self._strategy_widget = AnimatedSidePanel()
            self._strategy_widget._tab_category_keys = []
            self._strategy_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            # Получаем данные из реестра
            tab_tooltips = registry.get_tab_tooltips_dict()
            tab_names = registry.get_tab_names_dict()
            self._strategy_widget.set_tab_names(tab_names)
            
            self._category_tab_indices = {}
            # Получаем только включенные категории на основе фильтров
            category_keys = registry.get_enabled_category_keys()
            
            # Очищаем существующие вкладки
            self._strategy_widget.clear()
            self._strategy_widget._tab_category_keys = []
            
            # Создаём вкладки только для включенных категорий (по порядку)
            for idx, category_key in enumerate(category_keys):
                category_info = registry.get_category_info(category_key)
                if not category_info:
                    continue
                
                display_name = category_info.full_name if self._strategy_widget.is_pinned else category_info.short_name
                
                # Заглушка с сохранённым category_key
                placeholder = QWidget()
                placeholder.setProperty("category_key", category_key)
                p_layout = QVBoxLayout(placeholder)
                p_layout.setContentsMargins(20, 20, 20, 20)
                p_layout.addWidget(QLabel("⏳ Нажмите для загрузки..."))
                p_layout.addStretch()
                
                # Добавляем вкладку и сохраняем индекс
                actual_index = self._strategy_widget.addTab(placeholder, display_name, category_key)
                self._category_tab_indices[category_key] = actual_index
                
                if category_key in tab_tooltips:
                    self._strategy_widget.setTabToolTip(actual_index, tab_tooltips[category_key])
            
            self._strategy_widget.currentChanged.connect(self._on_tab_changed)
            self._strategy_widget.setMinimumHeight(500)  # Увеличенная высота блока стратегий
            self.content_layout.addWidget(self._strategy_widget)
            
            # Отступ перед командной строкой
            self.content_layout.addSpacing(20)
            
            # Виджет командной строки (отдельный блок внизу)
            self.cmd_widget = CommandLineWidget()
            self.cmd_widget.setMinimumHeight(200)  # Увеличенная высота
            self.content_layout.addWidget(self.cmd_widget)
            
            # Загружаем первую вкладку
            QTimer.singleShot(50, lambda: self._load_category_tab(0))
            
            # Обновляем отображение текущих стратегий
            QTimer.singleShot(100, self._update_current_strategies_display)
            
            # Генерируем командную строку
            QTimer.singleShot(200, self._generate_command_line)
            
            log("Direct режим загружен", "INFO")
            
        except Exception as e:
            log(f"Ошибка загрузки direct режима: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            raise
            
    def _load_bat_mode(self):
        """Загружает интерфейс для bat режима (Zapret 1)"""
        try:
            from strategy_menu.strategy_table_widget_favorites import StrategyTableWithFavoritesFilter
            
            # Получаем strategy_manager
            strategy_manager = None
            if hasattr(self.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.strategy_manager
            elif hasattr(self.parent_app, 'parent_app') and hasattr(self.parent_app.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.parent_app.strategy_manager
            
            # Создаём таблицу - минималистичный дизайн
            self._bat_table = StrategyTableWithFavoritesFilter(strategy_manager=strategy_manager, parent=self)
            self._bat_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._bat_table.setMinimumHeight(500)  # Увеличенная высота
            
            # Подключаем сигнал автоприменения
            if hasattr(self._bat_table, 'strategy_applied'):
                self._bat_table.strategy_applied.connect(self._on_bat_strategy_applied)
            
            # Подключаем сигнал изменения избранных
            if hasattr(self._bat_table, 'favorites_changed'):
                self._bat_table.favorites_changed.connect(self._update_favorites_count)
            
            self.content_layout.addWidget(self._bat_table, 1)
            
            # Загружаем локальные стратегии
            if strategy_manager:
                QTimer.singleShot(100, self._load_bat_strategies)
            else:
                log("strategy_manager недоступен для bat режима", "WARNING")
            
            log("Bat режим загружен", "INFO")
            
        except Exception as e:
            log(f"Ошибка загрузки bat режима: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            raise
            
    def _load_bat_strategies(self):
        """Загружает список bat стратегий"""
        try:
            if not self._bat_table:
                return
                
            strategy_manager = None
            if hasattr(self.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.strategy_manager
            elif hasattr(self.parent_app, 'parent_app') and hasattr(self.parent_app.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.parent_app.strategy_manager
                
            if strategy_manager:
                strategies = strategy_manager.get_local_strategies_only()
                if strategies:
                    self._bat_table.populate_strategies(strategies)
                    self._update_favorites_count()
                    log(f"Загружено {len(strategies)} bat стратегий", "DEBUG")
                else:
                    log("Нет локальных bat стратегий", "WARNING")
                    
        except Exception as e:
            log(f"Ошибка загрузки bat стратегий: {e}", "ERROR")
            import traceback
            log(f"Traceback: {traceback.format_exc()}", "DEBUG")
    
    def _update_favorites_count(self):
        """Обновляет счётчик избранных стратегий"""
        try:
            from strategy_menu import get_favorite_strategies
            favorites = get_favorite_strategies("bat")
            count = len(favorites) if favorites else 0
            
            if count > 0:
                self.favorites_count_label.setText(f"★ {count} избранных")
                self.favorites_count_label.show()
            else:
                self.favorites_count_label.hide()
        except Exception as e:
            log(f"Ошибка обновления счётчика избранных: {e}", "DEBUG")
            self.favorites_count_label.hide()
            
    def _on_bat_strategy_applied(self, strategy_id: str, strategy_name: str):
        """Обработчик автоприменения bat стратегии"""
        self.strategy_selected.emit(strategy_id, strategy_name)
        
        # Показываем спиннер загрузки
        self.show_loading()
        
        # Автоматически запускаем стратегию через dpi_controller
        try:
            app = self.parent_app
            if hasattr(app, 'dpi_controller') and app.dpi_controller:
                # Сохраняем последнюю стратегию
                from config import set_last_strategy
                set_last_strategy(strategy_name)
                
                # Запускаем BAT стратегию
                app.dpi_controller.start_dpi_async(selected_mode=strategy_name)
                log(f"BAT стратегия запущена: {strategy_name}", "INFO")
                
                # Обновляем лейбл текущей стратегии
                self.current_strategy_label.setText(f"🎯 {strategy_name}")
                if hasattr(app, 'current_strategy_label'):
                    app.current_strategy_label.setText(strategy_name)
                if hasattr(app, 'current_strategy_name'):
                    app.current_strategy_name = strategy_name
                
                # Через 5 секунд показываем галочку успеха
                QTimer.singleShot(5000, self.show_success)
            else:
                self.show_success()
        except Exception as e:
            log(f"Ошибка применения BAT стратегии: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            self.show_success()  # При ошибке тоже убираем спиннер
        
    def reload_for_mode_change(self):
        """Перезагружает страницу при смене режима"""
        self._current_mode = None
        self._initialized = False
        self._clear_content()
        
        # Добавляем плейсхолдер
        self.loading_label = QLabel("⏳ Загрузка...")
        self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 13px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.loading_label)
        
        QTimer.singleShot(100, self._load_content)
            
    def _on_tab_changed(self, index):
        """При смене вкладки загружаем контент (direct режим)"""
        self._load_category_tab(index)
        
    def _load_category_tab(self, index):
        """Загружает контент вкладки категории (direct режим)"""
        if not self._strategy_widget:
            return
            
        try:
            from strategy_menu.strategies_registry import registry
            from strategy_menu.widgets import CompactStrategyItem
            from strategy_menu import get_direct_strategy_selections
            
            widget = self._strategy_widget.widget(index)
            if not widget:
                return
            
            # Получаем category_key из property или из списка
            category_key = widget.property("category_key")
            if not category_key and hasattr(self._strategy_widget, '_tab_category_keys'):
                keys = self._strategy_widget._tab_category_keys
                if 0 <= index < len(keys):
                    category_key = keys[index]
            
            if not category_key:
                log(f"Не удалось получить category_key для вкладки {index}", "WARNING")
                return
            
            # Проверяем, загружена ли уже вкладка
            if hasattr(widget, '_loaded') and widget._loaded:
                return
                
            # Получаем стратегии для категории
            strategies_dict = registry.get_category_strategies(category_key)
            if not strategies_dict:
                return
            
            # Очищаем существующий виджет
            old_layout = widget.layout()
            if old_layout:
                while old_layout.count():
                    item = old_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            else:
                old_layout = QVBoxLayout(widget)
                old_layout.setContentsMargins(0, 0, 0, 0)
            
            # Создаём scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea{background:transparent;border:none}QScrollBar:vertical{background:rgba(255,255,255,0.05);width:6px}QScrollBar::handle:vertical{background:rgba(255,255,255,0.2);border-radius:3px}")
            
            content = QWidget()
            content.setStyleSheet("background:transparent")
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(8, 8, 8, 8)
            content_layout.setSpacing(4)
            
            # Получаем текущий выбор
            try:
                selections = get_direct_strategy_selections()
                current_selection = selections.get(category_key, "none")
            except:
                current_selection = "none"
            
            # Создаём группу радиокнопок
            button_group = QButtonGroup(content)
            button_group.setExclusive(True)
            
            # Создаём элементы стратегий
            for strategy_id, strategy_data in strategies_dict.items():
                item = CompactStrategyItem(
                    strategy_id=strategy_id,
                    strategy_data=strategy_data,
                    parent=content
                )
                button_group.addButton(item.radio)
                if strategy_id == current_selection:
                    item.radio.setChecked(True)
                item.clicked.connect(lambda sid=strategy_id, cat=category_key: 
                                   self._on_strategy_item_clicked(cat, sid))
                content_layout.addWidget(item)
                
            content_layout.addStretch()
            scroll.setWidget(content)
            old_layout.addWidget(scroll)
            
            widget._loaded = True
            log(f"Загружена категория: {category_key}", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка загрузки категории {index}: {e}", "ERROR")
            
    def _on_strategy_item_clicked(self, category_key: str, strategy_id: str):
        """Обработчик клика по стратегии - сразу применяет и перезапускает winws2"""
        try:
            from strategy_menu import save_direct_strategy_selection, combine_strategies
            from config import set_last_strategy
            
            # Показываем спиннер загрузки
            self.show_loading()
            
            # Сохраняем выбор
            save_direct_strategy_selection(category_key, strategy_id)
            self.category_selections[category_key] = strategy_id
            
            # Обновляем отображение текущих стратегий
            self._update_current_strategies_display()
            
            # Обновляем командную строку
            if self.cmd_widget:
                QTimer.singleShot(100, self.cmd_widget.generate_command)
            
            # Создаём комбинированную стратегию
            combined = combine_strategies(**self.category_selections)
            
            # Создаем объект для запуска
            combined_data = {
                'id': 'COMBINED_DIRECT',
                'name': 'Прямой запуск',
                'is_combined': True,
                'args': combined['args'],
                'selections': self.category_selections.copy()
            }
            
            # Сохраняем в реестр
            set_last_strategy("COMBINED_DIRECT")
            
            # Перезапускаем winws2.exe с новыми настройками
            app = self.parent_app
            if hasattr(app, 'dpi_controller') and app.dpi_controller:
                app.dpi_controller.start_dpi_async(selected_mode=combined_data)
                log(f"Применена стратегия: {category_key} = {strategy_id}", "DEBUG")
                
                # Обновляем UI
                if hasattr(app, 'current_strategy_label'):
                    app.current_strategy_label.setText("Прямой запуск")
                if hasattr(app, 'current_strategy_name'):
                    app.current_strategy_name = "Прямой запуск"
                
                # Через 5 секунд показываем галочку успеха (winws требует время на запуск)
                QTimer.singleShot(5000, self.show_success)
            else:
                # Если нет dpi_controller - сразу показываем галочку
                self.show_success()
            
            self.strategy_selected.emit("combined", "Прямой запуск")
            
        except Exception as e:
            log(f"Ошибка применения: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            self.show_success()  # При ошибке тоже убираем спиннер
            
    def _reload_strategies(self):
        """Перезагружает стратегии (direct режим)"""
        try:
            from strategy_menu.strategies_registry import registry
            registry.reload_strategies()
            
            self._current_mode = None
            self._initialized = False
            self._clear_content()
            
            self.loading_label = QLabel("⏳ Перезагрузка...")
            self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
            self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(self.loading_label)
            
            QTimer.singleShot(100, self._load_content)
            
        except Exception as e:
            log(f"Ошибка перезагрузки: {e}", "ERROR")
            
    def _open_folder(self):
        """Открывает папку стратегий"""
        try:
            from config import STRATEGIES_FOLDER
            import os
            os.startfile(STRATEGIES_FOLDER)
        except Exception as e:
            log(f"Ошибка открытия папки: {e}", "ERROR")
            
    def _clear_all(self):
        """Сбрасывает все стратегии"""
        try:
            from strategy_menu import get_default_selections, save_direct_strategy_selections
            defaults = get_default_selections()
            save_direct_strategy_selections(defaults)
            self.category_selections = defaults
            
            QMessageBox.information(self.window(), "Готово", "Все стратегии сброшены")
            
            self._reload_strategies()
            
        except Exception as e:
            log(f"Ошибка сброса: {e}", "ERROR")
            
    def _generate_command_line(self):
        """Генерирует командную строку"""
        if self.cmd_widget:
            self.cmd_widget.generate_command()
            
    def _show_cmd(self):
        """Разворачивает/сворачивает виджет командной строки"""
        if hasattr(self, 'cmd_widget') and self.cmd_widget:
            self.cmd_widget.generate_command()
            
    def _apply_strategy(self):
        """Применяет выбранную стратегию (direct режим)"""
        try:
            from strategy_menu import combine_strategies, save_direct_strategy_selections
            
            save_direct_strategy_selections(self.category_selections)
            combined = combine_strategies(**self.category_selections)
            self.strategy_selected.emit("combined", "Прямой запуск")
            
            log("Стратегия применена", "INFO")
            
        except Exception as e:
            log(f"Ошибка применения: {e}", "ERROR")
            QMessageBox.critical(self.window(), "Ошибка", f"Не удалось применить стратегию:\n{e}")
        
    def _update_current_strategies_display(self):
        """Обновляет отображение списка активных стратегий"""
        try:
            from strategy_menu import get_strategy_launch_method, get_direct_strategy_selections
            from strategy_menu.strategies_registry import registry
            
            if get_strategy_launch_method() != "direct":
                return
            
            selections = get_direct_strategy_selections()
            
            # Собираем только активные (не "none") стратегии
            active = []
            for cat_key, strat_id in selections.items():
                if strat_id and strat_id != "none":
                    # Получаем полное имя категории
                    cat_info = registry.get_category_info(cat_key)
                    cat_name = cat_info.full_name if cat_info else cat_key
                    active.append(cat_name)
            
            if active:
                # Показываем до 6 категорий, потом "+N"
                if len(active) > 6:
                    display = ", ".join(active[:6]) + f" +{len(active)-6}"
                else:
                    display = ", ".join(active)
                self.current_strategy_label.setText(display)
            else:
                self.current_strategy_label.setText("Не выбрана")
                
        except Exception as e:
            log(f"Ошибка обновления отображения: {e}", "ERROR")
            
    def update_current_strategy(self, name: str):
        """Обновляет отображение текущей стратегии"""
        try:
            from strategy_menu import get_strategy_launch_method
            if get_strategy_launch_method() == "direct":
                self._update_current_strategies_display()
            elif name and name != "Автостарт DPI отключен":
                self.current_strategy_label.setText(name)
            else:
                self.current_strategy_label.setText("Не выбрана")
        except:
            if name and name != "Автостарт DPI отключен":
                self.current_strategy_label.setText(name)
            else:
                self.current_strategy_label.setText("Не выбрана")

    def show_loading(self):
        """Показывает спиннер загрузки при перезапуске DPI"""
        if hasattr(self, 'status_indicator'):
            self.status_indicator.show_loading()
            
    def show_success(self):
        """Показывает галочку после успешного запуска DPI"""
        if hasattr(self, 'status_indicator'):
            self.status_indicator.show_success()


# Для совместимости
Win11ComboBox = QComboBox
