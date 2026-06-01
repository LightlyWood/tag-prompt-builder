# tag_prompt_builder/ui/dialogs/random_pool_manager_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QInputDialog, QMessageBox)
from tag_prompt_builder.managers.random_pool_manager import RandomPoolManager

class RandomPoolManagerDialog(QDialog):
    def __init__(self, pool_manager: RandomPoolManager, tag_manager, parent=None):
        super().__init__(parent)
        self.pool_manager = pool_manager
        self.tag_manager = tag_manager
        self.setWindowTitle("管理随机池")
        self.resize(400, 300)

        self.list_widget = QListWidget()
        self.refresh_list()

        btn_create = QPushButton("创建池")
        btn_create.clicked.connect(self.create_pool)
        btn_delete = QPushButton("删除池")
        btn_delete.clicked.connect(self.delete_pool)
        btn_edit = QPushButton("编辑标签")
        btn_edit.clicked.connect(self.edit_pool_tags)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_create)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_edit)
        btn_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(btn_layout)

    def refresh_list(self):
        self.list_widget.clear()
        for name in self.pool_manager.list_pool_names():
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)

    def create_pool(self):
        name, ok = QInputDialog.getText(self, "创建随机池", "池名称：")
        if ok and name.strip():
            self.pool_manager.create_pool(name.strip())
            self.refresh_list()

    def delete_pool(self):
        cur = self.list_widget.currentItem()
        if cur:
            name = cur.text()
            confirm = QMessageBox.question(self, "确认", f"删除池 '{name}'？")
            if confirm == QMessageBox.StandardButton.Yes:
                self.pool_manager.delete_pool(name)
                self.refresh_list()

    def edit_pool_tags(self):
        cur = self.list_widget.currentItem()
        if not cur:
            return
        pool_name = cur.text()
        from tag_prompt_builder.ui.dialogs.pool_tag_edit_dialog import PoolTagEditDialog
        dialog = PoolTagEditDialog(pool_name, self.pool_manager, self.tag_manager, self)
        dialog.exec()
        self.refresh_list()