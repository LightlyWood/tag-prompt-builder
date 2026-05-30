# ui/main_window.py
import sys
import json
import os
from PyQt6.QtWidgets import (QMainWindow, QSplitter, QVBoxLayout, QWidget,
                             QFileDialog, QMenuBar, QInputDialog, QMessageBox,
                             QTabWidget, QMenu, QDialog)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QModelIndex
from tag_prompt_builder.models.tag_model import TagTreeModel
from tag_prompt_builder.managers.tag_manager import TagManager
from tag_prompt_builder.ui.widgets.tag_tree_view import TagTreeView
from tag_prompt_builder.ui.widgets.preview_panel import PreviewPanel
from tag_prompt_builder.ui.widgets.favorites_panel import FavoritesPanel
from tag_prompt_builder.ui.widgets.tag_detail_panel import TagDetailPanel
from tag_prompt_builder.ui.dialogs.preset_manager_dialog import PresetManagerDialog
from tag_prompt_builder.models.tag_item import TagItem
from tag_prompt_builder.app_config import RECENT_FILE, PRESETS_DIR
from tag_prompt_builder.ui.widgets.layered_sort_panel import LayeredSortPanel

class MainWindow(QMainWindow):
    MAX_HISTORY = 20

    def __init__(self):
        super().__init__()
        self.setWindowTitle("提示词构建器 v0.9")
        self.resize(1200, 800)

        self.tag_manager = TagManager()
        self.tag_manager.load_default_library()

        self.model = TagTreeModel(self.tag_manager.root)

        self.tab_widget = QTabWidget()
        self.tag_tree_view = TagTreeView(self.model, tag_manager=self.tag_manager)
        self.tag_tree_view.tag_checked_changed.connect(self.refresh_all)
        self.tag_tree_view.favorites_changed.connect(self.refresh_favorites)
        self.tag_tree_view.tag_detail_requested.connect(self.show_tag_detail)

        self.favorites_panel = FavoritesPanel(self.tag_manager)
        self.favorites_panel.tag_checked_changed.connect(self.refresh_all)

        self.tab_widget.addTab(self.tag_tree_view, "标签库")
        self.tab_widget.addTab(self.favorites_panel, "收藏")

        self.sort_panel = LayeredSortPanel()
        self.sort_panel.set_tag_manager(self.tag_manager)
        self.sort_panel.order_changed.connect(self.refresh_preview)

        self.preview_panel = PreviewPanel()
        self.preview_panel.clipboard_copied.connect(self.on_clipboard_copied)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.sort_panel, 2)
        right_layout.addWidget(self.preview_panel, 1)

        self.detail_panel = TagDetailPanel()
        right_layout.addWidget(self.detail_panel, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tab_widget)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self.recent_list = self.load_recent()
        self.init_menu()
        self.refresh_favorites()
        self.update_recent_menu()

    # ---------- 标签详情 ----------
    def show_tag_detail(self, tag: TagItem):
        self.detail_panel.show_tag_detail(tag)

    # ---------- 同步与预览 ----------
    def refresh_all(self):
        self.sort_panel.sync_from_checked(self.tag_manager.root)
        self.refresh_preview()

    def refresh_preview(self):
        display, output = self.build_prompt_from_sort()
        self.preview_panel.update_preview(display, output)

    def build_prompt_from_sort(self):
        display_parts = []
        output_parts = []
        def traverse(node):
            if node.is_random_slot:
                tags = self.sort_panel.perform_random_slot(node)
                for tag in tags:
                    display_parts.append(tag.display_name)
                    output_parts.append(tag.name)
            elif not node.is_folder:
                tag = self.tag_manager.find_item_by_full_id(node.full_id)
                if tag and not tag.is_folder:
                    display_parts.append(tag.display_name)
                    output_parts.append(tag.name)
                else:
                    display_parts.append(node.display_name)
                    output_parts.append(node.display_name)
            else:
                for child in node.children:
                    traverse(child)

        for top in self.sort_panel.sort_root.children:
            traverse(top)
        return ', '.join(display_parts), ', '.join(output_parts)

    def on_clipboard_copied(self, text: str):
        text = text.strip()
        if not text:
            return
        if text in self.recent_list:
            self.recent_list.remove(text)
        self.recent_list.insert(0, text)
        if len(self.recent_list) > self.MAX_HISTORY:
            self.recent_list = self.recent_list[:self.MAX_HISTORY]
        self.save_recent()
        self.update_recent_menu()

    # ---------- 预设管理 ----------
    def apply_tag_preset(self, preset_name: str):
        preset = self.tag_manager.load_folder_preset(preset_name)
        if not preset:
            QMessageBox.warning(self, "预设不存在", "找不到该预设。")
            return
        tag_ids = preset.get('selected', [])
        if not tag_ids:
            QMessageBox.warning(self, "空预设", "该预设不含任何标签。")
            return
        def reset_checked(item):
            for child in item.children:
                child.checked = False
                if child.is_folder:
                    reset_checked(child)
        reset_checked(self.tag_manager.root)
        matched = 0
        for fid in tag_ids:
            tag = self.tag_manager.find_item_by_full_id(fid)
            if tag and not tag.is_folder:
                tag.checked = True
                matched += 1
        self.model.dataChanged.emit(QModelIndex(), QModelIndex())
        self.refresh_all()
        QMessageBox.information(self, "加载完成", f"成功勾选 {matched}/{len(tag_ids)} 个标签。")

    def save_folder_preset(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "保存预设", PRESETS_DIR, "JSON (*.json)")
        if file_name:
            sort_structure = self.sort_panel.get_sort_structure()
            selected_ids = []
            def collect(item):
                if not item.is_folder:
                    if item.checked:
                        selected_ids.append(item.full_id())
                else:
                    for child in item.children:
                        collect(child)
            collect(self.tag_manager.root)
            preset = {
                'type': 'folder_preset',
                'selected': selected_ids,
                'sort_structure': sort_structure
            }
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(preset, f, ensure_ascii=False, indent=2)
            except IOError:
                QMessageBox.warning(self, "保存失败", "无法写入文件。")

    def load_folder_preset(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "加载预设", PRESETS_DIR, "JSON (*.json)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    preset = json.load(f)
            except (json.JSONDecodeError, IOError):
                QMessageBox.warning(self, "加载失败", "无效的预设文件。")
                return
            if preset:
                def reset(item):
                    for c in item.children:
                        c.checked = False
                        if c.is_folder:
                            reset(c)
                reset(self.tag_manager.root)
                for fid in preset.get('selected', []):
                    tag = self.tag_manager.find_item_by_full_id(fid)
                    if tag and not tag.is_folder:
                        tag.checked = True
                if 'sort_structure' in preset:
                    self.sort_panel.restore_sort_structure(preset['sort_structure'], self.tag_manager)
                else:
                    self.sort_panel.sync_from_checked(self.tag_manager.root)
                self.model.dataChanged.emit(QModelIndex(), QModelIndex())
                self.refresh_preview()

    def manage_presets(self):
        dialog = PresetManagerDialog(self.tag_manager, self)
        dialog.exec()

    def import_from_prompt(self):
        text, ok = QInputDialog.getMultiLineText(self, "导入提示词",
                                                  "粘贴以逗号分隔的提示词：")
        if not ok or not text.strip():
            return
        raw_tags = [t.strip() for t in text.split(',') if t.strip()]
        if not raw_tags:
            return
        self.apply_tag_list(raw_tags)
        if QMessageBox.question(self, "保存预设", "是否保存为文件夹预设？",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.save_folder_preset()

    def apply_tag_list(self, raw_tags: list):
        name_map, display_map = {}, {}
        def collect(item):
            if not item.is_folder:
                name_map[item.name.lower()] = item
                display_map[item.display_name.lower()] = item
            else:
                for c in item.children:
                    collect(c)
        collect(self.tag_manager.root)
        matched, unmatched = [], []
        for tag in raw_tags:
            l = tag.lower()
            if l in name_map:
                matched.append(name_map[l])
            elif l in display_map:
                matched.append(display_map[l])
            else:
                unmatched.append(tag)
        if unmatched:
            QMessageBox.information(self, "未匹配标签", f"以下标签未找到：{', '.join(unmatched)}")
        if not matched:
            return
        def reset(item):
            for c in item.children:
                c.checked = False
                if c.is_folder:
                    reset(c)
        reset(self.tag_manager.root)
        for t in matched:
            t.checked = True
        self.model.dataChanged.emit(QModelIndex(), QModelIndex())
        self.refresh_all()

    # ---------- 最近使用 ----------
    def load_recent(self):
        if os.path.exists(RECENT_FILE):
            try:
                with open(RECENT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data[:self.MAX_HISTORY] if isinstance(data, list) else []
            except:
                pass
        return []

    def save_recent(self):
        try:
            with open(RECENT_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.recent_list, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def update_recent_menu(self):
        self.recent_menu.clear()
        if not self.recent_list:
            a = QAction("（无记录）", self)
            a.setEnabled(False)
            self.recent_menu.addAction(a)
            return
        for t in self.recent_list:
            d = t if len(t) <= 50 else t[:47] + '...'
            act = QAction(d, self)
            act.setToolTip(t)
            act.triggered.connect(lambda checked, text=t: self.restore_recent(text))
            self.recent_menu.addAction(act)
        self.recent_menu.addSeparator()
        clear_act = QAction("清空历史", self)
        clear_act.triggered.connect(self.clear_recent)
        self.recent_menu.addAction(clear_act)

    def clear_recent(self):
        self.recent_list.clear()
        self.save_recent()
        self.update_recent_menu()

    def restore_recent(self, text: str):
        raw_tags = [t.strip() for t in text.split(',') if t.strip()]
        if raw_tags:
            self.apply_tag_list(raw_tags)

    def manage_random_pools(self):
        QMessageBox.information(self, "提示", "随机池管理界面尚未实现。")

    # ---------- 菜单栏 ----------
    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        file_menu.addAction(QAction("从提示词导入", self, triggered=self.import_from_prompt))
        file_menu.addSeparator()
        file_menu.addAction(QAction("保存文件夹预设", self, triggered=self.save_folder_preset))
        file_menu.addAction(QAction("加载文件夹预设", self, triggered=self.load_folder_preset))
        file_menu.addAction(QAction("管理词组预设", self, triggered=self.manage_presets))

        manage_pools_action = QAction("管理随机池", self)
        manage_pools_action.triggered.connect(self.manage_random_pools)
        file_menu.addAction(manage_pools_action)

        self.recent_menu = QMenu("最近使用", self)
        menubar.addMenu(self.recent_menu)

    def refresh_favorites(self):
        self.favorites_panel.refresh()