# ui_main.py
from PyQt5.QtCore    import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QSpacerItem, QSizePolicy, QFrame
)

from theme import (THEMES, BUTTON_STYLE, COMMON_STYLE, BUTTON_HEIGHT,
                   STYLE_SHEET, RippleButton)


class MainWindowUI:
    """
    Миксин-класс: создаёт интерфейс, ничего не знает о логике.
    Гарантирует наличие атрибутов, которыми пользуется main.py
    (start_btn, stop_btn, theme_combo, status_label, button_grid …)
    """

    # ------------------------------------------------------------------
    def build_ui(self: QWidget, width: int, height: int):
        self.setStyleSheet(STYLE_SHEET)
        self.setMinimumSize(width, height)

        root = QVBoxLayout(self)

        # ---------- Заголовок ------------------------------------------
        ttl = QLabel("Zapret GUI")
        ttl.setStyleSheet(f"{COMMON_STYLE} font:16pt Arial;")
        root.addWidget(ttl, alignment=Qt.AlignCenter)

        line = QFrame(); line.setFrameShape(QFrame.HLine)
        root.addWidget(line)

        # ---------- Статус программы -----------------------------------
        proc_lbl = QLabel("Статус программы:"); proc_lbl.setStyleSheet("font-weight:bold")
        self.process_status_value = QLabel("проверка…")

        proc_lay = QHBoxLayout()
        proc_lay.addWidget(proc_lbl); proc_lay.addWidget(self.process_status_value)
        proc_lay.addStretch()
        root.addLayout(proc_lay)

        # ---------- Текущая стратегия ----------------------------------
        cur_hdr = QLabel("Текущая стратегия:")
        cur_hdr.setStyleSheet(f"{COMMON_STYLE} font-weight:bold;")
        cur_hdr.setAlignment(Qt.AlignCenter)
        root.addWidget(cur_hdr)

        self.current_strategy_label = QLabel("Не выбрана")
        self.current_strategy_label.setAlignment(Qt.AlignCenter)
        self.current_strategy_label.setWordWrap(True)
        self.current_strategy_label.setMinimumHeight(40)
        self.current_strategy_label.setStyleSheet(
            f"{COMMON_STYLE} font-weight:bold; font-size:12pt; color:#0077ff;")
        root.addWidget(self.current_strategy_label)

        self.select_strategy_btn = RippleButton(
            "Сменить стратегию обхода блокировок…", self, "0, 119, 255")
        self.select_strategy_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        root.addWidget(self.select_strategy_btn)

        # ---------- Grid-кнопки ----------------------------------------
        grid = QGridLayout(); grid.setColumnStretch(0,1); grid.setColumnStretch(1,1)
        self.button_grid = grid

        self.start_btn  = RippleButton("Запустить Zapret", self, "54, 153, 70")
        self.stop_btn   = RippleButton("Остановить Zapret", self, "255, 93, 174")
        self.autostart_enable_btn  = RippleButton("Вкл. автозапуск", self, "54, 153, 70")
        self.autostart_disable_btn = RippleButton("Выкл. автозапуск", self, "255, 93, 174")

        for b,c in ((self.start_btn,"54, 153, 70"),
                    (self.stop_btn,"255, 93, 174"),
                    (self.autostart_enable_btn,"54, 153, 70"),
                    (self.autostart_disable_btn,"255, 93, 174")):
            b.setStyleSheet(BUTTON_STYLE.format(c))

        grid.addWidget(self.start_btn,              0,0)
        grid.addWidget(self.autostart_enable_btn,   0,1)
        grid.addWidget(self.stop_btn,               0,0)
        grid.addWidget(self.autostart_disable_btn,  0,1)

        # ---- служебные/прочие кнопки ---------------------------------
        # кортеж:  text, color, row, col, col_span
        extra = [
            ("Открыть папку Zapret",           "0, 119, 255", 2,0),
            ("Тест соединения",                "0, 119, 255", 2,1),
            ("Обновить список сайтов",         "0, 119, 255", 3,0),
            ("Добавить свои сайты",            "0, 119, 255", 3,1),
            ("Обновить winws.exe",             "0, 119, 255", 4,0),
            ("Настройка DNS-серверов",         "0, 119, 255", 4,1),
            ("Разблокировать ChatGPT, Spotify, Notion и др.",
                                               "218, 165, 32",5,0,2),
            ("Что это такое?",                 "38, 38, 38",  6,0,2),
            ("Логи",                           "38, 38, 38",  7,0),
            ("Отправить лог",                  "38, 38, 38",  7,1),
            ("Проверить обновления",           "38, 38, 38",  8,0,2),
        ]

        for text,color,row,col,*span in extra:
            btn = RippleButton(text, self, color)
            btn.setStyleSheet(BUTTON_STYLE.format(color))
            grid.addWidget(btn, row, col, 1, span[0] if span else 1)
            # сохраняем ссылку на нужные отдельные кнопки
            if "ChatGPT" in text:
                self.proxy_button = btn
            if text == "Запустить Zapret":
                self.start_btn = btn
            # основная логика подпишет сигналы позже:
            setattr(self, f"extra_{row}_{col}_btn", btn)

        root.addLayout(grid)

        # ---------- Тема оформления -----------------------------------
        theme_lbl = QLabel("Тема оформления:"); theme_lbl.setStyleSheet(COMMON_STYLE)
        root.addWidget(theme_lbl, alignment=Qt.AlignCenter)

        self.theme_combo = QComboBox(); self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setStyleSheet(f"{COMMON_STYLE} text-align:center;")
        root.addWidget(self.theme_combo)

        # ---------- Статус-строка -------------------------------------
        self.status_label = QLabel(""); self.status_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_label)

        root.addItem(QSpacerItem(20,20,QSizePolicy.Minimum,QSizePolicy.Expanding))

        # ---------- ссылки --------------------------------------------
        self.bol_van_url   = QLabel(); self.bol_van_url.setAlignment(Qt.AlignCenter)
        self.author_label  = QLabel(); self.author_label.setAlignment(Qt.AlignCenter)
        self.support_label = QLabel(); self.support_label.setAlignment(Qt.AlignCenter)

        for w in (self.bol_van_url, self.author_label, self.support_label):
            w.setOpenExternalLinks(True); root.addWidget(w)

        # ---------- UUID ----------------------------------------------
        self.uuid_label = QLabel(); self.uuid_label.setAlignment(Qt.AlignCenter)
        self.uuid_label.setStyleSheet("color:#666;font-size:8pt;")
        root.addWidget(self.uuid_label)

        # ---------- сигналы-прокси (для main.py) ----------------------
        self.select_strategy_clicked  = self.select_strategy_btn.clicked
        self.start_clicked            = self.start_btn.clicked
        self.stop_clicked             = self.stop_btn.clicked
        self.autostart_enable_clicked = self.autostart_enable_btn.clicked
        self.autostart_disable_clicked= self.autostart_disable_btn.clicked
        self.theme_changed            = self.theme_combo.currentTextChanged