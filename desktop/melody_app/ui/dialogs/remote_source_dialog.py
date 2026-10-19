"""添加 WebDAV 远程库对话框：地址/账号/密码 + 连接测试 + DPAPI 保存密码。"""

from __future__ import annotations

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...core.sources.webdav_client import WebDavClient, WebDavConfig
from ..app_context import AppContext


class ConnectionTestWorker(QThread):
    finished_test = pyqtSignal(bool, str)

    def __init__(self, config: WebDavConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config

    def run(self) -> None:
        try:
            ok, message = WebDavClient(self._config).test_connection()
        except Exception as error:  # noqa: BLE001 - 转为可读提示
            ok, message = False, f"连接失败：{error}"
        self.finished_test.emit(ok, message)


class RemoteSourceDialog(QDialog):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._tester: ConnectionTestWorker | None = None

        self.setWindowTitle("添加 WebDAV 远程库")
        self.setModal(True)
        self.resize(580, 430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：家里的 NAS")
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://nas.example.com/dav/music")
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("可留空（匿名访问）")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("保存时用 Windows DPAPI 加密，不写入数据库")
        self.verify_checkbox = QCheckBox("校验 HTTPS 证书（自签证书时可关闭）")
        self.verify_checkbox.setChecked(True)
        form.addRow("名称", self.name_edit)
        form.addRow("地址", self.url_edit)
        form.addRow("用户名", self.user_edit)
        form.addRow("密码", self.password_edit)
        form.addRow("", self.verify_checkbox)
        layout.addLayout(form)

        hint = QLabel(
            "当前版本已支持连接测试与目录列举，扫描、封面与播放将在后续版本接入。"
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self._test_connection)
        buttons.addWidget(self.test_button)
        buttons.addStretch(1)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel, self
        )
        save_button = self.button_box.button(QDialogButtonBox.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        if save_button is not None:
            save_button.setText("保存")
        if cancel_button is not None:
            cancel_button.setText("取消")
        self.button_box.accepted.connect(self._save)
        self.button_box.rejected.connect(self.reject)
        buttons.addWidget(self.button_box)
        layout.addLayout(buttons)

        self.name_edit.setFocus()

    # ------------------------------------------------------------------ 辅助
    def _config(self) -> WebDavConfig:
        url = self.url_edit.text().strip()
        if not url:
            raise ValueError("请填写 WebDAV 地址")
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError("地址需要以 http:// 或 https:// 开头")
        return WebDavConfig(
            base_url=url,
            username=self.user_edit.text().strip(),
            password=self.password_edit.text(),
            verify_tls=self.verify_checkbox.isChecked(),
        )

    def _set_status(self, ok: bool, message: str) -> None:
        self.status_label.setText(("✓ " if ok else "✗ ") + message)
        self.status_label.setStyleSheet(
            f"color: {'#22c55e' if ok else '#ef4444'};"
        )

    # ------------------------------------------------------------------ 动作
    def _test_connection(self) -> None:
        try:
            config = self._config()
        except ValueError as error:
            self._set_status(False, str(error))
            return
        self.test_button.setEnabled(False)
        self.test_button.setText("测试中…")
        self.status_label.setText("正在连接…")
        self.status_label.setStyleSheet("color: #9aa1b1;")
        self._tester = ConnectionTestWorker(config, self)
        self._tester.finished_test.connect(self._on_test_finished)
        self._tester.start()

    def _on_test_finished(self, ok: bool, message: str) -> None:
        self.test_button.setEnabled(True)
        self.test_button.setText("测试连接")
        self._set_status(ok, message)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "添加远程库", "请填写名称。")
            return
        try:
            config = self._config()
        except ValueError as error:
            QMessageBox.warning(self, "添加远程库", str(error))
            return

        target = config.base_url.rstrip("/")
        for row in self._ctx.library.sources():
            if row.kind == "webdav" and (row.path or "").rstrip("/") == target:
                QMessageBox.warning(self, "添加远程库", "这个地址已经添加过了。")
                return

        try:
            source = self._ctx.library.add_remote_source(
                name,
                target,
                protocol="webdav",
                config={
                    "username": config.username,
                    "verify_tls": config.verify_tls,
                },
            )
        except Exception as error:  # noqa: BLE001 - 数据库错误直接提示
            QMessageBox.warning(self, "添加远程库", f"保存失败：{error}")
            return

        if config.password:
            try:
                if self._ctx.credentials is not None:
                    self._ctx.credentials.save(source.id, config.password)
            except Exception as error:  # noqa: BLE001 - DPAPI 失败不阻塞登记
                QMessageBox.warning(
                    self,
                    "密码保存失败",
                    f"远程库已登记，但密码未能加密保存：{error}\n"
                    "可以稍后在设置中重新添加或删除后重试。",
                )

        self._ctx.toast(f"已添加 WebDAV 远程库「{name}」（扫描/播放待实现）")
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._tester is not None and self._tester.isRunning():
            self._tester.wait(2000)
        super().closeEvent(event)
