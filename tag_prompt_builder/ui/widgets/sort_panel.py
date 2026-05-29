# ui/widgets/sort_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from models.tag_item import TagItem

class SortPanel(QWidget):
    order_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree.model().rowsMoved.connect(lambda: self.order_changed.emit())

        btn_random = QPushButton("随机抽取(待实现)")
        btn_random.clicked.connect(self.randomize)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        layout.addWidget(btn_random)

    def build_from_checked(self, root_item: TagItem):
        self.tree.clear()
        self._populate(root_item, None)

    def _populate(self, tag_item: TagItem, parent_item: QTreeWidgetItem):
        for child in tag_item.children:
            if child.is_folder:
                if self._has_checked_descendant(child):
                    folder_widget = QTreeWidgetItem(parent_item or self.tree)
                    folder_widget.setText(0, child.name)   # 文件夹显示原名
                    folder_widget.setData(0, Qt.ItemDataRole.UserRole, child)
                    if child.locked:
                        folder_widget.setForeground(0, Qt.GlobalColor.red)
                    self._populate(child, folder_widget)
            else:
                if child.checked:
                    tag_widget = QTreeWidgetItem(parent_item or self.tree)
                    tag_widget.setText(0, child.display_name)   # 显示中文
                    tag_widget.setData(0, Qt.ItemDataRole.UserRole, child)  # 存对象
                    tag_widget.setFlags(tag_widget.flags() | Qt.ItemFlag.ItemIsDragEnabled)

    def _has_checked_descendant(self, folder: TagItem) -> bool:
        for child in folder.children:
            if child.is_folder:
                if self._has_checked_descendant(child):
                    return True
            elif child.checked:
                return True
        return False

    def randomize(self):
        # TODO: 在选中范围内随机替换
        pass