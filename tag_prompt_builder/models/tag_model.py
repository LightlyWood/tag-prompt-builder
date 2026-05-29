# models/tag_model.py
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, QMimeData
from PyQt6.QtGui import QColor
from models.tag_item import TagItem

class TagTreeModel(QAbstractItemModel):
    def __init__(self, root: TagItem, parent=None):
        super().__init__(parent)
        self._root = root

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_item = self.item_from_index(parent)
        if row < len(parent_item.children):
            return self.createIndex(row, column, parent_item.children[row])
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        item = self.item_from_index(index)
        if item.parent and item.parent is not self._root:
            grand_parent = item.parent
            if grand_parent.parent:
                row = grand_parent.parent.children.index(grand_parent)
                return self.createIndex(row, 0, grand_parent)
        return QModelIndex()

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        return len(self.item_from_index(parent).children)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self.item_from_index(index)
        if role == Qt.ItemDataRole.DisplayRole:
            return item.display_name          # 显示中文名
        elif role == Qt.ItemDataRole.CheckStateRole:
            if not item.is_folder:
                return Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.ForegroundRole:
            if item.is_folder and item.single_selection:
                return QColor('blue')
        elif role == Qt.ItemDataRole.UserRole:
            return item                       # 传递原始对象
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        item = self.item_from_index(index)
        if role == Qt.ItemDataRole.CheckStateRole and not item.is_folder:
            item.checked = (value == Qt.CheckState.Checked.value)
            if item.parent and item.parent.single_selection and item.checked:
                for sibling in item.parent.children:
                    if sibling is not item and sibling.checked:
                        sibling.checked = False
                        sib_idx = self.index_from_item(sibling)
                        self.dataChanged.emit(sib_idx, sib_idx, [Qt.ItemDataRole.CheckStateRole])
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
        elif role == Qt.ItemDataRole.EditRole:
            item.display_name = value   # 允许编辑显示名
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item = self.item_from_index(index)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        if not item.is_folder:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def item_from_index(self, index):
        return index.internalPointer() if index.isValid() else self._root

    def index_from_item(self, item):
        if item is self._root:
            return QModelIndex()
        parent = item.parent
        if parent:
            row = parent.children.index(item)
            return self.createIndex(row, 0, item)
        return QModelIndex()

    def append_tag(self, parent_index, name, is_folder=False, display_name=None):
        parent_item = self.item_from_index(parent_index)
        if not parent_item.is_folder:
            return QModelIndex()
        new_item = TagItem(name, is_folder, display_name=display_name)
        row = len(parent_item.children)
        self.beginInsertRows(parent_index, row, row)
        parent_item.add_child(new_item)
        self.endInsertRows()
        return self.index(row, 0, parent_index)

    def remove_item(self, index):
        item = self.item_from_index(index)
        if item is self._root:
            return
        parent = item.parent
        if parent:
            row = parent.children.index(item)
            self.beginRemoveRows(self.index_from_item(parent), row, row)
            parent.remove_child(item)
            self.endRemoveRows()

    def move_item(self, src_index, dest_parent_index, dest_row):
        """拖拽移动（需配合 View 实现）"""
        # 简单实现，实际需要更多检查
        item = self.item_from_index(src_index)
        src_parent = item.parent
        dest_parent = self.item_from_index(dest_parent_index)
        if not src_parent or not dest_parent.is_folder:
            return
        # 不允许移至子代
        temp = dest_parent
        while temp:
            if temp is item:
                return
            temp = temp.parent
        old_row = src_parent.children.index(item)
        self.beginMoveRows(self.index_from_item(src_parent), old_row, old_row,
                           self.index_from_item(dest_parent), dest_row)
        src_parent.children.remove(item)
        dest_parent.children.insert(dest_row, item)
        item.parent = dest_parent
        self.endMoveRows()

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction