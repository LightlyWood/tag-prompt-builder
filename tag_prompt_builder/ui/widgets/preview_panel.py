# tag_prompt_builder/ui/widgets/preview_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from tag_prompt_builder.ui.helpers.bracket_checker import check_brackets
import pyperclip

class PreviewPanel(QWidget):
    clipboard_copied = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        btn_copy = QPushButton("复制到剪贴板(英文)")
        btn_copy.clicked.connect(self.copy_to_clipboard)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("实时预览(中文)"))
        layout.addWidget(self.text_edit)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_copy)
        btn_layout.addWidget(self.status_label)
        layout.addLayout(btn_layout)

        self.output_text = ""

    def update_preview(self, display_text: str, output_text: str):
        self.text_edit.setPlainText(display_text)
        self.output_text = output_text
        valid, msg = check_brackets(output_text)
        if valid:
            self.status_label.setText("✓ 括号格式正确")
            self.status_label.setStyleSheet("color: green")
        else:
            self.status_label.setText(f"⚠️ {msg}")
            self.status_label.setStyleSheet("color: red")

    def copy_to_clipboard(self):
        if not self.output_text.strip():
            return
        valid, msg = check_brackets(self.output_text)
        if not valid:
            reply = QMessageBox.warning(self, "括号错误", msg + "\n仍要复制吗？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        pyperclip.copy(self.output_text)
        self.clipboard_copied.emit(self.output_text)