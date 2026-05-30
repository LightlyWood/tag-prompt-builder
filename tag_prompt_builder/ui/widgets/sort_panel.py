# ui/widgets/sort_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from tag_prompt_builder.models.tag_item import TagItem

class SortPanel(QWidget):
    order_changed = pyqtSignal()
    random_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree.model().rowsMoved.connect(lambda: self.order_changed.emit())

        btn_random = QPushButton("随机抽取")
        btn_random.clicked.connect(lambda: self.random_requested.emit())

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        layout.addWidget(btn_random)

        self.item_map = {}

    def sync_from_checked(self, root_item: TagItem):
        """
        增量同步左侧勾选状态：
        - 新增勾选的标签 -> 按标签库默认层级添加到排序树（新节点追加到对应父文件夹末尾）
        - 取消勾选的标签 -> 从排序树中移除
        - 已存在的节点保持原位不动
        """
        # 1. 收集当前左侧所有勾选的标签（递归）
        checked_tags = set()
        def collect_checked(item):
            if not item.is_folder:
                if item.checked:
                    checked_tags.add(item)
            else:
                for child in item.children:
                    collect_checked(child)
        collect_checked(root_item)

        # 2. 移除排序树中已取消勾选的标签节点
        to_remove = []
        for tag, widget_item in self.item_map.items():
            if tag not in checked_tags:
                to_remove.append(tag)
        for tag in to_remove:
            widget_item = self.item_map.pop(tag)
            parent = widget_item.parent() or self.tree.invisibleRootItem()
            if parent is self.tree.invisibleRootItem():
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(widget_item))
            else:
                parent.takeChild(parent.indexOfChild(widget_item))
            # 如果父文件夹变为空，可选择保留空文件夹或移除。这里保留文件夹结构。

        # 3. 添加新勾选的标签
        for tag in checked_tags:
            if tag not in self.item_map:
                # 创建标签节点
                tag_item = QTreeWidgetItem()
                tag_item.setText(0, tag.display_name)
                tag_item.setData(0, Qt.ItemDataRole.UserRole, tag)
                tag_item.setFlags(tag_item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                # 查找或创建父文件夹节点（按标签库路径）
                parent_widget = self._ensure_folder_path(tag.parent, root_item)
                if parent_widget is None:
                    # 根级标签（极少出现，但处理）
                    self.tree.addTopLevelItem(tag_item)
                else:
                    parent_widget.addChild(tag_item)
                self.item_map[tag] = tag_item

        # 4. 移除空的文件夹节点（可选，清理无子项的文件夹）
        self._clean_empty_folders()

    def _ensure_folder_path(self, folder: TagItem, root_item: TagItem):
        """
        确保从根到指定文件夹的路径在排序树中存在，返回最末级文件夹的 QTreeWidgetItem。
        如果路径上的文件夹尚不存在，则创建（顺序按现有标签库顺序追加）。
        """
        if folder is None or folder is root_item:
            return None  # 根节点不需要创建
        # 递归先保证父路径存在
        parent_widget = self._ensure_folder_path(folder.parent, root_item)

        # 在当前层查找是否已有该文件夹节点
        existing = None
        if parent_widget is None:
            # 查找顶层节点
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data is folder:
                    existing = item
                    break
        else:
            for i in range(parent_widget.childCount()):
                item = parent_widget.child(i)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data is folder:
                    existing = item
                    break

        if existing:
            return existing

        # 不存在则创建新文件夹节点
        folder_item = QTreeWidgetItem()
        folder_item.setText(0, folder.name)
        folder_item.setData(0, Qt.ItemDataRole.UserRole, folder)
        if parent_widget is None:
            self.tree.addTopLevelItem(folder_item)
        else:
            parent_widget.addChild(folder_item)
        return folder_item

    def _clean_empty_folders(self):
        """移除排序树中没有任何子标签的空文件夹节点（递归向上）"""
        def clean(parent_widget):
            if parent_widget is None:
                # 顶层处理
                i = 0
                while i < self.tree.topLevelItemCount():
                    child = self.tree.topLevelItem(i)
                    data = child.data(0, Qt.ItemDataRole.UserRole)
                    if data and data.is_folder:
                        clean(child)
                        # 清理后如果文件夹仍无子项，删除
                        if child.childCount() == 0:
                            self.tree.takeTopLevelItem(i)
                            continue
                    i += 1
            else:
                i = 0
                while i < parent_widget.childCount():
                    child = parent_widget.child(i)
                    data = child.data(0, Qt.ItemDataRole.UserRole)
                    if data and data.is_folder:
                        clean(child)
                        if child.childCount() == 0:
                            parent_widget.takeChild(i)
                            continue
                    i += 1
        clean(None)

    def get_sort_structure(self):
        """
        导出当前排序树的完整结构（用于保存预设）。
        返回一个递归的 list/dict，包含文件夹和标签的 full_id。
        格式：[节点, ...]  节点为字符串（标签ID）或 {文件夹ID: [子节点, ...]}
        """
        def export_item(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data is None:
                return None
            if not data.is_folder:
                return data.full_id()
            # 文件夹
            children = []
            for i in range(item.childCount()):
                child = export_item(item.child(i))
                if child is not None:
                    children.append(child)
            return {data.full_id(): children}

        result = []
        for i in range(self.tree.topLevelItemCount()):
            node = export_item(self.tree.topLevelItem(i))
            if node is not None:
                result.append(node)
        return result

    def restore_sort_structure(self, structure, tag_manager):
        """
        根据导入的结构重建排序树（会清空当前树）。
        structure 为 get_sort_structure 的输出格式。
        tag_manager 用于根据 full_id 查找对应的 TagItem。
        """
        self.tree.clear()
        self.item_map.clear()

        def build_item(node, parent_widget):
            if isinstance(node, str):
                # 标签节点
                tag = tag_manager.find_item_by_full_id(node)
                if tag and not tag.is_folder:
                    tag_item = QTreeWidgetItem()
                    tag_item.setText(0, tag.display_name)
                    tag_item.setData(0, Qt.ItemDataRole.UserRole, tag)
                    tag_item.setFlags(tag_item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                    if parent_widget is None:
                        self.tree.addTopLevelItem(tag_item)
                    else:
                        parent_widget.addChild(tag_item)
                    self.item_map[tag] = tag_item
            elif isinstance(node, dict):
                for folder_id, children in node.items():
                    folder = tag_manager.find_item_by_full_id(folder_id)
                    if folder and folder.is_folder:
                        folder_item = QTreeWidgetItem()
                        folder_item.setText(0, folder.name)
                        folder_item.setData(0, Qt.ItemDataRole.UserRole, folder)
                        if parent_widget is None:
                            self.tree.addTopLevelItem(folder_item)
                        else:
                            parent_widget.addChild(folder_item)
                        for child in children:
                            build_item(child, folder_item)

        for item in structure:
            build_item(item, None)