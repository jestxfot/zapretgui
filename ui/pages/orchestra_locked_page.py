# ui/pages/orchestra_locked_page.py
"""
Страница управления залоченными стратегиями оркестратора.
Каждый домен отображается в виде редактируемого ряда с QSpinBox для номера стратегии.
Изменения автоматически сохраняются в реестр.
"""
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QWidget,
    QLineEdit, QSpinBox, QFrame, QMessageBox, QApplication
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from ui.widgets import NotificationBanner
from log import log
from orchestra.locked_strategies_manager import ASKEY_ALL


class LockedDomainRow(QFrame):
    """Виджет-ряд для одного залоченного домена с редактируемой стратегией"""

    def __init__(self, domain: str, strategy: int, proto: str, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.proto = proto
        self._setup_ui(domain, strategy, proto)

    def _setup_ui(self, domain: str, strategy: int, proto: str):
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
            }
            QFrame:hover {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Домен
        domain_label = QLabel(domain)
        domain_label.setStyleSheet("color: white; font-size: 13px; border: none; background: transparent;")
        layout.addWidget(domain_label, 1)

        # Протокол
        proto_label = QLabel(f"[{proto.upper()}]")
        proto_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; border: none; background: transparent;")
        proto_label.setFixedWidth(45)
        layout.addWidget(proto_label)

        # Стратегия SpinBox
        self.strat_spin = QSpinBox()
        self.strat_spin.setRange(1, 999)
        self.strat_spin.setValue(strategy)
        self.strat_spin.setFixedWidth(70)
        self.strat_spin.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.08);
                color: #60cdff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QSpinBox:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QSpinBox:focus {
                border: 1px solid #60cdff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
                border: none;
            }
        """)
        self.strat_spin.valueChanged.connect(self._on_strategy_changed)
        layout.addWidget(self.strat_spin)

        # Кнопка удаления (разлочить)
        delete_btn = QPushButton()
        delete_btn.setIcon(qta.icon("mdi.lock-open-variant-outline", color="white"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setToolTip("Разлочить")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 152, 0, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(255, 152, 0, 0.3);
            }
        """)
        delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(delete_btn)

    def _on_strategy_changed(self, value: int):
        """При изменении стратегии - уведомляем родителя для автосохранения"""
        parent = self.parent()
        while parent and not isinstance(parent, OrchestraLockedPage):
            parent = parent.parent()
        if parent:
            parent._on_row_strategy_changed(self.domain, value, self.proto)

    def _on_delete_clicked(self):
        """При клике на удаление - уведомляем родителя"""
        parent = self.parent()
        while parent and not isinstance(parent, OrchestraLockedPage):
            parent = parent.parent()
        if parent:
            parent._on_row_delete_requested(self.domain, self.proto)


