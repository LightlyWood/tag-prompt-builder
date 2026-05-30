# ui/dialogs/preset_manager_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt

class PresetManagerDialog(QDialog):
    def __init__(self, tag_manager, main_window, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.main_window = main_window
        self.setWindowTitle("管理词组预设")
        self.resize(400, 300)

        self.list_widget = QListWidget()
        self.refresh_list()

        btn_load = QPushButton("加载到全部")
        btn_load.clicked.connect(self.load_preset)
        btn_delete = QPushButton("删除")
        btn_delete.clicked.connect(self.delete_preset)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(btn_layout)

    def refresh_list(self):
        self.list_widget.clear()
        presets = self.tag_manager.list_tag_presets()
        for name in presets:
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)

    def load_preset(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "未选择", "请先选择一个预设。")
            return
        preset_name = current_item.text()
        confirm = QMessageBox.question(self, "确认加载",
                                       f"加载预设“{preset_name}”将清空当前所有选中并勾选预设中的标签。\n确定要加载吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.main_window.apply_tag_preset(preset_name)
        self.accept()

    def delete_preset(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            return
        preset_name = current_item.text()
        confirm = QMessageBox.question(self, "确认删除", f"确定要删除预设“{preset_name}”吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.tag_manager.delete_preset(preset_name)
            self.refresh_list()