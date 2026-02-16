# ui/pages/base_page.py
"""Базовый класс для страниц"""

import sys
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy, QPlainTextEdit, QTextEdit
from PyQt6.QtGui import QFont
from ui.theme import get_theme_tokens, bump_theme_refresh_counter


class ScrollBlockingPlainTextEdit(QPlainTextEdit):
    """QPlainTextEdit который не пропускает прокрутку к родителю"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Запрещаем перетаскивание окна при взаимодействии с редактором
        self.setProperty("noDrag", True)
    
    def wheelEvent(self, event):
        scrollbar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        
        # Если прокручиваем вверх и уже в начале - блокируем
        if delta > 0 and scrollbar.value() == scrollbar.minimum():
            event.accept()
            return
        
        # Если прокручиваем вниз и уже в конце - блокируем  
        if delta < 0 and scrollbar.value() == scrollbar.maximum():
            event.accept()
            return
        
        super().wheelEvent(event)
        event.accept()


class ScrollBlockingTextEdit(QTextEdit):
    """QTextEdit который не пропускает прокрутку к родителю"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Запрещаем перетаскивание окна при взаимодействии с редактором
        self.setProperty("noDrag", True)
    
    def wheelEvent(self, event):
        scrollbar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        
        # Если прокручиваем вверх и уже в начале - блокируем
        if delta > 0 and scrollbar.value() == scrollbar.minimum():
            event.accept()
            return
        
        # Если прокручиваем вниз и уже в конце - блокируем  
        if delta < 0 and scrollbar.value() == scrollbar.maximum():
            event.accept()
            return
        
        super().wheelEvent(event)
        event.accept()


class BasePage(QScrollArea):
    """Базовый класс для страниц контента"""
    
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._theme_refresh_pending_when_hidden = False
        self._last_theme_refresh_key: tuple[str, str, str] | None = None
        
        # Настройка ScrollArea
        self.setWidgetResizable(True)
        # На Windows принудительно показываем вертикальный скроллбар:
        # некоторые стили/настройки ОС делают скроллбары "transient" и они почти
        # не появляются/слишком быстро скрываются.
        if sys.platform.startswith("win"):
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        # ✅ Отключаем горизонтальный скролл - контент должен вписываться в ширину
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # Scrollbar styling is centralized in ui/theme.py tokens.
        # BasePage only ensures transparency and no frame.
        self.setStyleSheet(
            """
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            """
        )
        
        # Контейнер контента (с явным родителем!)
        self.content = QWidget(self)  # ✅ Родитель = self (QScrollArea)
        self.content.setStyleSheet("background-color: transparent;")
        # ✅ Политика размера: предпочитает минимальную ширину, не растягивается бесконечно
        self.content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setWidget(self.content)
        
        # Основной layout
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(16)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # ✅ Ограничиваем ширину контента чтобы не выходил за границы
        self.layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMaximumSize)
        
        # Заголовок страницы
        self.title_label = QLabel(title)
        self.title_label.setProperty("tone", "primary")
        self.title_label.setStyleSheet(
            """
            QLabel {
                font-size: 28px;
                font-weight: 600;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                padding-bottom: 4px;
            }
            """
        )
        self.layout.addWidget(self.title_label)
        
        # Подзаголовок
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setProperty("tone", "muted")
            self.subtitle_label.setStyleSheet(
                """
                QLabel {
                    font-size: 13px;
                    padding-bottom: 16px;
                }
                """
            )
            self.subtitle_label.setWordWrap(True)
            self.layout.addWidget(self.subtitle_label)

        self._apply_theme_styles()

    def _build_theme_refresh_key(self, tokens) -> tuple[str, str, str]:
        display_font_family = getattr(tokens, "font_family_display_qss", tokens.font_family_qss)
        return (str(tokens.theme_name), str(tokens.font_family_qss), str(display_font_family))

    def _apply_theme_styles(self) -> None:
        if self._applying_theme_styles:
            return
        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            theme_key = self._build_theme_refresh_key(tokens)
            if theme_key == self._last_theme_refresh_key:
                return

            display_font_family = getattr(tokens, "font_family_display_qss", tokens.font_family_qss)
            self.setStyleSheet(
                """
                QScrollArea {
                    background-color: transparent;
                    border: none;
                }
                """
            )
            self.content.setStyleSheet("background-color: transparent;")
            self.title_label.setStyleSheet(
                f"""
                QLabel {{
                    font-size: 28px;
                    font-weight: 600;
                    font-family: {display_font_family};
                    padding-bottom: 4px;
                }}
                """
            )
            if hasattr(self, "subtitle_label") and self.subtitle_label is not None:
                self.subtitle_label.setStyleSheet(
                    f"""
                    QLabel {{
                        font-size: 13px;
                        font-family: {tokens.font_family_qss};
                        padding-bottom: 16px;
                    }}
                    """
                )

            self._last_theme_refresh_key = theme_key
        finally:
            self._applying_theme_styles = False

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        try:
            page_key = self.__class__.__name__
            object_name = self.objectName()
            if object_name:
                page_key = f"{page_key}#{object_name}"
            bump_theme_refresh_counter(page_key)
        except Exception:
            pass
        self._apply_theme_styles()

    def showEvent(self, event):  # noqa: N802 (Qt override)
        super().showEvent(event)
        if not self._theme_refresh_pending_when_hidden:
            return
        self._theme_refresh_pending_when_hidden = False
        self._schedule_theme_refresh()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                try:
                    tokens = get_theme_tokens()
                    if self._build_theme_refresh_key(tokens) == self._last_theme_refresh_key:
                        return super().changeEvent(event)
                except Exception:
                    pass
                if not self.isVisible():
                    self._theme_refresh_pending_when_hidden = True
                    return super().changeEvent(event)
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)
        
    def add_widget(self, widget: QWidget, stretch: int = 0):
        """Добавляет виджет на страницу"""
        self.layout.addWidget(widget, stretch)
        
    def add_spacing(self, height: int = 16):
        """Добавляет вертикальный отступ"""
        from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
        spacer = QSpacerItem(0, height, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.layout.addItem(spacer)
        
    def add_section_title(self, text: str, return_widget: bool = False):
        """Добавляет заголовок секции"""
        tokens = get_theme_tokens()
        label = QLabel(text)
        label.setProperty("tone", "primary")
        label.setStyleSheet(
            f"""
            QLabel {{
                font-size: 13px;
                font-weight: 600;
                font-family: {tokens.font_family_qss};
                padding-top: 8px;
                padding-bottom: 4px;
            }}
            """
        )
        self.layout.addWidget(label)
        if return_widget:
            return label
