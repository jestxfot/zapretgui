# ui/pages/custom_domains_page.py
"""Страница управления пользовательскими доменами (other.user.txt)."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit
)
try:
    from qfluentwidgets import LineEdit, InfoBar
    _HAS_FLUENT = True
except ImportError:
    LineEdit = QLineEdit
    InfoBar = None
    _HAS_FLUENT = False

try:
    from qfluentwidgets import StrongBodyLabel, BodyLabel, CaptionLabel
    _HAS_FLUENT_LABELS = True
except ImportError:
    StrongBodyLabel = QLabel; BodyLabel = QLabel; CaptionLabel = QLabel
    _HAS_FLUENT_LABELS = False

from urllib.parse import urlparse
from typing import Optional
import re
import os

from .base_page import BasePage, ScrollBlockingPlainTextEdit
from ui.compat_widgets import SettingsCard, ActionButton, set_tooltip
from .strategies_page_base import ResetActionButton
from ui.theme import get_theme_tokens
from log import log

def split_domains(text: str) -> list[str]:
    """
    Разделяет домены по пробелам/запятым и склеенные домены.
    'vk.com youtube.com' -> ['vk.com', 'youtube.com']
    'vk.comyoutube.com' -> ['vk.com', 'youtube.com']

    ВАЖНО: Если домены разделены пробелами, они НЕ считаются склеенными.
    Склеенные - только когда нет пробела: vk.comyoutube.com
    """
    # Сначала разделяем по пробелам, табам, запятым
    parts = re.split(r'[\s,;]+', text)

    result = []
    for part in parts:
        part = part.strip().lower()
        if not part or part.startswith('#'):
            if part:
                result.append(part)
            continue

        # Пробуем разделить склеенные домены ТОЛЬКО если это одна строка без пробелов
        # Если пользователь ввёл "genshin-impact-map.app sample.com" с пробелом,
        # они уже разделены выше и сюда приходят отдельно
        separated = _split_glued_domains(part)
        result.extend(separated)

    return result

def _split_glued_domains(text: str) -> list[str]:
    """
    Разделяет склеенные домены типа vk.comyoutube.com
    Ищем паттерн: домен.TLD + начало нового домена (буквы + точка)

    ВАЖНО: Не разделяем если после TLD идёт часть того же домена.
    Например: genshin-impact-map.appsample.com - это ОДИН домен, не разделяем.
    Разделяем только очевидные случаи типа vk.comyoutube.com
    """
    if not text or len(text) < 5:
        return [text] if text else []

    # Проверяем: если строка выглядит как валидный домен (заканчивается на TLD) - не разделяем
    # Это предотвращает разделение something.appsample.com
    valid_tld_pattern = r'\.(com|ru|org|net|io|me|by|uk|de|fr|it|es|nl|pl|ua|kz|su|co|tv|cc|to|ai|gg|info|biz|xyz|dev|app|pro|online|store|cloud|shop|blog|tech|site|рф)$'
    if re.search(valid_tld_pattern, text, re.IGNORECASE):
        # Строка заканчивается на валидный TLD - это нормальный домен
        # Проверим нет ли ЯВНО склеенных доменов (TLD + домен + TLD)
        # Например: vk.comyoutube.com - есть .com в середине И .com в конце

        # Паттерн: TLD + буквы + точка + что-то + TLD в конце
        # Это поймает vk.comyoutube.com но НЕ поймает genshin-impact-map.appsample.com
        glued_pattern = r'(\.(com|ru|org|net|io|me))([a-z]{2,}[a-z0-9-]*\.[a-z]{2,})$'
        match = re.search(glued_pattern, text, re.IGNORECASE)
        if match:
            # Нашли склеенные домены: первый заканчивается на TLD, второй - полноценный домен
            end_of_first = match.start() + len(match.group(1))
            first_domain = text[:end_of_first]
            second_domain = match.group(3)
            return [first_domain, second_domain]

        # Не нашли склеенных - возвращаем как есть
        return [text]

    # Строка НЕ заканчивается на валидный TLD - возможно мусор, возвращаем как есть
    return [text]


class CustomDomainsPage(BasePage):
    """Страница управления пользовательскими доменами"""
    
    domains_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(
            "Кастомные (мои) домены (hostlist) для работы с Zapret", 
            "Управление доменами (other.txt). Субдомены учитываются автоматически. Строчка rkn.ru учитывает и сайт fuckyou.rkn.ru и сайт ass.rkn.ru. Чтобы исключить субдомены напишите домен с символов ^ в начале, то есть например так ^rkn.ru", 
            parent
        )
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(lambda _: self._apply_theme_styles())
        qconfig.themeColorChanged.connect(lambda _: self._apply_theme_styles())

        self._build_ui()
        QTimer.singleShot(100, self._load_domains)
        
    def _build_ui(self):
        """Строит UI страницы"""
        tokens = get_theme_tokens()
        
        # Описание
        desc_card = SettingsCard()
        desc = BodyLabel(
            "Здесь редактируется файл other.user.txt (только ваши домены). "
            "Системная база берётся из шаблона и отдельно хранится в other.base.txt, "
            "а общий other.txt собирается автоматически. URL автоматически преобразуются в домены. "
            "Изменения сохраняются автоматически. Поддерживается Ctrl+Z."
        )
        try:
            desc.setProperty("tone", "muted")
        except Exception:
            pass
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        self.layout.addWidget(desc_card)
        
        # Добавление домена
        add_card = SettingsCard("Добавить домен")
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)
        
        self.domain_input = LineEdit()
        self.domain_input.setPlaceholderText("Введите домен или URL (например: example.com или https://site.com/page)")
        self.domain_input.returnPressed.connect(self._add_domain)
        add_layout.addWidget(self.domain_input, 1)
        
        self.add_btn = ActionButton("Добавить", "fa5s.plus", accent=True)
        self.add_btn.setFixedHeight(38)
        self.add_btn.clicked.connect(self._add_domain)
        add_layout.addWidget(self.add_btn)
        
        add_card.add_layout(add_layout)
        self.layout.addWidget(add_card)
        
        # Действия
        actions_card = SettingsCard("Действия")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # Открыть файл
        self.open_file_btn = ActionButton("Открыть файл", "fa5s.external-link-alt")
        self.open_file_btn.setFixedHeight(36)
        set_tooltip(self.open_file_btn, "Сохраняет изменения и открывает other.user.txt в проводнике")
        self.open_file_btn.clicked.connect(self._open_file)
        actions_layout.addWidget(self.open_file_btn)

        # Сбросить файл
        self.reset_btn = ResetActionButton(
            "Сбросить файл",
            confirm_text="Подтвердить сброс",
        )
        self.reset_btn.setFixedHeight(36)
        set_tooltip(
            self.reset_btn,
            "Очищает other.user.txt (мои домены) и пересобирает other.txt из системной базы"
        )
        self.reset_btn.reset_confirmed.connect(self._reset_file)
        actions_layout.addWidget(self.reset_btn)

        # Очистить всё
        self.clear_btn = ResetActionButton(
            "Очистить всё",
            confirm_text="Подтвердить очистку",
        )
        self.clear_btn.setFixedHeight(36)
        set_tooltip(
            self.clear_btn,
            "Удаляет только пользовательские домены. Базовые домены из шаблона останутся"
        )
        self.clear_btn.reset_confirmed.connect(self._clear_all)
        actions_layout.addWidget(self.clear_btn)
        
        actions_layout.addStretch()
        actions_card.add_layout(actions_layout)
        self.layout.addWidget(actions_card)
        
        # Текстовый редактор (вместо списка)
        editor_card = SettingsCard("other.user.txt (редактор)")
        editor_layout = QVBoxLayout()
        editor_layout.setSpacing(8)
        
        self.text_edit = ScrollBlockingPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "Домены по одному на строку:\n"
            "example.com\n"
            "subdomain.site.org\n\n"
            "Комментарии начинаются с #"
        )
        self.text_edit.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 8px;
                padding: 12px;
                color: {tokens.fg};
                font-family: Consolas, 'Courier New', monospace;
                font-size: 13px;
            }}
            QPlainTextEdit:hover {{
                background: {tokens.surface_bg_hover};
                border: 1px solid {tokens.surface_border_hover};
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {tokens.accent_hex};
            }}
            """
        )
        self.text_edit.setMinimumHeight(350)
        
        # Автосохранение
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save)
        self.text_edit.textChanged.connect(self._on_text_changed)
        
        editor_layout.addWidget(self.text_edit)
        
        # Подсказка
        hint = CaptionLabel("💡 Изменения сохраняются автоматически через 500мс")
        try:
            hint.setProperty("tone", "faint")
        except Exception:
            pass
        editor_layout.addWidget(hint)
        
        editor_card.add_layout(editor_layout)
        self.layout.addWidget(editor_card)
        
        # Статистика
        self.status_label = CaptionLabel()
        try:
            self.status_label.setProperty("tone", "muted")
        except Exception:
            pass
        self.layout.addWidget(self.status_label)

        # Apply token-based styles (also used on theme change).
        self._apply_theme_styles()

    def _apply_theme_styles(self) -> None:
        tokens = get_theme_tokens()

        try:
            if hasattr(self, "text_edit") and self.text_edit is not None:
                self.text_edit.setStyleSheet(
                    f"""
                    QPlainTextEdit {{
                        background: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 8px;
                        padding: 12px;
                        color: {tokens.fg};
                        font-family: Consolas, 'Courier New', monospace;
                        font-size: 13px;
                    }}
                    QPlainTextEdit:hover {{
                        background: {tokens.surface_bg_hover};
                        border: 1px solid {tokens.surface_border_hover};
                    }}
                    QPlainTextEdit:focus {{
                        border: 1px solid {tokens.accent_hex};
                    }}
                    """
                )
        except Exception:
            pass

    def _load_domains(self):
        """Загружает домены из файла"""
        try:
            from config import OTHER_USER_PATH
            from utils.hostlists_manager import ensure_hostlists_exist

            ensure_hostlists_exist()
            
            domains = []
            
            if os.path.exists(OTHER_USER_PATH):
                with open(OTHER_USER_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            domains.append(line)
            
            # Блокируем сигнал чтобы не срабатывало автосохранение
            self.text_edit.blockSignals(True)
            self.text_edit.setPlainText('\n'.join(domains))
            self.text_edit.blockSignals(False)
            
            self._update_status()
            log(f"Загружено {len(domains)} строк из other.user.txt", "INFO")
            
        except Exception as e:
            log(f"Ошибка загрузки доменов: {e}", "ERROR")
            self.status_label.setText(f"❌ Ошибка: {e}")
            
    def _on_text_changed(self):
        """Запускает таймер автосохранения"""
        self._save_timer.start(500)
        self._update_status()
        
    def _auto_save(self):
        """Автосохранение"""
        self._save_domains()
        self.status_label.setText(self.status_label.text() + " • ✅ Сохранено")
        
    def _save_domains(self):
        """Сохраняет домены в файл"""
        try:
            from config import OTHER_USER_PATH
            os.makedirs(os.path.dirname(OTHER_USER_PATH), exist_ok=True)
            
            text = self.text_edit.toPlainText()
            domains = []
            normalized_lines = []  # Для обновления UI
            
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    # Сохраняем комментарии как есть
                    domains.append(line)
                    normalized_lines.append(line)
                    continue
                
                # Разделяем склеенные домены (vk.comyoutube.com -> vk.com, youtube.com)
                separated = split_domains(line)
                
                for item in separated:
                    # Нормализуем каждый домен
                    domain = self._extract_domain(item)
                    if domain:
                        if domain not in domains:
                            domains.append(domain)
                            normalized_lines.append(domain)
                    else:
                        # Невалидная строка - оставляем как есть
                        normalized_lines.append(item)
            
            with open(OTHER_USER_PATH, 'w', encoding='utf-8') as f:
                for domain in domains:
                    f.write(f"{domain}\n")

            # Rebuild combined other.txt from base + user.
            try:
                from utils.hostlists_manager import rebuild_other_files

                rebuild_other_files()
            except Exception:
                pass
            
            # Обновляем UI - заменяем URL на домены
            new_text = '\n'.join(normalized_lines)
            if new_text != text:
                cursor = self.text_edit.textCursor()
                pos = cursor.position()
                
                self.text_edit.blockSignals(True)
                self.text_edit.setPlainText(new_text)
                
                # Восстанавливаем позицию курсора
                cursor = self.text_edit.textCursor()
                cursor.setPosition(min(pos, len(new_text)))
                self.text_edit.setTextCursor(cursor)
                self.text_edit.blockSignals(False)
            
            log(f"Сохранено {len(domains)} строк в other.user.txt", "SUCCESS")
            self.domains_changed.emit()
            
        except Exception as e:
            log(f"Ошибка сохранения доменов: {e}", "ERROR")
            
    def _update_status(self):
        """Обновляет статус"""
        text = self.text_edit.toPlainText()
        lines = [l.strip() for l in text.split('\n') if l.strip() and not l.strip().startswith('#')]
        base_set = self._get_base_domains_set()

        valid_domains = []
        for line in lines:
            domain = self._extract_domain(line)
            if domain:
                valid_domains.append(domain)

        user_set = {d for d in valid_domains if d}
        user_count = len({d for d in user_set if d not in base_set})
        base_count = len(base_set)
        total_count = len(base_set.union(user_set))
        self.status_label.setText(
            f"📊 Доменов: {total_count} (база: {base_count}, пользовательские: {user_count})"
        )

    def _get_base_domains_set(self) -> set[str]:
        """Возвращает set системных доменов из кода."""
        try:
            from utils.hostlists_manager import get_base_domains_set

            return get_base_domains_set()
        except Exception:
            return set()
        
    def _extract_domain(self, text: str) -> Optional[str]:
        """Извлекает домен из URL или текста"""
        text = text.strip()

        # Маркер "не учитывать субдомены" (поддерживается в hostlist как ^domain)
        marker = ""
        if text.startswith('^'):
            marker = '^'
            text = text[1:].strip()
            if not text:
                return None
        
        # Убираем точку в начале (.com -> com)
        if text.startswith('.'):
            text = text[1:]
        
        # Если похоже на URL - парсим
        if '://' in text or text.startswith('www.'):
            if not text.startswith(('http://', 'https://')):
                text = 'https://' + text
            try:
                parsed = urlparse(text)
                domain = parsed.netloc or parsed.path.split('/')[0]
                if domain.startswith('www.'):
                    domain = domain[4:]
                domain = domain.split(':')[0]
                if domain.startswith('.'):
                    domain = domain[1:]
                domain = domain.lower()
                return f"{marker}{domain}" if marker else domain
            except:
                pass
        
        # Проверяем что это валидный домен
        domain = text.split('/')[0].split(':')[0].lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        if domain.startswith('.'):
            domain = domain[1:]
        
        # Одиночные TLD (com, ru, org) - валидны
        if re.match(r'^[a-z]{2,10}$', domain):
            return f"{marker}{domain}" if marker else domain
        
        # Домен с точкой (example.com)
        if '.' in domain and len(domain) > 3:
            if re.match(r'^[a-z0-9][a-z0-9\-\.]*[a-z0-9]$', domain):
                return f"{marker}{domain}" if marker else domain
        
        return None
        
    def _add_domain(self):
        """Добавляет домен"""
        text = self.domain_input.text().strip()
        if not text:
            return
        
        domain = self._extract_domain(text)
        
        if not domain:
            if InfoBar:
                InfoBar.warning(
                    title="Ошибка",
                    content=f"Не удалось распознать домен:\n{text}\n\nВведите корректный домен (например: example.com)",
                    parent=self.window(),
                )
            return

        # Проверяем дубликат
        current = self.text_edit.toPlainText()
        current_domains = [l.strip().lower() for l in current.split('\n') if l.strip() and not l.strip().startswith('#')]

        if domain.lower() in current_domains:
            if InfoBar:
                InfoBar.info(title="Информация", content=f"Домен уже добавлен:\n{domain}", parent=self.window())
            return
        
        # Добавляем в конец
        if current and not current.endswith('\n'):
            current += '\n'
        current += domain
        
        self.text_edit.setPlainText(current)
        self.domain_input.clear()
        
        log(f"Добавлен домен: {domain}", "SUCCESS")
                
    def _clear_all(self):
        """Очищает только пользовательские домены."""
        self.text_edit.setPlainText("")
        self._save_domains()
        log("Пользовательские домены удалены", "INFO")

    def _reset_file(self):
        """Очищает other.user.txt и пересобирает other.txt из базы."""
        try:
            from utils.hostlists_manager import reset_other_file_from_template

            if reset_other_file_from_template():
                self._load_domains()
                self.status_label.setText(self.status_label.text() + " • ✅ Сброшено")
            else:
                if InfoBar:
                    InfoBar.warning(title="Ошибка", content="Не удалось сбросить my hostlist", parent=self.window())
        except Exception as e:
            log(f"Ошибка сброса my hostlist: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось сбросить:\n{e}", parent=self.window())
                
    def _open_file(self):
        """Открывает файл в проводнике"""
        try:
            from config import OTHER_USER_PATH
            import subprocess
            from utils.hostlists_manager import ensure_hostlists_exist
            
            # Сначала сохраняем
            self._save_domains()
            ensure_hostlists_exist()
            
            if os.path.exists(OTHER_USER_PATH):
                subprocess.run(['explorer', '/select,', OTHER_USER_PATH])
            else:
                os.makedirs(os.path.dirname(OTHER_USER_PATH), exist_ok=True)
                with open(OTHER_USER_PATH, 'w', encoding='utf-8') as f:
                    pass
                subprocess.run(['explorer', os.path.dirname(OTHER_USER_PATH)])
                
        except Exception as e:
            log(f"Ошибка открытия файла: {e}", "ERROR")
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть:\n{e}", parent=self.window())
