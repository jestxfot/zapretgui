from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QMessageBox
)
from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QGuiApplication, QIcon

from config.config          import APP_VERSION
from config.urls            import INFO_URL, AUTHOR_URL
from tgram.tg_log_delta import get_client_id


from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QMessageBox
)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setFixedSize(440, 260)

        cid = get_client_id()

        # ---------------- корневой layout ----------------------------------
        vbox = QVBoxLayout(self)

        # 1. Заголовок + версия
        title = QLabel(f"<h3>Zapret&nbsp;GUI</h3>"
                       f"Версия: <b>{APP_VERSION}</b>")
        vbox.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        # 2. Строка с CID
        h_cid = QHBoxLayout()
        lbl_cid = QLabel(f"ID устройства: <code>{cid}</code>")
        h_cid.addWidget(lbl_cid)
        vbox.addLayout(h_cid)

        # 3. Ссылки
        links_html = f"""
        <br>
        <a href="{INFO_URL}">Руководство пользователя</a><br>
        Автор GUI: <a href="https://t.me/bypassblock">@bypassblock</a><br>
        Автор Zapret: <a href="{AUTHOR_URL}">bol-van&nbsp;(GitHub)</a><br>
        Поддержка: <a href="https://t.me/youtubenotwork">@youtubenotwork</a>
        """
        lbl_links = QLabel(links_html)
        lbl_links.setTextFormat(Qt.TextFormat.RichText)
        lbl_links.setOpenExternalLinks(True)
        vbox.addWidget(lbl_links)

        # 4. Нижняя панель  [Копировать ID] ……… [Закрыть]
        hbox_bottom = QHBoxLayout()

        btn_copy = QPushButton("Копировать ID", self)
        btn_copy.clicked.connect(lambda: self._copy_cid(cid))
        hbox_bottom.addWidget(btn_copy)

        hbox_bottom.addStretch()

        btn_close = QPushButton("Закрыть", self)
        btn_close.clicked.connect(self.accept)
        hbox_bottom.addWidget(btn_close)

        vbox.addLayout(hbox_bottom)

    # ------------------------------------------------------------------
    def _copy_cid(self, cid: str):
        """Копирует CID в clipboard и показывает уведомление."""
        QGuiApplication.clipboard().setText(cid)
        QMessageBox.information(self, "Скопировано",
                                "ID устройства скопирован в буфер обмена.")