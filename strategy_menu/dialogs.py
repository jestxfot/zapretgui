# strategy_menu/dialogs.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextBrowser, QPushButton
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont, QColor

from log import log
from launcher_common.constants import LABEL_TEXTS, LABEL_COLORS
from ui.theme import get_theme_tokens

class StrategyInfoDialog(QDialog):
    """Отдельное окно для отображения подробной информации о стратегии."""
    
    def __init__(self, parent=None, strategy_manager=None):
        super().__init__(parent)
        self.strategy_manager = strategy_manager
        self.setWindowTitle("Информация о стратегии")
        self.resize(700, 500)
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса окна информации."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        self.strategy_title = QLabel("Информация о стратегии")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self.strategy_title.setFont(title_font)
        self.strategy_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.strategy_title)
        
        # Детальная информация
        self.strategy_info = QTextBrowser()
        self.strategy_info.setOpenExternalLinks(True)
        layout.addWidget(self.strategy_info)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        close_button.setMaximumWidth(100)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self._apply_theme_styles()

    def _apply_theme_styles(self):
        tokens = get_theme_tokens()
        if tokens.is_light:
            browser_bg = "rgba(255, 255, 255, 0.92)"
            browser_border = "rgba(0, 0, 0, 0.12)"
        else:
            browser_bg = "rgba(0, 0, 0, 0.22)"
            browser_border = "rgba(255, 255, 255, 0.10)"

        self.strategy_title.setStyleSheet(f"color: {tokens.fg};")
        self.strategy_info.setStyleSheet(
            f"""
            QTextBrowser {{
                background-color: {browser_bg};
                border: 1px solid {browser_border};
                border-radius: 6px;
                color: {tokens.fg};
                font-size: 9pt;
                padding: 6px;
            }}
            """
        )
    
    def display_strategy_info(self, strategy_id, strategy_name):
        """Отображает информацию о выбранной стратегии."""
        try:
            strategies = self.strategy_manager.get_strategies_list()
            if strategy_id in strategies:
                strategy_info = strategies[strategy_id]
                
                # Устанавливаем заголовок
                title_text = strategy_info.get('name') or strategy_id
                
                # Добавляем метку
                label = strategy_info.get('label') or None
                if label and label in LABEL_TEXTS:
                    title_text += f" [{LABEL_TEXTS[label]}]"
                    label_color = LABEL_COLORS.get(label, "#000000")
                    self.strategy_title.setStyleSheet(f"color: {label_color};")
                else:
                    self.strategy_title.setStyleSheet("")
                
                self.strategy_title.setText(title_text)
                
                # Формируем HTML
                html = self._format_strategy_info_html(strategy_info, label)
                self.strategy_info.setHtml(html)
            else:
                self.strategy_info.setHtml(
                    "<p style='color:red; text-align: center;'>Информация не найдена</p>"
                )
        except Exception as e:
            log(f"Ошибка при получении информации: {str(e)}", level="❌ ERROR")
            self.strategy_info.setHtml(
                f"<p style='color:red; text-align: center;'>Ошибка: {str(e)}</p>"
            )
    
    def _format_strategy_info_html(self, strategy_info, label):
        """Форматирует HTML для отображения информации о стратегии."""
        tokens = get_theme_tokens()
        table_divider = "rgba(0, 0, 0, 0.10)" if tokens.is_light else "rgba(255, 255, 255, 0.08)"
        html = f"""<style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 5px;
                color: {tokens.fg};
                background-color: transparent;
                font-size: 9pt;
            }}
            h4 {{ margin: 10px 0 6px 0; }}
            a {{ color: {tokens.accent_hex}; }}
            table {{ border-collapse: collapse; }}
            td {{ padding: 3px 4px; border-bottom: 1px solid {table_divider}; }}
        </style>"""
        
        # Метка
        if label and label in LABEL_TEXTS:
            label_color = LABEL_COLORS.get(label, '#000000')
            qcolor = QColor(label_color)
            yiq = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000 if qcolor.isValid() else 0
            label_fg = "#111111" if yiq >= 160 else "#f5f5f5"
            html += f"""<p style='text-align: center; padding: 5px; 
                background-color: {label_color}; 
                color: {label_fg}; font-weight: bold; font-size: 10pt; 
                border-radius: 3px;'>{LABEL_TEXTS[label]}</p>"""
        
        # Описание
        description = strategy_info.get('description') or 'Описание отсутствует'
        html += f"<h4>Описание</h4><p>{description}</p>"
        
        # Основная информация
        html += "<h4>Информация</h4><table style='width: 100%;'>"
        
        provider = strategy_info.get('provider') or 'universal'
        html += f"<tr><td><b>Провайдер:</b></td><td>{provider}</td></tr>"
        
        version = strategy_info.get('version') or 'неизвестно'
        html += f"<tr><td><b>Версия:</b></td><td>{version}</td></tr>"
        
        author = strategy_info.get('author') or 'неизвестно'
        html += f"<tr><td><b>Автор:</b></td><td>{author}</td></tr>"
        
        date = strategy_info.get('date') or strategy_info.get('updated') or 'неизвестно'
        html += f"<tr><td><b>Дата:</b></td><td>{date}</td></tr>"
        
        html += "</table>"
        
        # Технические параметры
        html += "<h4>Технические параметры</h4>"
        
        ports = strategy_info.get('ports', [])
        if ports:
            ports_str = ", ".join(map(str, ports)) if isinstance(ports, list) else str(ports)
            html += f"<p><b>Порты:</b> {ports_str}</p>"
        
        host_lists = strategy_info.get('host_lists', [])
        if host_lists and not (isinstance(host_lists, list) and 'ВСЕ САЙТЫ' in host_lists):
            html += "<p><b>Списки хостов:</b> "
            if isinstance(host_lists, list):
                html += ", ".join(host_lists[:3])
                if len(host_lists) > 3:
                    html += f" и еще {len(host_lists) - 3}"
            else:
                html += str(host_lists)
            html += "</p>"
        elif 'ВСЕ САЙТЫ' in str(host_lists):
            html += "<p><b>Режим:</b> <span style='color:#00ff00;'>• ВСЕ САЙТЫ</span></p>"
        
        return html

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._apply_theme_styles()
        except Exception:
            pass
        super().changeEvent(event)
