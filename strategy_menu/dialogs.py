# strategy_menu/dialogs.py

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from qfluentwidgets import MessageBoxBase, SubtitleLabel, TextBrowser

from log import log
from launcher_common.constants import LABEL_TEXTS, LABEL_COLORS
from ui.theme import get_theme_tokens


class StrategyInfoDialog(MessageBoxBase):
    """Отдельное окно для отображения подробной информации о стратегии."""

    def __init__(self, parent=None, strategy_manager=None):
        if parent and not parent.isWindow():
            parent = parent.window()
        super().__init__(parent)
        self.strategy_manager = strategy_manager

        # --- Заголовок ---
        self.strategy_title = SubtitleLabel("Информация о стратегии", self.widget)
        self.strategy_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewLayout.addWidget(self.strategy_title)

        # --- Детальная информация ---
        self.strategy_info = TextBrowser(self.widget)
        self.strategy_info.setOpenExternalLinks(True)
        self.strategy_info.setMinimumSize(560, 340)
        self.viewLayout.addWidget(self.strategy_info, 1)

        # --- Кнопки ---
        self.yesButton.setText("Закрыть")
        self.hideCancelButton()

        self.widget.setMinimumSize(620, 500)

    def display_strategy_info(self, strategy_id, strategy_name):
        """Отображает информацию о выбранной стратегии."""
        try:
            strategies = self.strategy_manager.get_strategies_list()
            if strategy_id in strategies:
                strategy_info = strategies[strategy_id]

                title_text = strategy_info.get('name') or strategy_id
                label = strategy_info.get('label') or None
                if label and label in LABEL_TEXTS:
                    title_text += f" [{LABEL_TEXTS[label]}]"
                    label_color = LABEL_COLORS.get(label, "")
                    if label_color:
                        self.strategy_title.setStyleSheet(f"color: {label_color};")
                    else:
                        self.strategy_title.setStyleSheet("")
                else:
                    self.strategy_title.setStyleSheet("")

                self.strategy_title.setText(title_text)

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

        if label and label in LABEL_TEXTS:
            label_color = LABEL_COLORS.get(label, '#000000')
            qcolor = QColor(label_color)
            yiq = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000 if qcolor.isValid() else 0
            label_fg = "#111111" if yiq >= 160 else "#f5f5f5"
            html += f"""<p style='text-align: center; padding: 5px;
                background-color: {label_color};
                color: {label_fg}; font-weight: bold; font-size: 10pt;
                border-radius: 3px;'>{LABEL_TEXTS[label]}</p>"""

        description = strategy_info.get('description') or 'Описание отсутствует'
        html += f"<h4>Описание</h4><p>{description}</p>"

        html += "<h4>Информация</h4><table style='width: 100%;'>"
        html += f"<tr><td><b>Провайдер:</b></td><td>{strategy_info.get('provider') or 'universal'}</td></tr>"
        html += f"<tr><td><b>Версия:</b></td><td>{strategy_info.get('version') or 'неизвестно'}</td></tr>"
        html += f"<tr><td><b>Автор:</b></td><td>{strategy_info.get('author') or 'неизвестно'}</td></tr>"
        date = strategy_info.get('date') or strategy_info.get('updated') or 'неизвестно'
        html += f"<tr><td><b>Дата:</b></td><td>{date}</td></tr>"
        html += "</table>"

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
