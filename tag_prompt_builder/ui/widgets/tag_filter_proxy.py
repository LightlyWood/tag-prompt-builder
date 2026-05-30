# ui/widgets/tag_filter_proxy.py
from PyQt6.QtCore import QSortFilterProxyModel, QModelIndex, Qt
from tag_prompt_builder.models.tag_item import TagItem

class TagFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setRecursiveFilteringEnabled(True)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source_model = self.sourceModel()
        if not source_model:
            return False
        index = source_model.index(source_row, 0, source_parent)
        item = source_model.item_from_index(index)
        if not item:
            return False

        # 获取当前过滤模式（文本）
        pattern = self.filterRegularExpression()
        if pattern is None or not pattern.pattern():
            return True  # 无过滤时全部显示（包括空文件夹）

        if not item.is_folder:
            return self._matches(item)
        else:
            return self._has_matching_descendant(item)

    def _matches(self, item: TagItem) -> bool:
        pattern = self.filterRegularExpression()
        if pattern is None:
            return True
        text = pattern.pattern().lower()
        return (text in item.display_name.lower() or 
                text in item.name.lower())

    def _has_matching_descendant(self, folder: TagItem) -> bool:
        for child in folder.children:
            if child.is_folder:
                if self._has_matching_descendant(child):
                    return True
            elif self._matches(child):
                return True
        return False