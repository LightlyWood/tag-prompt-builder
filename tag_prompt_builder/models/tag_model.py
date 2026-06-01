# tag_prompt_builder/models/tag_model.py
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from tag_prompt_builder.models.tag_item import TagItem

class TagTreeModel(QAbstractItemModel):
    mutual_exclusion_violation = pyqtSignal(TagItem, TagItem)

    def __init__(self, tag_manager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self._root_id = '#root'

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_id = self._id_from_index(parent)
        children_ids = self.tag_manager._children_ids.get(parent_id, [])
        if row < len(children_ids):
            return self.createIndex(row, column, children_ids[row])
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        child_id = index.internalPointer()
        item = self.tag_manager._items.get(child_id)
        if not item or item.parent_id is None or item.parent_id == self._root_id:
            return QModelIndex()
        parent_id = item.parent_id
        grand_parent_id = self.tag_manager._items[parent_id].parent_id if parent_id in self.tag_manager._items else None
        siblings = self.tag_manager._children_ids.get(grand_parent_id or self._root_id, [])
        try:
            row = siblings.index(parent_id)
            return self.createIndex(row, 0, parent_id)
        except ValueError:
            return QModelIndex()

    def rowCount(self, parent=QModelIndex()):
        parent_id = self._id_from_index(parent)
        return len(self.tag_manager._children_ids.get(parent_id, []))

    def columnCount(self, parent=QModelIndex()):
        return 1

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item = self.item_from_index(index)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        if not item.is_folder:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self.item_from_index(index)
        if role == Qt.ItemDataRole.DisplayRole:
            return item.display_name
        elif role == Qt.ItemDataRole.CheckStateRole:
            if not item.is_folder:
                return Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.ForegroundRole:
            if item.is_folder and item.single_selection:
                return QColor('blue')
        elif role == Qt.ItemDataRole.UserRole:
            return item
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        item = self.item_from_index(index)
        if role == Qt.ItemDataRole.CheckStateRole and not item.is_folder:
            new_checked = (value == Qt.CheckState.Checked.value)
            if new_checked and item.parent_id:
                parent_item = self.tag_manager._items.get(item.parent_id)
                if parent_item and parent_item.single_selection:
                    # 获取当前父节点下的所有子节点，找出已选中的
                    siblings = [self.tag_manager._items[cid] for cid in self.tag_manager._children_ids.get(item.parent_id, [])]
                    current_checked = None
                    for sib in siblings:
                        if sib.checked and sib is not item:
                            current_checked = sib
                            break
                    if current_checked:
                        self.mutual_exclusion_violation.emit(parent_item, item)
                        return False
            item.checked = new_checked
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
        elif role == Qt.ItemDataRole.EditRole:
            item.display_name = value
            self.tag_manager.db.set_display_name(item.id, value)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            return True
        return False

    def item_from_index(self, index):
        if index.isValid():
            return self.tag_manager._items.get(index.internalPointer())
        return None

    def index_from_item(self, item):
        if item is None or item.id == self._root_id:
            return QModelIndex()
        parent_id = item.parent_id
        if parent_id:
            siblings = self.tag_manager._children_ids.get(parent_id, [])
            try:
                row = siblings.index(item.id)
                return self.createIndex(row, 0, item.id)
            except ValueError:
                pass
        return QModelIndex()

    # ---------- 增删改 ----------
    def append_tag(self, parent_index, name, is_folder=False, display_name=None):
        parent_item = self.item_from_index(parent_index) if parent_index.isValid() else None
        parent_id = parent_item.id if parent_item else self._root_id
        new_item = self.tag_manager.add_new_tag(parent_id, name, is_folder, display_name)
        # 通知视图新行插入
        siblings = self.tag_manager._children_ids.get(parent_id, [])
        row = siblings.index(new_item.id) if new_item.id in siblings else len(siblings)
        self.beginInsertRows(parent_index, row, row)
        self.endInsertRows()
        return self.index(row, 0, parent_index)

    def remove_item(self, index):
        item = self.item_from_index(index)
        if item is None or item.id == self._root_id:
            return
        parent_id = item.parent_id
        parent_index = self.index_from_item(self.tag_manager._items.get(parent_id)) if parent_id else QModelIndex()
        siblings = self.tag_manager._children_ids.get(parent_id, [])
        if item.id in siblings:
            row = siblings.index(item.id)
        else:
            row = 0
        self.beginRemoveRows(parent_index, row, row)
        self.tag_manager.delete_tag(item.id)
        self.endRemoveRows()

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    # ---------- 辅助方法 ----------
    def _id_from_index(self, index):
        return index.internalPointer() if index.isValid() else self._root_id

    def refresh_node(self, index):
        self.dataChanged.emit(index, index)

    def all_items(self):
        """返回所有叶子标签（非文件夹）的生成器"""
        for item in self.tag_manager._items.values():
            if not item.is_folder:
                yield item