# ui/pages/bat_strategies_page.py
"""Страница стратегий для BAT режима (Zapret 1 через .bat файлы)"""

from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QSizePolicy, QPushButton, QApplication)
from PyQt6.QtGui import QFont, QTextOption
import qtawesome as qta
import os

from .strategies_page_base import StrategiesPageBase
from .base_page import ScrollBlockingTextEdit
from ui.widgets import StrategySearchBar
from ui.theme import get_theme_tokens
from ui.compat_widgets import set_tooltip
from config import BAT_FOLDER
from log import log

try:
    from qfluentwidgets import BodyLabel as _BodyLabel
except ImportError:
    _BodyLabel = QLabel


class BatStrategiesPage(StrategiesPageBase):
    """Страница стратегий для BAT режима (Zapret 1 через .bat файлы)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_watcher = None
        self._watcher_active = False
        self._applying_local_theme = False
        self._local_theme_refresh_scheduled = False
        self._cmd_preview_label = None
        self._copy_cmd_btn = None
        log("BatStrategiesPage initialized", "DEBUG")

    def _load_content(self):
        """Загружает контент для BAT режима"""
        self._load_bat_mode()

    def _load_bat_mode(self):
        """Загружает интерфейс для bat режима (Zapret 1)"""
        try:
            from strategy_menu.strategy_table_widget_favorites import StrategyTableWithFavoritesFilter

            # Текущая стратегия (в начале контента)
            if hasattr(self, 'current_widget') and self.current_widget:
                if self.current_widget.parent() != self.content_container:
                    self.content_layout.insertWidget(0, self.current_widget)

            # Получаем strategy_manager
            strategy_manager = None
            if hasattr(self.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.strategy_manager
            elif hasattr(self.parent_app, 'parent_app') and hasattr(self.parent_app.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.parent_app.strategy_manager

            # Поисковая панель - только поиск по тексту
            # Фильтры и сортировка на отдельной странице StrategySortPage
            self.search_bar = StrategySearchBar(self)
            self.search_bar.search_changed.connect(self._on_bat_search_changed)
            # Скрываем фильтры и сортировку - они на отдельной странице
            self.search_bar._label_combo.hide()
            self.search_bar._desync_combo.hide()
            self.search_bar._sort_combo.hide()
            self.content_layout.addWidget(self.search_bar)

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

            # Виджет превью командной строки
            self._cmd_preview_widget = self._create_cmd_preview_widget()
            self.content_layout.addWidget(self._cmd_preview_widget)

            # Подключаем обновление превью при выборе стратегии
            if hasattr(self._bat_table, 'table') and hasattr(self._bat_table.table, 'itemSelectionChanged'):
                self._bat_table.table.itemSelectionChanged.connect(self._update_cmd_preview)

            # Загружаем локальные стратегии сразу
            if strategy_manager:
                self._load_bat_strategies()
                # Асинхронно применяем последнюю выбранную стратегию из реестра
                QTimer.singleShot(300, self._auto_select_last_bat_strategy)
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
                # DEBUG: Принудительно обновляем кэш для диагностики
                if hasattr(strategy_manager, 'refresh_strategies'):
                    log("DEBUG: Принудительное обновление кэша стратегий", "DEBUG")
                    strategy_manager.refresh_strategies()
                strategies = strategy_manager.get_local_strategies_only()
                if strategies:
                    # Сохраняем оригинальный dict
                    self._all_bat_strategies_dict = strategies.copy()

                    # DEBUG: Проверяем наличие general_alt11_191
                    if 'general_alt11_191' in strategies:
                        log("DEBUG: general_alt11_191 НАЙДЕН в strategies dict", "DEBUG")
                    else:
                        log("DEBUG: general_alt11_191 НЕ НАЙДЕН в strategies dict", "WARNING")
                        # Показываем похожие ключи
                        similar = [k for k in strategies.keys() if 'general_alt11' in k.lower()]
                        if similar:
                            log(f"DEBUG: Похожие ключи: {similar}", "DEBUG")

                    # Конвертируем dict в List[StrategyInfo] для фильтрации и сортировки
                    # Используем те же ID что и в dict для совместимости
                    self._all_bat_strategies = self._convert_dict_to_strategy_info_list(strategies)

                    self._update_favorites_count()
                    log(f"Загружено {len(strategies)} bat стратегий", "DEBUG")

                    if self.search_bar:
                        self.search_bar.set_result_count(len(self._all_bat_strategies))

                    # Применяем сохранённую сортировку из реестра
                    # Это перезаполнит таблицу с правильной сортировкой
                    self._apply_bat_filter()
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

    def _create_cmd_preview_widget(self) -> QWidget:
        """Создаёт виджет для превью командной строки"""
        tokens = get_theme_tokens()
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(8)

        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        label = _BodyLabel("Командная строка:")
        self._cmd_preview_label = label
        label.setStyleSheet(f"color: {tokens.fg_muted};")
        label.setFont(QFont("Segoe UI Variable", 9, QFont.Weight.Medium))
        header_layout.addWidget(label)

        # Кнопка копирования
        copy_btn = QPushButton()
        self._copy_cmd_btn = copy_btn
        copy_btn.setIcon(qta.icon('fa5s.copy', color=tokens.accent_hex))
        copy_btn.setFixedSize(24, 24)
        copy_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {tokens.surface_bg};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {tokens.surface_bg_hover};
            }}
            """
        )
        set_tooltip(copy_btn, "Копировать команду")
        copy_btn.clicked.connect(self._copy_cmd_to_clipboard)
        header_layout.addWidget(copy_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Текстовое поле для команды
        self._cmd_preview_text = ScrollBlockingTextEdit()
        self._cmd_preview_text.setReadOnly(True)
        self._cmd_preview_text.setMinimumHeight(80)
        self._cmd_preview_text.setMaximumHeight(150)
        self._cmd_preview_text.setStyleSheet(
            f"""
            QTextEdit {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 8px;
                color: {tokens.fg_muted};
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
                padding: 8px;
            }}
            """
        )
        self._cmd_preview_text.setPlaceholderText("Выберите стратегию для просмотра команды...")
        self._cmd_preview_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.addWidget(self._cmd_preview_text)

        return widget

    def _apply_local_theme(self) -> None:
        if self._applying_local_theme:
            return
        self._applying_local_theme = True
        try:
            tokens = get_theme_tokens()
            if self._cmd_preview_label is not None:
                self._cmd_preview_label.setStyleSheet(f"color: {tokens.fg_muted};")
                self._cmd_preview_label.setFont(QFont("Segoe UI Variable", 9, QFont.Weight.Medium))
            if self._copy_cmd_btn is not None:
                self._copy_cmd_btn.setIcon(qta.icon('fa5s.copy', color=tokens.accent_hex))
                self._copy_cmd_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {tokens.surface_bg};
                        border: none;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background: {tokens.surface_bg_hover};
                    }}
                    """
                )
            if hasattr(self, '_cmd_preview_text') and self._cmd_preview_text is not None:
                self._cmd_preview_text.setStyleSheet(
                    f"""
                    QTextEdit {{
                        background: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 8px;
                        color: {tokens.fg_muted};
                        font-family: 'Cascadia Code', 'Consolas', monospace;
                        font-size: 11px;
                        padding: 8px;
                    }}
                    """
                )
        finally:
            self._applying_local_theme = False

    def _schedule_local_theme_refresh(self) -> None:
        if self._applying_local_theme:
            return
        if self._local_theme_refresh_scheduled:
            return
        self._local_theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_local_theme_change)

    def _on_debounced_local_theme_change(self) -> None:
        self._local_theme_refresh_scheduled = False
        self._apply_local_theme()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_local_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)

    def _update_cmd_preview(self):
        """Обновляет превью командной строки для выбранной стратегии"""
        try:
            if not hasattr(self, '_cmd_preview_text') or not self._cmd_preview_text:
                return

            if not self._bat_table:
                return

            # Получаем выбранную стратегию (возвращает tuple: id, name)
            selected = self._bat_table.get_selected_strategy()
            if not selected or not selected[0]:
                self._cmd_preview_text.setPlainText("")
                return

            strategy_id, strategy_name = selected

            # Получаем полную информацию о стратегии из менеджера
            strategy_manager = None
            if hasattr(self, 'parent_app') and hasattr(self.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.strategy_manager
            elif hasattr(self, 'parent_app') and hasattr(self.parent_app, 'parent_app'):
                if hasattr(self.parent_app.parent_app, 'strategy_manager'):
                    strategy_manager = self.parent_app.parent_app.strategy_manager

            if not strategy_manager:
                self._cmd_preview_text.setPlainText(f"# Менеджер стратегий не доступен")
                return

            strategies = strategy_manager.get_strategies_list()
            strategy_info = strategies.get(strategy_id, {})
            file_path = strategy_info.get('file_path', '')

            if not file_path:
                self._cmd_preview_text.setPlainText(f"# Файл стратегии не найден: {strategy_name}")
                return

            # Полный путь к BAT файлу
            full_path = os.path.join(BAT_FOLDER, file_path)

            if not os.path.exists(full_path):
                self._cmd_preview_text.setPlainText(f"# Файл не существует: {full_path}")
                return

            # Парсим BAT файл
            from utils.bat_parser import parse_bat_file

            parsed = parse_bat_file(full_path, debug=False)
            if not parsed:
                self._cmd_preview_text.setPlainText(f"# Не удалось распарсить: {file_path}")
                return

            exe_path, args = parsed

            # Формируем командную строку с полными путями для копирования в консоль
            from config import WINWS_EXE
            from utils.args_resolver import resolve_args_paths

            bat_dir = os.path.dirname(full_path)
            work_dir = os.path.dirname(bat_dir)
            lists_dir = os.path.join(work_dir, "lists")
            bin_dir = os.path.join(work_dir, "bin")

            # Полный путь к exe
            full_exe = WINWS_EXE

            # Разрешаем пути в аргументах через общую функцию
            resolved_args = resolve_args_paths(args, lists_dir, bin_dir)

            # Для отображения добавляем кавычки вокруг путей с пробелами
            display_args = []
            for arg in resolved_args:
                if '=' in arg and ' ' in arg:
                    # Аргумент с путём содержащим пробелы
                    prefix, value = arg.split('=', 1)
                    if not value.startswith('"'):
                        display_args.append(f'{prefix}="{value}"')
                    else:
                        display_args.append(arg)
                else:
                    display_args.append(arg)

            # Формируем многострочное отображение (один аргумент на строку)
            # Первая строка - путь к exe
            lines = [f'"{full_exe}"']
            # Каждый аргумент на отдельной строке
            lines.extend(display_args)
            multi_line_cmd = '\n'.join(lines)

            self._cmd_preview_text.setPlainText(multi_line_cmd)

        except Exception as e:
            log(f"Ошибка обновления превью команды: {e}", "DEBUG")
            if hasattr(self, '_cmd_preview_text') and self._cmd_preview_text:
                self._cmd_preview_text.setPlainText(f"# Ошибка: {e}")

    def _format_cmd_for_display(self, cmd_parts: list) -> str:
        """Форматирует командную строку для удобного отображения"""
        lines = []
        current_line = []

        for part in cmd_parts:
            if part == '--new':
                # Сохраняем текущую строку
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                lines.append('--new')
            else:
                current_line.append(part)

        # Добавляем последнюю строку
        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def _copy_cmd_to_clipboard(self):
        """Копирует командную строку в буфер обмена"""
        try:
            if hasattr(self, '_cmd_preview_text') and self._cmd_preview_text:
                text = self._cmd_preview_text.toPlainText()
                if text:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(text)
                    log("Команда скопирована в буфер обмена", "INFO")
        except Exception as e:
            log(f"Ошибка копирования команды: {e}", "DEBUG")

    def _auto_select_last_bat_strategy(self):
        """Автоматически выбирает и применяет последнюю BAT-стратегию из реестра (асинхронно)"""
        try:
            if not self._bat_table:
                log("BAT таблица не готова для автовыбора", "DEBUG")
                return

            # Проверяем что таблица заполнена стратегиями
            if not hasattr(self._bat_table, 'strategies_map') or not self._bat_table.strategies_map:
                log("BAT таблица пустая, стратегии ещё не загружены", "DEBUG")
                return

            from config.reg import get_last_bat_strategy
            from strategy_menu import get_strategy_launch_method

            # Проверяем что мы всё ещё в BAT режиме
            if get_strategy_launch_method() != "bat":
                log("Режим уже не BAT, пропускаем автовыбор", "DEBUG")
                return

            # Получаем последнюю BAT-стратегию из реестра (отдельный ключ реестра)
            last_strategy_name = get_last_bat_strategy()

            if not last_strategy_name or last_strategy_name == "Автостарт DPI отключен":
                log("Нет сохранённой последней стратегии или автозапуск отключён", "DEBUG")
                self.current_strategy_label.setText("Не выбрана")
                return

            log(f"Автоматически применяется последняя BAT-стратегия: {last_strategy_name}", "INFO")

            # Программно выбираем стратегию в таблице
            # Это автоматически вызовет _on_item_selected -> strategy_applied сигнал -> _on_bat_strategy_applied
            self._bat_table.select_strategy_by_name(last_strategy_name)

            # Обновляем отображение текущей стратегии (дополнительно, на случай если сигнал не сработал)
            self.current_strategy_label.setText(f"{last_strategy_name}")

        except Exception as e:
            log(f"Ошибка автовыбора BAT-стратегии: {e}", "WARNING")
            import traceback
            log(f"Traceback: {traceback.format_exc()}", "DEBUG")
            # При ошибке показываем "Не выбрана"
            self.current_strategy_label.setText("Не выбрана")

    def start_watching(self):
        """Запускает мониторинг .bat файлов (только для bat режима)"""
        try:
            if self._watcher_active:
                return  # Уже активен

            if not os.path.exists(BAT_FOLDER):
                log(f"Папка bat не найдена для мониторинга: {BAT_FOLDER}", "WARNING")
                return

            # Создаём watcher если его нет
            if not self._file_watcher:
                self._file_watcher = QFileSystemWatcher()
                self._file_watcher.directoryChanged.connect(self._on_bat_folder_changed)
                self._file_watcher.fileChanged.connect(self._on_bat_file_changed)

            # Мониторим папку (для добавления/удаления файлов)
            self._file_watcher.addPath(BAT_FOLDER)

            # Мониторим все существующие .bat файлы (для изменения содержимого)
            self._add_bat_files_to_watcher(BAT_FOLDER)

            self._watcher_active = True
            log(f"Мониторинг .bat файлов запущен", "DEBUG")

        except Exception as e:
            log(f"Ошибка запуска мониторинга: {e}", "WARNING")

    def stop_watching(self):
        """Останавливает мониторинг .bat файлов (экономия ресурсов в direct режиме)"""
        try:
            if not self._watcher_active:
                return  # Уже остановлен

            if self._file_watcher:
                # Удаляем все пути из мониторинга
                directories = self._file_watcher.directories()
                files = self._file_watcher.files()

                if directories:
                    self._file_watcher.removePaths(directories)
                if files:
                    self._file_watcher.removePaths(files)

            self._watcher_active = False
            log(f"Мониторинг .bat файлов остановлен", "DEBUG")

        except Exception as e:
            log(f"Ошибка остановки мониторинга: {e}", "DEBUG")

    def _add_bat_files_to_watcher(self, folder_path: str):
        """Добавляет все .bat файлы в мониторинг"""
        try:
            if not os.path.exists(folder_path):
                return

            bat_files = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith('.bat')
            ]

            if bat_files:
                self._file_watcher.addPaths(bat_files)
                log(f"Добавлено {len(bat_files)} .bat файлов в мониторинг", "DEBUG")

        except Exception as e:
            log(f"Ошибка добавления файлов в мониторинг: {e}", "DEBUG")

    def _on_bat_folder_changed(self, path: str):
        """Обработчик изменений в папке .bat файлов (добавление/удаление)"""
        try:
            log(f"Обнаружены изменения в папке: {path}", "DEBUG")

            # При изменении папки нужно обновить список отслеживаемых файлов
            self._update_watched_files(path)

            # Обновляем список стратегий с небольшой задержкой
            QTimer.singleShot(500, self._refresh_bat_strategies)

        except Exception as e:
            log(f"Ошибка обработки изменений в папке: {e}", "ERROR")

    def _on_bat_file_changed(self, path: str):
        """Обработчик изменений в .bat файле (изменение содержимого)"""
        try:
            log(f"Обнаружены изменения в файле: {os.path.basename(path)}", "DEBUG")

            # Обновляем список стратегий с небольшой задержкой
            QTimer.singleShot(500, self._refresh_bat_strategies)

        except Exception as e:
            log(f"Ошибка обработки изменений в файле: {e}", "ERROR")

    def _update_watched_files(self, folder_path: str):
        """Обновляет список отслеживаемых файлов"""
        try:
            if not self._file_watcher:
                return

            # Удаляем все текущие файлы из мониторинга
            current_files = self._file_watcher.files()
            if current_files:
                self._file_watcher.removePaths(current_files)

            # Добавляем актуальный список файлов
            self._add_bat_files_to_watcher(folder_path)

        except Exception as e:
            log(f"Ошибка обновления отслеживаемых файлов: {e}", "DEBUG")

    def _refresh_bat_strategies(self):
        """Обновляет список bat стратегий"""
        try:
            # Получаем strategy_manager
            strategy_manager = None
            if hasattr(self.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.strategy_manager
            elif hasattr(self.parent_app, 'parent_app') and hasattr(self.parent_app.parent_app, 'strategy_manager'):
                strategy_manager = self.parent_app.parent_app.strategy_manager

            if not strategy_manager:
                log("strategy_manager не найден для обновления", "WARNING")
                return

            # Обновляем кэш стратегий
            strategies = strategy_manager.refresh_strategies()
            log(f"Обновлено {len(strategies)} bat стратегий", "INFO")

            # Обновляем список отслеживаемых файлов (на случай добавления/удаления)
            if os.path.exists(BAT_FOLDER):
                self._update_watched_files(BAT_FOLDER)

            # Обновляем таблицу
            if self._bat_table and strategies:
                self._bat_table.populate_strategies(strategies)
                self._update_favorites_count()
                log("Таблица стратегий обновлена", "DEBUG")

        except Exception as e:
            log(f"Ошибка обновления bat стратегий: {e}", "ERROR")
            import traceback
            log(f"Traceback: {traceback.format_exc()}", "DEBUG")

    def _on_bat_strategy_applied(self, strategy_id: str, strategy_name: str):
        """Обработчик автоприменения bat стратегии"""
        self.strategy_selected.emit(strategy_id, strategy_name)

        # Показываем спиннер загрузки
        self.show_loading()

        # Запускаем абсолютный таймаут защиты (10 секунд)
        # Если за это время процесс не запустится - принудительно покажем галочку
        self._absolute_timeout_timer.start(10000)
        log("Запущен таймаут защиты спиннера (10 секунд)", "DEBUG")

        # Автоматически запускаем стратегию через dpi_controller
        try:
            app = self.parent_app
            if hasattr(app, 'dpi_controller') and app.dpi_controller:
                # Сохраняем последнюю BAT-стратегию (отдельный ключ реестра)
                from config.reg import set_last_bat_strategy
                set_last_bat_strategy(strategy_name)

                # Запускаем BAT стратегию
                app.dpi_controller.start_dpi_async(selected_mode=strategy_name)
                log(f"BAT стратегия запущена: {strategy_name}", "INFO")

                # Обновляем лейбл текущей стратегии
                self.current_strategy_label.setText(f"{strategy_name}")
                if hasattr(app, 'current_strategy_label'):
                    app.current_strategy_label.setText(strategy_name)
                if hasattr(app, 'current_strategy_name'):
                    app.current_strategy_name = strategy_name

                # Запускаем мониторинг реального статуса процесса
                self._start_process_monitoring()
            else:
                self._stop_absolute_timeout()
                self.show_success()
        except Exception as e:
            log(f"Ошибка применения BAT стратегии: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            self._stop_absolute_timeout()
            self.show_success()
