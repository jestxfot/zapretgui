# ui/dialogs/add_category_dialog.py
"""
Диалог добавления пользовательской категории (сервиса/сайта).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QFormLayout, QFrame, QMessageBox,
    QWidget, QSpinBox, QCheckBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import qtawesome as qta

from log import log


class CompactInput(QLineEdit):
    """Компактное поле ввода"""
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(32)
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.06);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                background: rgba(96, 205, 255, 0.1);
            }
        """)


class CompactCombo(QComboBox):
    """Компактный комбобокс"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.06);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QComboBox:focus {
                background: rgba(96, 205, 255, 0.1);
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QComboBox QAbstractItemView {
                background: #252525;
                color: white;
                selection-background-color: rgba(96, 205, 255, 0.2);
                border: none;
            }
        """)


class AddCategoryDialog(QDialog):
    """Диалог добавления новой категории"""
    
    category_added = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить категорию")
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background: #1a1a1a;
            }
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 11px;
            }
            QCheckBox {
                color: rgba(255, 255, 255, 0.8);
                font-size: 11px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: none;
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator:checked {
                background: #60cdff;
            }
        """)
        
        self._build_ui()
        self.adjustSize()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Заголовок
        header = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.plus-circle', color='#60cdff').pixmap(20, 20))
        header.addWidget(icon_label)
        
        title = QLabel("Новая категория")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        title.setStyleSheet("color: white;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # === ОСНОВНЫЕ ПОЛЯ ===
        basic_frame = QFrame()
        basic_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 6px;
            }
        """)
        basic_layout = QGridLayout(basic_frame)
        basic_layout.setContentsMargins(12, 10, 12, 10)
        basic_layout.setSpacing(8)
        basic_layout.setColumnStretch(1, 1)
        
        # Ключ
        basic_layout.addWidget(QLabel("Ключ:"), 0, 0)
        self.key_input = CompactInput("mysite_tcp")
        self.key_input.setToolTip("Уникальный ID (латиница, цифры, _)")
        basic_layout.addWidget(self.key_input, 0, 1)
        
        # Название
        basic_layout.addWidget(QLabel("Название:"), 1, 0)
        self.name_input = CompactInput("Мой сайт")
        basic_layout.addWidget(self.name_input, 1, 1)
        
        layout.addWidget(basic_frame)
        
        # === ФИЛЬТР ===
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 6px;
            }
        """)
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(8)
        filter_layout.setColumnStretch(1, 1)
        
        # Заголовок секции
        filter_title = QLabel("⚙ Фильтр")
        filter_title.setStyleSheet("color: #60cdff; font-weight: 600; font-size: 11px;")
        filter_layout.addWidget(filter_title, 0, 0, 1, 2)
        
        # Протокол и порты в одной строке
        proto_ports = QHBoxLayout()
        proto_ports.setSpacing(8)
        
        self.protocol_combo = CompactCombo()
        self.protocol_combo.addItems(["TCP", "UDP"])
        self.protocol_combo.setFixedWidth(70)
        proto_ports.addWidget(self.protocol_combo)
        
        self.ports_input = CompactInput("80, 443")
        self.ports_input.setToolTip("Порты через запятую или диапазон")
        proto_ports.addWidget(self.ports_input)
        
        filter_layout.addWidget(QLabel("Протокол/порты:"), 1, 0)
        proto_widget = QWidget()
        proto_widget.setLayout(proto_ports)
        filter_layout.addWidget(proto_widget, 1, 1)
        
        # Тип фильтра
        filter_layout.addWidget(QLabel("Тип:"), 2, 0)
        self.filter_type_combo = CompactCombo()
        self.filter_type_combo.addItems(["hostlist", "ipset", "hostlist-domains"])
        self.filter_type_combo.setToolTip("hostlist - домены, ipset - IP адреса")
        filter_layout.addWidget(self.filter_type_combo, 2, 1)
        
        # Файл списка
        filter_layout.addWidget(QLabel("Файл:"), 3, 0)
        self.list_file_input = CompactInput("my-sites.txt")
        self.list_file_input.setToolTip("Файл в папке lists/")
        filter_layout.addWidget(self.list_file_input, 3, 1)
        
        layout.addWidget(filter_frame)
        
        # === СТРАТЕГИЯ ===
        strat_frame = QFrame()
        strat_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 6px;
            }
        """)
        strat_layout = QGridLayout(strat_frame)
        strat_layout.setContentsMargins(12, 10, 12, 10)
        strat_layout.setSpacing(8)
        strat_layout.setColumnStretch(1, 1)
        
        strat_title = QLabel("🎯 Стратегия")
        strat_title.setStyleSheet("color: #60cdff; font-weight: 600; font-size: 11px;")
        strat_layout.addWidget(strat_title, 0, 0, 1, 2)
        
        # Тип стратегий и стратегия по умолчанию
        strat_layout.addWidget(QLabel("Тип:"), 1, 0)
        self.strategy_type_combo = CompactCombo()
        self.strategy_type_combo.addItems(["tcp", "udp", "http80"])
        strat_layout.addWidget(self.strategy_type_combo, 1, 1)
        
        strat_layout.addWidget(QLabel("По умолчанию:"), 2, 0)
        self.default_strategy_input = CompactInput("other_seqovl")
        strat_layout.addWidget(self.default_strategy_input, 2, 1)
        
        layout.addWidget(strat_frame)
        
        # === ВНЕШНИЙ ВИД ===
        look_frame = QFrame()
        look_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 6px;
            }
        """)
        look_layout = QGridLayout(look_frame)
        look_layout.setContentsMargins(12, 10, 12, 10)
        look_layout.setSpacing(8)
        look_layout.setColumnStretch(1, 1)
        
        look_title = QLabel("🎨 Вид")
        look_title.setStyleSheet("color: #60cdff; font-weight: 600; font-size: 11px;")
        look_layout.addWidget(look_title, 0, 0, 1, 2)
        
        # Иконка и цвет
        icon_color = QHBoxLayout()
        icon_color.setSpacing(8)
        
        self.icon_combo = CompactCombo()
        self._populate_icons()
        self.icon_combo.setFixedWidth(140)
        icon_color.addWidget(self.icon_combo)
        
        self.color_input = CompactInput("#60cdff")
        self.color_input.setFixedWidth(80)
        self.color_input.setToolTip("Цвет иконки (HEX)")
        icon_color.addWidget(self.color_input)
        icon_color.addStretch()
        
        look_layout.addWidget(QLabel("Иконка/цвет:"), 1, 0)
        icon_widget = QWidget()
        icon_widget.setLayout(icon_color)
        look_layout.addWidget(icon_widget, 1, 1)
        
        # Порядок
        order_layout = QHBoxLayout()
        order_layout.setSpacing(8)
        
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 999)
        self.order_spin.setValue(100)
        self.order_spin.setFixedWidth(70)
        self.order_spin.setFixedHeight(32)
        self.order_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255, 255, 255, 0.06);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QSpinBox:focus {
                background: rgba(96, 205, 255, 0.1);
            }
        """)
        order_layout.addWidget(self.order_spin)
        order_layout.addStretch()
        
        look_layout.addWidget(QLabel("Порядок:"), 2, 0)
        order_widget = QWidget()
        order_widget.setLayout(order_layout)
        look_layout.addWidget(order_widget, 2, 1)
        
        layout.addWidget(look_frame)
        
        # === ОПЦИИ ===
        options_layout = QHBoxLayout()
        options_layout.setSpacing(16)
        
        self.requires_all_ports_check = QCheckBox("Все порты")
        self.requires_all_ports_check.setToolTip("Требует агрессивного режима")
        options_layout.addWidget(self.requires_all_ports_check)
        
        self.strip_payload_check = QCheckBox("Strip payload")
        self.strip_payload_check.setToolTip("Убирать payload (для IPset)")
        options_layout.addWidget(self.strip_payload_check)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # === КНОПКИ ===
        layout.addSpacing(4)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        buttons_layout.addStretch()
        
        save_btn = QPushButton("  Сохранить")
        save_btn.setIcon(qta.icon('fa5s.check', color='white'))
        save_btn.setFixedHeight(34)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #1a86d9;
            }
        """)
        save_btn.clicked.connect(self._save_category)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
        
    def _populate_icons(self):
        """Заполняет список иконок"""
        icons = [
            ("fa5s.globe", "🌐 Сайт"),
            ("fa5s.gamepad", "🎮 Игра"),
            ("fa5s.video", "📹 Видео"),
            ("fa5s.music", "🎵 Музыка"),
            ("fa5s.comments", "💬 Чат"),
            ("fa5s.cloud", "☁️ Облако"),
            ("fa5s.server", "🖥️ Сервер"),
            ("fa5s.shield-alt", "🛡️ VPN"),
            ("fa5s.download", "⬇️ Загрузка"),
            ("fa5s.shopping-cart", "🛒 Магазин"),
            ("fa5s.code", "💻 Код"),
            ("fa5b.chrome", "🌐 Браузер"),
        ]
        
        for icon_name, display_name in icons:
            self.icon_combo.addItem(display_name, icon_name)
            
    def _build_base_filter(self):
        """Строит base_filter"""
        protocol = self.protocol_combo.currentText()
        ports = self.ports_input.text().strip() or "443"
        filter_type = self.filter_type_combo.currentText()
        list_file = self.list_file_input.text().strip() or "my-sites.txt"
        
        proto_filter = f"--filter-{'udp' if protocol == 'UDP' else 'tcp'}={ports}"
        
        if filter_type == "hostlist":
            list_filter = f"--hostlist={list_file}"
        elif filter_type == "ipset":
            list_filter = f"--ipset={list_file}"
        else:
            domain = list_file.replace('.txt', '').replace('hostlist-', '')
            list_filter = f"--hostlist-domains={domain}"
            
        return f"{proto_filter} {list_filter}"
        
    def _save_category(self):
        """Сохраняет категорию"""
        key = self.key_input.text().strip()
        name = self.name_input.text().strip()
        
        if not key:
            QMessageBox.warning(self, "Ошибка", "Введите ключ категории")
            return
            
        if not all(c.isalnum() or c == '_' for c in key):
            QMessageBox.warning(self, "Ошибка", "Ключ: только латиница, цифры и _")
            return
            
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название")
            return
            
        category_data = {
            "key": key,
            "full_name": name,
            "description": f"{name} ({self.ports_input.text()})",
            "tooltip": f"🌐 {name}\nПорты: {self.ports_input.text()}",
            "color": self.color_input.text().strip() or "#60cdff",
            "default_strategy": self.default_strategy_input.text().strip() or "other_seqovl",
            "ports": self.ports_input.text().strip() or "443",
            "protocol": self.protocol_combo.currentText(),
            "order": self.order_spin.value(),
            "command_order": self.order_spin.value(),
            "needs_new_separator": True,
            "command_group": "user",
            "icon_name": self.icon_combo.currentData() or "fa5s.globe",
            "icon_color": self.color_input.text().strip() or "#60cdff",
            "base_filter": self._build_base_filter(),
            "strategy_type": self.strategy_type_combo.currentText(),
            "requires_all_ports": self.requires_all_ports_check.isChecked(),
            "strip_payload": self.strip_payload_check.isChecked()
        }
        
        try:
            from strategy_menu.strategies.strategy_loader import save_user_category
            from config import LISTS_FOLDER
            import os
            
            success, error = save_user_category(category_data)
            if success:
                log(f"Категория '{key}' сохранена", "INFO")
                self.category_added.emit(category_data)
                
                # ✅ Создаём файл списка автоматически если его нет
                list_file = self.list_file_input.text().strip() or "my-sites.txt"
                list_path = os.path.join(LISTS_FOLDER, list_file)
                
                file_created = False
                if not os.path.exists(list_path):
                    try:
                        os.makedirs(LISTS_FOLDER, exist_ok=True)
                        with open(list_path, 'w', encoding='utf-8') as f:
                            f.write(f"# Список для категории: {name}\n")
                            f.write("# Добавьте домены, по одному на строку\n")
                            f.write("# Пример:\n")
                            f.write("# example.com\n")
                            f.write("# subdomain.example.org\n")
                        file_created = True
                        log(f"Создан файл списка: {list_path}", "INFO")
                    except Exception as e:
                        log(f"Не удалось создать файл {list_path}: {e}", "WARNING")
                
                if file_created:
                    QMessageBox.information(
                        self, "Готово", 
                        f"✅ Категория «{name}» добавлена!\n\n"
                        f"Файл lists/{list_file} создан.\n"
                        f"Добавьте в него домены (по одному на строку)."
                    )
                else:
                    QMessageBox.information(
                        self, "Готово", 
                        f"✅ Категория «{name}» добавлена!\n\n"
                        f"Файл lists/{list_file} уже существует."
                    )
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", f"Ошибка: {error}")
                
        except Exception as e:
            log(f"Ошибка сохранения: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", str(e))
