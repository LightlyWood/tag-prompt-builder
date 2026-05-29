from PyQt6.QtWidgets import QTreeView, QMenu, QInputDialog, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from models.tag_model import TagTreeModel
from models.tag_item import TagItem

class TagTreeView(QTreeView):
    tag_checked_changed = pyqtSignal()

    def __init__(self, model: TagTreeModel, tag_manager=None, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager   # 用于保存库
        self.setModel(model)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.clicked.connect(self.on_clicked)

    def on_clicked(self, index):
        pass

    def show_context_menu(self, pos):
        index = self.indexAt(pos)
        menu = QMenu(self)
        if not index.isValid():
            add_folder = QAction("新建一级文件夹", self)
            add_folder.triggered.connect(lambda: self.add_root_folder())
            menu.addAction(add_folder)
            menu.exec(self.viewport().mapToGlobal(pos))
            return

        item = self.model.item_from_index(index)
        if item.is_folder:
            add_folder = QAction("新建子文件夹", self)
            add_folder.triggered.connect(lambda: self.add_folder(index))
            menu.addAction(add_folder)
            add_tag = QAction("新建标签", self)
            add_tag.triggered.connect(lambda: self.add_tag(index))
            menu.addAction(add_tag)
            rename = QAction("重命名", self)
            rename.triggered.connect(lambda: self.rename_item(index))
            menu.addAction(rename)
            delete = QAction("删除", self)
            delete.triggered.connect(lambda: self.delete_item(index))
            menu.addAction(delete)
            menu.addSeparator()
            toggle_single = QAction("切换互斥模式" if not item.single_selection else "取消互斥", self)
            toggle_single.triggered.connect(lambda: self.toggle_single(index))
            menu.addAction(toggle_single)
            toggle_lock = QAction("锁定" if not item.locked else "解锁", self)
            toggle_lock.triggered.connect(lambda: self.toggle_lock(index))
            menu.addAction(toggle_lock)
            copy_role = QAction("复制角色文件夹", self)
            copy_role.triggered.connect(lambda: self.copy_role(index))
            menu.addAction(copy_role)
        else:
            # ---------- 标签右键菜单 ----------
            rename = QAction("编辑名称", self)
            rename.triggered.connect(lambda: self.rename_item(index))
            menu.addAction(rename)
            delete = QAction("删除", self)
            delete.triggered.connect(lambda: self.delete_item(index))
            menu.addAction(delete)
            star = QAction("收藏", self)
            star.triggered.connect(lambda: self.toggle_star(index))
            menu.addAction(star)
            menu.addSeparator()

            # 参考网址子菜单
            if item.urls:
                url_menu = QMenu("打开参考网址", self)
                for url in item.urls:
                    action = QAction(url, self)
                    action.triggered.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))
                    url_menu.addAction(action)
                menu.addMenu(url_menu)
            else:
                no_url_action = QAction("打开参考网址（无）", self)
                no_url_action.setEnabled(False)
                menu.addAction(no_url_action)

            edit_urls_action = QAction("编辑参考网址", self)
            edit_urls_action.triggered.connect(lambda: self.edit_urls(index))
            menu.addAction(edit_urls_action)

        menu.exec(self.viewport().mapToGlobal(pos))

    def edit_urls(self, index):
        item = self.model.item_from_index(index)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑参考网址 - {item.display_name}")
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setPlainText('\n'.join(item.urls))
        layout.addWidget(text_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_urls = [line.strip() for line in text_edit.toPlainText().split('\n') if line.strip()]
            item.urls = new_urls
            if self.tag_manager:
                self.tag_manager.save_library()

    # 以下方法保持不变（仅列出，未修改）
    def add_root_folder(self):
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称:")
        if ok and name:
            self.model.append_tag(QModelIndex(), name, is_folder=True)

    def add_folder(self, parent_index):
        name, ok = QInputDialog.getText(self, "新建子文件夹", "名称:")
        if ok and name:
            self.model.append_tag(parent_index, name, is_folder=True)

    def add_tag(self, parent_index):
        text, ok = QInputDialog.getText(self, "新建标签", "输入 “英文” 或 “中文|英文”：")
        if ok and text:
            if '|' in text:
                parts = text.split('|', 1)
                display, value = parts[0].strip(), parts[1].strip()
            else:
                display = value = text.strip()
            self.model.append_tag(parent_index, value, is_folder=False, display_name=display)
            self.tag_checked_changed.emit()

    def rename_item(self, index):
        item = self.model.item_from_index(index)
        current = item.display_name if not item.is_folder else item.name
        text, ok = QInputDialog.getText(self, "重命名", "新名称:", text=current)
        if ok and text:
            if item.is_folder:
                self.model.setData(index, text, Qt.ItemDataRole.EditRole)
            else:
                if '|' in text:
                    parts = text.split('|', 1)
                    item.display_name = parts[0].strip()
                    item.name = parts[1].strip()
                else:
                    item.display_name = text
                    item.name = text
                self.model.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

    def delete_item(self, index):
        item = self.model.item_from_index(index)
        confirm = QMessageBox.question(self, "确认删除", f"删除 {item.name}？")
        if confirm == QMessageBox.StandardButton.Yes:
            self.model.remove_item(index)
            self.tag_checked_changed.emit()

    def toggle_single(self, index):
        item = self.model.item_from_index(index)
        item.single_selection = not item.single_selection
        self.model.dataChanged.emit(index, index)

    def toggle_lock(self, index):
        item = self.model.item_from_index(index)
        item.locked = not item.locked
        self.model.dataChanged.emit(index, index)

    def copy_role(self, index):
        item = self.model.item_from_index(index)
        if not item.is_folder:
            return
        new_name = f"{item.name}_copy"
        new_idx = self.model.append_tag(self.model.parent(index), new_name, is_folder=True)
        self._clone_tree(item, self.model.item_from_index(new_idx))
        self.expand(new_idx)
        self.tag_checked_changed.emit()

    def _clone_tree(self, src, dest):
        for child in src.children:
            if child.is_folder:
                new_child = TagItem(child.name, is_folder=True, display_name=child.display_name)
                dest.add_child(new_child)
                self._clone_tree(child, new_child)
            else:
                dest.add_child(TagItem(child.name, is_folder=False, display_name=child.display_name, urls=child.urls.copy()))

    def toggle_star(self, index):
        pass