class OrchestraLockedPage(BasePage):
    """Страница управления залоченными стратегиями"""

    def __init__(self, parent=None):
        super().__init__(
            "Залоченные стратегии",
            "Домены с фиксированной стратегией. Оркестратор не будет менять стратегию для этих доменов. Это значит что оркестратор нашёл для этих сайтов наилучшую стратегию. Вы можете зафиксировать свою стратегию для домена здесь.\nЕсли Вас не устраивает текущая стратегия - заблокируйте её здесь и оркестратор начнёт обучение заново при следующем посещении сайта.\nЕсли Вы просто хотите начать обучение заново - разлочьте стратегию.",
            parent
        )
        self.setObjectName("orchestraLockedPage")
        self._all_locked_data = []  # Кэш данных для фильтрации
        # Инициализируем пустые данные (будут загружены при первом showEvent)
        self._direct_locked_by_askey = {askey: {} for askey in ASKEY_ALL}
        self._initial_load_done = False
        self._setup_ui()

    def _setup_ui(self):
        # === Уведомление (баннер) ===
        self.notification_banner = NotificationBanner(self)
        self.layout.addWidget(self.notification_banner)

        # === Карточка добавления ===
        add_card = SettingsCard("Залочить стратегию вручную")
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

        # Домен
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com")
        self.domain_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 8px 12px;
            }
            QLineEdit:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QLineEdit:focus {
                border: 1px solid #60cdff;
            }
        """)
        add_layout.addWidget(self.domain_input, 1)

        # Протокол (askey)
        self.proto_combo = QComboBox()
        self.proto_combo.addItems([askey.upper() for askey in ASKEY_ALL])
        self.proto_combo.setFixedWidth(90)
        self.proto_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.06);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 8px 12px;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: white;
                selection-background-color: #0078d4;
            }
        """)
        add_layout.addWidget(self.proto_combo)

        # Стратегия
        self.strat_spin = QSpinBox()
        self.strat_spin.setRange(1, 999)
        self.strat_spin.setValue(1)
        self.strat_spin.setFixedWidth(70)
        self.strat_spin.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.06);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 8px 12px;
            }
            QSpinBox:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QSpinBox:focus {
                border: 1px solid #60cdff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
                border: none;
            }
        """)
        add_layout.addWidget(self.strat_spin)

        # Кнопка добавления
        self.lock_btn = QPushButton()
        self.lock_btn.setIcon(qta.icon("mdi.plus", color="white"))
        self.lock_btn.setIconSize(QSize(18, 18))
        self.lock_btn.setFixedSize(36, 36)
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.setToolTip("Залочить стратегию")
        self.lock_btn.clicked.connect(self._lock_strategy)
        self.lock_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(76, 175, 80, 0.2);
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(76, 175, 80, 0.4);
            }
        """)
        add_layout.addWidget(self.lock_btn)

        add_card.add_layout(add_layout)
        self.layout.addWidget(add_card)

        # === Карточка списка ===
        list_card = SettingsCard("Список залоченных")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        # Кнопка и счётчик сверху
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по доменам...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_list)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 200px;
            }
            QLineEdit:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QLineEdit:focus {
                border: 1px solid #60cdff;
            }
        """)
        top_row.addWidget(self.search_input)

        # Кнопка обновления списка из реестра
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setIcon(qta.icon("mdi.refresh", color="white"))
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._reload_from_registry)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.20);
            }
        """)
        top_row.addWidget(self.refresh_btn)

        self.unlock_all_btn = QPushButton("Разлочить все")
        self.unlock_all_btn.setIcon(qta.icon("mdi.lock-open-variant-outline", color="white"))
        self.unlock_all_btn.setIconSize(QSize(16, 16))
        self.unlock_all_btn.setFixedHeight(32)
        self.unlock_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unlock_all_btn.clicked.connect(self._unlock_all)
        self.unlock_all_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.20);
            }
        """)
        top_row.addWidget(self.unlock_all_btn)
        top_row.addStretch()

        list_layout.addLayout(top_row)

        # Счётчик на отдельной строке (чтобы влезал в таб)
        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        list_layout.addWidget(self.count_label)

        # Подсказка
        hint_label = QLabel("Измените номер стратегии и она автоматически сохранится")
        hint_label.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 10px; font-style: italic;")
        list_layout.addWidget(hint_label)

        # Контейнер для рядов (без скролла - страница сама прокручивается)
        self.rows_container = QWidget()
        self.rows_container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 8, 0, 0)
        self.rows_layout.setSpacing(4)
        list_layout.addWidget(self.rows_container)

        # Храним ссылки на ряды для быстрого доступа
        self._domain_rows = {}

        list_card.add_layout(list_layout)
        self.layout.addWidget(list_card)

    def showEvent(self, event):
        """При показе страницы загружаем данные один раз (без авто-обновления)"""
        super().showEvent(event)
        # Загружаем данные только при первом показе
        if not self._initial_load_done:
            self._initial_load_done = True
            self._reload_from_registry()

    def _get_runner(self):
        """Получает orchestra_runner из главного окна"""
        app = self.window()
        if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
            return app.orchestra_runner
        return None

    def _get_blocked_manager(self):
        """Получает blocked_strategies_manager из runner или создает временный"""
        runner = self._get_runner()
        if runner and hasattr(runner, 'blocked_manager'):
            return runner.blocked_manager
        # Создаем временный менеджер для проверки
        from orchestra.blocked_strategies_manager import BlockedStrategiesManager
        temp_manager = BlockedStrategiesManager()
        temp_manager.load()
        return temp_manager

    def _show_blocked_warning(self, domain: str, strategy: int):
        """
        Показывает предупреждение о заблокированной стратегии.

        Args:
            domain: Домен для которого заблокирована стратегия
            strategy: Номер заблокированной стратегии
        """
        message = (
            f"Стратегия #{strategy} заблокирована для {domain}. "
            "Разблокируйте её на странице 'Заблокированные'."
        )
        self.notification_banner.show_warning(message, auto_hide_ms=7000)

    def _refresh_data(self):
        """Обновляет все данные на странице (из памяти)"""
        self._refresh_locked_list()

    def _reload_from_registry(self):
        """Перезагружает данные из реестра и обновляет список"""
        # Визуальный фидбек
        old_text = self.refresh_btn.text()
        self.refresh_btn.setText("Загрузка...")
        self.refresh_btn.setEnabled(False)
        QApplication.processEvents()  # Обновить UI сразу

        try:
            runner = self._get_runner()
            if runner and hasattr(runner, 'locked_manager'):
                # Перезагружаем данные из реестра
                runner.locked_manager.load()
                log("Список залоченных перезагружен из реестра (runner)", "INFO")
            else:
                # Нет активного runner - загружаем напрямую из реестра
                self._load_directly_from_registry()
                log("Список залоченных перезагружен из реестра (direct)", "INFO")
            # Обновляем UI
            self._refresh_data()
        finally:
            # Восстанавливаем кнопку
            self.refresh_btn.setText(old_text)
            self.refresh_btn.setEnabled(True)

    def _load_directly_from_registry(self):
        """Загружает данные напрямую из реестра (без активного runner)"""
        from orchestra.locked_strategies_manager import LockedStrategiesManager
        # Создаём временный менеджер для загрузки данных
        temp_manager = LockedStrategiesManager()
        temp_manager.load()
        # Сохраняем данные для отображения
        self._direct_locked_by_askey = {askey: dict(temp_manager.locked_by_askey[askey]) for askey in ASKEY_ALL}
        total = sum(len(strategies) for strategies in self._direct_locked_by_askey.values())
        log(f"Загружено напрямую из реестра: {total} залоченных стратегий", "INFO")

    def _refresh_locked_list(self):
        """Обновляет список залоченных стратегий"""
        # Очищаем старые ряды
        self._domain_rows.clear()
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._all_locked_data = []

        runner = self._get_runner()

        # Источник данных: runner или напрямую загруженные из реестра
        if runner:
            locked_data = runner.locked_manager.locked_by_askey
        elif hasattr(self, '_direct_locked_by_askey'):
            locked_data = self._direct_locked_by_askey
        else:
            # Нет данных - попробуем загрузить
            self._load_directly_from_registry()
            locked_data = getattr(self, '_direct_locked_by_askey', {askey: {} for askey in ASKEY_ALL})

        # Собираем все данные по всем askey
        for askey in ASKEY_ALL:
            for hostname, strategy in locked_data.get(askey, {}).items():
                self._all_locked_data.append((hostname, strategy, askey))

        self._all_locked_data.sort(key=lambda x: x[0].lower())

        # Создаём ряды для каждого домена
        for domain, strategy, proto in self._all_locked_data:
            row = LockedDomainRow(domain, strategy, proto)
            key = f"{domain}:{proto}"
            self._domain_rows[key] = row
            self.rows_layout.addWidget(row)

        self._update_count()
        self._apply_filter()

    def _filter_list(self, text: str):
        """Фильтрует список по введённому тексту"""
        self._apply_filter()

    def _apply_filter(self):
        """Применяет текущий фильтр к рядам"""
        search = self.search_input.text().lower().strip()
        for key, row in self._domain_rows.items():
            domain = row.domain.lower()
            row.setVisible(search in domain if search else True)

    def _on_row_strategy_changed(self, domain: str, new_strategy: int, askey: str):
        """Автосохранение при изменении стратегии в SpinBox"""
        # Проверяем, не заблокирована ли эта стратегия для домена
        blocked_manager = self._get_blocked_manager()
        if blocked_manager.is_blocked(domain, new_strategy):
            self._show_blocked_warning(domain, new_strategy)
            log(f"[USER] Попытка изменить на заблокированную стратегию #{new_strategy} для {domain}", "WARNING")
            # Восстанавливаем предыдущее значение в SpinBox
            key = f"{domain}:{askey}"
            if key in self._domain_rows:
                row = self._domain_rows[key]
                # Получаем текущее значение из менеджера
                runner = self._get_runner()
                if runner and hasattr(runner, 'locked_manager'):
                    current = runner.locked_manager.locked_by_askey.get(askey, {}).get(domain, 1)
                elif askey in self._direct_locked_by_askey:
                    current = self._direct_locked_by_askey[askey].get(domain, 1)
                else:
                    current = 1
                row.strat_spin.blockSignals(True)
                row.strat_spin.setValue(current)
                row.strat_spin.blockSignals(False)
            return  # Не сохраняем заблокированную стратегию

        runner = self._get_runner()
        if runner and hasattr(runner, 'locked_manager'):
            # Используем lock для изменения (он автоматически сохраняет)
            # user_lock=True - ручное изменение через UI не перезаписывается auto-lock
            runner.locked_manager.lock(domain, new_strategy, askey, user_lock=True)
            log(f"[USER] Изменена стратегия: {domain} [{askey.upper()}] -> #{new_strategy}", "INFO")
            # Регенерируем learned-strategies.lua и перезапускаем для применения user lock
            if runner.is_running():
                runner._generate_learned_lua()
                log("[USER] Перезапуск оркестратора для применения user lock...", "INFO")
                runner.restart()
        else:
            # Без runner - сохраняем напрямую в реестр
            from orchestra.locked_strategies_manager import LockedStrategiesManager
            temp_manager = LockedStrategiesManager()
            temp_manager.load()
            temp_manager.lock(domain, new_strategy, askey, user_lock=True)
            # Обновляем локальный кэш
            if askey in self._direct_locked_by_askey:
                self._direct_locked_by_askey[askey][domain] = new_strategy
            log(f"[USER] Изменена стратегия (direct): {domain} [{askey.upper()}] -> #{new_strategy}", "INFO")

    def _on_row_delete_requested(self, domain: str, askey: str):
        """Разлочивание при нажатии кнопки удаления"""
        runner = self._get_runner()
        if runner and hasattr(runner, 'locked_manager'):
            runner.locked_manager.unlock(domain, askey)
            log(f"Разлочена стратегия для {domain} [{askey.upper()}]", "INFO")
            self._refresh_data()
            # Перезапускаем оркестратор
            if runner.is_running():
                QMessageBox.information(
                    self,
                    "Перезапуск оркестратора",
                    f"Стратегия разлочена для {domain}.\n\nОркестратор будет перезапущен для применения изменений."
                )
                runner.restart()
        else:
            # Без runner - удаляем напрямую из реестра
            from orchestra.locked_strategies_manager import LockedStrategiesManager
            temp_manager = LockedStrategiesManager()
            temp_manager.load()
            temp_manager.unlock(domain, askey)
            # Обновляем локальный кэш
            if askey in self._direct_locked_by_askey and domain in self._direct_locked_by_askey[askey]:
                del self._direct_locked_by_askey[askey][domain]
            log(f"Разлочена стратегия (direct) для {domain} [{askey.upper()}]", "INFO")
            self._refresh_data()

    def _update_count(self):
        """Обновляет счётчик"""
        runner = self._get_runner()
        if runner:
            locked_data = runner.locked_manager.locked_by_askey
        elif hasattr(self, '_direct_locked_by_askey'):
            locked_data = self._direct_locked_by_askey
        else:
            self.count_label.setText("Нажмите 'Обновить' для загрузки данных")
            return

        # Подсчёт по всем askey
        counts = {askey: len(locked_data.get(askey, {})) for askey in ASKEY_ALL}
        total = sum(counts.values())

        # Формируем вывод с разбиением по TCP/UDP
        tcp_count = counts.get('tls', 0) + counts.get('http', 0) + counts.get('mtproto', 0)
        udp_count = sum(counts.get(k, 0) for k in ['quic', 'discord', 'wireguard', 'dns', 'stun', 'unknown'])

        self.count_label.setText(
            f"Всего залочено: {total} (TCP: {tcp_count}, UDP: {udp_count})"
        )

    def _lock_strategy(self):
        """Залочивает стратегию"""
        domain = self.domain_input.text().strip().lower()
        if not domain:
            return

        strategy = self.strat_spin.value()
        askey = self.proto_combo.currentText().lower()

        # Проверяем, не заблокирована ли эта стратегия для домена
        blocked_manager = self._get_blocked_manager()
        if blocked_manager.is_blocked(domain, strategy):
            self._show_blocked_warning(domain, strategy)
            log(f"[USER] Попытка залочить заблокированную стратегию #{strategy} для {domain}", "WARNING")
            return  # Не лочим заблокированную стратегию

        runner = self._get_runner()
        if runner and hasattr(runner, 'locked_manager'):
            # user_lock=True - ручное добавление через UI не перезаписывается auto-lock
            runner.locked_manager.lock(domain, strategy, askey, user_lock=True)
            log(f"[USER] Залочена стратегия #{strategy} для {domain} [{askey.upper()}]", "INFO")
            # Регенерируем learned-strategies.lua и перезапускаем для применения user lock
            if runner.is_running():
                runner._generate_learned_lua()
                log("[USER] Перезапуск оркестратора для применения user lock...", "INFO")
                runner.restart()
        else:
            # Без runner - сохраняем напрямую
            from orchestra.locked_strategies_manager import LockedStrategiesManager
            temp_manager = LockedStrategiesManager()
            temp_manager.load()
            temp_manager.lock(domain, strategy, askey, user_lock=True)
            # Обновляем локальный кэш
            if askey in self._direct_locked_by_askey:
                self._direct_locked_by_askey[askey][domain] = strategy
            log(f"[USER] Залочена стратегия (direct) #{strategy} для {domain} [{askey.upper()}]", "INFO")

        # Очищаем поле и обновляем список
        self.domain_input.clear()
        self._refresh_data()

    def _unlock_all(self):
        """Разлочивает все стратегии"""
        runner = self._get_runner()
        if not runner:
            return

        total = sum(len(strategies) for strategies in runner.locked_manager.locked_by_askey.values())
        if total == 0:
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Разлочить все {total} стратегий?\nОркестратор начнёт обучение заново.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Разлочиваем все домены по всем askey
            for askey in ASKEY_ALL:
                for domain in list(runner.locked_manager.locked_by_askey.get(askey, {}).keys()):
                    runner.locked_manager.unlock(domain, askey)
            log(f"Разлочены все {total} стратегий", "INFO")
            self._refresh_data()
            # Перезапускаем оркестратор чтобы сбросить все hrec.nstrategy
            if runner.is_running():
                QMessageBox.information(
                    self,
                    "Перезапуск оркестратора",
                    f"Разлочены все {total} стратегий.\n\nОркестратор будет перезапущен для применения изменений."
                )
                runner.restart()
