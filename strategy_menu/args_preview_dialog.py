"""
Компактное окно информации о стратегии - Windows 11 Fluent Design
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTextEdit, QPushButton, QWidget,
                            QGraphicsDropShadowEffect, QApplication)
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                          pyqtSignal, QRectF, QObject, QEvent)
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QBrush, QPen, QCursor

from log import log


class _ArgsPreviewRightClickCloser(QObject):
    """
    App-wide right-click closer for ArgsPreviewDialog opened via RMB.

    Requirement:
    - If a preview window is open (opened via RMB), RMB anywhere closes it.
    - The same RMB should NOT open another preview (consume the event).
    """

    _APP_PROP = "zapretgui_args_preview_open"

    def __init__(self):
        super().__init__()
        self._dialogs = []
        self._installed = False

    def _ensure_installed(self) -> None:
        if self._installed:
            return
        app = QApplication.instance()
        if not app:
            return
        try:
            app.installEventFilter(self)
            self._installed = True
        except Exception:
            self._installed = False

    def _set_app_flag(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        has_open = False
        for dlg in list(self._dialogs):
            try:
                if dlg and dlg.isVisible() and (not getattr(dlg, "_hover_follow", False)):
                    has_open = True
                    break
            except RuntimeError:
                continue
            except Exception:
                continue
        try:
            app.setProperty(self._APP_PROP, bool(has_open))
        except Exception:
            pass

    def register(self, dialog: "ArgsPreviewDialog") -> None:
        if not dialog:
            return
        self._ensure_installed()
        if dialog not in self._dialogs:
            self._dialogs.append(dialog)

        # Hide/cancel hover-tooltip immediately when RMB preview opens.
        try:
            from .hover_tooltip import tooltip_manager
            tooltip_manager.hide_immediately()
        except Exception:
            pass

        self._set_app_flag()

    def unregister(self, dialog: "ArgsPreviewDialog") -> None:
        if not dialog:
            return
        try:
            if dialog in self._dialogs:
                self._dialogs.remove(dialog)
        except Exception:
            pass
        self._set_app_flag()

    def _close_topmost(self) -> bool:
        """
        Close the most recently registered visible interactive preview.

        Returns True if something was closed.
        """
        for dlg in reversed(list(self._dialogs)):
            try:
                if (not dlg) or (not dlg.isVisible()):
                    continue
                if getattr(dlg, "_hover_follow", False):
                    continue
                dlg.close_dialog()
                return True
            except RuntimeError:
                # C++ object deleted; ignore.
                continue
            except Exception:
                continue
        return False

    def eventFilter(self, obj, event):  # noqa: N802 (Qt override)
        try:
            et = event.type()
        except Exception:
            return False

        # Global ESC: close interactive RMB preview even without focus in the dialog.
        # Note: works while the app receives key events (i.e. is the active app).
        if et in (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride):
            try:
                if event.key() == Qt.Key.Key_Escape:
                    if self._close_topmost():
                        try:
                            event.accept()
                        except Exception:
                            pass
                        return True
            except Exception:
                pass
            return False

        if et == QEvent.Type.ContextMenu:
            if self._close_topmost():
                return True
            return False

        if et == QEvent.Type.MouseButtonPress:
            try:
                if event.button() == Qt.MouseButton.RightButton:
                    if self._close_topmost():
                        return True
            except Exception:
                pass
            return False

        return False


_args_preview_rmb_closer = _ArgsPreviewRightClickCloser()


class ArgsPreviewDialog(QDialog):
    """Компактное окно информации о стратегии - Fluent Design"""

    closed = pyqtSignal()
    rating_changed = pyqtSignal(str, str)  # strategy_id, new_rating (или None)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pinned = False
        self._hover_follow = False
        self._mouse_offset = None
        self._mouse_timer = QTimer(self)
        self._mouse_timer.timeout.connect(self._follow_cursor)
        
        self.setWindowFlags(self._popup_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)
        
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(150)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.init_ui()
        self.setWindowOpacity(0.0)

    def _sync_rmb_close_behavior(self) -> None:
        """
        Enable RMB-anywhere-to-close only for interactive preview (RMB-opened),
        not for hover-follow tooltip mode.
        """
        try:
            if self.isVisible() and (not self._hover_follow):
                _args_preview_rmb_closer.register(self)
            else:
                _args_preview_rmb_closer.unregister(self)
        except Exception:
            pass

    @staticmethod
    def _popup_flags():
        return (
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

    @staticmethod
    def _pinned_flags():
        # Tool window: stays above the app, but should NOT be topmost system-wide.
        return (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
        )

    @staticmethod
    def _tooltip_flags():
        return (
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
        )

    def set_hover_follow(self, enabled: bool, offset=None) -> None:
        """
        Hover-preview mode: show as a tooltip and follow the cursor.

        This prevents Qt.Popup auto-closing on click (which makes the preview
        "disappear" while selecting strategies).
        """
        enabled = bool(enabled)
        if bool(getattr(self, "_hover_follow", False)) == enabled:
            return
        self._hover_follow = enabled
        self._mouse_offset = offset

        if enabled:
            # Tooltip should not steal focus.
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            # And it should never block clicks/hover on the underlying UI.
            # (Some platforms/drivers can still treat tooltip windows as hit-testable.)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        else:
            try:
                self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
            except Exception:
                pass
            try:
                self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            except Exception:
                pass

        self._apply_window_flags()

        if enabled and not self._pinned:
            self._mouse_timer.start(16)  # ~60 FPS
        else:
            self._mouse_timer.stop()
        self._sync_rmb_close_behavior()

    def _apply_window_flags(self) -> None:
        was_visible = False
        try:
            was_visible = self.isVisible()
        except Exception:
            was_visible = False
        try:
            pos = self.pos()
        except Exception:
            pos = None
        try:
            opacity = float(self.windowOpacity())
        except Exception:
            opacity = 1.0

        try:
            if self._pinned:
                flags = self._pinned_flags()
            elif self._hover_follow:
                flags = self._tooltip_flags()
            else:
                flags = self._popup_flags()

            self.setWindowFlags(flags)
            self.setModal(False)
            if was_visible:
                self.show()
                if pos is not None:
                    self.move(pos)
                self.setWindowOpacity(opacity)
            self._sync_rmb_close_behavior()
        except Exception:
            pass

    def set_pinned(self, pinned: bool) -> None:
        pinned = bool(pinned)
        if bool(getattr(self, "_pinned", False)) == pinned:
            return
        self._pinned = pinned
        if pinned:
            self._mouse_timer.stop()
        elif self._hover_follow:
            self._mouse_timer.start(16)
        self._apply_window_flags()
        self._sync_rmb_close_behavior()

    def _follow_cursor(self):
        if self._pinned or (not self._hover_follow) or (not self.isVisible()):
            self._mouse_timer.stop()
            return
        # Keep hover-preview strictly within its source widget (strategies list).
        try:
            sw = getattr(self, "source_widget", None)
            if sw is not None:
                if (not sw.isVisible()) or (not sw.window().isVisible()):
                    self.close_dialog()
                    return
                w = QApplication.widgetAt(QCursor.pos())
                if (w is None) or (w is not sw and (not sw.isAncestorOf(w))):
                    self.close_dialog()
                    return
        except Exception:
            pass
        self._position_near_cursor(QCursor.pos())

    def _position_near_cursor(self, cursor_pos):
        try:
            from PyQt6.QtCore import QPoint
            offset = self._mouse_offset if self._mouse_offset is not None else QPoint(18, 18)
            target_pos = cursor_pos + offset
        except Exception:
            target_pos = cursor_pos

        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            try:
                if target_pos.x() + self.width() > screen_rect.right():
                    target_pos.setX(cursor_pos.x() - self.width() - 10)
                if target_pos.y() + self.height() > screen_rect.bottom():
                    target_pos.setY(cursor_pos.y() - self.height() - 10)
                if target_pos.x() < screen_rect.left():
                    target_pos.setX(screen_rect.left() + 5)
                if target_pos.y() < screen_rect.top():
                    target_pos.setY(screen_rect.top() + 5)
            except Exception:
                pass
        try:
            self.move(target_pos)
        except Exception:
            pass

    def wheelEvent(self, event):
        """
        Do not block page scrolling when the preview is under the cursor.

        If the wheel is over the args text area and it can scroll, keep default
        behavior. Otherwise, forward scrolling to the source_widget (usually a
        QScrollArea page), so users can keep scrolling the strategies list/page
        while the preview is visible.
        """
        try:
            pos = event.position().toPoint()
            child = self.childAt(pos)
        except Exception:
            child = None

        # Allow scrolling inside args_text if there is room to scroll.
        try:
            if child and (child is self.args_text or self.args_text.isAncestorOf(child)):
                sb = self.args_text.verticalScrollBar()
                dy = event.angleDelta().y()
                if (dy > 0 and sb.value() > sb.minimum()) or (dy < 0 and sb.value() < sb.maximum()):
                    return super().wheelEvent(event)
        except Exception:
            pass

        src = getattr(self, "source_widget", None)
        if src is None:
            event.ignore()
            return

        try:
            sb = src.verticalScrollBar()
        except Exception:
            event.ignore()
            return

        try:
            steps = int(event.angleDelta().y() / 120)
        except Exception:
            steps = 0

        if steps:
            delta = steps * max(10, int(sb.singleStep() or 10)) * 3
        else:
            # Smooth scrolling devices
            try:
                delta = int(event.pixelDelta().y() or 0)
            except Exception:
                delta = 0

        if delta:
            sb.setValue(sb.value() - delta)
            event.accept()
            return

        event.ignore()

    def init_ui(self):
        """Инициализация компактного интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # Контейнер
        self.container = QWidget()
        self.container.setObjectName("fluentContainer")
        
        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)
        
        # === Заголовок ===
        header = QHBoxLayout()
        header.setSpacing(8)
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        header.addWidget(self.title_label, 1)
        
        # Кнопка закрытия
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_dialog)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.5);
                border: none;
                font-size: 18px;
                font-weight: 400;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }
        """)
        header.addWidget(close_btn)
        container_layout.addLayout(header)
        
        # === Автор ===
        self.author_label = QLabel()
        self.author_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        self.author_label.hide()
        container_layout.addWidget(self.author_label)
        
        # === Информационная строка ===
        self.info_panel = QLabel()
        self.info_panel.setWordWrap(True)
        self.info_panel.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.7);
                font-size: 11px;
                padding: 6px 10px;
                background: rgba(255,255,255,0.04);
                border-radius: 6px;
            }
        """)
        self.info_panel.hide()
        container_layout.addWidget(self.info_panel)
        
        # === Аргументы ===
        self.args_widget = QWidget()
        args_layout = QVBoxLayout(self.args_widget)
        args_layout.setContentsMargins(0, 4, 0, 0)
        args_layout.setSpacing(6)
        
        # Заголовок аргументов
        args_header = QHBoxLayout()
        args_title = QLabel("Аргументы запуска:")
        args_title.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 11px;")
        args_header.addWidget(args_title)
        args_header.addStretch()
        
        self.copy_button = QPushButton("Копировать")
        self.copy_button.setFixedHeight(22)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self.copy_args)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.7);
                border: none;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }
        """)
        args_header.addWidget(self.copy_button)
        args_layout.addLayout(args_header)
        
        # Текст аргументов
        self.args_text = QTextEdit()
        self.args_text.setReadOnly(True)
        self.args_text.setStyleSheet("""
            QTextEdit {
                background: rgba(0,0,0,0.2);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                color: rgba(255,255,255,0.7);
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 10px;
                padding: 8px;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.15);
                border-radius: 2px;
            }
        """)
        self.args_text.setMinimumHeight(60)
        self.args_text.setMaximumHeight(120)
        args_layout.addWidget(self.args_text)
        
        container_layout.addWidget(self.args_widget)
        
        # === Метка стратегии ===
        self.label_widget = QLabel()
        self.label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_widget.hide()
        container_layout.addWidget(self.label_widget)
        
        # === Кнопки оценки ===
        rating_widget = QWidget()
        rating_layout = QHBoxLayout(rating_widget)
        rating_layout.setContentsMargins(0, 4, 0, 0)
        rating_layout.setSpacing(8)
        
        rating_label = QLabel("Оценить:")
        rating_label.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px;")
        rating_layout.addWidget(rating_label)
        rating_layout.addStretch()
        
        self.working_button = QPushButton("РАБОЧАЯ")
        self.working_button.setFixedHeight(26)
        self.working_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.working_button.clicked.connect(lambda: self._toggle_rating('working'))
        rating_layout.addWidget(self.working_button)
        
        self.broken_button = QPushButton("НЕРАБОЧАЯ")
        self.broken_button.setFixedHeight(26)
        self.broken_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.broken_button.clicked.connect(lambda: self._toggle_rating('broken'))
        rating_layout.addWidget(self.broken_button)
        
        container_layout.addWidget(rating_widget)
        
        # === Подсказка ===
        hint = QLabel("ESC — закрыть")
        hint.setStyleSheet("color: rgba(255,255,255,0.25); font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint)
        
        main_layout.addWidget(self.container)
        self.setFixedWidth(420)
        
        # Обновляем стили кнопок
        self._update_rating_buttons()
        
    def paintEvent(self, event):
        """Рисуем Fluent фон"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.container.geometry()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)
        
        # Градиент фона
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0, QColor(48, 48, 48, 252))
        gradient.setColorAt(1, QColor(36, 36, 36, 252))
        painter.fillPath(path, QBrush(gradient))
        
        # Рамка
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
        painter.drawPath(path)
        
    def set_strategy_data(
        self,
        strategy_data,
        strategy_id=None,
        source_widget=None,
        category_key=None,
        rating_getter=None,
        rating_toggler=None,
    ):
        """Устанавливает данные стратегии"""
        self.current_strategy_id = strategy_id
        self.current_category_key = category_key
        self.source_widget = source_widget
        self._rating_getter = rating_getter
        self._rating_toggler = rating_toggler
        
        # Заголовок
        name = strategy_data.get('name', strategy_id or 'Стратегия')
        self.title_label.setText(name)
        
        # Автор
        author = strategy_data.get('author')
        if author and author != 'unknown':
            self.author_label.setText(f"Автор: {author}")
            self.author_label.show()
        else:
            self.author_label.hide()
        
        # Инфо панель
        info_parts = []
        if strategy_id:
            info_parts.append(f"<span style='color:#60cdff'>ID:</span> {strategy_id}")
        version = strategy_data.get('version')
        if version:
            info_parts.append(f"<span style='color:#4ade80'>v{version}</span>")
        provider = strategy_data.get('provider', 'universal')
        provider_names = {'universal': 'All', 'rostelecom': 'Ростелеком', 'mts': 'МТС', 
                         'megafon': 'МегаФон', 'beeline': 'Билайн'}
        info_parts.append(f"<span style='color:#a78bfa'>{provider_names.get(provider, provider)}</span>")
        
        if info_parts:
            self.info_panel.setText(" • ".join(info_parts))
            self.info_panel.show()
        else:
            self.info_panel.hide()
        
        # Аргументы
        args = strategy_data.get('args', '')
        if args:
            self.args_text.setPlainText(args[:500] + ('...' if len(args) > 500 else ''))
            self.original_args = args
            self.args_widget.show()
        else:
            self.args_widget.hide()
            self.original_args = ""
        
        # Метка
        from launcher_common.constants import LABEL_TEXTS, LABEL_COLORS
        label = strategy_data.get('label')
        if label and label in LABEL_TEXTS:
            self.label_widget.setText(LABEL_TEXTS[label])
            self.label_widget.setStyleSheet(f"""
                QLabel {{
                    color: {LABEL_COLORS[label]};
                    font-weight: 600;
                    font-size: 11px;
                    padding: 4px 12px;
                    border: 1px solid {LABEL_COLORS[label]};
                    border-radius: 4px;
                }}
            """)
            self.label_widget.show()
        else:
            self.label_widget.hide()
        
        self._update_rating_buttons()
        self.adjustSize()
    
    def _get_rating_button_style(self, is_active, rating_type):
        """Стиль кнопки оценки"""
        if rating_type == 'working':
            color = '#4ade80'
        else:
            color = '#f87171'
        
        if is_active:
            return f"""
                QPushButton {{
                    background: {color};
                    color: #000;
                    border: none;
                    border-radius: 4px;
                    padding: 0 12px;
                    font-size: 10px;
                    font-weight: 600;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background: rgba(255,255,255,0.06);
                    color: rgba(255,255,255,0.6);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 4px;
                    padding: 0 12px;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.1);
                    color: {color};
                    border-color: {color};
                }}
            """
    
    def _update_rating_buttons(self):
        """Обновляет кнопки оценки"""
        if not hasattr(self, 'current_strategy_id') or not self.current_strategy_id:
            self.working_button.setStyleSheet(self._get_rating_button_style(False, 'working'))
            self.broken_button.setStyleSheet(self._get_rating_button_style(False, 'broken'))
            return

        category_key = getattr(self, 'current_category_key', None)
        current_rating = None
        if getattr(self, "_rating_getter", None):
            try:
                current_rating = self._rating_getter(self.current_strategy_id, category_key)
            except Exception:
                current_rating = None
        else:
            from strategy_menu import get_strategy_rating
            current_rating = get_strategy_rating(self.current_strategy_id, category_key)

        self.working_button.setStyleSheet(self._get_rating_button_style(current_rating == 'working', 'working'))
        self.broken_button.setStyleSheet(self._get_rating_button_style(current_rating == 'broken', 'broken'))
    
    def _toggle_rating(self, rating):
        """Переключает оценку"""
        if not hasattr(self, 'current_strategy_id') or not self.current_strategy_id:
            return

        category_key = getattr(self, 'current_category_key', None)
        new_rating = None
        if getattr(self, "_rating_toggler", None):
            try:
                new_rating = self._rating_toggler(self.current_strategy_id, rating, category_key)
            except Exception:
                new_rating = None
        else:
            from strategy_menu import toggle_strategy_rating
            new_rating = toggle_strategy_rating(self.current_strategy_id, rating, category_key)
        self._update_rating_buttons()
        # Уведомляем об изменении рейтинга
        self.rating_changed.emit(self.current_strategy_id, new_rating or "")
    
    def copy_args(self):
        """Копирует аргументы"""
        if hasattr(self, 'original_args'):
            QApplication.clipboard().setText(self.original_args)
            self.copy_button.setText("✓ Скопировано")
            self.copy_button.setStyleSheet("""
                QPushButton {
                    background: rgba(74, 222, 128, 0.2);
                    color: #4ade80;
                    border: none;
                    border-radius: 4px;
                    padding: 0 10px;
                    font-size: 11px;
                }
            """)
            QTimer.singleShot(1500, self._reset_copy_button)
    
    def _reset_copy_button(self):
        self.copy_button.setText("Копировать")
        self.copy_button.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.7);
                border: none;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }
        """)
    
    def show_animated(self, pos=None):
        if self._hover_follow and not self._pinned:
            self._position_near_cursor(QCursor.pos())
            self._mouse_timer.start(16)
        elif pos:
            self.move(pos)
        self.show()
        self._sync_rmb_close_behavior()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
    
    def close_dialog(self):
        self.hide_animated()
    
    def hide_animated(self):
        self._mouse_timer.stop()
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        try:
            self.opacity_animation.finished.disconnect(self._on_hide_finished)
        except Exception:
            pass
        self.opacity_animation.finished.connect(self._on_hide_finished)
        self.opacity_animation.start()
    
    def _on_hide_finished(self):
        try:
            self.opacity_animation.finished.disconnect(self._on_hide_finished)
        except:
            pass
        try:
            _args_preview_rmb_closer.unregister(self)
        except Exception:
            pass
        self.hide()
        self.closed.emit()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_dialog()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            _args_preview_rmb_closer.unregister(self)
        except Exception:
            pass
        return super().closeEvent(event)


class StrategyPreviewManager:
    """Менеджер окна предпросмотра"""

    _instance = None
    _rating_change_callbacks = []  # Callback'и для уведомления об изменении рейтинга

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.preview_dialog = None
            cls._instance._rating_change_callbacks = []
        return cls._instance

    def add_rating_change_callback(self, callback):
        """Добавляет callback для уведомления об изменении рейтинга"""
        if callback not in self._rating_change_callbacks:
            self._rating_change_callbacks.append(callback)

    def remove_rating_change_callback(self, callback):
        """Удаляет callback"""
        if callback in self._rating_change_callbacks:
            self._rating_change_callbacks.remove(callback)

    def _on_rating_changed(self, strategy_id, new_rating):
        """Вызывается при изменении рейтинга стратегии"""
        for callback in self._rating_change_callbacks:
            try:
                callback(strategy_id, new_rating)
            except Exception as e:
                log(f"Ошибка в callback рейтинга: {e}", "ERROR")

    def show_preview(self, widget, strategy_id, strategy_data, category_key=None, rating_getter=None, rating_toggler=None):
        # Проверяем что старый диалог ещё существует и не удалён Qt
        try:
            if self.preview_dialog is not None:
                # Проверяем что C++ объект не удалён
                try:
                    if self.preview_dialog.isVisible():
                        self.preview_dialog.close()
                except RuntimeError:
                    # C++ объект уже удалён
                    pass
                self.preview_dialog = None
        except RuntimeError:
            self.preview_dialog = None

        self.preview_dialog = ArgsPreviewDialog(widget)
        self.preview_dialog.closed.connect(self._on_preview_closed)
        self.preview_dialog.rating_changed.connect(self._on_rating_changed)
        self.preview_dialog.set_strategy_data(
            strategy_data,
            strategy_id,
            source_widget=widget,
            category_key=category_key,
            rating_getter=rating_getter,
            rating_toggler=rating_toggler,
        )

        cursor_pos = widget.mapToGlobal(widget.rect().center())

        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            if cursor_pos.x() + self.preview_dialog.width() > screen_rect.right():
                cursor_pos.setX(screen_rect.right() - self.preview_dialog.width() - 10)
            if cursor_pos.y() + 300 > screen_rect.bottom():
                cursor_pos.setY(screen_rect.bottom() - 300)

        self.preview_dialog.show_animated(cursor_pos)
    
    def _on_preview_closed(self):
        if self.preview_dialog is not None:
            try:
                self.preview_dialog.deleteLater()
            except RuntimeError:
                pass  # C++ объект уже удалён
            self.preview_dialog = None
    
    def cleanup(self):
        if self.preview_dialog is not None:
            try:
                self.preview_dialog.close()
                self.preview_dialog.deleteLater()
            except RuntimeError:
                pass  # C++ объект уже удалён
            self.preview_dialog = None


preview_manager = StrategyPreviewManager()
