# ui/dialogs/pool_tag_edit_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QInputDialog, QMessageBox)
from tag_prompt_builder.managers.random_pool_manager import RandomPoolManager

class PoolTagEditDialog(QDialog):
    def __init__(self, pool_name, pool_manager: RandomPoolManager, tag_manager, parent=None):
        super().__init__(parent)
        self.pool_name = pool_name
        self.pool_manager = pool_manager
        self.tag_manager = tag_manager
        self.setWindowTitle(f"编辑池 '{pool_name}' 的标签")
        self.resize(400, 300)

        self.list_widget = QListWidget()
        self.refresh_list()

        btn_add = QPushButton("添加标签")
        btn_add.clicked.connect(self.add_tag)
        btn_remove = QPushButton("移除选中")
        btn_remove.clicked.connect(self.remove_tag)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(btn_layout)

    def refresh_list(self):
        self.list_widget.clear()
        tags = self.pool_manager.get_pool_tags(self.pool_name, self.tag_manager)
        for tag in tags:
            self.list_widget.addItem(f"{tag.display_name} ({tag.name})")

    def add_tag(self):
        fid, ok = QInputDialog.getText(self, "添加标签", "输入标签的完整路径ID（例如 #root/...）：")
        if ok and fid:
            tag = self.tag_manager.find_item_by_full_id(fid)
            if tag and not tag.is_folder:
                self.pool_manager.add_tag_to_pool(self.pool_name, fid)
                self.refresh_list()
            else:
                QMessageBox.warning(self, "错误", "标签不存在或不是叶子标签。")

    def remove_tag(self):
        tags = self.pool_manager.get_pool_tags(self.pool_name, self.tag_manager)
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(tags):
            tag = tags[idx]
            self.pool_manager.remove_tag_from_pool(self.pool_name, tag.full_id())
            self.refresh_list()