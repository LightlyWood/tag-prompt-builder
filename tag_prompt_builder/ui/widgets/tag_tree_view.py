# tag_prompt_builder/ui/widgets/tag_tree_view.py
from PyQt6.QtWidgets import (QTreeView, QMenu, QInputDialog, QMessageBox, QDialog,
                             QVBoxLayout, QTextEdit, QDialogButtonBox, QLineEdit,
                             QWidget, QHBoxLayout, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QModelIndex
from PyQt6.QtGui import QAction, QDesktopServices
from tag_prompt_builder.models.tag_model import TagTreeModel
from tag_prompt_builder.models.tag_item import TagItem
from tag_prompt_builder.ui.widgets.tag_filter_proxy import TagFilterProxyModel

class TagTreeView(QWidget):
    tag_checked_changed = pyqtSignal()
    favorites_changed = pyqtSignal()
    tag_detail_requested = pyqtSignal(TagItem)

    def __init__(self, model: TagTreeModel, tag_manager=None, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.source_model = model

        self.source_model.mutual_exclusion_violation.connect(self.on_mutual_exclusion_violation)
        self.source_model.dataChanged.connect(self.on_model_data_changed)

        self.proxy_model = TagFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索标签（中文或英文）...")
        self.search_input.textChanged.connect(self.on_search_text_changed)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(True)
        self.tree_view.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)

        self.tree_view.viewport().installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_input)
        layout.addWidget(self.tree_view)

    def on_model_data_changed(self, topLeft, bottomRight, roles):
        if Qt.ItemDataRole.CheckStateRole in roles:
            self.tag_checked_changed.emit()

    def on_mutual_exclusion_violation(self, folder: TagItem, new_tag: TagItem):
        current_checked = None
        for sibling in folder.children:
            if sibling.checked and sibling is not new_tag:
                current_checked = sibling
                break
        if current_checked is None:
            new_tag.checked = True
            idx = self.source_model.index_from_item(new_tag)
            self.source_model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.CheckStateRole])
            self.tag_checked_changed.emit()
            return

        msg = f"标签组「{folder.name}」已选中「{current_checked.display_name}」，互斥模式下通常只需一个。\n请选择操作："
        dialog = QMessageBox(self)
        dialog.setWindowTitle("互斥警告")
        dialog.setText(msg)
        replace_btn = dialog.addButton("替换为新标签", QMessageBox.ButtonRole.AcceptRole)
        keep_both_btn = dialog.addButton("保留两者", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked == replace_btn:
            current_checked.checked = False
            new_tag.checked = True
            idx_old = self.source_model.index_from_item(current_checked)
            idx_new = self.source_model.index_from_item(new_tag)
            self.source_model.dataChanged.emit(idx_old, idx_old, [Qt.ItemDataRole.CheckStateRole])
            self.source_model.dataChanged.emit(idx_new, idx_new, [Qt.ItemDataRole.CheckStateRole])
            self.tag_checked_changed.emit()
        elif clicked == keep_both_btn:
            new_tag.checked = True
            idx_new = self.source_model.index_from_item(new_tag)
            self.source_model.dataChanged.emit(idx_new, idx_new, [Qt.ItemDataRole.CheckStateRole])
            self.tag_checked_changed.emit()

    def eventFilter(self, obj, event):
        if obj is self.tree_view.viewport() and event.type() == event.Type.MouseButtonRelease:
            pos = event.pos()
            index = self.tree_view.indexAt(pos)
            if index.isValid():
                rect = self.tree_view.visualRect(index)
                check_rect_width = 20
                if pos.x() - rect.x() > check_rect_width:
                    source_index = self.proxy_model.mapToSource(index)
                    item = self.source_model.item_from_index(source_index)
                    if not item.is_folder:
                        self.tag_detail_requested.emit(item)
                        return True
        return super().eventFilter(obj, event)

    def on_search_text_changed(self, text):
        self.proxy_model.setFilterFixedString(text)
        self.tree_view.expandAll()

    # ---------- 右键菜单 ----------
    def show_context_menu(self, pos):
        proxy_index = self.tree_view.indexAt(pos)
        if not proxy_index.isValid():
            menu = QMenu(self)
            add_folder = QAction("新建一级标签组", self)
            add_folder.triggered.connect(lambda: self.add_root_folder())
            menu.addAction(add_folder)
            menu.exec(self.tree_view.viewport().mapToGlobal(pos))
            return

        source_index = self.proxy_model.mapToSource(proxy_index)
        item = self.source_model.item_from_index(source_index)

        menu = QMenu(self)
        if item.is_folder:
            add_folder = QAction("新建子标签组", self)
            add_folder.triggered.connect(lambda checked, idx=source_index: self.add_folder(idx))
            menu.addAction(add_folder)
            add_tag = QAction("新建标签", self)
            add_tag.triggered.connect(lambda checked, idx=source_index: self.add_tag(idx))
            menu.addAction(add_tag)
            rename = QAction("重命名", self)
            rename.triggered.connect(lambda checked, idx=source_index: self.rename_item(idx))
            menu.addAction(rename)
            delete = QAction("删除", self)
            delete.triggered.connect(lambda checked, idx=source_index: self.delete_item(idx))
            menu.addAction(delete)
            menu.addSeparator()
            toggle_single = QAction("切换互斥模式" if not item.single_selection else "取消互斥", self)
            toggle_single.triggered.connect(lambda checked, idx=source_index: self.toggle_single(idx))
            menu.addAction(toggle_single)
            toggle_lock = QAction("锁定" if not item.locked else "解锁", self)
            toggle_lock.triggered.connect(lambda checked, idx=source_index: self.toggle_lock(idx))
            menu.addAction(toggle_lock)
            copy_role = QAction("复制角色标签组", self)
            copy_role.triggered.connect(lambda checked, idx=source_index: self.copy_role(idx))
            menu.addAction(copy_role)
            menu.addSeparator()
            save_tag_preset_action = QAction("保存为组合", self)
            save_tag_preset_action.triggered.connect(lambda checked, idx=source_index: self.save_as_tag_preset(idx))
            menu.addAction(save_tag_preset_action)
            load_tag_preset_action = QAction("加载组合", self)
            load_tag_preset_action.triggered.connect(lambda checked, idx=source_index: self.load_tag_preset(idx))
            menu.addAction(load_tag_preset_action)
        else:
            rename = QAction("编辑名称", self)
            rename.triggered.connect(lambda checked, idx=source_index: self.rename_item(idx))
            menu.addAction(rename)
            delete = QAction("删除", self)
            delete.triggered.connect(lambda checked, idx=source_index: self.delete_item(idx))
            menu.addAction(delete)
            star = QAction("取消收藏" if item.starred else "收藏", self)
            star.triggered.connect(lambda checked, idx=source_index: self.toggle_star(idx))
            menu.addAction(star)
            menu.addSeparator()
            if item.wiki_url:
                open_wiki = QAction("打开Danbooru Wiki", self)
                open_wiki.triggered.connect(lambda checked, u=item.wiki_url: QDesktopServices.openUrl(QUrl(u)))
                menu.addAction(open_wiki)
            if item.urls:
                url_menu = QMenu("打开参考网址", self)
                for url in item.urls:
                    action = QAction(url, self)
                    action.triggered.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))
                    url_menu.addAction(action)
                menu.addMenu(url_menu)
            else:
                no_url = QAction("打开参考网址（无）", self)
                no_url.setEnabled(False)
                menu.addAction(no_url)
            edit_urls = QAction("编辑参考网址", self)
            edit_urls.triggered.connect(lambda checked, idx=source_index: self.edit_urls(idx))
            menu.addAction(edit_urls)
            view_detail = QAction("查看详情", self)
            view_detail.triggered.connect(lambda checked, idx=source_index: self.view_detail(idx))
            menu.addAction(view_detail)

        menu.exec(self.tree_view.viewport().mapToGlobal(pos))

    def view_detail(self, source_index):
        item = self.source_model.item_from_index(source_index)
        if not item.is_folder:
            self.tag_detail_requested.emit(item)

    def save_as_tag_preset(self, source_index):
        folder_item = self.source_model.item_from_index(source_index)
        if not folder_item.is_folder:
            return
        tag_ids = []
        def collect_checked(item):
            for child in item.children:
                if child.is_folder:
                    collect_checked(child)
                elif child.checked:
                    tag_ids.append(child.full_id())
        collect_checked(folder_item)
        if not tag_ids:
            QMessageBox.information(self, "无选中", "当前标签组下没有选中的标签。")
            return
        preset_name, ok = QInputDialog.getText(self, "保存组合", "组合名称：")
        if ok and preset_name.strip():
            self.tag_manager.save_tag_preset(preset_name.strip(), tag_ids)

    def load_tag_preset(self, source_index):
        folder_item = self.source_model.item_from_index(source_index)
        if not folder_item.is_folder:
            return
        presets = self.tag_manager.list_tag_presets()
        if not presets:
            QMessageBox.information(self, "无组合", "还没有保存任何组合。")
            return
        item, ok = QInputDialog.getItem(self, "加载组合", "选择组合：", presets, 0, False)
        if ok and item:
            tag_ids = self.tag_manager.load_tag_preset(item)
            if not tag_ids:
                QMessageBox.warning(self, "空组合", "该组合不含任何标签。")
                return
            matched = 0
            for fid in tag_ids:
                tag = self.tag_manager.find_item_by_full_id(fid)
                if tag and not tag.is_folder:
                    # 使用 ID 前缀判断是否属于该文件夹子树
                    if fid.startswith(folder_item.id + '/'):
                        tag.checked = True
                        matched += 1
            self.source_model.beginResetModel()
            self.source_model.endResetModel()
            self.tag_checked_changed.emit()
            QMessageBox.information(self, "加载完成", f"成功勾选 {matched} 个标签。")

    def add_root_folder(self):
        self.search_input.clear()
        name, ok = QInputDialog.getText(self, "新建标签组", "标签组名称:")
        if ok and name:
            self.source_model.append_tag(QModelIndex(), name, is_folder=True)
            self.tree_view.expandAll()

    def add_folder(self, source_index):
        self.search_input.clear()
        name, ok = QInputDialog.getText(self, "新建子标签组", "名称:")
        if ok and name:
            self.source_model.append_tag(source_index, name, is_folder=True)
            self.tree_view.expandAll()

    def add_tag(self, source_index):
        text, ok = QInputDialog.getText(self, "新建标签", "输入 “英文” 或 “中文|英文”：")
        if ok and text:
            if '|' in text:
                parts = text.split('|', 1)
                display, value = parts[0].strip(), parts[1].strip()
            else:
                display = value = text.strip()
            self.source_model.append_tag(source_index, value, is_folder=False, display_name=display)
            self.tag_checked_changed.emit()
            self.tree_view.expandAll()

    def rename_item(self, source_index):
        item = self.source_model.item_from_index(source_index)
        current = item.display_name if not item.is_folder else item.name
        text, ok = QInputDialog.getText(self, "重命名", "新名称:", text=current)
        if ok and text:
            if item.is_folder:
                self.source_model.setData(source_index, text, Qt.ItemDataRole.EditRole)
            else:
                if '|' in text:
                    parts = text.split('|', 1)
                    item.display_name = parts[0].strip()
                    item.name = parts[1].strip()
                else:
                    item.display_name = text
                    item.name = text
                self.source_model.dataChanged.emit(source_index, source_index, [Qt.ItemDataRole.DisplayRole])

    def delete_item(self, source_index):
        item = self.source_model.item_from_index(source_index)
        confirm = QMessageBox.question(self, "确认删除", f"删除 {item.name}？")
        if confirm == QMessageBox.StandardButton.Yes:
            self.source_model.remove_item(source_index)
            self.tag_checked_changed.emit()

    def toggle_single(self, source_index):
        item = self.source_model.item_from_index(source_index)
        item.single_selection = not item.single_selection
        self.source_model.dataChanged.emit(source_index, source_index)

    def toggle_lock(self, source_index):
        item = self.source_model.item_from_index(source_index)
        item.locked = not item.locked
        self.source_model.dataChanged.emit(source_index, source_index)

    def copy_role(self, source_index):
        """复制标签组及其全部子内容（基于数据库复制）"""
        item = self.source_model.item_from_index(source_index)
        if not item.is_folder:
            return
        try:
            new_id = self.tag_manager.copy_subtree(item.id)
            QMessageBox.information(self, "复制成功", f"标签组已复制为 {item.name}_copy")
            self.source_model.beginResetModel()
            self.source_model.endResetModel()
            self.tree_view.expandAll()
            self.tag_checked_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "复制失败", str(e))

    def edit_urls(self, source_index):
        item = self.source_model.item_from_index(source_index)
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

    def toggle_star(self, source_index):
        item = self.source_model.item_from_index(source_index)
        item.starred = not item.starred
        if self.tag_manager:
            self.tag_manager.toggle_star(item.id, item.starred)
        self.favorites_changed.emit()