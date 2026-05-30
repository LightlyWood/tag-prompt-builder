# ui/widgets/favorites_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from tag_prompt_builder.models.tag_item import TagItem

class FavoritesPanel(QWidget):
    tag_checked_changed = pyqtSignal()

    def __init__(self, tag_manager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self.on_item_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)

    def refresh(self):
        self.list_widget.clear()
        favorites = []
        def collect_favorites(item):
            if not item.is_folder:
                if item.starred:
                    favorites.append(item)
            else:
                for child in item.children:
                    collect_favorites(child)
        collect_favorites(self.tag_manager.root)

        for item in favorites:
            widget_item = QListWidgetItem(item.display_name)
            widget_item.setCheckState(Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked)
            widget_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(widget_item)

    def on_item_changed(self, item):
        tag_item = item.data(Qt.ItemDataRole.UserRole)
        if tag_item:
            tag_item.checked = (item.checkState() == Qt.CheckState.Checked)
            self.tag_checked_changed.emit()