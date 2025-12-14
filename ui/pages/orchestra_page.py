# ui/pages/orchestra_page.py
"""Страница оркестратора автоматического обучения (circular)"""

import os
from queue import Queue, Empty
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QCheckBox,
    QLineEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QFont, QTextCursor
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from log import log
from config import LOGS_FOLDER, REGISTRY_PATH
from config.reg import reg
from orchestra import DEFAULT_WHITELIST, REGISTRY_ORCHESTRA


class OrchestraPage(BasePage):
    """Страница оркестратора с логами обучения"""

    clear_learned_requested = pyqtSignal()  # Сигнал очистки данных обучения
    log_received = pyqtSignal(str)  # Сигнал для получения логов из потока runner'а

    # Состояния оркестратора
    STATE_STOPPED = "stopped"
    STATE_LEARNING = "learning"
    STATE_WORKING = "working"

    def __init__(self, parent=None):
        super().__init__(
            "Оркест v0.3 (Pre-Alpha)",
            "Автоматическое обучение стратегий DPI bypass. Система находит лучшую стратегию для каждого домена (ВРЕМЕННО ТОЛЬКО ДЛЯ TCP ТРАФИКА!).",
            parent
        )
        self._build_ui()

        # Путь к лог-файлу
        self._log_file_path = os.path.join(LOGS_FOLDER, "winws2_orchestra.log")
        self._last_log_position = 0  # Позиция в файле для инкрементального чтения
        self._current_state = self.STATE_STOPPED  # Текущее состояние

        # Таймер для обновления статуса и логов
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_all)

        # Thread-safe очередь для логов из runner потока
        self._log_queue = Queue()

        # Таймер для обработки очереди логов (50ms - быстро, но не блокирует UI)
        self._log_queue_timer = QTimer(self)
        self._log_queue_timer.timeout.connect(self._process_log_queue)
        self._log_queue_timer.start(50)

        # Подключаем сигнал для обновления логов (теперь только из main thread)
        self.log_received.connect(self._on_log_received)

    def _build_ui(self):
        """Строит UI страницы"""

        # === Статус карточка ===
        status_card = SettingsCard("Статус обучения")
        status_layout = QVBoxLayout()

        # Статус
        status_row = QHBoxLayout()
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(24, 24)
        self.status_label = QLabel("Не запущен")
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 14px;")
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_layout.addLayout(status_row)

        # Информация о режимах
        info_label = QLabel(
            "• LEARNING - система перебирает стратегии\n"
            "• LOCKED - найдена рабочая стратегия (3 успеха)\n"
            "• UNLOCKED - переобучение (2 сбоя после LOCK)"
        )
        info_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 8px;")
        status_layout.addWidget(info_label)

        status_card.add_layout(status_layout)
        self.layout.addWidget(status_card)

        # === Лог карточка ===
        log_card = SettingsCard("Лог обучения")
        log_layout = QVBoxLayout()

        # Текстовое поле для логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        self.log_text.setPlaceholderText("Логи обучения будут отображаться здесь...")
        log_layout.addWidget(self.log_text)

        # Чекбокс сохранения debug файла
        self.debug_checkbox = QCheckBox("Сохранять сырой debug файл (для отладки)")
        self.debug_checkbox.setStyleSheet("""
            QCheckBox {
                color: rgba(255,255,255,0.7);
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255,255,255,0.3);
                background: rgba(0,0,0,0.2);
            }
            QCheckBox::indicator:checked {
                background: #8a2be2;
                border-color: #8a2be2;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(255,255,255,0.5);
            }
        """)
        # Загружаем состояние из реестра
        saved_debug = reg(f"{REGISTRY_PATH}\\Orchestra", "KeepDebugFile")
        self.debug_checkbox.setChecked(bool(saved_debug))
        self.debug_checkbox.stateChanged.connect(self._on_debug_toggled)
        log_layout.addWidget(self.debug_checkbox)

        # Кнопки
        btn_row = QHBoxLayout()

        self.clear_log_btn = QPushButton("Очистить лог")
        self.clear_log_btn.setIcon(qta.icon("mdi.delete", color="#ff6b6b"))
        self.clear_log_btn.clicked.connect(self._clear_log)
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 107, 107, 0.1);
                border: 1px solid rgba(255, 107, 107, 0.3);
                border-radius: 6px;
                color: #ff6b6b;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: rgba(255, 107, 107, 0.2);
            }
        """)
        btn_row.addWidget(self.clear_log_btn)

        btn_row.addStretch()

        self.clear_learned_btn = QPushButton("Сбросить обучение")
        self.clear_learned_btn.setIcon(qta.icon("mdi.restart", color="#ff9800"))
        self.clear_learned_btn.clicked.connect(self._clear_learned)
        self.clear_learned_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 152, 0, 0.1);
                border: 1px solid rgba(255, 152, 0, 0.3);
                border-radius: 6px;
                color: #ff9800;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: rgba(255, 152, 0, 0.2);
            }
        """)
        btn_row.addWidget(self.clear_learned_btn)

        log_layout.addLayout(btn_row)
        log_card.add_layout(log_layout)
        self.layout.addWidget(log_card)

        # === Обученные домены ===
        domains_card = SettingsCard("Обученные домены")
        domains_layout = QVBoxLayout()

        self.domains_label = QLabel("Нет данных")
        self.domains_label.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 12px;")
        self.domains_label.setWordWrap(True)
        domains_layout.addWidget(self.domains_label)

        domains_card.add_layout(domains_layout)
        self.layout.addWidget(domains_card)

        # === История стратегий с рейтингами ===
        history_card = SettingsCard("📊 История стратегий (рейтинги)")
        history_layout = QVBoxLayout()

        # Описание
        history_desc = QLabel("Рейтинг = успехи / (успехи + провалы). При UNLOCK выбирается лучшая стратегия из истории.")
        history_desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        history_desc.setWordWrap(True)
        history_layout.addWidget(history_desc)

        # Виджет истории
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setMaximumHeight(200)
        self.history_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: rgba(255,255,255,0.8);
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 6px;
            }
        """)
        self.history_text.setPlaceholderText("История стратегий появится после обучения...")
        history_layout.addWidget(self.history_text)

        history_card.add_layout(history_layout)
        self.layout.addWidget(history_card)

        # === Белый список ===
        whitelist_card = SettingsCard("Белый список (исключения)")
        whitelist_layout = QVBoxLayout()

        # Описание
        whitelist_desc = QLabel("Домены из белого списка НЕ обрабатываются оркестратором.\nБазовые домены нельзя удалить, пользовательские — можно.")
        whitelist_desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        whitelist_desc.setWordWrap(True)
        whitelist_layout.addWidget(whitelist_desc)

        # Список доменов
        self.whitelist_widget = QListWidget()
        self.whitelist_widget.setMaximumHeight(150)
        self.whitelist_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(0,0,0,0.2);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                color: rgba(255,255,255,0.8);
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: rgba(138,43,226,0.3);
            }
        """)
        whitelist_layout.addWidget(self.whitelist_widget)

        # Кнопки управления
        whitelist_buttons = QHBoxLayout()

        # Поле ввода + кнопка добавления
        self.whitelist_input = QLineEdit()
        self.whitelist_input.setPlaceholderText("example.com")
        self.whitelist_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(0,0,0,0.2);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                color: white;
                padding: 6px;
                font-size: 12px;
            }
        """)
        self.whitelist_input.returnPressed.connect(self._add_whitelist_domain)
        whitelist_buttons.addWidget(self.whitelist_input)

        add_btn = ActionButton("Добавить", "fa5s.plus")
        add_btn.clicked.connect(self._add_whitelist_domain)
        whitelist_buttons.addWidget(add_btn)

        remove_btn = ActionButton("Удалить", "fa5s.trash-alt")
        remove_btn.clicked.connect(self._remove_whitelist_domain)
        whitelist_buttons.addWidget(remove_btn)

        whitelist_layout.addLayout(whitelist_buttons)
        whitelist_card.add_layout(whitelist_layout)
        self.layout.addWidget(whitelist_card)

        # Загружаем whitelist
        self._update_whitelist()

        # Обновляем статус
        self._update_status(self.STATE_STOPPED)

    def _update_status(self, state: str):
        """Обновляет статус на основе состояния"""
        self._current_state = state

        if state == self.STATE_LEARNING:
            self.status_icon.setPixmap(
                qta.icon("mdi.brain", color="#FF9800").pixmap(24, 24)  # Оранжевый - обучение
            )
            self.status_label.setText("🔄 LEARNING - идёт обучение")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 14px;")
        elif state == self.STATE_WORKING:
            self.status_icon.setPixmap(
                qta.icon("mdi.brain", color="#4CAF50").pixmap(24, 24)  # Зелёный - работает
            )
            self.status_label.setText("✅ WORKING - используются лучшие стратегии")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px;")
        else:
            self.status_icon.setPixmap(
                qta.icon("mdi.brain", color="#666").pixmap(24, 24)
            )
            self.status_label.setText("Не запущен")
            self.status_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 14px;")

    def _clear_log(self):
        """Очищает лог"""
        self.log_text.clear()
        # Сбрасываем позицию чтобы перечитать файл с начала
        self._last_log_position = 0

    def _clear_learned(self):
        """Сбрасывает данные обучения"""
        self.clear_learned_requested.emit()
        self.append_log("[INFO] Данные обучения сброшены")
        self._update_domains({})

    def _on_debug_toggled(self, state):
        """Обработчик переключения сохранения debug файла"""
        keep = state == Qt.CheckState.Checked.value
        # Сохраняем в реестр
        reg(f"{REGISTRY_PATH}\\Orchestra", "KeepDebugFile", 1 if keep else 0)
        try:
            app = self.window()
            if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                app.orchestra_runner.set_keep_debug_file(keep)
                status = "будет сохранён" if keep else "будет удалён после остановки"
                self.append_log(f"[INFO] Debug файл {status}")
        except Exception as e:
            log(f"Ошибка переключения debug: {e}", "DEBUG")

    def _update_all(self):
        """Обновляет статус, данные обучения, историю и whitelist"""
        try:
            app = self.window()
            if hasattr(app, 'dpi_starter') and app.dpi_starter:
                is_running = app.dpi_starter.check_process_running_wmi(silent=True)

                if not is_running:
                    self._update_status(self.STATE_STOPPED)
                else:
                    # Если процесс запущен но состояние не определено - ставим LEARNING
                    if self._current_state == self.STATE_STOPPED:
                        self._update_status(self.STATE_LEARNING)

                # Обновляем данные обучения и историю
                self._update_learned_domains()

            # Обновляем whitelist (всегда, даже если runner не запущен)
            self._update_whitelist()
        except Exception:
            pass

    def _on_log_received(self, text: str):
        """Обработчик сигнала - добавляет лог и определяет состояние"""
        print(f"[DEBUG _on_log_received] {text[:80]}...")  # DEBUG
        self.append_log(text)
        self._detect_state_from_line(text)

    def emit_log(self, text: str):
        """Публичный метод для отправки логов (вызывается из callback runner'а).
        Thread-safe: использует очередь вместо прямого emit сигнала.
        """
        # Кладём в очередь - это thread-safe операция
        self._log_queue.put(text)

    def _process_log_queue(self):
        """Обрабатывает очередь логов из main thread (вызывается таймером)"""
        # Обрабатываем до 20 сообщений за раз чтобы не блокировать UI
        for _ in range(20):
            try:
                text = self._log_queue.get_nowait()
                self.log_received.emit(text)
            except Empty:
                break

    def _read_log_file(self):
        """Читает новые строки из лог-файла и определяет состояние"""
        try:
            if not os.path.exists(self._log_file_path):
                return

            with open(self._log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Переходим к последней прочитанной позиции
                f.seek(self._last_log_position)

                # Читаем новые строки
                new_content = f.read()
                if new_content:
                    # Добавляем в лог и определяем состояние
                    for line in new_content.splitlines():
                        if line.strip():
                            self.append_log(line)
                            # Определяем состояние из лога
                            self._detect_state_from_line(line)

                    # Обновляем позицию
                    self._last_log_position = f.tell()
        except Exception as e:
            log(f"Ошибка чтения лог-файла: {e}", "DEBUG")

    def _detect_state_from_line(self, line: str):
        """Определяет состояние оркестратора из строки лога"""
        line_upper = line.upper()

        # Паттерны для WORKING (LOCKED = работает на найденной стратегии)
        working_patterns = ["LOCKED", "[LOCKED]", "SUCCESS"]
        # Паттерны для LEARNING (ищет стратегию)
        learning_patterns = ["UNLOCKING", "UNLOCKED", "FAIL", "CIRCULAR", "TRY STRATEGY"]

        for pattern in working_patterns:
            if pattern in line_upper:
                self._update_status(self.STATE_WORKING)
                return

        for pattern in learning_patterns:
            if pattern in line_upper:
                self._update_status(self.STATE_LEARNING)
                return

    def _update_learned_domains(self):
        """Обновляет данные обученных доменов из реестра через runner"""
        try:
            app = self.window()
            if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                learned = app.orchestra_runner.get_learned_data()
                self._update_domains(learned)
            else:
                self._update_domains({'tls': {}, 'http': {}})
        except Exception as e:
            log(f"Ошибка чтения обученных доменов: {e}", "DEBUG")

    def _update_domains(self, data: dict):
        """Обновляет список обученных доменов (TLS, HTTP) и историю с рейтингами"""
        tls_data = data.get('tls', {})
        http_data = data.get('http', {})
        history_data = data.get('history', {})
        total_count = len(tls_data) + len(http_data)

        # === Обновляем виджет обученных доменов ===
        if total_count == 0:
            self.domains_label.setText("Нет обученных доменов\n\nПри запуске оркестратор начнёт обучение и сохранит лучшие стратегии для каждого домена.")
        else:
            text = f"🔒 Обучено: {total_count}\n\n"

            # TLS домены (порт 443)
            if tls_data:
                text += f"📦 TLS (443): {len(tls_data)}\n"
                for domain, strats in sorted(tls_data.items()):
                    strat_num = strats[0] if strats else "?"
                    rate_str = ""
                    if domain in history_data and strat_num in history_data[domain]:
                        h = history_data[domain][strat_num]
                        rate_str = f" ({h['rate']}%)"
                    text += f"  • {domain} = #{strat_num}{rate_str}\n"

            # HTTP домены (порт 80)
            if http_data:
                if tls_data:
                    text += "\n"
                text += f"🌐 HTTP (80): {len(http_data)}\n"
                for domain, strats in sorted(http_data.items()):
                    strat_num = strats[0] if strats else "?"
                    rate_str = ""
                    if domain in history_data and strat_num in history_data[domain]:
                        h = history_data[domain][strat_num]
                        rate_str = f" ({h['rate']}%)"
                    text += f"  • {domain} = #{strat_num}{rate_str}\n"

            self.domains_label.setText(text)

        # === Обновляем виджет истории ===
        self._update_history_widget(history_data, tls_data, http_data)

    def _update_history_widget(self, history_data: dict, tls_data: dict, http_data: dict):
        """Обновляет виджет истории стратегий с рейтингами"""
        if not history_data:
            self.history_text.setPlainText("")
            return

        lines = []
        total_strategies = 0

        # Сортируем домены по количеству стратегий в истории
        sorted_domains = sorted(history_data.keys(), key=lambda d: len(history_data[d]), reverse=True)

        for domain in sorted_domains:
            strategies = history_data[domain]
            if not strategies:
                continue

            # Определяем статус домена
            is_locked_tls = domain in tls_data
            is_locked_http = domain in http_data
            status = ""
            if is_locked_tls:
                status = " [TLS LOCK]"
            elif is_locked_http:
                status = " [HTTP LOCK]"

            # Сортируем стратегии по рейтингу
            sorted_strats = sorted(strategies.items(), key=lambda x: x[1]['rate'], reverse=True)

            lines.append(f"═══ {domain}{status} ═══")

            for strat_num, h in sorted_strats:
                s = h['successes']
                f = h['failures']
                rate = h['rate']

                # Визуальный индикатор рейтинга
                if rate >= 80:
                    bar = "████████░░"
                    indicator = "🟢"
                elif rate >= 60:
                    bar = "██████░░░░"
                    indicator = "🟡"
                elif rate >= 40:
                    bar = "████░░░░░░"
                    indicator = "🟠"
                else:
                    bar = "██░░░░░░░░"
                    indicator = "🔴"

                lines.append(f"  {indicator} #{strat_num:3d}: {bar} {rate:3d}% ({s}✓/{f}✗)")
                total_strategies += 1

            lines.append("")

        # Добавляем итог
        if lines:
            lines.insert(0, f"Всего: {len(history_data)} доменов, {total_strategies} записей\n")

        self.history_text.setPlainText("\n".join(lines))

    def append_log(self, text: str):
        """Добавляет строку в лог"""
        self.log_text.append(text)
        # Прокручиваем вниз
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def start_monitoring(self):
        """Запускает мониторинг"""
        # Подключаем callback к runner если он уже запущен (при автозапуске callback не устанавливается)
        try:
            app = self.window()
            if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                runner = app.orchestra_runner
                if runner.output_callback is None:
                    print("[DEBUG start_monitoring] Устанавливаем callback на запущенный runner")  # DEBUG
                    runner.set_output_callback(self.emit_log)
        except Exception as e:
            print(f"[DEBUG start_monitoring] Ошибка установки callback: {e}")  # DEBUG

        # Сбрасываем позицию чтения лога при старте
        self._last_log_position = 0
        self.update_timer.start(5000)  # Обновляем каждые 5 секунд (было 500мс)
        self._update_all()  # Сразу обновляем

    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.update_timer.stop()

    def showEvent(self, event):
        """Автозапуск мониторинга при показе страницы"""
        super().showEvent(event)
        self.start_monitoring()

    def hideEvent(self, event):
        """Остановка мониторинга при скрытии страницы"""
        super().hideEvent(event)
        self.stop_monitoring()

    def set_learned_data(self, data: dict):
        """Устанавливает данные обучения"""
        self._update_domains(data)

    # ==================== WHITELIST METHODS ====================

    def _update_whitelist(self):
        """Обновляет список whitelist из runner или напрямую из реестра"""
        self.whitelist_widget.clear()

        try:
            # Пробуем получить через runner
            app = self.window()
            if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                data = app.orchestra_runner.get_full_whitelist()
                default_domains = data.get('default', [])
                user_domains = data.get('user', [])
            else:
                # Runner не готов - загружаем напрямую
                default_domains = list(DEFAULT_WHITELIST)
                user_domains = []
                # Загружаем user домены из реестра
                reg_data = reg(REGISTRY_ORCHESTRA, "Whitelist")
                if reg_data:
                    user_domains = [d.strip() for d in reg_data.split(",") if d.strip()]

            # Добавляем default домены (серые, нельзя удалить)
            for domain in sorted(default_domains):
                item = QListWidgetItem(f"🔒 {domain}")
                item.setData(Qt.ItemDataRole.UserRole, ("default", domain))
                item.setForeground(Qt.GlobalColor.gray)
                self.whitelist_widget.addItem(item)

            # Добавляем user домены (можно удалить)
            for domain in sorted(user_domains):
                item = QListWidgetItem(f"👤 {domain}")
                item.setData(Qt.ItemDataRole.UserRole, ("user", domain))
                self.whitelist_widget.addItem(item)

        except Exception as e:
            log(f"Ошибка обновления whitelist: {e}", "DEBUG")

    def _add_whitelist_domain(self):
        """Добавляет домен в whitelist"""
        domain = self.whitelist_input.text().strip().lower()
        if not domain:
            return

        try:
            app = self.window()
            if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                if app.orchestra_runner.add_to_whitelist(domain):
                    self.whitelist_input.clear()
                    self._update_whitelist()
                    self.append_log(f"[INFO] Добавлен в whitelist: {domain}")
                else:
                    self.append_log(f"[WARNING] Не удалось добавить: {domain}")
        except Exception as e:
            log(f"Ошибка добавления в whitelist: {e}", "DEBUG")

    def _remove_whitelist_domain(self):
        """Удаляет выбранный домен из whitelist"""
        current = self.whitelist_widget.currentItem()
        if not current:
            return

        data = current.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        dtype, domain = data

        if dtype == "default":
            self.append_log(f"[WARNING] Нельзя удалить базовый домен: {domain}")
            return

        try:
            app = self.window()
            if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                if app.orchestra_runner.remove_from_whitelist(domain):
                    self._update_whitelist()
                    self.append_log(f"[INFO] Удалён из whitelist: {domain}")
        except Exception as e:
            log(f"Ошибка удаления из whitelist: {e}", "DEBUG")
